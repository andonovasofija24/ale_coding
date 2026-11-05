"""
Course grading scheme and each student's standing.

The scheme (course.grading):
  weights     % of the final grade per category of assignment: labs, homework, k1, k2, exam
  thresholds  the % needed for grades 6, 7, 8, 9, 10 (default 50 / 60 / 70 / 80 / 90)
  rules       the course's rules, each switched on or off by the teacher:
                max_missed_labs        at most N labs missed (absent, or nothing handed in and not graded)
                min_labs_signature     at least X % of the lab points for the signature
                min_colloquium         at least X % on each colloquium to pass it
                k1_exempt_qualifying   at least X % on colloquium 1 = exempt from its qualifying part
                signature_for_exam     no signature, no exam

For each student: points per category, total so far, signature, exam eligibility, exemption, passed colloquia,
a proposed grade — and for every "no" the reason, so the teacher (and the student) can see why.
Only assignments that count already are used: published and closed (or graded and published).

The estimated grade ("if you keep going like this"): the same weights and thresholds, but for a part that has no
points yet it takes what the student has practised — the practice assignments made for that colloquium / the exam,
the labs still open, and their own practice in the subject (tasks they finished out of those they started).
"""
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Assignment, Attendance, Course, Submission, TaskGrade
from app.models.session import Session
from app.models.task import Task
from app.models.user import UserProfile

CATEGORIES = ("labs", "homework", "k1", "k2", "exam")
RULE_TYPES = ("max_missed_labs", "min_labs_signature", "min_colloquium", "k1_exempt_qualifying", "signature_for_exam")
DEFAULT = {
    "weights": {"labs": 20, "homework": 0, "k1": 40, "k2": 40, "exam": 0},
    "thresholds": [50, 60, 70, 80, 90],
    "rules": [
        {"type": "max_missed_labs", "enabled": False, "value": 1},
        {"type": "min_labs_signature", "enabled": False, "value": 50},
        {"type": "min_colloquium", "enabled": False, "value": 50},
        {"type": "k1_exempt_qualifying", "enabled": False, "value": 80},
        {"type": "signature_for_exam", "enabled": False, "value": None},
    ],
}


def category_of(a: Assignment) -> str:
    if a.category:
        return a.category
    return {"lab": "labs", "homework": "homework", "exam": "exam"}.get(a.kind, "none")


def scheme(course: Course) -> dict:
    """The course's scheme with defaults filled in (every rule type present, in a fixed order)."""
    g = course.grading or {}
    weights = {**DEFAULT["weights"], **(g.get("weights") or {})}
    thresholds = g.get("thresholds") or DEFAULT["thresholds"]
    saved = {r["type"]: r for r in (g.get("rules") or []) if r.get("type") in RULE_TYPES}
    rules = [{**d, **saved.get(d["type"], {})} for d in DEFAULT["rules"]]
    return {"weights": weights, "thresholds": thresholds, "rules": rules}


def _rule(sch: dict, t: str):
    r = next(x for x in sch["rules"] if x["type"] == t)
    return r if r.get("enabled") else None


def grade_for(pct: float, thresholds: list) -> int:
    g = 5
    for i, th in enumerate(thresholds):
        if pct >= th:
            g = 6 + i
    return g


