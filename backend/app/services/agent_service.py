"""
Strands-based AI agent for adaptive learning guidance.
The provider/model/key come from the admin's AI settings (bring your own key), see ai_config.py.
Every call is timed and recorded for the monitoring dashboard, see observability.py.
"""
import asyncio
import json
import re
import time

from strands import Agent

from app.core.language import Lang
from app.services import ai_config, observability


# ---------------------------------------------------------------------------
# Programming language of the task (C, C++, Java, Python)
# ---------------------------------------------------------------------------

PROG_NAMES = {"cpp": "C++", "c": "C", "java": "Java", "python": "Python", "javascript": "JavaScript", "sql": "SQL",
              "postgresql": "PostgreSQL", "typescript": "TypeScript", "php": "PHP", "bash": "Bash", "csharp": "C#",
              "kotlin": "Kotlin", "prolog": "Prolog", "lisp": "Common Lisp", "asm": "x86-64 assembly (NASM)",
              "web": "HTML/CSS/JavaScript", "uml": "UML class diagram", "er": "ER diagram",
              "usecase": "UML use case diagram", "state": "UML state machine diagram", "activity": "UML activity diagram",
              "component": "UML component diagram", "package": "UML package diagram", "deployment": "UML deployment diagram",
              "relational": "relational database schema", "sequence": "UML sequence diagram",
              "git": "Git (a Bash script of git commands)", "dockerfile": "Dockerfile",
              "yaml": "YAML (GitHub Actions / docker-compose / Kubernetes)", "terraform": "Terraform (HCL)"}
_FENCES = {"cpp": "cpp", "c": "c", "java": "java", "python": "python", "javascript": "javascript", "sql": "sql",
           "postgresql": "sql", "typescript": "typescript", "php": "php", "bash": "bash", "csharp": "csharp",
           "kotlin": "kotlin", "prolog": "prolog", "lisp": "lisp", "asm": "nasm", "web": "html", "uml": "json", "er": "json", "usecase": "json", "state": "json",
           "activity": "json", "component": "json", "package": "json", "deployment": "json", "relational": "json",
           "sequence": "json", "git": "bash", "dockerfile": "dockerfile", "yaml": "yaml", "terraform": "hcl"}


def _prog(prog_lang: str) -> str:
    return PROG_NAMES.get(prog_lang, "C++")


def _fence(prog_lang: str) -> str:
    return _FENCES.get(prog_lang, "cpp")


DIAGRAM_GUIDE = {
    "sequence": "Node types: actor (a person), lifeline (an object, named like \"k:Корисник\" or \":Контролер\"). "
                "Edges are the MESSAGES, listed in the order they happen (top to bottom): sync (a call, label = the "
                "operation, e.g. \"најди(id)\"), async (a signal), reply (the answer going back, label = what is "
                "returned), create (one object creates another). from = the sender, to = the receiver; a message to "
                "itself has from = to.",
    "uml": "Node types: class, abstract, interface, enum. Edges: association, aggregation / composition (from the WHOLE "
           "to the PART), inheritance / realization (from the CHILD to the PARENT), dependency; multiplicities like "
           "1, 0..1, 0..*, 1..*.",
    "er": "Node types: entity, weak (weak entity); attributes with \"pk\": true for primary keys. Edges: relationship, "
          "named with a verb in \"label\", cardinalities 1 / N / M at the two ends.",
    "usecase": "Node types: actor, usecase, system (the system boundary, a big box around the use cases). Edges: "
               "association (actor – use case), include and extend (from the base use case to the included one; for "
               "extend from the extension to the base), inheritance (from the specific actor/use case to the general).",
    "state": "Node types: state (its \"attributes\" are internal activities like \"entry / …\", \"do / …\"), initial, "
             "final, choice (unnamed pseudo-states are allowed). Edges: transition, from the source to the target state, "
             "\"label\" = \"event [guard] / action\".",
    "activity": "Node types: action, initial, final, flow_final, decision, merge, fork, join, swimlane (a partition: a "
                "big box). Edges: flow, from one step to the next; guards on flows leaving a decision go in \"label\" "
                "(e.g. \"[valid]\"). Give decisions a short question as their name.",
    "component": "Node types: component, interface, class. Edges: dependency (a component requires / uses an interface "
                 "or another component), realization (a component provides an interface), association.",
    "package": "Node types: package (its \"attributes\" list what it contains), class, interface. Edges: dependency, "
               "import, merge (from the client package to the supplier), inheritance.",
    "deployment": "Node types: node (an execution environment / server), device (hardware), artifact (a deployed file "
                  "like app.war), component. Edges: association (a communication path; protocol like HTTPS in "
                  "\"label\"), deploy (from the artifact to the node), dependency.",
    "relational": "Node types: table; \"attributes\" are the columns, with \"pk\": true for the primary key and "
                  "\"fk\": true for foreign keys (\"type\" = the SQL type). Edges: foreign_key, from the referencing "
                  "table to the referenced one, multiplicities like N (from) and 1 (to).",
}


