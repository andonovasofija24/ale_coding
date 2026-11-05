"""
Runs ONE PostgreSQL test inside the sandbox (as the submission's unprivileged user):

    python3 -I pg_exec.py <dir>      # <dir> holds setup.sql, query.sql, check.sql

Connects (PG* environment variables) to the test's own, freshly created database as the low-privilege
"student" role, runs the test's setup, then the student's SQL, then the optional check query, and prints the
result like sql_exec.py: a header line with the column names, then one line per row, cells separated by " | ".
The database is dropped by the runner afterwards, so nothing the student does survives the test.
"""
import datetime
import decimal
import os
import sys

import psycopg

MAX_ROWS = 10_000


def fmt(value) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (float, decimal.Decimal)):
        return f"{round(float(value), 4):.4f}".rstrip("0").rstrip(".")
    if isinstance(value, (datetime.date, datetime.datetime, datetime.time)):
        return value.isoformat(sep=" ") if isinstance(value, datetime.datetime) else value.isoformat()
    if isinstance(value, bytes):
        return value.hex()
    return str(value).replace("\n", " ")


def has_code(sql: str) -> bool:
    for line in sql.splitlines():
        line = line.split("--", 1)[0].strip()
        if line and line != ";":
            return True
    return False


def fail(kind: str, message: str) -> None:
    sys.stderr.write(f"{kind}\n{message}\n")
    sys.exit(1)


def run(con, sql: str, who: str):
    """Run a whole script (one round trip); return the last result that has rows/columns."""
    last = None
    try:
        with con.cursor() as cur:
            cur.execute(sql)
            while True:
                if cur.description:
                    last = ([d.name for d in cur.description], cur.fetchmany(MAX_ROWS))
                if not cur.nextset():
                    break
    except psycopg.errors.QueryCanceled:
        fail("TIME LIMIT EXCEEDED", "")
    except psycopg.Error as e:
        msg = (e.diag.message_primary or str(e)).strip()
        if e.diag.message_hint:
            msg += f"\nHINT: {e.diag.message_hint}"
        if who == "setup":
            fail("RUNTIME ERROR", f"The test's own data could not be created: {msg}")
        kind = "COMPILE ERROR" if isinstance(e, psycopg.errors.SyntaxError) else "RUNTIME ERROR"
        fail(kind, f"SQL error: {msg}")
    return last


def main() -> None:
    d = sys.argv[1]
    read = lambda name: open(os.path.join(d, name), encoding="utf-8").read()
    try:
        con = psycopg.connect(autocommit=True)
    except psycopg.Error as e:
        fail("RUNTIME ERROR", f"Could not connect to the PostgreSQL sandbox: {e}")

    run(con, read("setup.sql"), "setup")
    query = read("query.sql")
    if not has_code(query):
        fail("RUNTIME ERROR", "No SQL to run — write your query.")
    result = run(con, query, "student")
    check = read("check.sql")
    if has_code(check):
        result = run(con, check, "check")

    if result is None:
        return
    cols, rows = result
    out = [" | ".join(cols)] + [" | ".join(fmt(v) for v in row) for row in rows]
    sys.stdout.write("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
