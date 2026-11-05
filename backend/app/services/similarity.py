"""
Structural similarity of solutions (a plagiarism check in the spirit of JPlag / MOSS).

Each solution becomes a stream of tokens in which comments and whitespace are gone, identifiers become `V`,
numbers `N`, strings `S`, while keywords, operators and punctuation stay as they are. So renaming variables,
re-indenting, rewording comments or changing literals does not hide a copy — reordering the logic does.

Two solutions are compared on shared runs of K tokens (k-grams). Similarity = the share of both solutions'
tokens covered by shared runs (2·covered / (len A + len B)), like JPlag. Runs that also appear in the task's
starter code are ignored — everybody got that code.

The result is a hint for the teacher, never proof on its own.
"""
import re
from itertools import combinations

K = 8           # tokens in a run; shorter runs are too common to mean anything
MIN_TOKENS = 20  # very short solutions (a one-liner) are not compared

_LINE_COMMENT = {
    "python": ("#",), "bash": ("#",), "php": ("//", "#"), "sql": ("--",), "postgresql": ("--",),
    "prolog": ("%",), "lisp": (";",), "asm": (";", "#"),
    "git": ("#",), "dockerfile": ("#",), "yaml": ("#",), "terraform": ("#", "//"),
}
_DEFAULT_LINE_COMMENT = ("//",)
_BLOCK_COMMENT = {
    "python": None, "bash": None, "lisp": ("#|", "|#"), "asm": None, "prolog": ("/*", "*/"),
    "git": None, "dockerfile": None, "yaml": None,
}
_DEFAULT_BLOCK = ("/*", "*/")

_C_LIKE = """
if else for while do switch case default break continue return goto try catch finally throw throws new delete
this super static const final public private protected virtual override abstract class struct union enum
interface extends implements import package namespace using include define typedef template typename
int long short char float double bool boolean void string auto signed unsigned var let val fun function fn
true false null nullptr undefined typeof instanceof sizeof in of is as yield async await echo
cout cin endl std printf scanf main
"""
KEYWORDS = {
    "c_like": set(_C_LIKE.split()),
    "python": set("""if elif else for while break continue return def class lambda try except finally raise with as
        pass yield import from global nonlocal in is not and or None True False print input range len""".split()),
    "sql": set("""select from where join left right inner outer full cross on group by order having limit offset union
        all distinct into values insert update delete set create table drop alter as and or not in is null exists
        between like case when then else end count sum avg min max asc desc with primary key references""".split()),
    "bash": set("""if then else elif fi for while until do done case esac in function return local echo read
        printf exit export let declare""".split()),
    "lisp": set("""defun defvar defparameter let let* setq setf if cond when unless lambda loop do dolist dotimes
        progn format car cdr cons list null nil t and or not mapcar funcall apply""".split()),
    "prolog": set("""is not fail true write nl findall member append length""".split()),
    "asm": set("""mov add sub mul div inc dec cmp jmp je jne jg jl jge jle call ret push pop lea and or xor
        syscall int section global""".split()),
}
_FAMILY = {"python": "python", "sql": "sql", "postgresql": "sql", "bash": "bash", "lisp": "lisp",
           "git": "bash", "dockerfile": "bash", "yaml": "bash", "terraform": "bash",
           "prolog": "prolog", "asm": "asm"}


def _keywords(language: str) -> set[str]:
    return KEYWORDS[_FAMILY.get(language, "c_like")]


_TOKEN = re.compile(r"""
    (?P<str>"(?:\\.|[^"\\\n])*"|'(?:\\.|[^'\\\n])*'|`(?:\\.|[^`\\])*`)
  | (?P<num>\b\d[\d_]*(?:\.\d+)?(?:[eE][+-]?\d+)?[a-zA-Z]*\b|\b0[xX][0-9a-fA-F]+\b)
  | (?P<id>[A-Za-z_$][A-Za-z0-9_$]*)
  | (?P<op>==|!=|<=|>=|&&|\|\||<<|>>|\+\+|--|->|=>|::|\+=|-=|\*=|/=|%=|[^\sA-Za-z0-9_])
""", re.VERBOSE)