def _harness_note(prog_lang: str, task_kind: str) -> str:
    """How the platform runs the student's code — the AI must not ask for things that would break it."""
    if prog_lang in DIAGRAM_GUIDE:
        what = PROG_NAMES[prog_lang]
        return (f"TASK KIND: DIAGRAM — the student draws a {what} in the platform's diagram editor (boxes and lines, not "
                "code). You see it as the editor's JSON: \"nodes\" are the boxes (with their \"type\" and listed "
                "\"attributes\"/\"methods\"); \"edges\" are the lines with their kind, label and the multiplicities at the "
                "\"from\" and \"to\" ends (ignore ids and x/y positions). " + DIAGRAM_GUIDE[prog_lang] + " Tests check that "
                "the right elements, their contents and the links between them exist. Talk about the diagram "
                "(\"add …\", \"the transition from … to …\"), never about JSON or code.")
    if prog_lang == "web":
        return ("TASK KIND: WEB PAGE (HTML/CSS/JavaScript). The student's work is several files in one text, separated by "
                "marker lines like `<!-- file: index.html -->`, `<!-- file: style.css -->`, `<!-- file: script.js -->`; "
                "index.html must link the others (<link rel=\"stylesheet\" href=\"style.css\">, "
                "<script src=\"script.js\"></script>). Tests open index.html in a real browser (no internet, so no CDN "
                "libraries or web fonts) and check the page: elements, texts, computed CSS, behaviour after clicks, "
                "layout at a phone width, and in visual tests how similar it looks to the teacher's solution. When you "
                "refer to code, name the file.")
    if prog_lang == "postgresql":
        return ("TASK KIND: SQL QUERY (PostgreSQL 16). Each test gets its own fresh database: the test creates and "
                "fills the tables, then runs the student's SQL; the rows of the student's LAST query (or, for "
                "INSERT/UPDATE/DELETE tasks, of the test's own check query) are compared with the expected table. "
                "Column names/aliases and row order don't matter unless the task asks for an order (ORDER BY). "
                "The student writes only SQL (PL/pgSQL functions are allowed) — no CREATE TABLE for the given tables.")
    if prog_lang == "sql" or task_kind == "query":
        return ("TASK KIND: SQL QUERY (SQLite dialect). Each test creates and fills the tables, then runs the "
                "student's SQL; the rows of the student's LAST query (or, for INSERT/UPDATE/DELETE tasks, of the "
                "test's own check query) are compared with the expected table. Column names/aliases and row order "
                "don't matter unless the task asks for an order (ORDER BY). The student writes only SQL — no "
                "program code, no CREATE TABLE for the given tables. Mention SQLite only if a PostgreSQL/MySQL-only "
                "feature (e.g. ILIKE, ::casts, SERIAL) is the problem.")
    if task_kind == "program":
        return ("TASK KIND: PROGRAM. The student writes the whole program; each test feeds standard input and "
                "compares standard output. "
                + {"java": "The program needs a class with public static void main.",
                   "python": "The program is top-level Python code that reads input() / sys.stdin.",
                   "javascript": "The program is a Node.js script that reads standard input, e.g. "
                                 "require('fs').readFileSync(0, 'utf8'), and prints with console.log.",
                   "typescript": "The program is a TypeScript (Node.js) script that reads standard input with "
                                 "require('fs').readFileSync(0, 'utf8'); it is type-checked with tsc first.",
                   "php": "The program is a PHP script that reads STDIN (fgets(STDIN), fscanf) and prints with echo.",
                   "bash": "The program is a Bash script that reads standard input (read) and prints with echo/printf.",
                   "csharp": "The program needs a class with static void Main; it reads Console.ReadLine().",
                   "kotlin": "The program needs fun main(); it reads input with readln() / readLine().",
                   "prolog": "The program defines main/0, which reads standard input and writes the answer (SWI-Prolog).",
                   "lisp": "The program is a Common Lisp script (SBCL): top-level forms that read *standard-input*.",
                   "asm": "The program is x86-64 NASM assembly with `main` (linked with gcc, can call printf/scanf) "
                          "or `_start` (linked with ld, uses syscalls).",
                   }.get(prog_lang, "The program needs its own main()."))
    return ("TASK KIND: FUNCTION. The student writes functions/classes only; the platform runs each test by calling "
            "them. " + {
                "java": "Only-methods code is placed inside the platform's test class (methods should be static); "
                        "student classes stay top-level. A student-written main() or public class Main would break the tests.",
                "python": "The test code is appended BELOW the student's code and run as one script, so the student "
                          "must not read input() or print anything at module level unless the task asks for it.",
                "javascript": "The test code is appended BELOW the student's code and run as one Node.js script "
                              "(CommonJS), so the student must not read stdin or print at the top level unless the "
                              "task asks for it, and must not use `export` / ES-module `import`.",
                "typescript": "The test code is appended BELOW the student's code; the whole file is type-checked "
                              "with tsc (type errors fail every test) and run with Node.js. No `export`/`import`.",
                "php": "The test code is appended BELOW the student's code in one PHP file, so the student must not "
                       "echo anything at the top level and must not end the file with ?>.",
                "bash": "The test commands are appended BELOW the student's script, so the student writes functions "
                        "and must not read input or echo at the top level unless the task asks for it.",
                "csharp": "Only-methods code is placed inside the platform's static test class (methods must be "
                          "static); student classes stay top-level. A student-written Main would break the tests.",
                "kotlin": "The platform adds `fun main() { <test> }` below the student's code, so the student must "
                          "not write their own main().",
                "prolog": "The student writes facts and rules (SWI-Prolog). Each test is a goal run after loading "
                          "them; a test that fails prints `false`. No main/0 is needed.",
                "lisp": "The student writes definitions (defun, defstruct...); each test's forms run after them "
                        "(SBCL). No top-level printing unless the task asks for it.",
                "git": "The student writes a Bash script of git commands. Each test runs it in a fresh, empty "
                       "directory (git is configured: user, e-mail, default branch main; there is no network, so no "
                       "clone/push/pull from the internet), then runs the test's own Bash commands in that directory "
                       "and compares what they print, e.g. `git log --oneline | wc -l` or `git branch --show-current`.",
                "dockerfile": DEVOPS_FILE_GUIDE + " Dockerfile helpers: stages() (FROM images), instr('RUN') "
                              "(all RUN arguments), first(name), last(name), has(name, text), user(), workdir(), "
                              "exposed() (ports as strings), env() (dict), cmd() / entrypoint() (lists), copies() "
                              "(list of (src, dst)). Nothing is built.",
                "yaml": DEVOPS_FILE_GUIDE + " YAML helpers: y (the first document), docs (all documents), "
                        "get(y, 'jobs.test.runs-on') (dotted path; numbers index lists; 'on' works for GitHub "
                        "Actions), find(obj, key) (every value of a key at any depth).",
                "terraform": DEVOPS_FILE_GUIDE + " Terraform helpers: resource('aws_s3_bucket', 'logs') (its "
                             "arguments as a dict), resources(type) (name -> body), variable(name), output(name), "
                             "provider(name), module(name), data(type, name), locals_(), ref(v) ('${var.x}' -> "
                             "'var.x'), block(body, 'versioning_configuration') (a nested block as a dict). "
                             "Nothing is planned or applied (no network, no providers).",
                "asm": "The student writes x86-64 NASM functions marked `global` that follow the System V ABI "
                       "(arguments in rdi, rsi, rdx, rcx, r8, r9; result in rax). Each test is C code inside main() "
                       "that calls them; the student must not write main or _start.",
            }.get(prog_lang, "Each test snippet is placed inside the platform's own main(), so a student-written "
                             "main() would break every test."))


DEVOPS_FILE_GUIDE = ("The student writes the whole file. Each test is Python code with plain `assert`s about "
                     "the parsed file (an assert message says what is missing); the test passes when it prints OK "
                     "(expected output: OK).")


class AIUnavailable(RuntimeError):
    """No usable API key (none configured, or it can't be decrypted)."""


def _make_agent(system_prompt: str, language: Lang = "en", prog_lang: str = "cpp") -> Agent:
    cfg = ai_config.current()
    if not cfg.api_key:
        raise AIUnavailable("No API key configured for the AI provider")
    prompt = (system_prompt + _language_instruction(language)).replace("C++", _prog(prog_lang))
    agent = Agent(model=ai_config.build_model(cfg), system_prompt=prompt, callback_handler=None)
    agent._ale_cfg = cfg  # remembered for the event record
    agent._ale_prog = prog_lang
    return agent


def _safe_error(e: Exception, key: str) -> str:
    msg = f"{type(e).__name__}: {e}"
    return msg.replace(key, ai_config.mask_key(key)) if key else msg


async def _invoke(agent: Agent, prompt: str, operation: str):
    """Run the (blocking) agent in a thread; record duration, tokens and outcome."""
    cfg: ai_config.AIConfig = getattr(agent, "_ale_cfg", ai_config.current())
    start = time.perf_counter()
    try:
        result = await asyncio.to_thread(agent, prompt)
    except Exception as e:
        await observability.record(
            "ai", operation, ok=False, duration_ms=round((time.perf_counter() - start) * 1000),
            provider=cfg.provider, model=cfg.model, prog_language=getattr(agent, "_ale_prog", ""),
            error=_safe_error(e, cfg.api_key),
        )
        raise
    usage = getattr(getattr(result, "metrics", None), "accumulated_usage", None) or {}
    await observability.record(
        "ai", operation, ok=True, duration_ms=round((time.perf_counter() - start) * 1000),
        provider=cfg.provider, model=cfg.model, prog_language=getattr(agent, "_ale_prog", ""),
        input_tokens=int(usage.get("inputTokens", 0) or 0), output_tokens=int(usage.get("outputTokens", 0) or 0),
    )
    return result


async def test_connection(cfg: "ai_config.AIConfig") -> dict:
    """Send a tiny prompt with a candidate configuration. Returns {ok, latency_ms, reply | error}."""
    if not cfg.api_key:
        return {"ok": False, "latency_ms": 0, "error": "No API key"}
    if not cfg.model:
        return {"ok": False, "latency_ms": 0, "error": "No model"}
    start = time.perf_counter()
    try:
        agent = Agent(model=ai_config.build_model(cfg), system_prompt="You are a connectivity check.", callback_handler=None)
        agent._ale_cfg = cfg
        result = await asyncio.wait_for(_invoke(agent, "Reply with exactly: OK", "test_connection"), timeout=45)
        return {"ok": True, "latency_ms": round((time.perf_counter() - start) * 1000), "reply": str(result).strip()[:200]}
    except Exception as e:
        return {"ok": False, "latency_ms": round((time.perf_counter() - start) * 1000), "error": _safe_error(e, cfg.api_key)[:500]}


# ---------------------------------------------------------------------------
# Response language
# ---------------------------------------------------------------------------

