"""
DevOps tasks: Git, Dockerfile, YAML (GitHub Actions, docker-compose, Kubernetes …) and Terraform.

Git  — the student writes a Bash script of git commands. Every test runs it in a fresh, empty directory (git is
       configured: user, e-mail, branch "main"), then the test's own Bash commands check what was made
       (e.g. `git log --oneline | wc -l`). The test's output is compared with the expected output.

Dockerfile / YAML / Terraform — nothing is built or deployed (the runner has no network): the student's file is
       parsed, and the test is Python code with plain `assert`s on what was written, using small helpers:

    Dockerfile  stages (list of FROM images), instr("RUN") (all RUN arguments), first("FROM"), last("CMD"),
                has("EXPOSE", "8080"), user() (the last USER), workdir(), exposed() (ports), env() (dict),
                cmd() / entrypoint() (as lists — JSON form or split), copies() (list of (src, dst))
    YAML        y (the first document), docs (all documents), get(y, "jobs.test.runs-on") (dotted path; ints
                index lists), find(obj, key) (every value of a key at any depth)
    Terraform   tf (the parsed file), resource("aws_s3_bucket", "logs"), resources("aws_instance") (name → body),
                variable("region"), output("arn"), provider("aws"), module("vpc"), data("aws_ami", "ubuntu"),
                locals_(), ref(value) ("${var.x}" → "var.x"), block(body, "versioning_configuration")

A test passes when its code runs to the end; it prints "OK" (expected output "OK"). A failed assert prints
"FAIL: <its message>" so the student sees what is missing. A file that doesn't parse is a compile error.
"""
import json
import os
import shlex
import sys

from app.languages import Build, _write
from app.schemas import TestCasePayload

GIT_ENV = {
    "GIT_AUTHOR_NAME": "Student", "GIT_AUTHOR_EMAIL": "student@ale.local",
    "GIT_COMMITTER_NAME": "Student", "GIT_COMMITTER_EMAIL": "student@ale.local",
    "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0", "LC_ALL": "C.UTF-8",
}


def build_git(student_code: str, tc: TestCasePayload, tmp: str) -> Build:
    """The student's script runs in work/ (a fresh directory); then the test's commands run there."""
    work = os.path.join(tmp, "work")
    os.makedirs(work, exist_ok=True)
    os.chmod(work, 0o777)
    gitconfig = os.path.join(tmp, ".gitconfig")
    _write(gitconfig, "[user]\n\tname = Student\n\temail = student@ale.local\n[init]\n\tdefaultBranch = main\n"
                      "[advice]\n\tdetachedHead = false\n[core]\n\tpager = cat\n[merge]\n\tff = true\n"
                      "[safe]\n\tdirectory = *\n")  # the work dir is made by the runner, used by the sandbox user
    _write(os.path.join(tmp, "solution.sh"), student_code + "\n")
    _write(os.path.join(tmp, "check.sh"), (tc.test_code if tc.type == "code_sample" else "") + "\n")
    script = (
        "cd work && "
        "bash -e ../solution.sh > ../student.out 2>&1 || "
        "{ echo 'Your script stopped with an error:' >&2; tail -n 20 ../student.out >&2; exit 1; }; "
        "bash ../check.sh"
    )
    env = {**GIT_ENV, "HOME": tmp, "GIT_CONFIG_GLOBAL": gitconfig}
    return Build(compile=["bash", "-n", os.path.join(tmp, "solution.sh")], run=["bash", "-c", script], env=env)


# ---------------------------------------------------------------------------------------------------------------------
# Dockerfile / YAML / Terraform: parse, then run the test's asserts

