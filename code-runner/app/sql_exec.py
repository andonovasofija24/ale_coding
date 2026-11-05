"""
Runs ONE SQL test inside the sandbox (as the submission's unprivileged user):

    python3 -I sql_exec.py <dir>      # <dir> holds setup.sql, query.sql, check.sql

1. setup.sql  — the test's tables and data (written by the teacher)
2. query.sql  — the student's SQL, statement by statement
3. check.sql  — optional query that inspects the result of the student's changes

Prints the result of check.sql (if present) or of the student's last statement that returned rows,
as a text table: a header line with the column names, then one line per row, cells separated by " | ".
Errors go to stderr with the usual first line ("COMPILE ERROR" for SQL syntax errors, else "RUNTIME ERROR").

The database is in memory and dies with the process; ATTACH (which could create files) is not allowed.
"""
import os
import sqlite3
import sys

MAX_ROWS = 10_000
_DENY = {sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH}


def statements(sql: str):
    """Split SQL into complete statements (semicolons inside strings, comments and triggers are respected)."""
    buf = ""
    for ch in sql:
        buf += ch
        if ch == ";" and sqlite3.complete_statement(buf):
            if _has_code(buf):
                yield buf.strip()
            buf = ""
    if _has_code(buf):
        yield buf.strip()


def _has_code(sql: str) -> bool:
    for line in sql.splitlines():
        line = line.split("--", 1)[0].strip()
        if line and line != ";":
            return True
    return False


def fmt(value) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, float):
        return f"{round(value, 4):.4f}".rstrip("0").rstrip(".")
    if isinstance(value, bytes):
        return value.hex()
    return str(value).replace("\n", " ")


def fail(kind: str, message: str) -> None:
    sys.stderr.write(f"{kind}\n{message}\n")
    sys.exit(1)


def run(con: sqlite3.Connection, sql: str, who: str):
    last = None
    for stmt in statements(sql):
        try:
            cur = con.execute(stmt)
            if cur.description:
                last = ([d[0] for d in cur.description], cur.fetchmany(MAX_ROWS))
        except sqlite3.Error as e:
            msg = str(e)
            if who == "setup":
                fail("RUNTIME ERROR", f"The test's own data could not be created: {msg}")
            kind = "COMPILE ERROR" if "syntax error" in msg or "incomplete input" in msg else "RUNTIME ERROR"
            shown = stmt if len(stmt) < 300 else stmt[:300] + " …"
            fail(kind, f"SQL error: {msg}\n  in: {shown}")
    return last


def main() -> None:
    d = sys.argv[1]
    read = lambda name: open(os.path.join(d, name), encoding="utf-8").read()
    con = sqlite3.connect(":memory:", isolation_level=None)
    con.execute("PRAGMA foreign_keys = ON")
    con.set_authorizer(lambda action, *_: sqlite3.SQLITE_DENY if action in _DENY else sqlite3.SQLITE_OK)

    run(con, read("setup.sql"), "setup")
    query = read("query.sql")
    if not _has_code(query):
        fail("RUNTIME ERROR", "No SQL to run — write your query.")
    result = run(con, query, "student")
    check = read("check.sql")
    if _has_code(check):
        result = run(con, check, "check")

    if result is None:
        return  # nothing returned rows: empty output
    cols, rows = result
    out = [" | ".join(cols)] + [" | ".join(fmt(v) for v in row) for row in rows]
    sys.stdout.write("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