def _language_instruction(language: Lang) -> str:
    """Appended to every system prompt so all student-facing text is in the chosen language."""
    if language == "mk":
        return """

LANGUAGE: Write ALL student-facing text (titles, descriptions, feedback, hints, explanations) in Macedonian,
using the Cyrillic alphabet. Use standard Macedonian programming terminology as taught at Macedonian
universities (e.g. "функција", "класа", "променлива", "низа", "покажувач", "конструктор").
Keep C++ code, identifiers, keywords and compiler messages exactly as they are — do not translate code.
JSON keys and values like "correctness"/"optimization" and true/false must stay in English."""
    return """

LANGUAGE: Write all student-facing text in English."""


def _language_reminder(language: Lang) -> str:
    """Short reminder placed at the END of the user prompt — the task text and JSON examples are in English,
    so without it the model tends to drift back to English (or Latin transliteration) in titles."""
    if language == "mk":
        return (
            "\n\nIMPORTANT: every student-facing text field (title, description, feedback, hint, explanation) "
            "MUST be in Macedonian written in Cyrillic — including the title. Never write it in English and never "
            "transliterate Macedonian into Latin letters (wrong: \"Implementiraj\", \"Implement resizing\"; "
            "right: \"Имплементирај зголемување во push()\"). Code identifiers such as push() stay as they are."
        )
    return "\n\nIMPORTANT: every student-facing text field must be in English."


# ---------------------------------------------------------------------------
# Next-step generation (adaptive: one step at a time, based on the student's code)
# ---------------------------------------------------------------------------

NEXT_STEP_SYSTEM_PROMPT = """You are an expert programming tutor specializing in C++ for undergraduate students.
You guide a student through a programming task ONE STEP AT A TIME. You never give a full plan.
Each time you are called, look at the student's CURRENT code and decide the single most useful next step.

How to choose the next step:
1. Compare the student's current code against the task requirements (the model solution is only for your
   reference — the student may solve it differently, and that is fine).
2. Pick the ONE most important thing that is still missing or wrong. Prefer, in this order:
   a) code that does not compile or has an obvious logic error,
   b) required classes/functions/behaviour that are not implemented yet,
   c) edge cases and required error handling,
   d) only when everything above is done: code quality / optimization.
3. If the student already implemented more than the previous step asked for, skip ahead — never ask for
   something that is already present and correct.
4. Do not repeat a step that is already completed unless the current code broke it again.
5. The step must be small (achievable in 5-15 minutes by an intermediate student) but meaningful:
   a step is a piece of working behaviour (e.g. "implement greet so it returns the greeting"),
   not a purely syntactic fragment (e.g. do NOT make a step that is only "declare the function
   without a body" or "add an #include").
6. Be concrete and actionable — say exactly WHAT to do, but do NOT write the solution code for them
   and do NOT reveal the model solution.

Never ask the student to:
- write a test program or test/demo code — the platform runs the tests automatically (see TASK KIND:
  for FUNCTION tasks an extra main()/entry point written by the student would BREAK every test; for PROGRAM
  tasks the student does write the whole program, including the part that reads the input);
- add anything the task requirements do not ask for (extra methods, input/output, extra features).
An "optimization" step is allowed only for a real problem in the student's code that relates to the
requirements (e.g. a memory leak or an obvious inefficiency) — never just to give the student more work.

AUTOMATIC TEST RESULTS are the ground truth about behaviour: the platform really compiled and ran the
student's current code against all of the task's tests before asking you.
- If a test fails, the next step must address the cause of that failure (compile error first).
- NEVER propose a step for behaviour that passing tests already show works (e.g. do not ask to "handle n == 0"
  when a test with n == 0 passes, and do not ask for special cases that the general code already handles).
- If ALL tests pass, the task is solved: set "done" to true. Only if the task text explicitly requires
  something the tests cannot check (e.g. freeing memory in a destructor) and the code clearly lacks it,
  you may instead return ONE "optimization" step for exactly that.
- Some tests are hidden from the student: never quote their input or expected output; describe the problem
  in general terms instead.

When the student's code satisfies ALL task requirements, set "done" to true. Do not invent extra steps.

Explain, don't just instruct. Students learn more when they know WHY. For every step also give:
- "why": 1-3 sentences on the PURPOSE of the step — which goal of the whole task it serves and the idea behind
  it. Example (building a number from its digits): "Multiplying by 10 moves every digit one place to the left,
  so the next digit fits in the units place: 4 → 47 → 472. That is how a one-digit number grows into a
  two-, three-digit one." Concrete, with a tiny example when it helps; never the solution code.
- "tip": ONE extra, genuinely informative fact connected to the step: a concept behind it, a common mistake,
  or where this is used in real programs (e.g. "The same idea turns the text '472' into the number 472 —
  that is what atoi / int() do."). Short. Never the solution.

You MUST respond with valid JSON only, no markdown fences, in this exact format:
{
  "done": false,
  "title": "Short title (max 60 chars)",
  "description": "What the student should do in this step (1-3 sentences).",
  "why": "Why this step / the idea behind it (1-3 sentences).",
  "tip": "One extra useful fact (1-2 sentences).",
  "step_type": "correctness"
}
"step_type" is "correctness" for steps a)-c) and "optimization" for step d).
When "done" is true, "title", "description", "why" and "tip" may be empty strings.
"""


def _fix_escapes(text: str) -> str:
    """Double every backslash that does not start a valid JSON escape (pairs like \\\\ are kept as they are)."""
    return re.sub(r"\\(.?)", lambda m: m.group(0) if m.group(1) and m.group(1) in '"\\/bfnrtu'
                  else "\\\\" + m.group(1), text, flags=re.S)


def _loads(text: str):
    """json.loads that also accepts what models often write inside strings: raw newlines/tabs and
    backslashes that are not JSON escapes (e.g. Prolog's `A \\== B` or a LaTeX `\\(`)."""
    try:
        return json.loads(text, strict=False)
    except json.JSONDecodeError:
        return json.loads(_fix_escapes(text), strict=False)


