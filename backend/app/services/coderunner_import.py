"""
Import Moodle CodeRunner questions (Moodle XML export) as ALE tasks.

A Moodle XML export looks like:

    <quiz>
      <question type="category">...</question>
      <question type="coderunner">
        <name><text>Stack</text></name>
        <questiontext format="html"><text><![CDATA[<p>...</p>]]></text></questiontext>
        <coderunnertype>cpp_function</coderunnertype>
        <answer><![CDATA[ ...model solution... ]]></answer>
        <answerpreload><![CDATA[ ...starter code... ]]></answerpreload>
        <testcases>
          <testcase testtype="0" useasexample="1" hiderestiffail="0" mark="1.0">
            <testcode><text>cout << f(2);</text></testcode>
            <stdin><text></text></stdin>
            <expected><text>4</text></expected>
            <display><text>SHOW</text></display>
          </testcase>
        </testcases>
      </question>
    </quiz>

Mapping to ALE (languages: C, C++, Java, Python, JavaScript, PHP):
- cpp_/c_function, java_method, java_class -> "code_sample" tests (test code calls the student's code)
- cpp_/c_/java_program                    -> "stdin_stdout" tests (student writes the program, test gives stdin)
- python3, nodejs, php                     -> per test: "code_sample" if it has test code, else "stdin_stdout"
- display SHOW (or useasexample=1) -> visible test; HIDE / HIDE_IF_FAIL / HIDE_IF_SUCCEED -> hidden test
- question text (HTML) -> Markdown
"""
import re
from dataclasses import dataclass, field

from defusedxml import ElementTree as ET  # safe against XXE / entity-expansion attacks
from markdownify import markdownify

MAX_BYTES = 5 * 1024 * 1024

# CodeRunner question type -> (ALE language, test type). "auto" = per test: code_sample if it has test code,
# otherwise stdin_stdout (CodeRunner's python3 type runs the answer and then the test code, with optional stdin).
_SUPPORTED = {
    "cpp_function": ("cpp", "code_sample"),
    "cpp_program": ("cpp", "stdin_stdout"),
    "c_function": ("c", "code_sample"),
    "c_program": ("c", "stdin_stdout"),
    "python3": ("python", "auto"),
    "python3_w_input": ("python", "auto"),
    "java_method": ("java", "code_sample"),
    "java_class": ("java", "code_sample"),
    "java_program": ("java", "stdin_stdout"),
    "nodejs": ("javascript", "auto"),
    "php": ("php", "auto"),
}


class CoderunnerImportError(ValueError):
    """The file is not a usable Moodle XML export (user-facing message key in .code)."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass
class ParsedTest:
    type: str
    test_code: str
    stdin: str
    expected_output: str
    is_hidden: bool
    order: int


@dataclass
class ParsedQuestion:
    index: int
    title: str
    description: str
    starter_code: str
    model_solution: str
    language: str
    coderunner_type: str
    test_cases: list[ParsedTest] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)  # warning codes, translated on the frontend


@dataclass
class SkippedQuestion:
    title: str
    reason: str  # reason code, translated on the frontend
    detail: str = ""


def _text(el, path: str) -> str:
    """Text of <path><text>...</text></path> or of <path>...</path>, '' if missing."""
    if el is None:
        return ""
    node = el.find(path)
    if node is None:
        return ""
    inner = node.find("text")
    value = inner.text if inner is not None else node.text
    return value or ""


def _strip_trailing_ws(s: str) -> str:
    return "\n".join(line.rstrip() for line in s.replace("\r\n", "\n").split("\n")).strip("\n")


def html_to_markdown(html: str, code_language: str = "cpp") -> str:
    if not html.strip():
        return ""
    md = markdownify(html, heading_style="ATX", bullets="-", code_language=code_language)
    md = re.sub(r"\n{3,}", "\n\n", md)  # collapse the blank lines markdownify leaves around blocks
    return md.strip()


def parse_moodle_xml(data: bytes) -> tuple[list[ParsedQuestion], list[SkippedQuestion]]:
    if len(data) > MAX_BYTES:
        raise CoderunnerImportError("tooLarge")
    try:
        root = ET.fromstring(data)
    except Exception:
        raise CoderunnerImportError("notXml")
    if root.tag != "quiz":
        raise CoderunnerImportError("notMoodle")

    parsed: list[ParsedQuestion] = []
    skipped: list[SkippedQuestion] = []

    for q in root.findall("question"):
        qtype = q.get("type", "")
        if qtype == "category":
            continue  # Moodle category markers, not questions
        title = _text(q, "name").strip() or "(untitled)"

        if qtype != "coderunner":
            skipped.append(SkippedQuestion(title, "notCoderunner", qtype))
            continue

        cr_type = (q.findtext("coderunnertype") or "").strip()
        if cr_type not in _SUPPORTED:
            skipped.append(SkippedQuestion(title, "unsupportedLanguage", cr_type or "?"))
            continue
        language, test_type = _SUPPORTED[cr_type]

        warnings: list[str] = []
        question_html = _text(q, "questiontext")
        if "@@PLUGINFILE@@" in question_html:
            warnings.append("images")
            question_html = re.sub(r"<img[^>]*@@PLUGINFILE@@[^>]*>", "", question_html)
        description = html_to_markdown(question_html, language)
        if not description:
            warnings.append("noDescription")

        model_solution = _strip_trailing_ws(q.findtext("answer") or "")
        if not model_solution:
            warnings.append("noSolution")
        starter_code = _strip_trailing_ws(q.findtext("answerpreload") or "")

        tests: list[ParsedTest] = []
        tc_root = q.find("testcases")
        for i, tc in enumerate(tc_root.findall("testcase") if tc_root is not None else []):
            if tc.get("testtype", "0") not in ("0", ""):
                continue  # "precheck only" tests are not real grading tests
            display = _text(tc, "display").strip().upper() or "SHOW"
            example = tc.get("useasexample", "0") == "1"
            code = _strip_trailing_ws(_text(tc, "testcode"))
            this_type = ("code_sample" if code.strip() else "stdin_stdout") if test_type == "auto" else test_type
            tests.append(ParsedTest(
                type=this_type,
                test_code=code if this_type == "code_sample" else "",
                stdin=_text(tc, "stdin").replace("\r\n", "\n"),
                expected_output=_text(tc, "expected").replace("\r\n", "\n"),
                is_hidden=not (display == "SHOW" or example),
                order=len(tests),
            ))

        if not tests:
            skipped.append(SkippedQuestion(title, "noTests"))
            continue
        if all(t.is_hidden for t in tests):
            warnings.append("noVisibleTests")
        if not any(t.is_hidden for t in tests):
            warnings.append("noHiddenTests")
        if test_type == "code_sample" and any(not t.test_code.strip() for t in tests):
            warnings.append("emptyTestCode")

        parsed.append(ParsedQuestion(
            index=len(parsed),
            title=title[:500],
            description=description,
            starter_code=starter_code,
            model_solution=model_solution,
            language=language,
            coderunner_type=cr_type,
            test_cases=tests,
            warnings=warnings,
        ))

    if not parsed and not skipped:
        raise CoderunnerImportError("noQuestions")
    return parsed, skipped