async def compute(db: AsyncSession, course: Course, gradebook: dict, now: datetime | None = None) -> dict:
    """`gradebook` = assignments.gradebook_data(course) (points per student and assignment)."""
    now = now or datetime.utcnow()
    sch = scheme(course)
    rows = {a.id: a for a in (await db.execute(select(Assignment).where(Assignment.course_id == course.id))).scalars()}
    info = {}
    for ga in gradebook["assignments"]:
        a = rows.get(uuid.UUID(ga["id"]))
        if a is None:
            continue
        closed = bool(a.due_at and a.due_at <= now)
        info[ga["id"]] = {"cat": category_of(a), "max": ga["max_points"], "counts": a.published and (closed or a.grades_published),
                          "closed": a.published and closed, "prep": a.practice_for if a.published else None,
                          "open": a.published and not closed and not a.grades_published}
    aids = list(rows)
    present = {(str(x.assignment_id), str(x.user_id)): x.status for x in (await db.execute(
        select(Attendance).where(Attendance.assignment_id.in_(aids)))).scalars()} if aids else {}
    handed = {(str(a), str(u)) for a, u in (await db.execute(select(Submission.assignment_id, Submission.user_id).where(
        Submission.assignment_id.in_(aids)).group_by(Submission.assignment_id, Submission.user_id))).all()} if aids else set()
    graded = {(str(a), str(u)) for a, u in (await db.execute(select(TaskGrade.assignment_id, TaskGrade.user_id).where(
        TaskGrade.assignment_id.in_(aids)).group_by(TaskGrade.assignment_id, TaskGrade.user_id))).all()} if aids else set()
    indexes = dict((await db.execute(select(UserProfile.user_id, UserProfile.index_number))).all())

    r_missed, r_labs = _rule(sch, "max_missed_labs"), _rule(sch, "min_labs_signature")
    r_coll, r_exempt, r_sig_exam = _rule(sch, "min_colloquium"), _rule(sch, "k1_exempt_qualifying"), _rule(sch, "signature_for_exam")
    weights = sch["weights"]
    own = await _own_practice(db, course, [uuid.UUID(x["user_id"]) for x in gradebook["students"]])
    out = []
    for s in gradebook["students"]:
        uid = s["user_id"]
        cats = {c: {"got": 0.0, "max": 0.0} for c in CATEGORIES}
        missed = 0
        for aid, cell in s["scores"].items():
            i = info.get(aid)
            if not i or not cell["applies"]:
                continue
            if i["cat"] in cats and i["counts"]:
                cats[i["cat"]]["got"] += cell["score"] or 0
                cats[i["cat"]]["max"] += i["max"]
            if i["cat"] == "labs" and i["closed"]:
                st = present.get((aid, uid))
                if st == "absent" or (st is None and (aid, uid) not in handed and (aid, uid) not in graded):
                    missed += 1
        pct = {c: (round(100 * v["got"] / v["max"], 1) if v["max"] else None) for c, v in cats.items()}
        total = round(sum(weights.get(c, 0) * (pct[c] or 0) / 100 for c in CATEGORIES), 1)
        reasons = []
        signature = None
        if r_missed or r_labs:
            signature = True
            if r_missed and missed > int(r_missed["value"] or 0):
                signature = False
                reasons.append({"key": "missed_labs", "n": missed, "max": int(r_missed["value"] or 0)})
            if r_labs and (pct["labs"] or 0) < float(r_labs["value"] or 0):
                signature = False
                reasons.append({"key": "labs_low", "got": pct["labs"] or 0, "need": r_labs["value"]})
        eligible = True
        if r_sig_exam and signature is False:
            eligible = False
            reasons.append({"key": "no_signature_exam"})
        colloquia = {}
        for k in ("k1", "k2"):
            if cats[k]["max"]:
                passed = None if not r_coll else pct[k] >= float(r_coll["value"] or 0)
                colloquia[k] = {"pct": pct[k], "passed": passed}
                if passed is False:
                    reasons.append({"key": "k_failed", "k": k, "got": pct[k], "need": r_coll["value"]})
        exempt = None
        if r_exempt and cats["k1"]["max"]:
            exempt = pct["k1"] >= float(r_exempt["value"] or 0)
            if not exempt:
                reasons.append({"key": "not_exempt", "got": pct["k1"], "need": r_exempt["value"]})
        weighted = [c for c in CATEGORIES if weights.get(c, 0) > 0]
        complete = all(pct[c] is not None for c in weighted) and bool(weighted)
        grade = None
        if not complete:
            reasons.append({"key": "incomplete"})
        elif signature is False or any(v["passed"] is False for v in colloquia.values()):
            pass  # no signature, or the colloquium path is closed: the reason is already listed
        else:
            grade = grade_for(total, sch["thresholds"])
        out.append({"user_id": uid, "name": s["name"], "email": s["email"], "group": s["group"],
                    "index": indexes.get(uuid.UUID(uid), "") or "",
                    "categories": {c: {**cats[c], "pct": pct[c]} for c in CATEGORIES}, "total": total,
                    "missed_labs": missed, "signature": signature, "eligible_exam": eligible, "exempt": exempt,
                    "colloquia": colloquia, "grade": grade, "reasons": reasons,
                    "estimate": _estimate(s, info, pct, weights, sch["thresholds"], own.get(uid)),
                    # the professor's final grade (the proposed one above is only a suggestion)
                    "final_grade": ((course.final_grades or {}).get(uid) or {}).get("grade")})
    return {"scheme": sch, "students": out,
            "assignments": [{"id": aid, "category": i["cat"], "counts": i["counts"]} for aid, i in info.items()]}


async def _own_practice(db: AsyncSession, course: Course, user_ids: list) -> dict:
    """{user_id: % of the subject's tasks finished out of those started} — the student's own practice (also with
    their own AI key) in the course's subject."""
    if not course.subject_id or not user_ids:
        return {}
    started: dict = {}
    done: dict = {}
    for uid, tid, status in (await db.execute(select(Session.user_id, Session.task_id, Session.status).join(
            Task, Task.id == Session.task_id).where(Task.subject_id == course.subject_id, Session.user_id.in_(user_ids)))).all():
        started.setdefault(str(uid), set()).add(tid)
        if status == "completed":
            done.setdefault(str(uid), set()).add(tid)
    return {u: round(100 * len(done.get(u, ())) / len(t), 1) for u, t in started.items() if t}