def _parse_json_object(text: str) -> dict:
    text = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`").strip()
    try:
        data = _loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise
        data = _loads(match.group())
    if not isinstance(data, dict):
        raise ValueError("Expected a JSON object")
    return data


async def generate_next_step(
    task_requirements: str,
    model_solution: str,
    student_code: str,
    completed_steps: list[str],
    language: str = "cpp",
    response_language: Lang = "en",
    test_report: str | None = None,
    task_kind: str = "function",
    approach: str = "",
    previous_approaches: list[str] | None = None,
) -> dict:
    """Decide the single next step for the student.

    approach: the student is writing ANOTHER solution of the task following this approach ("" = the first one);
    previous_approaches: how their earlier solutions solved it (this one must be different).

    test_report: summary of really running the task's tests on student_code (None if not available).

    Returns {done: bool, title: str, description: str, step_type: "correctness"|"optimization"}.
    Raises RuntimeError if the agent's answer cannot be parsed.
    """
    completed_text = (
        "\n".join(f"{i + 1}. {t}" for i, t in enumerate(completed_steps))
        if completed_steps else "(none yet — this is the first step)"
    )
    prompt = f"""Task requirements:
{task_requirements}

Model solution (for your reference only — do not reveal it):
{model_solution}

Programming language: {_prog(language)}
{_harness_note(language, task_kind)}

Steps the student has already completed:
{completed_text}

Student's CURRENT code:
```{_fence(language)}
{student_code}
```

AUTOMATIC TEST RESULTS for the CURRENT code:
{test_report or "(not available — judge from the code)"}
{_approach_note(approach, previous_approaches)}
Decide the single next step. Respond with JSON.{_language_reminder(response_language)}"""

    agent = _make_agent(NEXT_STEP_SYSTEM_PROMPT, response_language, language)
    result = await _invoke(agent, prompt, "next_step")
    text = str(result)

    try:
        data = _parse_json_object(text)
    except (json.JSONDecodeError, ValueError):
        raise RuntimeError(f"Agent returned invalid next-step JSON: {text[:200]}")

    step_type = data.get("step_type", "correctness")
    if step_type not in ("correctness", "optimization"):
        step_type = "correctness"
    return {
        "done": bool(data.get("done", False)),
        "title": str(data.get("title", "")).strip()[:500],
        "description": str(data.get("description", "")).strip(),
        "why": str(data.get("why", "") or "").strip()[:2000],
        "tip": str(data.get("tip", "") or "").strip()[:1000],
        "step_type": step_type,
    }


def _approach_note(approach: str, previous: list[str] | None) -> str:
    if not approach:
        return ""
    prev = "\n".join(f"- {p}" for p in (previous or []) if p) or "- (the first, free solution)"
    return f"""
ANOTHER SOLUTION: the student already solved this task and is now writing a DIFFERENT solution, following this
approach: {approach}
Their earlier solution(s) used:
{prev}
Guide them along THIS approach (even if the model solution uses another one). The task is done only when the
tests pass AND the code really follows this approach — if the tests pass but the code is just the earlier
solution again, it is not done.
"""


ALTERNATIVES_SYSTEM_PROMPT = """You are a C++ programming tutor. A student has just finished a task (all tests pass).
Tell them whether the task can be solved in other, genuinely DIFFERENT ways that are worth writing as a separate
solution to learn something (a different algorithm or data structure, recursion vs. iteration, a library
facility vs. by hand, a different time/space trade-off…). Cosmetic differences (other variable names, a for
instead of a while doing the same thing, reordering) do NOT count.

How many solutions in total (including the ones already written) make sense:
- a small task (a few lines, one obvious idea): at most 2, often only 1 — then return an empty list;
- a medium task: at most 3;
- a large task (several functions / classes, several ideas): at most 5.
Never list an approach the student already used.

You MUST respond with valid JSON only, no markdown fences:
{"size": "small" | "medium" | "large",
 "alternatives": [{"title": "Short name of the approach (max 60 chars)",
                   "idea": "1-2 sentences: what is different and what the student learns from it (no code)"}]}
"""

_MAX_SOLUTIONS = {"small": 2, "medium": 3, "large": 5}


async def alternative_solutions(task_requirements: str, model_solution: str, student_code: str, language: str,
                                done_approaches: list[str], solutions_written: int,
                                response_language: Lang = "en") -> list[dict]:
    """Other ways to solve the task, for "write another solution". [] if there is essentially one way or the
    student already wrote as many as make sense (at most 5 in total). Never raises: [] on any problem."""
    if solutions_written >= 5:
        return []
    done = "\n".join(f"- {a}" for a in done_approaches if a) or "- (only the one below)"
    prompt = f"""Task requirements:
{task_requirements}

Model solution (reference only):
{model_solution}

Programming language: {_prog(language)}

The student has written {solutions_written} solution(s). Approaches already used:
{done}

Their latest solution:
```{_fence(language)}
{student_code}
```

Respond with JSON.{_language_reminder(response_language)}"""
    try:
        agent = _make_agent(ALTERNATIVES_SYSTEM_PROMPT, response_language, language)
        data = _parse_json_object(str(await _invoke(agent, prompt, "alternatives")))
    except AIUnavailable:
        return []
    except Exception:
        return []
    size = data.get("size") if data.get("size") in _MAX_SOLUTIONS else "medium"
    room = max(0, _MAX_SOLUTIONS[size] - solutions_written)
    out = []
    for a in data.get("alternatives") or []:
        if isinstance(a, dict) and str(a.get("title", "")).strip():
            out.append({"title": str(a["title"]).strip()[:120], "idea": str(a.get("idea", "") or "").strip()[:600]})
    return out[:room]


# ---------------------------------------------------------------------------
# Step evaluation
# ---------------------------------------------------------------------------

EVAL_SYSTEM_PROMPT = """You are an expert C++ programming tutor evaluating a student's code.
Be encouraging but honest. Focus on whether the current step's GOAL is achieved.

How to decide "passed":
- The step is a minimum requirement, not an exact specification. If the code achieves the step's goal,
  it PASSES — even if the student went further than the step asked (e.g. the step asked to declare a
  function and the student also implemented its body), or solved it in a different but correct way.
- NEVER fail a student for doing more than the step asked, and never ask them to remove working code.
- Fail only if the step's goal is missing, incorrect, or the relevant code would not compile.
- Judge only what the current step is about; problems that belong to later parts of the task are not a
  reason to fail this step (you may mention them briefly in the feedback).

You MUST respond with valid JSON only (no markdown), in this exact format:
{
  "passed": true/false,
  "feedback": "Concise feedback (2-4 sentences). If passed: say what was achieved AND briefly WHY it works (the idea behind it, e.g. what a loop variable means at each pass), so the student understands rather than just gets a tick. If failed: specific guidance on what is still missing or wrong for THIS step, and why it matters."
}
Do not announce or describe a "next step" in the feedback — the next step is decided separately after
this one passes. When failed, refer to what is missing as part of the current step.
"""


async def evaluate_step(
    step_title: str,
    step_description: str,
    student_code: str,
    task_requirements: str,
    attempt_number: int = 1,
    response_language: Lang = "en",
    prog_language: str = "cpp",
) -> dict:
    """Returns {passed: bool, feedback: str}."""
    prompt = f"""Task requirements (for context):
{task_requirements}

Current step to evaluate:
Title: {step_title}
What the student should have done: {step_description}

Student's code (attempt #{attempt_number}):
```{_fence(prog_language)}
{student_code}
```

Does this code satisfy the current step? Respond with JSON.{_language_reminder(response_language)}"""

    agent = _make_agent(EVAL_SYSTEM_PROMPT, response_language, prog_language)
    result = await _invoke(agent, prompt, "evaluate")
    text = str(result)
    try:
        data = _parse_json_object(text)
    except (json.JSONDecodeError, ValueError):
        # Not JSON at all: show the answer as feedback rather than failing the check.
        return {"passed": False, "feedback": re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`").strip()}
    return {"passed": bool(data.get("passed", False)), "feedback": str(data.get("feedback", ""))}


# ---------------------------------------------------------------------------
# Error explanation
# ---------------------------------------------------------------------------

EXPLAIN_SYSTEM_PROMPT = """You are a C++ programming tutor helping a student understand why their code failed.

Rules:
- Explain the root cause of the error in plain language (no jargon).
- Point to the specific line or construct that caused it.
- Give ONE clear, actionable fix — what exactly the student needs to add or change.
- Do not write the full corrected code for them.
- Keep it to 4-6 sentences.
"""


async def explain_test_errors(
    student_code: str,
    errors: list[str],
    task_requirements: str,
    response_language: Lang = "en",
    prog_language: str = "cpp",
) -> str:
    errors_text = "\n---\n".join(errors)
    prompt = f"""Task requirements (for context):
{task_requirements}

Student's code:
```{_fence(prog_language)}
{student_code}
```

Errors from the test runner:
{errors_text}

Explain what is wrong and how to fix it.{_language_reminder(response_language)}"""

    agent = _make_agent(EXPLAIN_SYSTEM_PROMPT, response_language, prog_language)
    result = await _invoke(agent, prompt, "explain")
    return str(result).strip()


# ---------------------------------------------------------------------------
# Hint generation
# ---------------------------------------------------------------------------

HINT_SYSTEM_PROMPT = """You are a helpful C++ programming tutor giving a hint to a student.
Rules:
- Give ONE specific, actionable hint.
- Do NOT give the answer or write code for them.
- Keep it to 2-3 sentences.
- Be encouraging.
"""


async def get_hint(
    step_title: str,
    step_description: str,
    student_code: str,
    response_language: Lang = "en",
    prog_language: str = "cpp",
    operation: str = "hint",
) -> str:
    """A hint for the current step (or, with operation="task_hint", for the whole task during an assignment that
    allows only a limited number of hints — those calls are counted)."""
    prompt = f"""Current step: {step_title}
What the student should implement: {step_description}

Student's current code:
```{_fence(prog_language)}
{student_code}
```

Give a hint to help them move forward without revealing the solution.{_language_reminder(response_language)}"""

    agent = _make_agent(HINT_SYSTEM_PROMPT, response_language, prog_language)
    result = await _invoke(agent, prompt, operation)
    return str(result).strip()


