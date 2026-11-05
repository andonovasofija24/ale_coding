"""
Editor diagnostics: compile (never run) the student's code and return the compiler's errors and warnings with the
line and column in the student's own code — shown in the editor as red / yellow underlines, like in an IDE.

The code is built exactly like for a test (app/languages.py), with an empty test, so the student sees the same
errors the tests would give. The platform adds its own lines around the student's code (headers, a main(), a test
class); compiler line numbers are mapped back to the student's lines by matching the lines of both texts.

Checks never wait in the queue: when every sandbox slot is busy (e.g. during an exam) the check is skipped.
"""
import difflib
import os
import re

from app import sandbox
from app.languages import builder
from app.schemas import TestCasePayload

CHECK_TIMEOUT = 25
NO_CHECK = {"sql", "postgresql", "web", "lisp"}  # SQL: no compiler; web: the editor checks HTML/CSS/JS itself
MAX_DIAGNOSTICS = 50

# file:line[:col]: [fatal] error|warning: message      (gcc, g++, javac, kotlinc, nasm, pyflakes-like)
# file(line,col): error CODE: message                    (tsc, csc)
_GENERIC = re.compile(
    r"^(?P<file>[^\s:()]+?)(?::(?P<line>\d+)(?::(?P<col>\d+))?|\((?P<line2>\d+),(?P<col2>\d+)\))\s*:?\s*"
    r"(?P<sev>fatal error|error|warning|Error|Warning)\b[^:]*:\s*(?P<msg>.+)$", re.M)
_PYFLAKES = re.compile(r"^(?P<file>[^:\n]+):(?P<line>\d+):(?:(?P<col>\d+):?)?\s+(?P<msg>.+)$", re.M)
_NODE = re.compile(r"^(?P<file>\S+\.js):(?P<line>\d+)\s*$", re.M)
_PHP = re.compile(r"(?:PHP )?(?P<sev>Parse error|Fatal error|Warning):\s*(?P<msg>.+?) in \S+ on line (?P<line>\d+)")
_BASH = re.compile(r"^\S+: line (?P<line>\d+): (?P<msg>.*(?:syntax error|unexpected|expected).*)$", re.M)
_PY_WARNINGS = ("imported but unused", "is assigned to but never used", "redefinition of unused", "unable to detect undefined names")


def _line_map(generated: str, student: str) -> dict[int, int]:
    """Generated line number (1-based) -> student line number, for lines that are the student's."""
    g, s = generated.split("\n"), student.split("\n")
    out = {}
    sm = difflib.SequenceMatcher(None, g, s, autojunk=False)
    for block in sm.get_matching_blocks():
        for k in range(block.size):
            out[block.a + k + 1] = block.b + k + 1
    return out


def _source_files(d: str) -> dict[str, str]:
    out = {}
    for name in os.listdir(d):
        p = os.path.join(d, name)
        if os.path.isfile(p) and not name.startswith(".") and os.path.getsize(p) < 2_000_000:
            try:
                with open(p, encoding="utf-8") as f:
                    out[name] = f.read()
            except (UnicodeDecodeError, OSError):
                pass
    return out


def check(code: str, language: str, kind: str = "function") -> dict:
    """{"diagnostics": [{line, column, severity, message}], "skipped": bool}"""
    if language in ("dockerfile", "yaml", "terraform") and code.strip():
        from app import devops  # parsed here, never run: no sandbox needed
        return {"diagnostics": devops.check_syntax(code, language), "skipped": False}
    if language == "git":
        language = "bash"
    if language in NO_CHECK or not code.strip():
        return {"diagnostics": [], "skipped": language in NO_CHECK}
    try:
        with sandbox.slot(wait=False) as slot:
            return {"diagnostics": _check(code, language, kind, slot), "skipped": False}
    except sandbox.RunnerBusy:
        return {"diagnostics": [], "skipped": True}


