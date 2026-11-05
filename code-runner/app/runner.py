"""
Compile and run student code against test cases. Languages and their test semantics: app/languages.py.

Everything (compiling included) runs inside the sandbox (app/sandbox.py): an unprivileged per-submission user,
resource limits, and a queue that bounds how many submissions run at once.

Each test returns passed/actual_output/error. Errors start with "COMPILE ERROR", "TIME LIMIT EXCEEDED"
or "RUNTIME ERROR" so the backend can classify them.
"""
import hashlib

from app import sandbox
from app.languages import Build, builder
from app.schemas import TestCasePayload, TestResult

COMPILE_TIMEOUT = 30  # seconds, wall clock (javac is slow to start)
RUN_TIMEOUT = 5       # seconds, wall clock per test
SHOWN_OUTPUT = 10_000  # characters of a program's output sent back for display
_ERROR_PREFIXES = ("COMPILE ERROR", "RUNTIME ERROR", "TIME LIMIT EXCEEDED")


def _normalize(output: str) -> str:
    """Strip trailing whitespace per line and trailing blank lines before comparing."""
    return "\n".join(line.rstrip() for line in output.splitlines()).strip()


def _fail(tc: TestCasePayload, error: str, actual: str = "") -> TestResult:
    return TestResult(passed=False, actual_output=actual[:SHOWN_OUTPUT], expected_output=tc.expected_output, error=error)


def run_all(student_code: str, test_cases: list[TestCasePayload], language: str = "cpp",
            reference_code: str = "") -> list[TestResult]:
    """Run all tests of one submission inside one sandbox slot (waits in the queue for a free slot).

    Each distinct program is compiled once: all stdin/stdout tests share one build;
    every code_sample test is its own program (student code + that test's code).
    """
    if language == "web":  # HTML/CSS/JS: tested in a browser (app/web.py)
        from app import web
        return web.run_web(student_code, test_cases, reference_code)
    build = builder(language)
    with sandbox.slot() as slot:
        builds: dict[str, tuple[str, Build, str | None]] = {}  # key -> (dir, build, compile_error)
        results = []
        for tc in test_cases:
            key = hashlib.sha1(((tc.test_code if tc.type == "code_sample" else "") + "\0" + tc.type).encode()).hexdigest()
            if key not in builds:
                d = slot.new_dir(f"b{len(builds)}")
                b = build(student_code, tc, d)
                error = None
                if b.compile:
                    p = sandbox.run(b.compile, slot=slot, cwd=d, timeout=b.compile_timeout or COMPILE_TIMEOUT,
                                    limits=sandbox.JVM_COMPILE_LIMITS if b.vm else sandbox.COMPILE_LIMITS,
                                    env_extra=b.env)
                    if p.timed_out:
                        error = "COMPILE TIMEOUT"
                    elif p.returncode != 0:
                        msg = (p.stderr or p.stdout or f"exit code {p.returncode}").strip().replace(d + "/", "")
                        error = f"COMPILE ERROR\n{msg[-4000:]}"
                builds[key] = (d, b, error)
            d, b, error = builds[key]
            if error:
                results.append(_fail(tc, error))
                continue
            if b.before:
                try:
                    b.before()  # e.g. create the test's own PostgreSQL database
                except Exception as e:
                    results.append(_fail(tc, f"RUNTIME ERROR\nCould not prepare the test: {e}"))
                    continue
            try:
                results.append(_run_one(tc, slot, d, b))
            finally:
                if b.after:
                    b.after()
        return results


def _run_one(tc: TestCasePayload, slot: "sandbox.Slot", d: str, b: Build) -> TestResult:
    p = sandbox.run(b.run, slot=slot, cwd=d, stdin=tc.stdin, timeout=RUN_TIMEOUT,
                    limits=sandbox.JVM_RUN_LIMITS if b.vm else sandbox.RUN_LIMITS, env_extra=b.env)
    if p.timed_out:
        return _fail(tc, "TIME LIMIT EXCEEDED", p.stdout)
    if p.output_limit:
        return _fail(tc, f"RUNTIME ERROR\nOutput limit exceeded (more than {sandbox.OUTPUT_LIMIT // sandbox.MB} MB)", p.stdout)
    if p.returncode != 0:
        # The program crashed (exception / segfault / out of memory). Show what it printed plus the error.
        err = p.stderr.strip().replace(d + "/", "")
        if b.self_reported_errors and err.startswith(_ERROR_PREFIXES):
            return _fail(tc, err[-3000:], p.stdout)
        if not err:
            err = f"exit code {p.returncode}" if p.returncode > 0 else f"killed by signal {-p.returncode}"
            if p.returncode == -9:
                err += " (memory limit?)"
        return _fail(tc, f"RUNTIME ERROR\n{err[-2000:]}", p.stdout)
    passed = b.compare(p.stdout, tc.expected_output) if b.compare else _normalize(p.stdout) == _normalize(tc.expected_output)
    return TestResult(passed=passed, actual_output=p.stdout[:SHOWN_OUTPUT], expected_output=tc.expected_output, error=None)
