"""
Language registry. Adding a language = writing one `build_*` function and one LANGUAGES entry.

A build function writes the program for ONE test into a work directory and says how to compile and run it:

    build(student_code, test, workdir) -> Build

Test semantics (same as Moodle CodeRunner):
- "code_sample": the student writes functions / classes / a query; the test is code that uses them.
- "stdin_stdout": the student writes a whole program; the test gives stdin and checks stdout.

Per language:
    C        : student code + `int main(void) { <test> }`         (common headers are included)
    C++      : student code + `int main() { <test> }`             (common headers are included)
    Java     : student code + `public class __Tester__ { main() { <test> } }`
               - only methods (no class) -> placed inside __Tester__ (call them directly)
               - classes -> stay top-level (non-public) and the test uses them
    Python   : student code, then the test code appended below it
    JavaScript: student code, then the test code appended below it (Node.js, CommonJS)
    SQL      : the test's code creates and fills tables (SQLite); then the student's query runs and its result
               table is compared with the expected one. Optional markers in the test code:
                 "-- check"   : what follows runs AFTER the student's code and its result is compared
                                (for INSERT / UPDATE / DELETE / CREATE tasks)
                 "-- ordered" : row order matters (otherwise rows are compared as a set)
    PostgreSQL: the same as SQL, but every test gets its own fresh PostgreSQL database (the sql-sandbox service),
               created before the test and dropped after it.
    TypeScript: like JavaScript; type-checked and compiled with tsc first (type errors = compile errors)
    PHP      : student code, then the test code appended below it
    Bash     : student code (functions), then the test commands appended below it
    C#       : like Java: only methods -> inside the tester class; classes -> top-level; `using`s collected
    Kotlin   : student code + `fun main() { <test> }`
    Prolog   : the test is a goal that runs after the student's clauses are loaded (SWI-Prolog)
    Lisp     : the test forms run after the student's definitions (SBCL, Common Lisp)
    Git / Dockerfile / YAML / Terraform: see app/devops.py
    Assembly : x86-64 NASM. Function tasks: the test is C code inside main() that calls the student's functions
               (declare them in the test, e.g. `extern long sum(long, long);`). Program tasks: the student
               writes `main` (linked with gcc) or `_start` (linked with ld).

Which languages are really available depends on what is installed in the image: see `available()`.
"""
import glob
import os
import re
import secrets
import shutil
from dataclasses import dataclass
from typing import Callable

from app.schemas import TestCasePayload

JVM_FLAGS = ["-XX:+UseSerialGC", "-XX:ActiveProcessorCount=1", "-XX:TieredStopAtLevel=1", "-XX:-UsePerfData",
             "-Xshare:auto"]


@dataclass
class Build:
    run: list[str]
    compile: list[str] | None = None
    # Runtimes that reserve a lot of virtual memory (JVM, V8) can't run under an address-space limit;
    # their heap is capped with their own flags instead (and by the container's memory limit).
    vm: bool = False
    # The program writes its own "COMPILE ERROR" / "RUNTIME ERROR" first line to stderr (used by SQL).
    self_reported_errors: bool = False
    compare: Callable[[str, str], bool] | None = None  # None = compare text line by line
    env: dict[str, str] | None = None                  # extra environment for compile + run
    compile_timeout: int | None = None                 # seconds; None = the default (30)
    before: Callable[[], None] | None = None           # runs (as the runner, not the student) before the test
    after: Callable[[], None] | None = None            # ... and after it, even if it failed


