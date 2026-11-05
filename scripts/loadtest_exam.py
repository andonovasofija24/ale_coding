#!/usr/bin/env python3
"""
Load test: N students take an exam at the same time.

Creates a throw-away course with one C task and an exam, registers N students, then every student — all at
once — logs in, opens the exam, starts it, opens the task and submits (2 submissions each: a wrong one, then
a correct one). Prints how long each step took (median / 95th percentile / max) and every error.

Usage (the stack must be running):
    pip install httpx
    python scripts/loadtest_exam.py --base http://localhost:8000 --students 200 \
        --admin-email admin@example.com --admin-password <FIRST_ADMIN_PASSWORD>

On a server behind nginx use --base https://ale.example.mk/api
The test data stays in the database (course "LOADTEST-xxxx"); archive or delete the course afterwards.
"""
import argparse
import asyncio
import random
import statistics
import time
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

import httpx

GOOD = '#include <stdio.h>\nint main(void){int n,x;long s=0;scanf("%d",&n);for(int i=0;i<n;i++){scanf("%d",&x);if(x%2==0)s+=x;}printf("%ld\\n",s);return 0;}'
BAD = GOOD.replace("x%2==0", "x%2==1")


def pct(values, p):
    if not values:
        return 0.0
    values = sorted(values)
    k = min(len(values) - 1, max(0, round(p / 100 * (len(values) - 1))))
    return values[k]


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8000")
    ap.add_argument("--students", type=int, default=200)
    ap.add_argument("--admin-email", default="admin@example.com")
    ap.add_argument("--admin-password", required=True)
    ap.add_argument("--ramp", type=float, default=5.0, help="seconds over which students arrive (0 = all at once)")
    ap.add_argument("--timeout", type=float, default=300.0)
    args = ap.parse_args()

    times: dict[str, list[float]] = defaultdict(list)
    errors: Counter = Counter()
    run_id = uuid.uuid4().hex[:4].upper()
    limits = httpx.Limits(max_connections=args.students + 20, max_keepalive_connections=args.students + 20)

    async with httpx.AsyncClient(base_url=args.base, timeout=args.timeout, limits=limits) as c:
        async def timed(step, method, url, **kw):
            t = time.perf_counter()
            try:
                r = await c.request(method, url, **kw)
            except httpx.HTTPError as e:
                times[step].append(time.perf_counter() - t)
                errors[f"{step}: {type(e).__name__}"] += 1
                return None
            times[step].append(time.perf_counter() - t)
            if r.status_code >= 400:
                detail = ""
                try:
                    detail = r.json().get("detail", "")
                except Exception:
                    pass
                errors[f"{step}: {r.status_code} {detail}"[:120]] += 1
            return r

        # --- setup ------------------------------------------------------------------------------------------
        r = await c.post("/auth/login", json={"email": args.admin_email, "password": args.admin_password})
        r.raise_for_status()
        A = {"Authorization": "Bearer " + r.json()["access_token"]}
        r = await c.post("/admin/tasks", headers=A, json={
            "title": f"Loadtest {run_id}", "description": "sum of even numbers", "language": "c", "is_public": False,
            "starter_code": "", "model_solution": GOOD, "test_cases": [
                {"type": "stdin_stdout", "stdin": "5\n1 2 3 4 5\n", "expected_output": "6", "order": 0},
                {"type": "stdin_stdout", "stdin": "3\n-2 7 10\n", "expected_output": "8", "order": 1},
                {"type": "stdin_stdout", "stdin": "4\n1 3 5 7\n", "expected_output": "0", "is_hidden": True, "order": 2}]})
        r.raise_for_status()
        task_id = r.json()["id"]
        r = await c.post("/courses", headers=A, json={"code": f"LOADTEST-{run_id}", "name": f"Load test {run_id}"})
        r.raise_for_status()
        course_id = r.json()["id"]
        now = datetime.now(timezone.utc)
        r = await c.post(f"/courses/{course_id}/assignments", headers=A, json={
            "title": "Load test exam", "kind": "exam", "published": True, "duration_minutes": 60, "ai_mode": "off",
            "results_visibility": "summary", "opens_at": (now - timedelta(minutes=1)).isoformat(),
            "due_at": (now + timedelta(hours=2)).isoformat(), "tasks": [{"task_id": task_id, "points": 10}]})
        r.raise_for_status()
        exam_id = r.json()["id"]

        emails = [f"lt{run_id.lower()}{i:04d}@loadtest.ale-platform.mk" for i in range(args.students)]
        print(f"Registering {args.students} students…", flush=True)
        t0 = time.perf_counter()
        sem = asyncio.Semaphore(20)

        async def register(e):
            async with sem:
                await timed("register", "POST", "/auth/register", json={"email": e, "password": "pw123456", "name": e[:12]})
        await asyncio.gather(*(register(e) for e in emails))
        print(f"  done in {time.perf_counter() - t0:.1f}s", flush=True)
        for i in range(0, len(emails), 200):
            (await c.post(f"/courses/{course_id}/members", headers=A, json={"emails": emails[i:i + 200]})).raise_for_status()

        # --- the exam --------------------------------------------------------------------------------------
        print(f"Exam: {args.students} students, arriving over {args.ramp:.0f}s…", flush=True)
        times.clear()
        done = Counter()

        async def student(i, e):
            await asyncio.sleep(random.uniform(0, args.ramp))
            r = await timed("1 login", "POST", "/auth/login", json={"email": e, "password": "pw123456"})
            if r is None or r.status_code != 200:
                return
            H = {"Authorization": "Bearer " + r.json()["access_token"]}
            await timed("2 open exam", "GET", f"/assignments/{exam_id}", headers=H)
            r = await timed("3 start", "POST", f"/assignments/{exam_id}/start", headers=H)
            if r is None or r.status_code != 200:
                return
            await timed("4 open task", "GET", f"/tasks/{task_id}", headers=H)
            for code in (BAD, GOOD):
                await asyncio.sleep(random.uniform(0, 2))
                r = await timed("5 submit (incl. waiting for the result)", "POST",
                                f"/assignments/{exam_id}/tasks/{task_id}/submit", headers=H, json={"code": code})
                if r is not None and r.status_code == 200:
                    body = r.json()
                    sid = body.get("submission_id")
                    t = time.perf_counter()
                    while body.get("status") in ("pending", "running") and sid:  # queued: wait for the result like the browser does
                        await asyncio.sleep(1.5)
                        try:
                            rr = await c.get(f"/submissions/{sid}/result", headers=H)
                        except httpx.TransportError:  # a reused connection the server had closed: just ask again
                            continue
                        if rr.status_code != 200:
                            errors[f"6 result: {rr.status_code}"] += 1
                            break
                        body = rr.json()
                    if sid and body.get("status") not in ("pending", "running"):
                        times["6 result ready after submit"].append(time.perf_counter() - t)
                    done[body.get("status", "done")] += 1

        t0 = time.perf_counter()
        await asyncio.gather(*(student(i, e) for i, e in enumerate(emails)))
        wall = time.perf_counter() - t0

        # --- report ----------------------------------------------------------------------------------------
        print(f"\nAll students finished in {wall:.1f}s\n")
        print(f"{'step':<42}{'count':>7}{'median':>9}{'p95':>9}{'max':>9}")
        for step in sorted(times):
            v = times[step]
            print(f"{step:<42}{len(v):>7}{statistics.median(v):>8.2f}s{pct(v, 95):>8.2f}s{max(v):>8.2f}s")
        print(f"\nsubmissions finished: {sum(done.values())} / {args.students * 2}  {dict(done)}")
        if errors:
            print("\nERRORS:")
            for k, n in errors.most_common():
                print(f"  {n:>5} × {k}")
        else:
            print("\nNo errors.")
        print(f"\nTest course: LOADTEST-{run_id} (id {course_id}) — archive or delete it when done.")


if __name__ == "__main__":
    asyncio.run(main())