EMAIL_SYSTEM_PROMPT = """You write short, clear e-mails from a university teacher (Faculty of Computer Science and Engineering,
Skopje) to the students of a course. You get the facts and a first draft; improve it.
Rules:
- Keep EVERY fact exactly: titles, dates and times, links, numbers. Never invent facts, rooms or rules.
- Polite, warm and professional; short paragraphs; no emojis; at most ~120 words.
- Write a Macedonian version (correct Cyrillic, formal "Вие" form) and an English version with the same content.
- Keep the teacher's signature at the end.
- Answer ONLY with JSON: {"subject_mk": "...", "body_mk": "...", "subject_en": "...", "body_en": "..."}
"""


async def draft_email(facts: str, current: dict, notes: str = "") -> dict:
    """A better version of a course e-mail in both languages, for the teacher to check before sending."""
    prompt = f"""FACTS:
{facts}

CURRENT DRAFT (Macedonian):
Subject: {current.get('subject_mk', '')}
{current.get('body_mk', '')}

CURRENT DRAFT (English):
Subject: {current.get('subject_en', '')}
{current.get('body_en', '')}

TEACHER'S WISHES: {notes or '(none)'}"""
    agent = _make_agent(EMAIL_SYSTEM_PROMPT, "mk", "cpp")
    data = _parse_json_object(str(await _invoke(agent, prompt, "draft_email")))
    return {k: str(data.get(k, current.get(k, ""))).strip() for k in ("subject_mk", "body_mk", "subject_en", "body_en")}


TRANSLATE_SYSTEM_PROMPT = """You translate programming assignments for a university (Faculty of Computer Science, Skopje)
between Macedonian and English.
Rules:
- Translate the title and the Markdown description faithfully; keep the same structure, lists, tables and emphasis.
- Do NOT translate anything inside backticks or code blocks, identifiers, function names, file names, column names,
  sample input/output, or text the program must print exactly.
- Use correct academic terminology (Macedonian: низа, функција, променлива, класа, стек, барање, излез, влез...).
- Answer ONLY with JSON: {"title": "...", "description": "..."}
"""


# ---------------------------------------------------------------------------
# Diagrams: the teacher's solution from the task text, and reading a student's picture of a diagram
# ---------------------------------------------------------------------------

_DIAGRAM_FORMAT = """Answer with ONLY a JSON object:
{"nodes": [{"id": "n1", "name": "...", "aliases": ["..."], "type": "(see the node types of this diagram)",
            "attributes": [{"name": "...", "aliases": ["..."], "type": "...", "visibility": "-|+|#|", "pk": false, "fk": false}],
            "methods": [{"name": "...", "params": "...", "returns": "...", "visibility": "+"}]}],
 "edges": [{"from": "n1", "to": "n2", "kind": "(see the edge kinds of this diagram)",
            "fromMult": "...", "toMult": "...", "label": "..."}]}
fromMult is written at the "from" end, toMult at the "to" end. Pseudo-nodes (initial, final, decision, fork…) may have
an empty name. "methods" only for classes."""

DIAGRAM_DRAFT_PROMPT = """You are a university teacher of software design and databases. From the task description, draw the
model solution as a diagram.
Rules:
- Use exactly the names the task uses (in the task's language); add 1-3 "aliases" per class/entity/attribute: the
  same name in the other language (Macedonian <-> English) and common synonyms, so students' names are accepted.
- Follow the notation of THIS kind of diagram (below): its node types, edge kinds and edge directions.
- Class diagrams: attributes with types and visibility, the methods the task asks for, multiplicities. ER and
  relational schemas: mark primary keys ("pk": true) and, in tables, foreign keys ("fk": true). State and activity
  diagrams: one initial node, the final node(s), every step reachable; labels on transitions / guards on flows.
- Only what the task asks for or clearly implies — no extra elements.
""" + _DIAGRAM_FORMAT

DIAGRAM_READ_PROMPT = """You read a student's diagram from a picture (a photo, a scan or an export from a drawing tool).
Transcribe EXACTLY what is drawn — do not correct mistakes, do not add anything that is not in the picture, do not
complete missing parts: the result is graded. Keep the student's names and spelling. Do not add "aliases".
If a part can't be read, leave it out.
""" + _DIAGRAM_FORMAT


async def _vision(system: str, text: str, images: list[bytes], operation: str) -> str:
    """One request with pictures, straight to the provider's SDK (the agent library does not pass pictures on)."""
    import base64
    cfg = ai_config.current()
    if not cfg.api_key:
        raise AIUnavailable("No API key configured for the AI provider")
    pics = [base64.b64encode(p).decode() for p in images]
    start = time.perf_counter()
    try:
        if cfg.provider == "anthropic":
            from anthropic import AsyncAnthropic
            client = AsyncAnthropic(api_key=cfg.api_key)
            content = [{"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": p}} for p in pics]
            r = await client.messages.create(model=cfg.model, max_tokens=16000, system=system,
                                             messages=[{"role": "user", "content": content + [{"type": "text", "text": text}]}])
            out = "".join(getattr(b, "text", "") for b in r.content)
            tokens = (r.usage.input_tokens, r.usage.output_tokens)
        else:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=cfg.api_key,
                                 base_url=cfg.base_url if cfg.provider == "openai_compatible" and cfg.base_url else None)
            content = [{"type": "text", "text": text}] + \
                [{"type": "image_url", "image_url": {"url": f"data:image/png;base64,{p}", "detail": "high"}} for p in pics]
            r = await client.chat.completions.create(model=cfg.model, max_tokens=16000,
                                                     messages=[{"role": "system", "content": system}, {"role": "user", "content": content}])
            out = r.choices[0].message.content or ""
            tokens = (r.usage.prompt_tokens if r.usage else 0, r.usage.completion_tokens if r.usage else 0)
    except Exception as e:
        await observability.record("ai", operation, ok=False, duration_ms=round((time.perf_counter() - start) * 1000),
                                   provider=cfg.provider, model=cfg.model, error=_safe_error(e, cfg.api_key))
        raise
    await observability.record("ai", operation, ok=True, duration_ms=round((time.perf_counter() - start) * 1000),
                               provider=cfg.provider, model=cfg.model, input_tokens=tokens[0], output_tokens=tokens[1])
    return out


async def diagram_draft(description: str, kind: str, extra_text: str = "", images: list[bytes] | None = None) -> dict:
    """The model solution of a diagram task, drawn by AI from the task text (and a PDF's text or pages)."""
    prompt = f"""DIAGRAM: {PROG_NAMES.get(kind, kind).upper()}
NOTATION: {DIAGRAM_GUIDE.get(kind, '')}

TASK DESCRIPTION:
{description or '(see the attached pages)'}

{('TEXT OF THE ATTACHED DOCUMENT:' + chr(10) + extra_text[:30_000]) if extra_text else ''}"""
    if images:
        raw = await _vision(DIAGRAM_DRAFT_PROMPT, prompt, images, "diagram_draft")
    else:
        agent = _make_agent(DIAGRAM_DRAFT_PROMPT, "en", kind)
        raw = str(await _invoke(agent, prompt, "diagram_draft"))
    return _parse_json_object(raw)


async def diagram_read(images: list[bytes], kind: str, task_text: str = "") -> dict:
    """A student's drawing as a diagram (exactly as drawn), from pictures."""
    prompt = (f"The picture shows a student's {PROG_NAMES.get(kind, kind)}.\nNOTATION: {DIAGRAM_GUIDE.get(kind, '')}\n"
              f"The task (for context only — do not use it to fix the drawing):\n{task_text[:3000]}")
    return _parse_json_object(await _vision(DIAGRAM_READ_PROMPT, prompt, images, "diagram_read"))


SUGGEST_TESTS_SYSTEM_PROMPT = """You write automatic tests for programming tasks of a university course.
You get the task description, the programming language, the teacher's model solution and the tests that already exist.
Propose NEW tests that check what the description asks for — typical cases first, then edge cases. Do not repeat
existing tests. The model solution must pass every test you write.
Answer with ONLY a JSON object: {"tests": [{"title": "...", "type": "code_sample" | "stdin_stdout",
"test_code": "...", "stdin": "...", "expected_output": "...", "hidden": true | false}]}
- "title": a few words saying what the test checks, in the language of the task description.
- Mark about a third of them (the edge cases) "hidden": true.
- expected_output must be exactly what the model solution prints (if unsure, leave it "" — the teacher fills it by
  running the model solution).
"""

