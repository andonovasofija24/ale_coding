"""
HTML / CSS / JavaScript tasks ("web").

The student's work is several files kept in ONE text (so saving, submitting, plagiarism checks and code views work
like for every other language). Files are separated by marker lines:

    <!-- file: index.html -->
    <!doctype html> ...
    <!-- file: style.css -->
    h1 { color: navy; }
    <!-- file: script.js -->
    document.querySelector('button').onclick = ...

Text before the first marker (or a text without markers) is index.html.

Tests run in a real browser (headless Chromium via Playwright), every test in a fresh page. A test is JavaScript
that runs in the loaded page and prints with `print(...)`; its output is compared with the expected output, like
the "code_sample" tests of the other languages. Helpers available in a test:

    $(sel)  $$(sel)  exists(sel)  count(sel)  text(sel)  attr(sel, name)  css(sel, prop)  hex(sel, prop)
    visible(sel)  rect(sel)  click(sel)  type(sel, value)  sleep(ms)

Directives (comment lines at the top of the test):
    // viewport: 375x667      the page size for this test (default 1280x800)
    // visual: 90             visual test: a screenshot of the student's page is compared with the teacher's
                              model solution; passes with at least 90 % similarity (the test body is ignored)

The browser runs as the slot user inside the sandbox (app/webrun.py), with no network: only the student's own
files are loaded.
"""
import json
import os
import re
import sys

from app import sandbox
from app.schemas import TestCasePayload, TestResult

MARKER = re.compile(r"^[ \t]*<!--\s*file:\s*([A-Za-z0-9_.\-]+)\s*-->[ \t]*$", re.M)
ALLOWED = re.compile(r"^[A-Za-z0-9_\-]{1,40}\.(html|css|js)$")
MAX_FILES = 10
APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BROWSERS = os.getenv("PLAYWRIGHT_BROWSERS_PATH", "")
WEB_PYTHON = os.getenv("WEB_PYTHON", sys.executable)  # the Python that has Playwright

WEB_LIMITS = sandbox.Limits(cpu_seconds=90, memory_bytes=None, file_bytes=64 * sandbox.MB, processes=512, open_files=2048)


def split_bundle(code: str) -> dict[str, str]:
    """{file name: content}. Unknown names are ignored; index.html always exists."""
    files: dict[str, str] = {}
    parts = MARKER.split(code)
    head = parts[0]
    if head.strip() or len(parts) == 1:
        files["index.html"] = head.strip("\n")
    for i in range(1, len(parts), 2):
        name, body = parts[i], parts[i + 1] if i + 1 < len(parts) else ""
        if ALLOWED.match(name) and len(files) < MAX_FILES:
            files[name] = body.strip("\n") + "\n"
    if "index.html" not in files:
        html = next((n for n in files if n.endswith(".html")), None)
        files["index.html"] = files.get(html, "") if html else ""
    return files


def _write_files(d: str, files: dict[str, str], uid: int | None) -> None:
    os.makedirs(d, exist_ok=True)
    for name, body in files.items():
        p = os.path.join(d, name)
        with open(p, "w", encoding="utf-8") as f:
            f.write(body)
        if uid is not None:
            os.chown(p, uid, uid)
    if uid is not None:
        os.chown(d, uid, uid)


def available() -> bool:
    import importlib.util
    return importlib.util.find_spec("playwright") is not None


def run_web(student_code: str, test_cases: list[TestCasePayload], reference_code: str = "") -> list[TestResult]:
    with sandbox.slot() as slot:
        uid = slot.uid if sandbox.SWITCH_USER else None
        work = slot.new_dir("web")
        _write_files(os.path.join(work, "student"), split_bundle(student_code), uid)
        if reference_code.strip():
            _write_files(os.path.join(work, "reference"), split_bundle(reference_code), uid)
        job = os.path.join(work, "job.json")
        with open(job, "w", encoding="utf-8") as f:
            json.dump({"dir": work, "has_reference": bool(reference_code.strip()),
                       "tests": [{"code": tc.test_code, "expected": tc.expected_output} for tc in test_cases]}, f)
        if uid is not None:
            os.chown(job, uid, uid)
        env = {"PYTHONPATH": APP_ROOT, "PLAYWRIGHT_BROWSERS_PATH": BROWSERS} if BROWSERS else {"PYTHONPATH": APP_ROOT}
        # (not -I: the runner's own package comes from PYTHONPATH; the work dir holds only .html/.css/.js files)
        p = sandbox.run([WEB_PYTHON, "-B", "-m", "app.webrun", job],
                        slot=slot, cwd=work, limits=WEB_LIMITS, timeout=20 + 8 * len(test_cases), env_extra=env)
        try:
            rows = json.loads(p.stdout.strip().splitlines()[-1]) if p.stdout.strip() else None
        except (ValueError, IndexError):
            rows = None
        if not isinstance(rows, list) or len(rows) != len(test_cases):
            why = "TIME LIMIT EXCEEDED" if p.timed_out else \
                "RUNTIME ERROR\nThe browser could not test the page." + (f"\n{p.stderr.strip()[-1500:]}" if p.stderr.strip() else "")
            return [TestResult(passed=False, actual_output="", expected_output=tc.expected_output, error=why) for tc in test_cases]
        return [TestResult(**r) for r in rows]