def _check(code: str, language: str, kind: str, slot) -> list[dict]:
    d = slot.new_dir("check")
    tc = TestCasePayload(type="stdin_stdout" if kind == "program" else "code_sample", test_code="", expected_output="")
    b = builder(language)(code, tc, d)
    cmd = b.compile
    if language in ("c", "cpp"):  # syntax and type check only, with the usual warnings
        src = os.path.join(d, "solution.c" if language == "c" else "solution.cpp")
        cmd = (["gcc", "-std=gnu11"] if language == "c" else ["g++", "-std=c++17"]) + \
            ["-fsyntax-only", "-Wall", "-fno-diagnostics-color", "-fdiagnostics-column-unit=byte", src]
    elif language == "python":
        cmd = ["python3", "-I", "-B", "-m", "pyflakes", os.path.join(d, "solution.py")]
    if not cmd:
        return []
    p = sandbox.run(cmd, slot=slot, cwd=d, timeout=CHECK_TIMEOUT,
                    limits=sandbox.JVM_COMPILE_LIMITS if b.vm else sandbox.COMPILE_LIMITS, env_extra=b.env)
    if p.timed_out:
        return []
    output = (p.stderr + "\n" + p.stdout).replace(d + "/", "")
    files = _source_files(d)
    maps = {name: _line_map(text, code) for name, text in files.items()}
    if language == "csharp":  # the builder points messages at "solution.cs" = the student's lines without `using`s
        kept = [i + 1 for i, ln in enumerate(code.split("\n")) if not re.match(r"\s*using\s+[\w.]+\s*;", ln)]
        maps["solution.cs"] = {k + 1: v for k, v in enumerate(kept)}
    n_lines = code.count("\n") + 1

    # the file that holds most of the student's code (compilers sometimes name it differently, e.g. csc)
    main_map = max(maps.values(), key=len, default={})

    def place(file: str | None, line: int) -> int | None:
        m = maps.get(os.path.basename(file.strip())) if file else None
        if m is None:
            if file and os.path.basename(file.strip()).endswith((".h", ".hpp")):
                return None  # a library header, not the student's code
            m = main_map
        if line in m:
            return m[line]
        # a line the platform added (e.g. the closing brace of its class): the nearest student line before it
        before = [v for k, v in m.items() if k < line]
        return max(before) if before else (1 if m else None)

    found: list[dict] = []

    lines_out = output.split("\n")

    def caret_column(match_end: int) -> int | None:
        """javac / kotlinc print the source line and a ^ under the problem instead of a column."""
        idx = output.count("\n", 0, match_end)
        for k in (idx + 2, idx + 1):
            if k < len(lines_out) and lines_out[k].strip() == "^":
                return lines_out[k].index("^") + 1
        return None

    def add(file, line, col, sev, msg):
        ln = place(file, int(line))
        if ln is None or not 1 <= ln <= n_lines:
            return
        found.append({"line": ln, "column": max(1, int(col or 1)),
                      "severity": "warning" if sev.lower().startswith("warn") else "error",
                      "message": msg.strip()[:500]})

    if language == "python":
        if "SyntaxError" in output or "invalid syntax" in output:
            for m in _PYFLAKES.finditer(output):
                add(m["file"], m["line"], m["col"], "error", m["msg"])
                break
        else:
            for m in _PYFLAKES.finditer(output):
                sev = "warning" if any(w in m["msg"] for w in _PY_WARNINGS) else "error"
                add(m["file"], m["line"], m["col"], sev, m["msg"])
    elif language == "javascript":
        m, msg = _NODE.search(output), re.search(r"^(\w*Error: .+)$", output, re.M)
        if m and msg:
            add(m["file"], m["line"], 1, "error", msg.group(1))
    elif language == "php":
        for m in _PHP.finditer(output):
            add(None, m["line"], 1, "warning" if m["sev"] == "Warning" else "error", m["msg"])
    elif language == "bash":
        for m in _BASH.finditer(output):
            add(None, m["line"], 1, "error", m["msg"])
    elif language == "prolog":
        for m in re.finditer(r"(?P<sev>ERROR|Warning):\s*(?P<file>[^\s:]+):(?P<line>\d+):(?:(?P<col>\d+):)?\s*(?P<msg>.*)", output):
            add(m["file"], m["line"], m["col"], m["sev"], m["msg"] or "syntax error")
    else:
        for m in _GENERIC.finditer(output):
            add(m["file"], m["line"] or m["line2"], m["col"] or m["col2"] or caret_column(m.end()), m["sev"], m["msg"])
    # one message per place, errors first
    seen, out = set(), []
    for x in sorted(found, key=lambda x: (x["severity"] != "error", x["line"], x["column"])):
        k = (x["line"], x["column"], x["message"])
        if k not in seen:
            seen.add(k)
            out.append(x)
    return sorted(out[:MAX_DIAGNOSTICS], key=lambda x: (x["line"], x["column"]))