_TEST_FORMATS = {
    "web": """FORMAT FOR THIS LANGUAGE (web page): type "code_sample". test_code is JavaScript that runs inside the loaded
page and prints with print(...); expected_output is what it prints. Helpers: $(sel), $$(sel), exists(sel), count(sel),
text(sel) (trimmed text), attr(sel, name), css(sel, prop) (computed value, e.g. "flex", "16px", "rgb(39, 71, 201)"),
hex(sel, prop) (a colour as "#2747c9"), visible(sel), rect(sel) ({x, y, width, height}), await click(sel),
await type(sel, value), await sleep(ms). Examples:
  print(count('nav a'))                                   -> 4
  print(css('.cards', 'display'))                          -> grid
  await click('#add'); print(count('li'))                  -> 1
  // viewport: 375x667   (first line: test at a phone width)
  print(css('nav', 'flex-direction'))                      -> column
One visual test compares the page with the model solution: test_code "// visual: 85" and expected_output "".
Use one check per test; prefer stable facts (structure, computed styles, behaviour) over exact pixel sizes.
Write them like a professional web teacher, covering in this order:
1. structure and semantics: the elements, ids / classes and texts the task names; landmarks (nav, main, header, form),
   headings, lists; counts (count('…')).
2. accessibility: every form field has a <label for>, images have alt, buttons have text, <html lang>.
3. styles the task asks for, as computed values: colours with hex(), display flex / grid, directions, gaps, radii,
   widths; centring checked with rect() against document.documentElement.clientWidth (± a few px).
4. responsive layout: at least one test that starts with `// viewport: 375x667` and checks that things stack
   (rect(a).y < rect(b).y) or the number of grid columns (css(sel, 'grid-template-columns').split(' ').length).
5. behaviour (JavaScript tasks): click / type, then check the DOM — including edge cases (empty or wrong input,
   clicking twice).
6. exactly one visual test.
Check what the description demands, never one particular way of writing the code; a check over a list should also
check the list is not empty (count(…) === 3 && …every(…)).""",
    "sql": """FORMAT FOR THIS LANGUAGE (SQL): type "code_sample"; test_code creates and fills the tables (CREATE TABLE +
INSERT); the student's query runs after it; expected_output is the result table: a header line and rows, columns
separated by "|".""",
    "postgresql": """FORMAT FOR THIS LANGUAGE (PostgreSQL): as for SQL — test_code creates and fills the tables;
expected_output is the result table, columns separated by "|" with a header line.""",
}


async def suggest_tests(description: str, language: str, model_solution: str, existing: list[dict], kind: str,
                        count: int = 5) -> list[dict]:
    """Draft tests for the teacher to review (they are never saved without the teacher)."""
    fmt = _TEST_FORMATS.get(language) or (
        "FORMAT: " + ("type \"stdin_stdout\": stdin is the program's input, expected_output its exact output."
                      if kind == "program" else
                      "type \"code_sample\": test_code is code that calls the student's functions/classes and prints the "
                      "result; expected_output is the exact printed text."))
    shown = "\n".join(f"- {t.get('test_code') or ''} {('stdin: ' + t['stdin']) if t.get('stdin') else ''} -> "
                      f"{t.get('expected_output', '')}" for t in existing[:30]) or "(none)"
    prompt = f"""LANGUAGE: {_prog(language)}
{_harness_note(language, kind)}
{fmt}

TASK DESCRIPTION:
{description}

MODEL SOLUTION:
{model_solution or '(none)'}

EXISTING TESTS:
{shown}

Write {count} new tests."""
    agent = _make_agent(SUGGEST_TESTS_SYSTEM_PROMPT, "en", language)
    data = _parse_json_object(str(await _invoke(agent, prompt, "suggest_tests")))
    out = []
    for t in (data.get("tests") or [])[:12]:
        if not isinstance(t, dict):
            continue
        typ = "stdin_stdout" if t.get("type") == "stdin_stdout" and language != "web" else "code_sample"
        out.append({"title": str(t.get("title", ""))[:200], "type": typ, "test_code": str(t.get("test_code", ""))[:20_000],
                    "stdin": str(t.get("stdin", ""))[:20_000] if typ == "stdin_stdout" else "",
                    "expected_output": str(t.get("expected_output", ""))[:20_000], "is_hidden": bool(t.get("hidden"))})
    return out


async def translate_task(title: str, description: str, source: Lang, target: Lang) -> dict:
    """A draft translation of a task for the teacher to check (never shown to students without saving)."""
    names = {"mk": "Macedonian", "en": "English"}
    prompt = f"""Translate from {names[source]} to {names[target]}.

TITLE:
{title}

DESCRIPTION (Markdown):
{description}"""
    agent = _make_agent(TRANSLATE_SYSTEM_PROMPT, target, "cpp")
    data = _parse_json_object(str(await _invoke(agent, prompt, "translate_task")))
    return {"title": str(data.get("title", "")).strip(), "description": str(data.get("description", "")).strip()}


IMPROVE_SYSTEM_PROMPT = """You are a programming teacher reviewing a student's solution that already passes all tests.
Suggest how to make it better: readability (names, structure, repetition), efficiency (complexity, needless work),
robustness (edge cases the tests may miss), and idiomatic use of the language.
Rules:
- At most 3 suggestions, most valuable first, each 1-2 sentences, as a short Markdown list.
- Point to the exact place (line, variable or construct) each suggestion is about.
- Do NOT rewrite the whole solution; a tiny snippet (max 3 lines) is fine when it makes a point clearer.
- If the solution is already clean, say so briefly and give one optional idea.
"""


async def improve_solution(task_title: str, task_description: str, student_code: str,
                           response_language: Lang = "en", prog_language: str = "cpp") -> str:
    """Suggestions for improving a solution that passes every test (counted when the assignment limits them)."""
    prompt = f"""Task: {task_title}
{task_description}

Student's solution (passes all tests):
```{_fence(prog_language)}
{student_code}
```

Give your suggestions.{_language_reminder(response_language)}"""
    agent = _make_agent(IMPROVE_SYSTEM_PROMPT, response_language, prog_language)
    return str(await _invoke(agent, prompt, "task_improve")).strip()


# ---------------------------------------------------------------------------
# Test-case visualization (step-by-step trace of an example test)
# ---------------------------------------------------------------------------