def _write(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


# ---------------------------------------------------------------------------
# C and C++
# ---------------------------------------------------------------------------

CPP_PREAMBLE = """
#include <iostream>
#include <string>
#include <fstream>
#include <sstream>
#include <vector>
#include <stdexcept>
#include <cmath>
#include <iomanip>
#include <algorithm>
using namespace std;
"""

C_PREAMBLE = """
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <ctype.h>
#include <stdbool.h>
#include <limits.h>
"""


def _has_main(code: str) -> bool:
    return re.search(r"\bint\s+main\s*\(", code) is not None


def build_cpp(student_code: str, tc: TestCasePayload, tmp: str) -> Build:
    src, exe = os.path.join(tmp, "solution.cpp"), os.path.join(tmp, "solution")
    if tc.type == "code_sample":
        source = f"{CPP_PREAMBLE}\n{student_code}\n\nint main() {{\n{tc.test_code}\n    return 0;\n}}\n"
    else:
        source = f"{CPP_PREAMBLE}\n{student_code}\n"
    _write(src, source)
    return Build(compile=["g++", "-std=c++17", "-O0", "-pipe", "-o", exe, src, "-lm"], run=[exe])


def build_c(student_code: str, tc: TestCasePayload, tmp: str) -> Build:
    src, exe = os.path.join(tmp, "solution.c"), os.path.join(tmp, "solution")
    if tc.type == "code_sample":
        source = f"{C_PREAMBLE}\n{student_code}\n\nint main(void) {{\n{tc.test_code}\n    return 0;\n}}\n"
    else:
        source = f"{C_PREAMBLE}\n{student_code}\n"
    _write(src, source)
    return Build(compile=["gcc", "-std=gnu11", "-O0", "-pipe", "-o", exe, src, "-lm"], run=[exe])


# ---------------------------------------------------------------------------
# Java
# ---------------------------------------------------------------------------

JAVA_DEFAULT_IMPORTS = ["import java.util.*;", "import java.io.*;"]
_JAVA_TOP_CLASS = re.compile(r"^(\s*)(public\s+)?((?:abstract\s+|final\s+)*(?:class|interface|enum|record)\s+\w+)", re.M)


def _split_java_imports(code: str) -> tuple[list[str], str]:
    imports, rest = [], []
    for line in code.split("\n"):
        (imports if re.match(r"\s*import\s+[\w.*]+\s*;", line) else rest).append(line)
    return [i.strip() for i in imports], "\n".join(rest)


def _has_top_level_type(code: str) -> bool:
    """True if the code declares a class/interface/enum at brace depth 0 (not just methods)."""
    depth = 0
    for m in re.finditer(r"[{}]|\b(class|interface|enum|record)\s+\w+", code):
        tok = m.group(0)
        if tok == "{":
            depth += 1
        elif tok == "}":
            depth -= 1
        elif depth == 0:
            return True
    return False


def _java_main_class(code: str) -> str:
    """Name of the class that declares `static void main` (falls back to the first class, then Main)."""
    main_pos = code.find("static void main")
    best, first = None, None
    for m in re.finditer(r"\bclass\s+(\w+)", code):
        first = first or m.group(1)
        if main_pos == -1 or m.start() < main_pos:
            best = m.group(1)
    return best or first or "Main"


def build_java(student_code: str, tc: TestCasePayload, tmp: str) -> Build:
    imports, body = _split_java_imports(student_code)
    imports = list(dict.fromkeys(JAVA_DEFAULT_IMPORTS + imports))  # de-duplicated, order kept

    if tc.type == "code_sample":
        if _has_top_level_type(body):
            # Student classes stay top-level; "public" is dropped so they can share one file with the tester.
            body = _JAVA_TOP_CLASS.sub(lambda m: m.group(1) + m.group(3), body)
            source = "\n".join(imports) + f"\n\n{body}\n\npublic class __Tester__ {{\n" \
                f"    public static void main(String[] args) throws Exception {{\n{tc.test_code}\n    }}\n}}\n"
        else:
            # Only methods: put them inside the tester class so the test can call them directly.
            source = "\n".join(imports) + "\n\npublic class __Tester__ {\n" + body + \
                f"\n\n    public static void main(String[] args) throws Exception {{\n{tc.test_code}\n    }}\n}}\n"
        main_class, file_name = "__Tester__", "__Tester__.java"
    else:
        main_class = _java_main_class(body)
        # Make sure only the main class is public, and the file is named after it.
        body = _JAVA_TOP_CLASS.sub(lambda m: m.group(1) + m.group(3), body)
        body = re.sub(r"^(\s*)((?:abstract\s+|final\s+)*class\s+" + re.escape(main_class) + r"\b)",
                      r"\1public \2", body, count=1, flags=re.M)
        source = "\n".join(imports) + "\n\n" + body + "\n"
        file_name = f"{main_class}.java"

    _write(os.path.join(tmp, file_name), source)
    javac = ["javac", *("-J" + f for f in JVM_FLAGS), "-J-Xmx512m",
             "-encoding", "UTF-8", "-nowarn", "-d", tmp, os.path.join(tmp, file_name)]
    run = ["java", *JVM_FLAGS, "-Xss8m", "-Xmx256m", "-Dfile.encoding=UTF-8", "-cp", tmp, main_class]
    return Build(compile=javac, run=run, vm=True)


# ---------------------------------------------------------------------------
# Python
# ---------------------------------------------------------------------------

_PY_SYNTAX_CHECK = """
import sys, traceback
try:
    compile(open(sys.argv[1], encoding="utf-8").read(), "solution.py", "exec")
except SyntaxError as e:
    sys.stderr.write("".join(traceback.format_exception_only(type(e), e)))
    sys.exit(1)
"""


def build_python(student_code: str, tc: TestCasePayload, tmp: str) -> Build:
    src = os.path.join(tmp, "solution.py")
    source = student_code if tc.type != "code_sample" or not tc.test_code.strip() \
        else f"{student_code}\n\n{tc.test_code}\n"
    _write(src, source)
    # Syntax check first (compile to memory only) so syntax errors are reported like compile errors elsewhere.
    return Build(compile=["python3", "-I", "-B", "-c", _PY_SYNTAX_CHECK, src], run=["python3", "-I", "-B", src])


# ---------------------------------------------------------------------------
# JavaScript (Node.js)
# ---------------------------------------------------------------------------

NODE_FLAGS = ["--max-old-space-size=256", "--stack-size=4000"]


def build_javascript(student_code: str, tc: TestCasePayload, tmp: str) -> Build:
    src = os.path.join(tmp, "solution.js")
    source = student_code if tc.type != "code_sample" or not tc.test_code.strip() \
        else f"{student_code}\n;\n{tc.test_code}\n"
    _write(src, source)
    # `node --check` = syntax check only, reported like a compile error.
    return Build(compile=["node", "--check", src], run=["node", *NODE_FLAGS, src], vm=True)


# ---------------------------------------------------------------------------
# SQL (SQLite)
# ---------------------------------------------------------------------------

SQL_EXEC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sql_exec.py")


def _split_check(test_code: str) -> tuple[str, str]:
    """Setup part and check part of an SQL test (split at a line '-- check')."""
    parts = re.split(r"^\s*--\s*check\s*$", test_code, maxsplit=1, flags=re.M | re.I)
    return parts[0], (parts[1] if len(parts) > 1 else "")


def build_sql(student_code: str, tc: TestCasePayload, tmp: str) -> Build:
    setup, check = _split_check(tc.test_code)
    _write(os.path.join(tmp, "setup.sql"), setup)
    _write(os.path.join(tmp, "query.sql"), student_code)
    _write(os.path.join(tmp, "check.sql"), check)
    ordered = re.search(r"^\s*--\s*ordered\s*$", tc.test_code, flags=re.M | re.I) is not None
    return Build(run=["python3", "-I", "-B", SQL_EXEC, tmp], self_reported_errors=True,
                 compare=lambda actual, expected: sql_tables_equal(actual, expected, ordered))


def _sql_cell(cell: str) -> str:
    """Normalise one cell: numbers by value (9.50 == 9.5 == 9.5000001), NULL case-insensitive."""
    c = cell.strip()
    if c.upper() == "NULL":
        return "NULL"
    try:
        v = float(c)
    except ValueError:
        return c
    return f"{round(v, 4):.4f}".rstrip("0").rstrip(".") if v == v else c


def _sql_rows(text: str) -> list[tuple[str, ...]]:
    lines = [ln for ln in text.strip().splitlines() if ln.strip()]
    # First line is the header (column names): not compared, students may name columns differently.
    return [tuple(_sql_cell(c) for c in ln.split("|")) for ln in lines[1:]]


def sql_tables_equal(actual: str, expected: str, ordered: bool) -> bool:
    a, e = _sql_rows(actual), _sql_rows(expected)
    if not actual.strip() and expected.strip():
        return False
    return a == e if ordered else sorted(a) == sorted(e)


# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# PostgreSQL (separate sql-sandbox service; one throwaway database per test)
# ---------------------------------------------------------------------------

PG_EXEC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pg_exec.py")
PG_HOST = os.getenv("PG_SANDBOX_HOST", "")
PG_PORT = os.getenv("PG_SANDBOX_PORT", "5432")
PG_ADMIN = (os.getenv("PG_SANDBOX_ADMIN_USER", "runner_admin"), os.getenv("PG_SANDBOX_ADMIN_PASSWORD", ""))
PG_STUDENT = (os.getenv("PG_SANDBOX_STUDENT_USER", "student"),)


def _pg_admin():
    import psycopg  # only needed when PostgreSQL is used
    return psycopg.connect(host=PG_HOST, port=PG_PORT, user=PG_ADMIN[0], password=PG_ADMIN[1],
                           dbname="postgres", autocommit=True, connect_timeout=5)


_pg_student_password: str | None = None


def _student_password() -> str:
    """A random password for the student role, set once per runner start (never the guessable default)."""
    global _pg_student_password
    if _pg_student_password is None:
        from psycopg import sql
        pw = secrets.token_urlsafe(24)
        with _pg_admin() as con:
            con.execute(sql.SQL("ALTER ROLE {} PASSWORD {}").format(sql.Identifier(PG_STUDENT[0]), sql.Literal(pw)))
        _pg_student_password = pw
    return _pg_student_password


def build_postgresql(student_code: str, tc: TestCasePayload, tmp: str) -> Build:
    b = build_sql(student_code, tc, tmp)
    db = "t_" + secrets.token_hex(8)

    def before():
        b.env["PGPASSWORD"] = _student_password()
        with _pg_admin() as con:
            con.execute(f'CREATE DATABASE "{db}" OWNER "{PG_STUDENT[0]}" TEMPLATE template0 ENCODING \'UTF8\'')

    def after():
        try:
            with _pg_admin() as con:
                con.execute(f'DROP DATABASE IF EXISTS "{db}" WITH (FORCE)')
        except Exception:
            pass

    # The student's process gets only the student role's credentials, for this one database.
    b.run = ["python3", "-I", "-B", PG_EXEC, tmp]
    b.env = {"PGHOST": PG_HOST, "PGPORT": PG_PORT, "PGUSER": PG_STUDENT[0], "PGPASSWORD": "",
             "PGDATABASE": db, "PGCONNECT_TIMEOUT": "5",
             # per-session limits (also set on the role); the database is force-dropped after the test anyway
             "PGOPTIONS": "-c statement_timeout=4000 -c lock_timeout=2000 -c idle_in_transaction_session_timeout=5000"}
    b.before, b.after = before, after
    return b


# ---------------------------------------------------------------------------
# TypeScript (tsc type-check + compile, then Node.js)
# ---------------------------------------------------------------------------

TS_HOME = os.getenv("TS_HOME", "/opt/ts")


def build_typescript(student_code: str, tc: TestCasePayload, tmp: str) -> Build:
    src = os.path.join(tmp, "solution.ts")
    source = student_code if tc.type != "code_sample" or not tc.test_code.strip() \
        else f"{student_code}\n;\n{tc.test_code}\n"
    _write(src, source)
    tsc = ["node", os.path.join(TS_HOME, "node_modules/typescript/bin/tsc"), "--target", "ES2022",
           "--module", "commonjs", "--lib", "ES2022", "--typeRoots", os.path.join(TS_HOME, "node_modules/@types"),
           "--types", "node", "--skipLibCheck", "--noEmitOnError", "--pretty", "false", "--outDir", tmp, src]
    return Build(compile=tsc, run=["node", *NODE_FLAGS, os.path.join(tmp, "solution.js")], vm=True)


# ---------------------------------------------------------------------------
# PHP
# ---------------------------------------------------------------------------

def build_php(student_code: str, tc: TestCasePayload, tmp: str) -> Build:
    src = os.path.join(tmp, "solution.php")
    code = student_code.strip()
    if not code.startswith("<?php"):
        code = "<?php\n" + code
    code = re.sub(r"\?>\s*$", "", code)  # a closing tag would turn the appended test into plain text
    test = re.sub(r"^\s*<\?php", "", tc.test_code) if tc.type == "code_sample" else ""
    _write(src, f"{code}\n{test}\n")
    ini = ["-d", "display_errors=stderr", "-d", "memory_limit=256M", "-d", "error_reporting=E_ALL"]
    return Build(compile=["php", "-l", src], run=["php", *ini, src])


# ---------------------------------------------------------------------------
# Bash
# ---------------------------------------------------------------------------

def build_bash(student_code: str, tc: TestCasePayload, tmp: str) -> Build:
    src = os.path.join(tmp, "solution.sh")
    test = tc.test_code if tc.type == "code_sample" else ""
    _write(src, f"{student_code}\n{test}\n")
    return Build(compile=["bash", "-n", src], run=["bash", src])


# ---------------------------------------------------------------------------
# C# (Roslyn csc from the .NET SDK — much faster than `dotnet build`)
# ---------------------------------------------------------------------------

DOTNET_ROOT = os.getenv("DOTNET_ROOT", "/usr/share/dotnet")
CS_USINGS = ["using System;", "using System.Collections.Generic;", "using System.Linq;", "using System.Text;",
             "using System.IO;"]
_DOTNET_ENV = {"DOTNET_ROOT": DOTNET_ROOT, "DOTNET_CLI_TELEMETRY_OPTOUT": "1", "DOTNET_NOLOGO": "1",
               "DOTNET_SYSTEM_GLOBALIZATION_INVARIANT": "1", "DOTNET_GCHeapHardLimit": "0x10000000",
               "DOTNET_TieredPGO": "0", "DOTNET_TC_QuickJitForLoops": "1",
               # W^X double-maps code through a huge memory file, which the file-size limit (RLIMIT_FSIZE) kills
               "DOTNET_EnableWriteXorExecute": "0"}


def _dotnet_paths() -> tuple[str, str, list[str]]:
    """(dotnet executable, csc.dll, reference assemblies) of the newest SDK installed."""
    dotnet = os.path.join(DOTNET_ROOT, "dotnet")
    csc = sorted(glob.glob(os.path.join(DOTNET_ROOT, "sdk/*/Roslyn/bincore/csc.dll")))[-1]
    ref_dir = sorted(glob.glob(os.path.join(DOTNET_ROOT, "packs/Microsoft.NETCore.App.Ref/*/ref/net*")))[-1]
    return dotnet, csc, sorted(glob.glob(os.path.join(ref_dir, "*.dll")))


def _runtime_version() -> str:
    versions = sorted(os.listdir(os.path.join(DOTNET_ROOT, "shared/Microsoft.NETCore.App")),
                      key=lambda v: [int(x) if x.isdigit() else 0 for x in re.split(r"[.-]", v)])
    return versions[-1]


def build_csharp(student_code: str, tc: TestCasePayload, tmp: str) -> Build:
    usings, body = [], []
    for line in student_code.split("\n"):
        (usings if re.match(r"\s*using\s+[\w.]+\s*;", line) else body).append(line)
    usings = list(dict.fromkeys(CS_USINGS + [u.strip() for u in usings]))
    body_text = "\n".join(body)
    if tc.type == "code_sample":
        tester = f"public static class __Tester__ {{\n    public static void Main() {{\n{tc.test_code}\n    }}\n}}\n"
        # "#line" keeps compiler messages pointing at the student's own line numbers.
        if re.search(r"\b(class|struct|interface|enum|record)\s+\w+", body_text):
            source = "\n".join(usings) + f"\n#line 1 \"solution.cs\"\n{body_text}\n#line default\n{tester}"
        else:  # only methods: they go inside the tester class
            source = "\n".join(usings) + f"\npublic static class __Tester__ {{\n#line 1 \"solution.cs\"\n{body_text}\n" \
                f"#line default\n    public static void Main() {{\n{tc.test_code}\n    }}\n}}\n"
        main = ["-main:__Tester__"]
    else:
        source = "\n".join(usings) + f"\n#line 1 \"solution.cs\"\n{body_text}\n"
        main = []
    _write(os.path.join(tmp, "Program.cs"), source)
    rt = _runtime_version()
    _write(os.path.join(tmp, "program.runtimeconfig.json"),
           '{"runtimeOptions":{"tfm":"net%s","framework":{"name":"Microsoft.NETCore.App","version":"%s"}}}'
           % (".".join(rt.split(".")[:2]), rt))
    dotnet, csc, refs = _dotnet_paths()
    compile_cmd = [dotnet, csc, "-nologo", "-noconfig", "-nostdlib", "-target:exe", "-langversion:latest",
                   "-nullable:disable", "-nowarn:CS8632", *main, "-out:" + os.path.join(tmp, "program.dll"),
                   *("-r:" + r for r in refs), os.path.join(tmp, "Program.cs")]
    return Build(compile=compile_cmd, run=[dotnet, os.path.join(tmp, "program.dll")], vm=True, env=_DOTNET_ENV)


# ---------------------------------------------------------------------------
# Kotlin (kotlinc -> jar, run on the JVM)
# ---------------------------------------------------------------------------

def build_kotlin(student_code: str, tc: TestCasePayload, tmp: str) -> Build:
    src, jar = os.path.join(tmp, "solution.kt"), os.path.join(tmp, "solution.jar")
    source = f"{student_code}\n\nfun main() {{\n{tc.test_code}\n}}\n" if tc.type == "code_sample" else student_code
    _write(src, source)
    env = {"JAVA_OPTS": "-Xmx768m -XX:+UseSerialGC -XX:TieredStopAtLevel=1 -XX:-UsePerfData -Xss8m"}
    return Build(compile=["kotlinc", src, "-include-runtime", "-nowarn", "-d", jar],
                 run=["java", *JVM_FLAGS, "-Xss8m", "-Xmx256m", "-jar", jar], vm=True, env=env, compile_timeout=90)


# ---------------------------------------------------------------------------
# Prolog (SWI-Prolog)
# ---------------------------------------------------------------------------

def build_prolog(student_code: str, tc: TestCasePayload, tmp: str) -> Build:
    src = os.path.join(tmp, "solution.pl")
    _write(src, student_code)
    load_check = ["swipl", "--on-error=status", "-q", "-g", "halt", src]
    if tc.type == "code_sample":
        goal = tc.test_code.strip().rstrip(".").strip() or "true"
        _write(os.path.join(tmp, "test.pl"),
               f":- initialization(run_test, main).\nrun_test :- ( {goal} ) -> true ; (write(false), nl).\n")
        # --on-warning=status is not used here: singleton warnings in a goal should not fail the test.
        return Build(compile=load_check, run=["swipl", "-q", src, os.path.join(tmp, "test.pl")])
    return Build(compile=load_check, run=["swipl", "-q", "-g", "main", "-t", "halt", src])


# ---------------------------------------------------------------------------
# Common Lisp (SBCL)
# ---------------------------------------------------------------------------

def build_lisp(student_code: str, tc: TestCasePayload, tmp: str) -> Build:
    src = os.path.join(tmp, "solution.lisp")
    test = tc.test_code if tc.type == "code_sample" else ""
    _write(src, f"{student_code}\n\n{test}\n")
    sbcl = ["sbcl", "--dynamic-space-size", "512", "--noinform", "--non-interactive", "--no-sysinit", "--no-userinit"]
    # Compile first: reader errors (unbalanced parentheses...) and full WARNINGs are reported as compile errors.
    check = sbcl + ["--eval", f'(multiple-value-bind (out warn fail) (compile-file "{src}" :output-file "{tmp}/check.fasl")'
                              f' (declare (ignore out warn)) (sb-ext:exit :code (if fail 1 0)))']
    # Run: on an error print only its message (not SBCL's long backtrace).
    run = sbcl + ["--eval", f'(handler-case (load "{src}") (error (e) (format *error-output* "~a~%" e) (sb-ext:exit :code 1)))']
    return Build(compile=check, run=run, vm=True)


# ---------------------------------------------------------------------------
# Assembly (x86-64, NASM)
# ---------------------------------------------------------------------------

def build_asm(student_code: str, tc: TestCasePayload, tmp: str) -> Build:
    asm, obj, exe = os.path.join(tmp, "solution.asm"), os.path.join(tmp, "solution.o"), os.path.join(tmp, "solution")
    _write(asm, student_code)
    nasm = f"nasm -f elf64 -o {obj} {asm}"
    if tc.type == "code_sample":
        _write(os.path.join(tmp, "test.c"), f"{C_PREAMBLE}\nint main(void) {{\n{tc.test_code}\n    return 0;\n}}\n")
        link = f"gcc -no-pie -O0 -o {exe} {tmp}/test.c {obj}"
    elif re.search(r"\b_start\b", student_code):
        link = f"ld -o {exe} {obj}"
    else:
        link = f"gcc -no-pie -o {exe} {obj}"
    return Build(compile=["sh", "-c", f"{nasm} && {link}"], run=[exe])


# ---------------------------------------------------------------------------

LANGUAGES: dict[str, Callable[[str, TestCasePayload, str], Build]] = {
    "cpp": build_cpp,
    "c": build_c,
    "java": build_java,
    "python": build_python,
    "javascript": build_javascript,
    "sql": build_sql,
    "postgresql": build_postgresql,
    "typescript": build_typescript,
    "php": build_php,
    "bash": build_bash,
    "csharp": build_csharp,
    "kotlin": build_kotlin,
    "prolog": build_prolog,
    "lisp": build_lisp,
    "asm": build_asm,
}

# What has to be installed for each language (checked at startup and shown to admins).
_REQUIRES: dict[str, Callable[[], bool]] = {
    "cpp": lambda: bool(shutil.which("g++", path=os.getenv("SANDBOX_PATH"))),
    "c": lambda: bool(shutil.which("gcc", path=os.getenv("SANDBOX_PATH"))),
    "java": lambda: bool(shutil.which("javac", path=os.getenv("SANDBOX_PATH"))),
    "python": lambda: True,
    "javascript": lambda: bool(shutil.which("node", path=os.getenv("SANDBOX_PATH"))),
    "sql": lambda: True,
    "postgresql": lambda: bool(PG_HOST),
    "typescript": lambda: os.path.exists(os.path.join(TS_HOME, "node_modules/typescript/bin/tsc")),
    "php": lambda: bool(shutil.which("php", path=os.getenv("SANDBOX_PATH"))),
    "bash": lambda: bool(shutil.which("bash", path=os.getenv("SANDBOX_PATH"))),
    "csharp": lambda: bool(glob.glob(os.path.join(DOTNET_ROOT, "sdk/*/Roslyn/bincore/csc.dll"))),
    "kotlin": lambda: bool(shutil.which("kotlinc", path=os.getenv("SANDBOX_PATH"))),
    "prolog": lambda: bool(shutil.which("swipl", path=os.getenv("SANDBOX_PATH"))),
    "lisp": lambda: bool(shutil.which("sbcl", path=os.getenv("SANDBOX_PATH"))),
    "asm": lambda: bool(shutil.which("nasm", path=os.getenv("SANDBOX_PATH"))),
    "web": lambda: _web_available(),
}


# DevOps (app/devops.py): Git scripts, Dockerfile, YAML, Terraform — registered here, defined there.
from app import devops as _devops  # noqa: E402  (it imports Build / _write from this module)

LANGUAGES.update({"git": _devops.build_git, "dockerfile": _devops.build_config("dockerfile"),
                  "yaml": _devops.build_config("yaml"), "terraform": _devops.build_config("terraform")})
_REQUIRES.update({"git": _devops.git_available, "dockerfile": lambda: True,
                  "yaml": lambda: _devops.config_available("yaml"), "terraform": lambda: _devops.config_available("terraform")})


def _web_available() -> bool:
    from app import web
    return web.available()


def available() -> list[str]:
    """Languages whose compiler / runtime is installed in this runner."""
    out = []
    for lang, check in _REQUIRES.items():
        try:
            if check():
                out.append(lang)
        except Exception:
            pass
    return out


def builder(language: str) -> Callable[[str, TestCasePayload, str], Build]:
    return LANGUAGES.get(language, build_cpp)