def _estimate(s: dict, info: dict, pct: dict, weights: dict, thresholds: list, own: float | None) -> dict:
    """Per weighted part: the real % if it has points ("real"), else the practice made for it ("prep" — practice
    assignments for that colloquium / the exam, or labs / homework still open: "open"), else the student's own
    practice in the subject ("own"). With every weighted part known: the grade it would be."""
    parts = {}
    for c in CATEGORIES:
        if not weights.get(c):
            continue
        if pct[c] is not None:
            parts[c] = {"pct": pct[c], "source": "real"}
            continue
        got = mx = 0.0
        src = None
        for aid, cell in s["scores"].items():
            i = info.get(aid)
            if not i or not cell["applies"] or not i["max"]:
                continue
            if i["prep"] == c or (i["open"] and i["cat"] == c):
                got += cell["score"] or 0
                mx += i["max"]
                src = "prep" if i["prep"] == c or src == "prep" else "open"
        tried = mx and any(info.get(a, {}).get("prep") == c or (info.get(a, {}).get("open") and info.get(a, {}).get("cat") == c)
                           for a, cell in s["scores"].items() if cell["score"] is not None)
        if tried:
            parts[c] = {"pct": round(100 * got / mx, 1), "source": src}
        elif own is not None:
            parts[c] = {"pct": own, "source": "own"}
        else:
            parts[c] = {"pct": None, "source": None}
    known = parts and all(v["pct"] is not None for v in parts.values())
    total = round(sum(weights.get(c, 0) * (v["pct"] or 0) / 100 for c, v in parts.items()), 1) if known else None
    return {"grade": grade_for(total, thresholds) if known else None, "total": total, "parts": parts, "own": own}


def reason_text(r: dict, lang: str = "mk") -> str:
    mk = {
        "missed_labs": "пропуштени {n} лабораториски (дозволено {max})",
        "labs_low": "{got}% од лабораториските (потребно {need}%)",
        "no_signature_exam": "нема потпис — нема право на испит",
        "k_failed": "{K}: {got}% (потребно {need}%)",
        "not_exempt": "К1: {got}% — не е ослободен од квалификацискиот дел (потребно {need}%)",
        "incomplete": "уште нема поени во сите делови",
    }
    en = {
        "missed_labs": "{n} labs missed ({max} allowed)",
        "labs_low": "{got}% of the lab points ({need}% needed)",
        "no_signature_exam": "no signature — may not take the exam",
        "k_failed": "{K}: {got}% ({need}% needed)",
        "not_exempt": "C1: {got}% — not exempt from the qualifying part ({need}% needed)",
        "incomplete": "not all parts have points yet",
    }
    k = {"k1": "К1", "k2": "К2"} if lang == "mk" else {"k1": "C1", "k2": "C2"}
    return (mk if lang == "mk" else en)[r["key"]].format(K=k.get(r.get("k", ""), ""), **{x: v for x, v in r.items() if x != "key"})


def validate(body: dict) -> dict:
    """Clean a scheme sent by the teacher (raises ValueError with a readable message)."""
    w = body.get("weights") or {}
    weights = {c: float(w.get(c, 0) or 0) for c in CATEGORIES}
    if any(v < 0 or v > 100 for v in weights.values()):
        raise ValueError("Weights must be between 0 and 100")
    if round(sum(weights.values()), 6) != 100:
        raise ValueError("The weights must add up to 100%")
    th = [float(x) for x in (body.get("thresholds") or DEFAULT["thresholds"])]
    if len(th) != 5 or any(not 0 < x <= 100 for x in th) or th != sorted(th) or len(set(th)) != 5:
        raise ValueError("Thresholds: five increasing numbers between 0 and 100")
    rules = []
    for r in body.get("rules") or []:
        if r.get("type") not in RULE_TYPES:
            continue
        v = r.get("value")
        if r["type"] != "signature_for_exam":
            v = float(v or 0)
            if v < 0 or (r["type"] != "max_missed_labs" and v > 100) or (r["type"] == "max_missed_labs" and v > 10):
                raise ValueError("Rule value out of range")
            if r["type"] == "max_missed_labs":
                v = int(v)
        rules.append({"type": r["type"], "enabled": bool(r.get("enabled")), "value": v})
    return {"weights": weights, "thresholds": th, "rules": rules}