def _strip_comments(code: str, language: str) -> str:
    """Blank out comments but keep newlines, so token line numbers stay true."""
    line_marks = _LINE_COMMENT.get(language, _DEFAULT_LINE_COMMENT)
    block = _BLOCK_COMMENT.get(language, _DEFAULT_BLOCK)
    out, i, n = [], 0, len(code)
    quote = None
    while i < n:
        c = code[i]
        if quote:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(code[i + 1])
                i += 2
                continue
            if c == quote or c == "\n":
                quote = None
            i += 1
            continue
        if c in "\"'`" and language not in ("lisp",):
            quote = c
            out.append(c)
            i += 1
            continue
        if block and code.startswith(block[0], i):
            j = code.find(block[1], i + len(block[0]))
            j = n if j < 0 else j + len(block[1])
            out.append("".join(ch if ch == "\n" else " " for ch in code[i:j]))
            i = j
            continue
        if any(code.startswith(m, i) for m in line_marks):
            j = code.find("\n", i)
            j = n if j < 0 else j
            out.append(" " * (j - i))
            i = j
            continue
        out.append(c)
        i += 1
    return "".join(out)


def tokenize(code: str, language: str) -> list[tuple[str, int]]:
    """[(normalized token, 1-based line)]"""
    if language == "web":
        return _tokenize_web(code or "")
    text = _strip_comments(code or "", language)
    kw = _keywords(language)
    skip = ";,{}" if _FAMILY.get(language, "c_like") == "c_like" else ";,"
    tokens, line, last = [], 1, 0
    for m in _TOKEN.finditer(text):
        line += text.count("\n", last, m.start())
        last = m.start()
        kind = m.lastgroup
        v = m.group()
        if kind == "str":
            tokens.append(("S", line))
        elif kind == "num":
            tokens.append(("N", line))
        elif kind == "id":
            tokens.append((v.lower() if v.lower() in kw else "V", line))
        else:
            if v in skip:  # optional separators / braces shouldn't move the windows
                continue
            tokens.append((v, line))
    return tokens


# ---- web pages (HTML / CSS / JavaScript in one text, files separated by <!-- file: name --> lines) ----------------
# HTML becomes its tag structure (tag names, attribute names; class / id values -> C; each text -> W), CSS its rules
# (selectors with classes / ids -> C, properties, value kinds), JavaScript the usual tokens. So renaming classes,
# rewording texts or changing colours does not hide a copied page — its structure and rules do show.

_FILE_MARK = re.compile(r"^\s*<!--\s*file:\s*([\w.\-/]+)\s*-->\s*$", re.M)
_TAG = re.compile(r"<!--.*?-->|<(/?)([a-zA-Z][\w-]*)([^>]*)>", re.S)
_ATTR = re.compile(r"([:@\w-]+)(?:\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s>]+))?")
_CSS_TOKEN = re.compile(r"(?P<sel>[.#][\w-]+)|(?P<hex>#[0-9a-fA-F]{3,8}\b)|(?P<num>-?\d*\.?\d+(?:[a-z%]+)?)|(?P<word>[a-zA-Z-]+)"
                        r"|(?P<str>\"[^\"]*\"|'[^']*')|(?P<op>[{}:>+~(),*\[\]=@!])")


def _line_at(text: str, pos: int, base: int) -> int:
    return base + text.count("\n", 0, pos)


