"""
C++ compilation and execution.
For code_sample tests: student code + test snippet are wrapped in a main() and compiled.
For stdin_stdout tests: student code + a standard main() reads stdin, student code is expected
  to define main() itself OR we wrap it. We use the stdin_stdout approach where student code
  is expected to contain main().
"""
import os
import re
import subprocess
import tempfile
from app.schemas import TestCasePayload, TestResult

COMPILE_TIMEOUT = 15  # seconds
RUN_TIMEOUT = 5       # seconds

# Common headers injected for code_sample tests so students don't have to include them
CODE_SAMPLE_PREAMBLE = """
#include <iostream>
#include <string>
#include <fstream>
#include <sstream>
#include <vector>
#include <stdexcept>
#include <cmath>
#include <iomanip>
using namespace std;
"""


def _normalize(output: str) -> str:
    """Normalize output for comparison: strip trailing whitespace per line, strip trailing newlines."""
    lines = output.splitlines()
    lines = [line.rstrip() for line in lines]
    return "\n".join(lines).strip()


def _run_test(student_code: str, tc: TestCasePayload) -> TestResult:
    with tempfile.TemporaryDirectory() as tmpdir:
        src_path = os.path.join(tmpdir, "solution.cpp")
        bin_path = os.path.join(tmpdir, "solution")

        if tc.type == "code_sample":
            source = f"""{CODE_SAMPLE_PREAMBLE}

{student_code}

int main() {{
{tc.test_code}
    return 0;
}}
"""
        else:
            # stdin_stdout: student code must contain main()
            source = f"""{CODE_SAMPLE_PREAMBLE}

{student_code}
"""

        with open(src_path, "w") as f:
            f.write(source)

        # Compile
        compile_proc = subprocess.run(
            ["g++", "-std=c++17", "-O0", "-o", bin_path, src_path, "-lm"],
            capture_output=True,
            text=True,
            timeout=COMPILE_TIMEOUT,
        )

        if compile_proc.returncode != 0:
            error_msg = compile_proc.stderr.strip()
            # Adjust line numbers: preamble is ~12 lines, main() wrapper adds 2
            return TestResult(
                passed=False,
                actual_output="",
                expected_output=tc.expected_output,
                error=f"COMPILE ERROR\n{error_msg}",
            )

        # Run
        try:
            run_proc = subprocess.run(
                [bin_path],
                input=tc.stdin,
                capture_output=True,
                text=True,
                timeout=RUN_TIMEOUT,
            )
            actual = run_proc.stdout
            if run_proc.returncode != 0 and run_proc.stderr:
                actual = run_proc.stderr

        except subprocess.TimeoutExpired:
            return TestResult(
                passed=False,
                actual_output="",
                expected_output=tc.expected_output,
                error="TIME LIMIT EXCEEDED",
            )

        passed = _normalize(actual) == _normalize(tc.expected_output)
        return TestResult(
            passed=passed,
            actual_output=actual,
            expected_output=tc.expected_output,
            error=None,
        )


def run_all(student_code: str, test_cases: list[TestCasePayload]) -> list[TestResult]:
    results = []
    for tc in test_cases:
        try:
            results.append(_run_test(student_code, tc))
        except subprocess.TimeoutExpired:
            results.append(TestResult(
                passed=False,
                actual_output="",
                expected_output=tc.expected_output,
                error="COMPILE TIMEOUT",
            ))
        except Exception as e:
            results.append(TestResult(
                passed=False,
                actual_output="",
                expected_output=tc.expected_output,
                error=str(e),
            ))
    return results