_HELPERS = r'''
import json, re, shlex, sys

def _fail(msg):
    raise AssertionError(msg)

# ---- Dockerfile
def _parse_dockerfile(text):
    lines, buf = [], ""
    for raw in text.splitlines():
        s = raw.rstrip()
        if not buf and (not s.strip() or s.lstrip().startswith("#")):
            continue
        if s.endswith("\\"):
            buf += s[:-1] + " "
            continue
        buf += s
        lines.append(buf.strip()); buf = ""
    if buf.strip():
        lines.append(buf.strip())
    out = []
    known = {"FROM","RUN","CMD","LABEL","EXPOSE","ENV","ADD","COPY","ENTRYPOINT","VOLUME","USER","WORKDIR","ARG",
             "ONBUILD","STOPSIGNAL","HEALTHCHECK","SHELL","MAINTAINER"}
    for i, l in enumerate(lines, 1):
        parts = l.split(None, 1)
        word = parts[0].upper()
        if word not in known:
            raise SyntaxError(f"Unknown instruction: {parts[0]}")
        out.append((word, parts[1].strip() if len(parts) > 1 else ""))
    if not out or out[0][0] not in ("FROM", "ARG"):
        raise SyntaxError("A Dockerfile must start with FROM (or ARG before FROM)")
    return out

def instr(name): return [a for w, a in D if w == name.upper()]
def first(name):
    v = instr(name); return v[0] if v else None
def last(name):
    v = instr(name); return v[-1] if v else None
def has(name, text=""): return any(text.lower() in a.lower() for a in instr(name))
def _words(a):
    a = a.strip()
    if a.startswith("["):
        try: return json.loads(a)
        except Exception: pass
    return shlex.split(a)
def cmd(): v = last("CMD"); return _words(v) if v else None
def entrypoint(): v = last("ENTRYPOINT"); return _words(v) if v else None
def user(): return last("USER")
def workdir(): return last("WORKDIR")
def exposed(): return [p.split("/")[0] for a in instr("EXPOSE") for p in a.split()]
def env():
    out = {}
    for a in instr("ENV"):
        if "=" in a.split()[0]:
            for kv in shlex.split(a):
                k, _, v = kv.partition("="); out[k] = v
        else:
            k, _, v = a.partition(" "); out[k] = v.strip()
    return out
def copies():
    out = []
    for a in instr("COPY") + instr("ADD"):
        w = [x for x in _words(a) if not x.startswith("--")]
        if len(w) >= 2: out.append((" ".join(w[:-1]), w[-1]))
    return out
def stages(): return [a.split()[0] for a in instr("FROM")]

# ---- YAML
def get(obj, path, default=None):
    cur = obj
    for p in str(path).split("."):
        if isinstance(cur, list):
            try: cur = cur[int(p)]
            except Exception: return default
        elif isinstance(cur, dict):
            if p not in cur:
                # YAML 1.1 reads a bare `on:` as True (GitHub Actions)
                if p == "on" and True in cur: cur = cur[True]; continue
                return default
            cur = cur[p]
        else:
            return default
    return cur
def find(obj, key):
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key: out.append(v)
            out += find(v, key)
    elif isinstance(obj, list):
        for v in obj: out += find(v, key)
    return out

# ---- Terraform
def _merged(kind):
    out = {}
    for item in TF.get(kind, []) if isinstance(TF, dict) else []:
        for k, v in item.items():
            if kind in ("resource", "data"):
                for n, body in v.items(): out.setdefault(k, {})[n] = body
            else:
                out[k] = v
    return out
def resources(type_): return _merged("resource").get(type_, {})
def resource(type_, name):
    r = resources(type_).get(name)
    if r is None: _fail(f'resource "{type_}" "{name}" is missing')
    return r
def data(type_, name):
    r = _merged("data").get(type_, {}).get(name)
    if r is None: _fail(f'data "{type_}" "{name}" is missing')
    return r
def _named(kind, name, what):
    r = _merged(kind).get(name)
    if r is None: _fail(f'{what} "{name}" is missing')
    return r
def variable(name): return _named("variable", name, "variable")
def output(name): return _named("output", name, "output")
def provider(name): return _named("provider", name, "provider")
def module(name): return _named("module", name, "module")
def locals_():
    out = {}
    for item in TF.get("locals", []): out.update(item)
    return out
def ref(v):
    if isinstance(v, str) and v.startswith("${") and v.endswith("}"): return v[2:-1]
    return v
def block(body, name):
    b = body.get(name) if isinstance(body, dict) else None
    if b is None: _fail(f'block "{name}" is missing')
    return b[0] if isinstance(b, list) and b and isinstance(b[0], dict) else b
'''