VISUALIZE_SYSTEM_PROMPT = """You are a C++ tutor who helps students UNDERSTAND a programming task by visualizing
how an example test runs, step by step, assuming a CORRECT solution.

You get: the task requirements, a reference solution (for computing correct behaviour only — never show its
code), and one example test. A test is either:
- "code_sample": a snippet that calls the student's classes/functions (inside main() in C/C++/Java,
  appended after the solution in Python), or
- "stdin_stdout": a full program reads the given standard input and prints output.
For SQL tasks the test code creates and fills tables and the solution is a query. Then each frame is one
logical step of evaluating the query (FROM/JOIN, WHERE, GROUP BY + aggregates, HAVING, SELECT, ORDER BY),
"line" is 0, "code" names the clause (e.g. "JOIN ocena ON ..."), "structures" show the input tables and the
intermediate result as "table" structures (highlight the rows that are kept/joined/changed), and "output" is
the final result table only in the last frame (header line, then rows, cells separated by " | ").

Produce a short trace of "frames". Each frame is one meaningful moment of execution (usually one statement of
the test; for stdin tests, one logical processing step such as reading a value or handling one input line).
For each frame describe the state AFTER that moment:
- "line": 1-based line number in the test snippet that is executing (for stdin tests, the line of stdin being
  processed, or 0 if not tied to a line),
- "code": that line's text (or a short description for stdin tests),
- "explanation": 1-2 short sentences: what happens and why, in plain language for a student,
- "structures": the relevant data/objects and their state, each one of:
    {"name": "s", "kind": "stack", "items": ["1", "2", "3"], "highlight": [2]}       (items bottom -> top)
    {"name": "v", "kind": "array", "items": ["4", "7"], "highlight": []}             (array/vector/list)
    {"name": "q", "kind": "queue", "items": ["a", "b"], "highlight": [0]}            (front -> back)
    {"name": "c", "kind": "object", "type": "Circle", "fields": [{"name": "radius", "value": "5"}]}
    {"name": "x", "kind": "value", "value": "42"}
    {"name": "student", "kind": "table", "columns": ["id", "ime"], "rows": [["1", "Ана"], ["2", "Марко"]], "highlight": [1]}
                                                                                     (SQL tables / intermediate results)
  "highlight" = indices of items that just changed or are being accessed (may be empty).
  Show internal state only at the level a student thinks about (e.g. stack elements, not capacity/pointers),
  unless the task is about that internal state.
- "output": the COMPLETE program output so far (cumulative), exactly as printed.
- "exception": the exception message if this frame throws/catches one, otherwise "".
- "focus": the "name" of the structure being processed / explained RIGHT NOW (the one the student's eye should
  be on), or "" if none; "focus_index": the index of the item / row being processed in it (-1 if not an item);
  "focus_field": for an object, the field being processed ("" otherwise).
- "why": 1-2 sentences on WHY this moment matters — its purpose in reaching the result (e.g. "×10 shifts the
  digits left so the next digit fits in the units place: 4 → 47"). "" if the explanation already says it.
- "tip": optionally ONE extra informative fact connected to this moment (a concept, a pitfall, real-world
  use); "" in most frames — use it only where it really adds something.

Rules:
- Use as many frames as the student needs to understand the run — every meaningful moment, including each
  loop iteration that teaches something (typically 6-40). For very long loops show the first iterations in
  full, then one frame that summarizes the repetition, then the end. Skip trivial lines (#include, braces).
  Keep values as strings.
- The output of the last frame must equal the test's expected output.
- Never reveal or describe the implementation of the solution — only observable behaviour and state.

You MUST respond with valid JSON only, no markdown fences, in this format:
{"frames": [ {"line": 1, "code": "...", "explanation": "...", "why": "", "tip": "", "focus": "v", "focus_index": 0,
               "focus_field": "", "structures": [...], "output": "", "exception": ""} ]}
"""

_STRUCT_KINDS = ("stack", "array", "queue", "object", "value", "table")
MAX_FRAMES = 120  # only a safety limit: the AI decides how many moments the run needs


def _clean_frames(data: dict) -> list[dict]:
    """Coerce the agent's JSON into the exact shape the frontend expects."""
    frames_in = data.get("frames") if isinstance(data, dict) else None
    if not isinstance(frames_in, list) or not frames_in:
        raise ValueError("No frames")

    def s(v) -> str:
        return "" if v is None else str(v)

    frames = []
    for f in frames_in[:MAX_FRAMES]:
        if not isinstance(f, dict):
            continue
        structs = []
        for st in f.get("structures") or []:
            if not isinstance(st, dict):
                continue
            kind = st.get("kind") if st.get("kind") in _STRUCT_KINDS else "value"
            item = {"name": s(st.get("name")), "kind": kind, "type": s(st.get("type")),
                    "items": [], "highlight": [], "fields": [], "value": s(st.get("value")),
                    "columns": [], "rows": []}
            if kind in ("stack", "array", "queue"):
                item["items"] = [s(x) for x in (st.get("items") or [])][:50]
                item["highlight"] = [h for h in (st.get("highlight") or [])
                                     if isinstance(h, int) and 0 <= h < len(item["items"])]
            elif kind == "table":
                item["columns"] = [s(c) for c in (st.get("columns") or [])][:12]
                item["rows"] = [[s(c) for c in r][:12] for r in (st.get("rows") or []) if isinstance(r, list)][:30]
                item["highlight"] = [h for h in (st.get("highlight") or [])
                                     if isinstance(h, int) and 0 <= h < len(item["rows"])]
            elif kind == "object":
                item["fields"] = [{"name": s(fl.get("name")), "value": s(fl.get("value"))}
                                  for fl in (st.get("fields") or []) if isinstance(fl, dict)][:20]
            structs.append(item)
        line = f.get("line")
        focus = s(f.get("focus"))
        fi = f.get("focus_index")
        frames.append({
            "line": line if isinstance(line, int) and line >= 0 else 0,
            "code": s(f.get("code")),
            "explanation": s(f.get("explanation")),
            "why": s(f.get("why"))[:600],
            "tip": s(f.get("tip"))[:600],
            "focus": focus if any(x["name"] == focus for x in structs) else "",
            "focus_index": fi if isinstance(fi, int) and fi >= 0 else -1,
            "focus_field": s(f.get("focus_field")),
            "structures": structs,
            "output": s(f.get("output")),
            "exception": s(f.get("exception")),
        })
    if not frames:
        raise ValueError("No valid frames")
    return frames


async def visualize_test(
    task_requirements: str,
    model_solution: str,
    test_type: str,
    test_code: str,
    stdin: str,
    expected_output: str,
    response_language: Lang = "en",
    prog_language: str = "cpp",
) -> list[dict]:
    """Return a list of frames describing how the example test runs. Raises RuntimeError on bad output."""
    if test_type == "code_sample":
        numbered = "\n".join(f"{i + 1}: {ln}" for i, ln in enumerate(test_code.split("\n")))
        test_text = f"Type: code_sample\nTest snippet (line numbers added):\n{numbered}"
    else:
        numbered = "\n".join(f"{i + 1}: {ln}" for i, ln in enumerate(stdin.split("\n")))
        test_text = f"Type: stdin_stdout\nStandard input (line numbers added):\n{numbered}"

    prompt = f"""Task requirements:
{task_requirements}

Reference solution (for computing behaviour only — do not reveal it):
{model_solution}

{test_text}

Expected output:
{expected_output}

Programming language: {_prog(prog_language)}

Produce the step-by-step trace as JSON. The "explanation" texts are student-facing.{_language_reminder(response_language)}"""

    agent = _make_agent(VISUALIZE_SYSTEM_PROMPT, response_language, prog_language)
    result = await _invoke(agent, prompt, "visualize")
    text = str(result)
    try:
        return _clean_frames(_parse_json_object(text))
    except (json.JSONDecodeError, ValueError) as e:
        raise RuntimeError(f"Agent returned invalid visualization JSON: {text[:200]}") from e


# ---------------------------------------------------------------------------
# AI practice: a whole new task for one student (on their own AI key)
# ---------------------------------------------------------------------------

PRACTICE_SYSTEM_PROMPT = """You are a university teaching assistant at FINKI (Faculty of Computer Science and Engineering,
Skopje). You write ONE new practice task for a student of the given subject, in the given programming language
(or diagram kind), at the given level, like the tasks in that subject's labs and exams.

The task must be self-contained, precise and testable automatically:
- the description says exactly what to write: names and signatures of the functions / classes (for FUNCTION tasks),
  or the exact input and output format (for PROGRAM tasks), with one or two small examples;
- for SQL: describe the tables (names, columns, types) the query works on — the tests create exactly those;
- for web pages: what must be on the page (elements, ids / classes the tests can find, layout, behaviour);
- for diagrams: a short story of a domain with every element the diagram must contain (in words).
Levels: "easy" = one idea, a few lines; "medium" = a typical lab task; "hard" = an exam-level task with several parts.
If a topic is given, the task is about it. Make it different from the student's previous tasks (listed).
Write in a friendly, clear style; the description is Markdown.

Answer with ONLY a JSON object:
{"title": "short title (max 70 chars)",
 "description": "Markdown task text",
 "starter_code": "what the student starts from (signatures with empty bodies, or a skeleton; '' for diagrams)",
 "model_solution": "a complete, correct solution that follows the description exactly ('' for diagrams)"}
"""

PRACTICE_LEVELS = ("easy", "medium", "hard")