def _tokenize_css(css: str, base: int, offset_text: str = "") -> list[tuple[str, int]]:
    css = re.sub(r"/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group()), css, flags=re.S)
    out, in_block = [], False
    for m in _CSS_TOKEN.finditer(css):
        line = _line_at(css, m.start(), base)
        kind, v = m.lastgroup, m.group()
        if kind == "op":
            if v == "{":
                in_block = True
            elif v == "}":
                in_block = False
            out.append((v, line))
        elif kind == "sel" and not in_block:
            out.append((v[0] + "C", line))
        elif kind == "hex" or (kind == "sel" and in_block):
            out.append(("COLOR", line))
        elif kind == "num":
            out.append(("N", line))
        elif kind == "str":
            out.append(("S", line))
        else:
            out.append((v.lower(), line))
    return out


def _tokenize_html(html: str, base: int) -> list[tuple[str, int]]:
    out, last = [], 0
    raw_until = None  # inside <style> / <script>
    for m in _TAG.finditer(html):
        if m.group(2) is None:  # a comment
            continue
        closing, tag, attrs = m.group(1), m.group(2).lower(), m.group(3) or ""
        between = html[last:m.start()]
        if raw_until and closing and tag == raw_until:
            body_line = _line_at(html, last, base)
            if tag == "style":
                out += _tokenize_css(between, body_line)
            else:
                out += [(t, body_line + ln - 1) for t, ln in tokenize(between, "javascript")]
            raw_until = None
        elif raw_until:
            continue
        elif re.sub(r"<![^>]*>", "", between).strip():  # (a <!doctype> is not text)
            out.append(("W", _line_at(html, last, base)))
        line = _line_at(html, m.start(), base)
        out.append((("</" if closing else "<") + tag, line))
        if not closing:
            for a in _ATTR.finditer(attrs):
                name = a.group(1).lower()
                if name == "/":
                    continue
                out.append(("@" + name, line))
                if a.group(2) is not None and name in ("class", "id", "for", "href", "src", "name"):
                    out.append(("C", line))
            if tag in ("style", "script") and not attrs.rstrip().endswith("/"):
                raw_until = tag
        last = m.end()
    if html[last:].strip() and not raw_until:
        out.append(("W", _line_at(html, last, base)))
    return out


def _tokenize_web(code: str) -> list[tuple[str, int]]:
    marks = list(_FILE_MARK.finditer(code))
    parts = [("index.html", 0, len(code))] if not marks else \
        [(m.group(1).lower(), m.end(), marks[i + 1].start() if i + 1 < len(marks) else len(code)) for i, m in enumerate(marks)]
    if marks and marks[0].start() > 0 and code[:marks[0].start()].strip():
        parts.insert(0, ("index.html", 0, marks[0].start()))
    out = []
    for name, a, b in parts:
        text, base = code[a:b], code.count("\n", 0, a) + 1
        if name.endswith(".css"):
            out += _tokenize_css(text, base)
        elif name.endswith(".js"):
            out += [(t, base + ln - 1) for t, ln in tokenize(text, "javascript")]
        else:
            out += _tokenize_html(text, base)
    return out


def _grams(tokens: list[tuple[str, int]]) -> dict[int, list[int]]:
    """{hash of a K-token run: [start positions]}"""
    out: dict[int, list[int]] = {}
    seq = [t for t, _ in tokens]
    for i in range(len(seq) - K + 1):
        out.setdefault(hash(tuple(seq[i:i + K])), []).append(i)
    return out


def _ranges(lines: set[int]) -> list[list[int]]:
    """{1,2,3,7,8} -> [[1,3],[7,8]]"""
    out: list[list[int]] = []
    for ln in sorted(lines):
        if out and ln <= out[-1][1] + 1:
            out[-1][1] = ln
        else:
            out.append([ln, ln])
    return out


class _Doc:
    def __init__(self, code: str, language: str, ignore: set[int]):
        self.tokens = tokenize(code, language)
        self.grams = {h: p for h, p in _grams(self.tokens).items() if h not in ignore}

    def covered(self, shared: set[int]) -> tuple[int, set[int]]:
        pos: set[int] = set()
        for h in shared:
            for p in self.grams[h]:
                pos.update(range(p, p + K))
        return len(pos), {self.tokens[p][1] for p in pos}


def compare(a: str, b: str, language: str, starter: str = "") -> dict:
    ignore = set(_grams(tokenize(starter, language))) if starter else set()
    return _compare(_Doc(a, language, ignore), _Doc(b, language, ignore))


def _compare(da: _Doc, db: _Doc) -> dict:
    if len(da.tokens) < MIN_TOKENS or len(db.tokens) < MIN_TOKENS:
        return {"similarity": 0.0, "lines_a": [], "lines_b": []}
    shared = da.grams.keys() & db.grams.keys()
    ca, la = da.covered(shared)
    cb, lb = db.covered(shared)
    sim = (ca + cb) / (len(da.tokens) + len(db.tokens))
    return {"similarity": round(sim, 3), "lines_a": _ranges(la), "lines_b": _ranges(lb)}


def compare_all(codes: dict[str, str], language: str, threshold: float = 0.6, starter: str = "",
                limit: int = 200) -> list[dict]:
    """Pairs of {key: code} at or above the threshold, most similar first."""
    ignore = set(_grams(tokenize(starter, language))) if starter else set()
    docs = {k: _Doc(v, language, ignore) for k, v in codes.items()}
    out = []
    for ka, kb in combinations(sorted(docs), 2):
        r = _compare(docs[ka], docs[kb])
        if r["similarity"] >= threshold:
            out.append({"a": ka, "b": kb, **r})
    out.sort(key=lambda x: -x["similarity"])
    return out[:limit]