_RUNNER = r'''
import sys, traceback
KIND, SRC, TEST, MODE = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
text = open(SRC, encoding="utf-8").read()
D = TF = y = None; docs = []
try:
    if KIND == "dockerfile":
        D = _parse_dockerfile(text)
    elif KIND == "yaml":
        import yaml
        docs = [d for d in yaml.safe_load_all(text) if d is not None]
        if not docs: raise SyntaxError("The file is empty")
        y = docs[0]
    elif KIND == "terraform":
        import hcl2, io
        TF = hcl2.load(io.StringIO(text))
except Exception as e:
    line = getattr(e, "problem_mark", None) or getattr(e, "line", None)
    where = f" (line {line.line + 1})" if hasattr(line, "line") else (f" (line {line})" if isinstance(line, int) else "")
    print(f"{type(e).__name__}{where}: {str(e).splitlines()[0] if str(e) else ''}", file=sys.stderr)
    sys.exit(1)
if MODE == "parse":
    sys.exit(0)
try:
    exec(compile(open(TEST, encoding="utf-8").read(), "test", "exec"), globals())
    print("OK")
except AssertionError as e:
    print("FAIL: " + (str(e) or "a check did not hold"))
except Exception as e:
    print(f"FAIL: {type(e).__name__}: {e}")
'''


def build_config(kind: str):
    ext = {"dockerfile": "Dockerfile", "yaml": "config.yaml", "terraform": "main.tf"}[kind]

    def build(student_code: str, tc: TestCasePayload, tmp: str) -> Build:
        src, test, prog = os.path.join(tmp, ext), os.path.join(tmp, "test.py"), os.path.join(tmp, "check.py")
        _write(src, student_code)
        _write(test, tc.test_code if tc.type == "code_sample" else "")
        _write(prog, _HELPERS + _RUNNER)
        py = os.getenv("CONFIG_PYTHON") or sys.executable  # a Python with PyYAML + python-hcl2
        return Build(compile=[py, prog, kind, src, test, "parse"], run=[py, prog, kind, src, test, "run"],
                     env={"PYTHONDONTWRITEBYTECODE": "1"})
    return build


def check_syntax(code: str, kind: str) -> list[dict]:
    """Editor checks while typing: where the file does not parse."""
    import io
    try:
        if kind == "yaml":
            import yaml
            list(yaml.safe_load_all(code))
        elif kind == "terraform":
            import hcl2
            hcl2.load(io.StringIO(code))
        elif kind == "dockerfile":
            ns: dict = {}
            exec(_HELPERS, ns)
            ns["_parse_dockerfile"](code)
        return []
    except Exception as e:
        mark = getattr(e, "problem_mark", None)
        line = mark.line + 1 if mark is not None else getattr(e, "line", None)
        msg = str(e).splitlines()[0] if str(e) else type(e).__name__
        if line is None and kind == "dockerfile":
            word = msg.split(": ", 1)[-1]
            for i, l in enumerate(code.splitlines(), 1):
                if l.strip().split(" ")[0] == word:
                    line = i
                    break
        return [{"line": int(line) if isinstance(line, int) else 1, "column": 1, "severity": "error", "message": msg[:300]}]


def git_available() -> bool:
    import shutil
    return bool(shutil.which("git", path=os.getenv("SANDBOX_PATH")))


def config_available(kind: str) -> bool:
    try:
        if kind == "yaml":
            import yaml  # noqa: F401
        if kind == "terraform":
            import hcl2  # noqa: F401
        return True
    except ImportError:
        return False


__all__ = ["build_git", "build_config", "check_syntax", "git_available", "config_available", "json", "shlex"]