async def practice_task(subject: str, language: str, kind: str, level: str, topic: str, previous: list[str],
                        response_language: Lang = "mk") -> dict:
    """Title, description, starter code and model solution of a new practice task. Raises RuntimeError on bad output."""
    prev = "\n".join(f"- {p}" for p in previous[:30]) or "(none)"
    prompt = f"""SUBJECT: {subject}
LANGUAGE: {_prog(language)}
{_harness_note(language, kind)}
LEVEL: {level if level in PRACTICE_LEVELS else "medium"}
TOPIC: {topic.strip() or "(any topic typical for the subject)"}

The student's previous practice tasks in this subject:
{prev}

Write the task. JSON only.{_language_reminder(response_language)}"""
    agent = _make_agent(PRACTICE_SYSTEM_PROMPT, response_language, language)
    text = str(await _invoke(agent, prompt, "practice_task"))
    try:
        data = _parse_json_object(text)
    except (json.JSONDecodeError, ValueError) as e:
        raise RuntimeError(f"Agent returned invalid practice JSON: {text[:200]}") from e
    out = {k: str(data.get(k) or "").strip() for k in ("title", "description", "starter_code", "model_solution")}
    if not out["title"] or not out["description"]:
        raise RuntimeError("The practice task has no title or description")
    out["title"] = out["title"][:200]
    return out


# ---------------------------------------------------------------------------
# Grading tutor: a suggestion of points for the staff member who grades (лаборант, assistant, professor)
# ---------------------------------------------------------------------------

GRADING_SYSTEM_PROMPT = """You are a grading assistant for university lab work (Faculty of Computer Science, Skopje).
A staff member (often a лаборант) grades one student's solution and asks you for a suggestion. They decide; you only
help them grade quickly, fairly and consistently.
Rules:
- Base everything on the task, the automatic test results and the student's code. Never invent tests or output.
- If all tests pass, start from full points and deduct only for clear problems the task asks about (e.g. a required
  function, structure or style that is missing, hard-coded answers, solutions that only fit the visible tests).
- If tests fail, the automatic points already reflect it: suggest giving back part of the points only for work that
  is clearly correct (e.g. one small mistake), and say so.
- With a rubric, score every criterion (within its maximum) and let the points be their sum.
- "issues": concrete, with the line number of the student's code when there is one. At most 6.
- "comment": 1-3 sentences to the student — polite, specific, what to improve. No grades in it.
- Answer ONLY with JSON:
  {"points": number, "rubric_scores": {"<criterion id>": number} or null, "summary": "...",
   "strengths": ["..."], "issues": [{"line": number or null, "note": "..."}], "comment": "..."}
"""


async def grading_assist(task_title: str, task_description: str, model_solution: str, language: str, rubric: list,
                         max_points: float, auto_points: float | None, passed: int | None, total: int | None,
                         student_code: str, response_language: Lang = "mk") -> dict:
    """A suggestion of points (and per-criterion scores), what is good, the issues by line, and a comment."""
    rub = "\n".join(f'- id "{c.get("id")}": {c.get("title") or c.get("name") or ""} (max {c.get("points")})'
                    for c in (rubric or [])) or "(none)"
    tests = f"{passed} of {total} tests passed" if total else "no automatic tests for this task"
    numbered = "\n".join(f"{i:>3}| {line}" for i, line in enumerate((student_code or "").splitlines(), start=1))
    prompt = f"""TASK: {task_title}
{task_description}

MAX POINTS: {max_points:g}
AUTOMATIC POINTS (from the tests): {'-' if auto_points is None else f'{auto_points:g}'} ({tests})
RUBRIC:
{rub}

MODEL SOLUTION (for you only):
```{_fence(language)}
{model_solution or '(not given)'}
```

STUDENT'S SOLUTION (line numbers on the left):
```{_fence(language)}
{numbered or '(empty)'}
```{_language_reminder(response_language)}"""
    agent = _make_agent(GRADING_SYSTEM_PROMPT, response_language, language)
    data = _parse_json_object(str(await _invoke(agent, prompt, "grading_assist")))
    crit = {str(c.get("id")): float(c.get("points") or 0) for c in (rubric or []) if c.get("id") is not None}
    scores = None
    if crit and isinstance(data.get("rubric_scores"), dict):
        scores = {k: round(min(max(float(v or 0), 0.0), crit[k]), 2) for k, v in data["rubric_scores"].items()
                  if k in crit and isinstance(v, (int, float))}
    try:
        points = float(data.get("points"))
    except (TypeError, ValueError):
        points = sum(scores.values()) if scores else (auto_points or 0.0)
    if scores and crit:
        total_crit = sum(crit.values()) or 1
        points = sum(scores.values()) / total_crit * max_points
    issues = []
    for x in (data.get("issues") or [])[:6]:
        if isinstance(x, dict) and str(x.get("note") or "").strip():
            line = x.get("line")
            issues.append({"line": int(line) if isinstance(line, (int, float)) and line >= 1 else None,
                           "note": str(x["note"]).strip()})
    return {"points": round(min(max(points, 0.0), max_points), 2), "rubric_scores": scores,
            "summary": str(data.get("summary") or "").strip(),
            "strengths": [str(x).strip() for x in (data.get("strengths") or []) if str(x).strip()][:5],
            "issues": issues, "comment": str(data.get("comment") or "").strip()}


# ---------------------------------------------------------------------------
# Staff: a project task (the students hand in a zip) with a rubric and a reference solution (files)
# ---------------------------------------------------------------------------

PROJECT_SYSTEM_PROMPT = """You are a university teacher at FINKI (Faculty of Computer Science and Engineering, Skopje).
Write a small PROJECT task for a lab or a colloquium exercise: the students hand in a zip with several files, and the
staff grade it with a rubric. Also write the reference solution as files (for the staff only).
Rules:
- The task must fit the subject, the language and the level; doable in 60-120 minutes.
- Description in Markdown: what to build, the required files / classes / functions, input and output, and exactly
  what goes into the zip (file names and folders).
- Rubric: 3-6 criteria with points that add up to 10, each concrete and checkable.
- Reference solution: 2-6 complete, runnable files (no placeholders), at most ~250 lines in total.
- Answer ONLY with JSON:
  {"title": "...", "description": "...", "rubric": [{"title": "...", "points": 3}],
   "files": [{"path": "src/Main.java", "content": "..."}]}
"""


async def project_task(subject: str, language: str, level: str, topic: str, previous: list[str],
                       response_language: Lang = "mk") -> dict:
    prev = "\n".join(f"- {p}" for p in previous[:30]) or "(none)"
    prompt = f"""SUBJECT: {subject}
LANGUAGE: {_prog(language)}
LEVEL: {level}
TOPIC: {topic.strip() or "(any topic typical for the subject)"}

Tasks the course already has (do not repeat them):
{prev}

Write the project task. JSON only.{_language_reminder(response_language)}"""
    agent = _make_agent(PROJECT_SYSTEM_PROMPT, response_language, language)
    data = _parse_json_object(str(await _invoke(agent, prompt, "project_task")))
    title, description = str(data.get("title") or "").strip()[:200], str(data.get("description") or "").strip()
    files = []
    for f in (data.get("files") or [])[:12]:
        if isinstance(f, dict) and str(f.get("path") or "").strip() and str(f.get("content") or "").strip():
            path = str(f["path"]).strip().lstrip("/").replace("..", "")[:200]
            files.append({"path": path, "content": str(f["content"])[:60_000]})
    rubric = []
    for i, c in enumerate((data.get("rubric") or [])[:8], start=1):
        if isinstance(c, dict) and str(c.get("title") or "").strip():
            try:
                pts = max(0.0, min(100.0, float(c.get("points") or 0)))
            except (TypeError, ValueError):
                pts = 0.0
            if pts > 0:
                rubric.append({"id": f"c{i}", "title": str(c["title"]).strip()[:200], "points": pts})
    if not title or not description or not files or not rubric:
        raise RuntimeError("The project task is incomplete")
    return {"title": title, "description": description, "rubric": rubric, "files": files}
