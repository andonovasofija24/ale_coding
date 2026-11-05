"""
Diagram tasks. Kinds (the task's "language"):

    uml         UML class diagram         usecase     UML use case diagram      state       UML state machine
    activity    UML activity / flowchart  component   UML component diagram     package     UML package diagram
    deployment  UML deployment diagram    er          ER diagram                relational  relational schema (tables)

The student's diagram is kept as JSON text (like code: saved, submitted, compared):

    {"kind": ...,
     "nodes": [{"id", "name", "type", "x", "y", ("w", "h" for boxes that contain others),
                "attributes": [{"name", "type", "visibility", "pk", "fk"}],
                "methods": [{"name", "params", "returns", "visibility"}]}],
     "edges": [{"id", "from", "to", "kind", "fromMult", "toMult", "label"}]}

Node types and edge kinds per diagram kind are in KIND_SPEC. Pseudo-nodes (initial, final, decision, fork…) may have
no name. Directed edges go from -> to (child -> parent for inheritance, whole -> part for aggregation/composition,
source -> target for transitions and flows, client -> supplier for dependencies, referencing -> referenced table for
foreign keys). "attributes" are what a box lists: attributes, columns (relational), internal activities (state:
"entry / …"), contents (package) or stereotypes/artifacts (deployment).

A test is one check (JSON in the test's code):

    {"check": "node", "name": "Книга", "aliases": ["Book"], "type": "abstract"}
    {"check": "attribute", "node": "Книга", "name": "isbn", "pk": true, "fk": true, "type": "String"}
    {"check": "method", "node": "Книга", "name": "позајми"}
    {"check": "relation", "a": "Член", "b": "Позајмица", "kind": "association", "mult_a": "1", "mult_b": "0..*",
     "label": "плати"}                     (a / b may be "@initial", "@final", "@decision"… = any node of that type)
    {"check": "path", "a": "@initial", "b": "Платена"}     a directed path from a to b
    {"check": "reachable"}                                 every node can be reached from the start
    {"check": "count", "type": "final", "min": 1, "max": 2}   (no "type" = all named boxes)

Names are compared forgivingly: upper/lower case, Cyrillic/Latin spelling, spaces and underscores, small typos, and
the aliases the teacher (or the AI draft) listed. Checks run here, in the backend — no code is executed.
"""
import json
import re
import unicodedata
from difflib import SequenceMatcher

from app.services.code_runner_client import RunResult

PSEUDO = {"initial", "final", "flow_final", "decision", "merge", "fork", "join", "choice"}

KIND_SPEC = {
    "uml": {"nodes": ("class", "abstract", "interface", "enum"),
            "edges": ("association", "aggregation", "composition", "inheritance", "realization", "dependency"),
            "default_node": "class", "default_edge": "association", "methods": True},
    "er": {"nodes": ("entity", "weak"), "edges": ("relationship",), "default_node": "entity", "default_edge": "relationship"},
    "usecase": {"nodes": ("actor", "usecase", "system"), "edges": ("association", "include", "extend", "inheritance"),
                "default_node": "usecase", "default_edge": "association"},
    "state": {"nodes": ("state", "initial", "final", "choice"), "edges": ("transition",),
              "default_node": "state", "default_edge": "transition", "flow": True},
    "activity": {"nodes": ("action", "initial", "final", "flow_final", "decision", "merge", "fork", "join", "swimlane"),
                 "edges": ("flow",), "default_node": "action", "default_edge": "flow", "flow": True},
    "component": {"nodes": ("component", "interface", "class"), "edges": ("dependency", "realization", "association"),
                  "default_node": "component", "default_edge": "dependency"},
    "package": {"nodes": ("package", "class", "interface"), "edges": ("dependency", "import", "merge", "inheritance"),
                "default_node": "package", "default_edge": "dependency"},
    "deployment": {"nodes": ("node", "device", "artifact", "component"), "edges": ("association", "deploy", "dependency"),
                   "default_node": "node", "default_edge": "association"},
    "relational": {"nodes": ("table",), "edges": ("foreign_key",), "default_node": "table", "default_edge": "foreign_key"},
    # lifelines side by side; messages are horizontal arrows, their order is top to bottom ("y" of each edge)
    "sequence": {"nodes": ("actor", "lifeline"), "edges": ("sync", "async", "reply", "create"),
                 "default_node": "lifeline", "default_edge": "sync", "sequence": True},
}
KINDS = tuple(KIND_SPEC)
NODE_TYPES = tuple(sorted({t for s in KIND_SPEC.values() for t in s["nodes"]}))
EDGE_KINDS = tuple(sorted({k for s in KIND_SPEC.values() for k in s["edges"]}))
CONTAINERS = {"system", "swimlane", "package", "node", "device"}  # boxes drawn around others (they have w / h)
MAX_NODES, MAX_EDGES, MAX_MEMBERS = 80, 160, 60

_TR = dict(zip("абвгдеѓжзѕијклљмнњопрстќуфхцчџш",
               ["a", "b", "v", "g", "d", "e", "gj", "zh", "z", "dz", "i", "j", "k", "l", "lj", "m", "n", "nj", "o", "p",
                "r", "s", "t", "kj", "u", "f", "h", "c", "ch", "dj", "sh"]))


def is_diagram(language: str) -> bool:
    return language in KIND_SPEC


def empty(kind: str) -> str:
    return json.dumps({"kind": kind, "nodes": [], "edges": []}, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Reading a diagram
# ---------------------------------------------------------------------------

def _s(v, n=200) -> str:
    return str(v if v is not None else "").strip()[:n]


def _aliases(x: dict) -> dict:
    """Other accepted names (e.g. the English and Macedonian name), kept only when given."""
    al = [_s(v, 120) for v in (x.get("aliases") or []) if isinstance(v, str) and v.strip()][:6]
    return {"aliases": al} if al else {}


def _num(v, default=0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def parse(text, kind: str = "uml") -> dict:
    """A clean diagram from (possibly hand-edited or AI-written) JSON. Never raises: bad input -> empty diagram."""
    try:
        data = json.loads(text) if isinstance(text, str) else (text or {})
    except (ValueError, TypeError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    kind = data.get("kind") if data.get("kind") in KIND_SPEC else (kind if kind in KIND_SPEC else "uml")
    spec = KIND_SPEC[kind]
    nodes, ids = [], set()
    for i, n in enumerate((data.get("nodes") or [])[:MAX_NODES]):
        if not isinstance(n, dict):
            continue
        typ = n.get("type") if n.get("type") in spec["nodes"] else spec["default_node"]
        if not _s(n.get("name")) and typ not in PSEUDO:
            continue
        nid = _s(n.get("id"), 60) or f"n{i + 1}"
        while nid in ids:
            nid += "_"
        ids.add(nid)
        attrs = [{"name": _s(a.get("name"), 160), "type": _s(a.get("type"), 80), "visibility": _s(a.get("visibility"), 1),
                  "pk": bool(a.get("pk")), "fk": bool(a.get("fk")), **_aliases(a)}
                 for a in (n.get("attributes") or [])[:MAX_MEMBERS] if isinstance(a, dict) and _s(a.get("name"))]
        meths = [{"name": _s(m.get("name"), 120), "params": _s(m.get("params"), 200), "returns": _s(m.get("returns"), 80),
                  "visibility": _s(m.get("visibility"), 1)}
                 for m in (n.get("methods") or [])[:MAX_MEMBERS] if isinstance(m, dict) and _s(m.get("name"))]
        node = {"id": nid, "name": _s(n.get("name"), 120), "type": typ, "x": _num(n.get("x")), "y": _num(n.get("y")),
                "attributes": attrs, "methods": meths if spec.get("methods") or typ in ("class", "interface") else [], **_aliases(n)}
        if typ in CONTAINERS:
            node["w"], node["h"] = max(120.0, _num(n.get("w"), 360)), max(80.0, _num(n.get("h"), 300))
        nodes.append(node)
    edges = []
    for i, e in enumerate((data.get("edges") or [])[:MAX_EDGES]):
        if not isinstance(e, dict) or e.get("from") not in ids or e.get("to") not in ids:
            continue
        edge = {"id": _s(e.get("id"), 60) or f"e{i + 1}", "from": e["from"], "to": e["to"],
                "kind": e.get("kind") if e.get("kind") in spec["edges"] else spec["default_edge"],
                "fromMult": _s(e.get("fromMult"), 20), "toMult": _s(e.get("toMult"), 20), "label": _s(e.get("label"), 160)}
        if spec.get("sequence"):  # when it happens: top to bottom (no "y" = in the order they are listed)
            edge["y"] = _num(e.get("y"), 120 + i * 50) or 120 + i * 50
        edges.append(edge)
    return {"kind": kind, "nodes": nodes, "edges": edges}


def layout(d: dict) -> dict:
    """Give nodes without a position a place on a grid (AI drafts and readings from pictures have none)."""
    if all(n["x"] == 0 and n["y"] == 0 for n in d["nodes"]):
        if KIND_SPEC[d["kind"]].get("sequence"):  # lifelines in a row, at the top
            for i, n in enumerate(d["nodes"]):
                n["x"], n["y"] = 60 + i * 220, 40
            return d
        flow = KIND_SPEC[d["kind"]].get("flow")
        inner = [n for n in d["nodes"] if n["type"] not in CONTAINERS]
        for i, n in enumerate(inner):
            if flow:  # states / activities: top to bottom in two columns
                n["x"], n["y"] = 80 + (i % 2) * 300, 40 + (i // 2) * 150
            else:
                n["x"], n["y"] = 60 + (i % 3) * 300, 60 + (i // 3) * 240
        for j, n in enumerate([n for n in d["nodes"] if n["type"] in CONTAINERS]):
            if inner and n["type"] == "system":
                n["x"], n["y"] = 230, 20
                n["w"], n["h"] = 640, max(300, 60 + ((len(inner) + 2) // 3) * 240)
            else:
                n["x"], n["y"] = 20 + j * 40, 20 + j * 40
    return d


def dump(d: dict) -> str:
    return json.dumps(d, ensure_ascii=False, indent=1)


# ---------------------------------------------------------------------------
# Names and multiplicities
# ---------------------------------------------------------------------------

def norm(name: str) -> str:
    s = unicodedata.normalize("NFKC", name or "").lower()
    s = "".join(_TR.get(ch, ch) for ch in s)
    s = unicodedata.normalize("NFKD", s)
    return re.sub(r"[^a-z0-9]", "", "".join(ch for ch in s if not unicodedata.combining(ch)))


def loose(s: str) -> str:
    """Latin spellings students use without the Macedonian letters: chlen / clen / člen, shifra / sifra, kjar / kar."""
    for x, y in (("ch", "c"), ("sh", "s"), ("zh", "z"), ("kj", "k"), ("gj", "g"), ("dz", "z"), ("dj", "d"),
                 ("lj", "l"), ("nj", "n"), ("x", "ks"), ("w", "v"), ("y", "i")):
        s = s.replace(x, y)
    return s


def same_name(actual: str, expected: str, aliases=()) -> bool:
    a = norm(actual)
    if not a:
        return False
    for e in [expected, *(aliases or [])]:
        n = norm(e)
        if not n:
            continue
        if a == n or loose(a) == loose(n):
            return True
        if min(len(a), len(n)) >= 5 and SequenceMatcher(None, a, n).ratio() >= 0.85:
            return True
    return False


def label_ok(actual: str, expected: str) -> bool:
    """A transition / flow label: every word the teacher wrote (event, [guard], / action) must be in the student's."""
    if not (expected or "").strip():
        return True
    words = [norm(w) for w in re.split(r"[\s\[\]/(),:;]+", expected) if norm(w)]
    have = loose(norm(actual))
    return all(loose(w) in have or any(same_name(x, w) for x in re.split(r"[\s\[\]/(),:;]+", actual or "")) for w in words)


def _find_nodes(d: dict, name: str, aliases=()) -> list:
    """"@final" = every node of that type; otherwise the first box with a matching name."""
    if name.startswith("@"):
        return [n for n in d["nodes"] if n["type"] == name[1:]]
    n = next((n for n in d["nodes"] if same_name(n["name"], name, aliases)), None)
    if n is None and d["kind"] == "sequence":  # lifelines: "k:Корисник", ":Корисник" and "Корисник" are the same object
        want = [name.split(":")[-1], *[a.split(":")[-1] for a in (aliases or [])]]
        n = next((n for n in d["nodes"] if same_name(n["name"].split(":")[-1], want[0], want[1:])), None)
    return [n] if n else []


def _find_node(d: dict, name: str, aliases=()):
    found = _find_nodes(d, name, aliases)
    return found[0] if found else None


_MANY = {"*", "n", "m", "many", "0..*", "0..n", "0..m"}


def mult(m: str) -> tuple:
    """(min or None when not said, max as int or 'many'). '1' -> (None, 1); '0..*' -> (0, 'many'); 'N' -> (None, 'many')."""
    s = (m or "").strip().lower().replace(" ", "").replace("…", "..")
    if not s:
        return (None, None)
    if ".." in s:
        lo, hi = s.split("..", 1)
        lo_v = int(lo) if lo.isdigit() else None
        hi_v = "many" if hi in ("*", "n", "m") else (int(hi) if hi.isdigit() else None)
        return (lo_v, hi_v)
    if s in _MANY:
        return (None, "many")
    return (None, int(s)) if s.isdigit() else (None, None)


def mult_ok(actual: str, expected: str) -> bool:
    if not (expected or "").strip():
        return True
    a, e = mult(actual), mult(expected)
    if e[1] is not None and a[1] != e[1]:
        return False
    implicit = a[0] if a[0] is not None else (1 if a[1] == 1 else 0 if a[1] == "many" else None)  # "*" = 0..*
    if e[0] is not None and implicit != e[0]:
        return False
    return True


_KIND_OK = {
    "association": {"association", "aggregation", "composition", "relationship"},
    "relationship": {"relationship", "association", "aggregation", "composition"},
    "aggregation": {"aggregation"}, "composition": {"composition"}, "inheritance": {"inheritance"},
    "realization": {"realization", "inheritance"}, "dependency": {"dependency", "import", "include"},
    "include": {"include"}, "extend": {"extend"}, "transition": {"transition", "flow"}, "flow": {"flow", "transition"},
    "import": {"import"}, "merge": {"merge"}, "deploy": {"deploy", "dependency"},
    "foreign_key": {"foreign_key"},
    "sync": {"sync"}, "async": {"async"}, "reply": {"reply"}, "create": {"create", "sync"},
}
_DIRECTED = {"inheritance", "realization", "aggregation", "composition", "dependency", "include", "extend",
             "transition", "flow", "import", "merge", "deploy", "foreign_key", "sync", "async", "reply", "create"}


def _reach(d: dict, starts: list) -> set:
    nxt: dict[str, list] = {}
    for e in d["edges"]:
        nxt.setdefault(e["from"], []).append(e["to"])
    seen, todo = set(), [n["id"] for n in starts]
    while todo:
        x = todo.pop()
        if x not in seen:
            seen.add(x)
            todo.extend(nxt.get(x, []))
    return seen


# ---------------------------------------------------------------------------
# Words (Macedonian / English)
# ---------------------------------------------------------------------------

T = {
    "mk": {
        "no_node": "Нема „{name}“.", "node_ok": "„{name}“ постои.", "wrong_type": "„{name}“ треба да биде {type}.",
        "no_attr": "„{node}“ нема {member} „{name}“{have}.", "attr_ok": "„{node}“ има {member} „{name}“.",
        "not_pk": "„{name}“ во „{node}“ треба да е примарен клуч.", "not_fk": "„{name}“ во „{node}“ треба да е надворешен клуч.",
        "attr_type": "„{name}“ во „{node}“ треба да е од тип {type} (сега: {got}).",
        "no_method": "„{node}“ нема метод „{name}“{have}.", "method_ok": "„{node}“ има метод „{name}“.",
        "no_rel": "Нема врска меѓу {a} и {b}.", "rel_kind": "Врската {a} – {b} е {got}, треба {kind}.",
        "rel_dir": "Врската {a} – {b} е во погрешна насока.",
        "rel_mult": "Мултипликативноста на {a} – {b} е {got_a} / {got_b}, треба {exp_a} / {exp_b}.",
        "rel_label": "Врската {a} → {b} има ознака „{got}“, треба „{exp}“.",
        "rel_ok": "Врската {a} – {b} е точна.", "count": "Има {n} {of}, треба {range}.", "count_ok": "Бројот на {of} е во ред ({n}).",
        "missing_node_for": "Нема {name}, па не може да се провери.", "have": " (има: {list})", "nodes": "елементи",
        "no_path": "Од {a} не може да се стигне до {b}.", "path_ok": "Од {a} се стигнува до {b}.",
        "unreachable": "Не може да се стигне до: {list}.", "reach_ok": "До секој елемент може да се стигне од почетокот.",
        "no_start": "Нема почеток (почетна состојба).", "bad_check": "Тестот е погрешно напишан.",
        "no_msg": "Нема порака {msg}.", "order_ok": "Пораката {b} доаѓа по {a}.", "order_bad": "Пораката {b} треба да дојде по {a}, а е пред неа.",
    },
    "en": {
        "no_node": "There is no “{name}”.", "node_ok": "“{name}” exists.", "wrong_type": "“{name}” should be {type}.",
        "no_attr": "“{node}” has no {member} “{name}”{have}.", "attr_ok": "“{node}” has the {member} “{name}”.",
        "not_pk": "“{name}” in “{node}” should be the primary key.", "not_fk": "“{name}” in “{node}” should be a foreign key.",
        "attr_type": "“{name}” in “{node}” should be of type {type} (now: {got}).",
        "no_method": "“{node}” has no method “{name}”{have}.", "method_ok": "“{node}” has the method “{name}”.",
        "no_rel": "There is no link between {a} and {b}.", "rel_kind": "{a} – {b} is {got}, it should be {kind}.",
        "rel_dir": "The link {a} – {b} points the wrong way.",
        "rel_mult": "The multiplicity of {a} – {b} is {got_a} / {got_b}, it should be {exp_a} / {exp_b}.",
        "rel_label": "The link {a} → {b} is labelled “{got}”, it should be “{exp}”.",
        "rel_ok": "The link {a} – {b} is right.", "count": "There are {n} {of}, it should be {range}.",
        "count_ok": "The number of {of} is right ({n}).", "missing_node_for": "There is no {name}, so this can't be checked.",
        "have": " (it has: {list})", "nodes": "elements",
        "no_path": "{b} can't be reached from {a}.", "path_ok": "{b} can be reached from {a}.",
        "unreachable": "These can't be reached: {list}.", "reach_ok": "Everything can be reached from the start.",
        "no_start": "There is no start (initial node).", "bad_check": "The test is not written correctly.",
        "no_msg": "There is no message {msg}.", "order_ok": "The message {b} comes after {a}.",
        "order_bad": "The message {b} should come after {a}, but it is before it.",
    },
}
KIND_NAMES = {
    "mk": {"association": "асоцијација", "aggregation": "агрегација", "composition": "композиција", "inheritance": "наследување",
           "realization": "реализација", "dependency": "зависност", "relationship": "релација", "include": "«include»",
           "extend": "«extend»", "transition": "премин", "flow": "тек", "import": "«import»", "merge": "«merge»",
           "deploy": "«deploy»", "foreign_key": "надворешен клуч",
           "abstract": "апстрактна класа", "interface": "интерфејс", "enum": "енумерација", "weak": "слаб ентитет",
           "class": "класа", "entity": "ентитет", "actor": "актер", "usecase": "случај на употреба", "system": "граница на системот",
           "state": "состојба", "initial": "почетна состојба", "final": "крајна состојба", "choice": "избор",
           "action": "активност", "flow_final": "крај на тек", "decision": "одлука", "merge_node": "спојување",
           "fork": "разгранување (fork)", "join": "спојување (join)", "swimlane": "лента (swimlane)",
           "component": "компонента", "package": "пакет", "node": "јазол", "device": "уред", "artifact": "артефакт", "table": "табела",
           "lifeline": "објект (линија на живот)", "sync": "синхрона порака", "async": "асинхрона порака", "reply": "одговор",
           "create": "креирање"},
    "en": {"association": "an association", "aggregation": "an aggregation", "composition": "a composition",
           "inheritance": "inheritance", "realization": "a realization", "dependency": "a dependency", "relationship": "a relationship",
           "include": "«include»", "extend": "«extend»", "transition": "a transition", "flow": "a flow", "import": "«import»",
           "merge": "«merge»", "deploy": "«deploy»", "foreign_key": "a foreign key",
           "abstract": "an abstract class", "interface": "an interface", "enum": "an enum", "weak": "a weak entity",
           "class": "a class", "entity": "an entity", "actor": "an actor", "usecase": "a use case", "system": "the system boundary",
           "state": "a state", "initial": "the initial node", "final": "a final node", "choice": "a choice",
           "action": "an action", "flow_final": "a flow final", "decision": "a decision", "merge_node": "a merge",
           "fork": "a fork", "join": "a join", "swimlane": "a swimlane",
           "component": "a component", "package": "a package", "node": "a node", "device": "a device", "artifact": "an artifact",
           "table": "a table", "lifeline": "an object (lifeline)", "sync": "a synchronous message", "async": "an asynchronous message",
           "reply": "a reply", "create": "a create message"},
}
MEMBER = {  # what "attributes" are called in each kind of diagram
    "mk": {"relational": "колона", "state": "внатрешна активност", "package": "елемент", "deployment": "елемент", "": "атрибут"},
    "en": {"relational": "column", "state": "internal activity", "package": "element", "deployment": "element", "": "attribute"},
}
PSEUDO_NAMES = {
    "mk": {"initial": "почетокот", "final": "крајот", "flow_final": "крајот на текот", "decision": "одлуката", "merge": "спојувањето",
           "fork": "разгранувањето", "join": "спојувањето", "choice": "изборот"},
    "en": {"initial": "the start", "final": "the end", "flow_final": "the flow end", "decision": "the decision", "merge": "the merge",
           "fork": "the fork", "join": "the join", "choice": "the choice"},
}


def _q(name: str, lang: str) -> str:
    """A name in quotes, or the words for a pseudo-node ("@initial" -> "the start")."""
    if name.startswith("@"):
        return PSEUDO_NAMES[lang].get(name[1:], name[1:])
    return f"„{name}“" if lang == "mk" else f"“{name}”"


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def evaluate(d: dict, check: dict, lang: str = "mk") -> tuple[bool, str]:
    """(passed, what was found, in words)."""
    t, kn = T[lang], KIND_NAMES[lang]
    c = check.get("check")
    try:
        if c == "node":
            n = _find_node(d, check["name"], check.get("aliases"))
            if n is None:
                return False, t["no_node"].format(name=check["name"])
            want = check.get("type")
            if want and n["type"] != want and not (want == "class" and n["type"] in ("class", "abstract")) \
                    and not (want == "node" and n["type"] == "device"):
                return False, t["wrong_type"].format(name=n["name"], type=kn.get(want, want))
            return True, t["node_ok"].format(name=n["name"])
        if c in ("attribute", "method"):
            n = _find_node(d, check["node"], check.get("node_aliases"))
            if n is None:
                return False, t["missing_node_for"].format(name=_q(check["node"], lang))
            members = n["attributes"] if c == "attribute" else n["methods"]
            m = next((x for x in members if same_name(x["name"], check["name"], check.get("aliases"))
                      or (d["kind"] == "state" and label_ok(x["name"], check["name"]))), None)
            word = MEMBER[lang].get(d["kind"], MEMBER[lang][""])
            if m is None:
                have = t["have"].format(list=", ".join(x["name"] for x in members[:8])) if members else ""
                if c == "attribute":
                    return False, t["no_attr"].format(node=n["name"], name=check["name"], have=have, member=word)
                return False, t["no_method"].format(node=n["name"], name=check["name"], have=have)
            if c == "attribute":
                if check.get("pk") and not m["pk"]:
                    return False, t["not_pk"].format(name=m["name"], node=n["name"])
                if check.get("fk") and not m["fk"]:
                    return False, t["not_fk"].format(name=m["name"], node=n["name"])
                if check.get("type") and m["type"] and norm(m["type"]) != norm(check["type"]):
                    return False, t["attr_type"].format(name=m["name"], node=n["name"], type=check["type"], got=m["type"])
                return True, t["attr_ok"].format(node=n["name"], name=m["name"], member=word)
            return True, t["method_ok"].format(node=n["name"], name=m["name"])
        if c == "relation":
            A, B = _find_nodes(d, check["a"], check.get("a_aliases")), _find_nodes(d, check["b"], check.get("b_aliases"))
            qa, qb = _q(A[0]["name"] if len(A) == 1 and A[0]["name"] else check["a"], lang), \
                _q(B[0]["name"] if len(B) == 1 and B[0]["name"] else check["b"], lang)
            if not A or not B:
                return False, t["missing_node_for"].format(name=_q(check["a"] if not A else check["b"], lang))
            ia, ib = {n["id"] for n in A}, {n["id"] for n in B}
            edges = [(e, False) for e in d["edges"] if e["from"] in ia and e["to"] in ib] + \
                    [(e, True) for e in d["edges"] if e["from"] in ib and e["to"] in ia and not (e["from"] in ia and e["to"] in ib)]
            if not edges:
                if d["kind"] == "sequence":
                    return False, t["no_msg"].format(msg=_msg_words(check, lang) + (f" ({qa} → {qb})" if check.get("label") else ""))
                return False, t["no_rel"].format(a=qa, b=qb)
            kind = check.get("kind") or ""
            ok_kinds = _KIND_OK.get(kind, {kind}) if kind else set(EDGE_KINDS)
            fitting = [(e, rev) for e, rev in edges if e["kind"] in ok_kinds]
            if not fitting:
                e = edges[0][0]
                return False, t["rel_kind"].format(a=qa, b=qb, got=kn.get(e["kind"], e["kind"]), kind=kn.get(kind, kind))
            if kind in _DIRECTED:
                straight = [(e, rev) for e, rev in fitting if not rev]
                if not straight:
                    return False, t["rel_dir"].format(a=qa, b=qb)
                fitting = straight
            want_label = check.get("label", "")
            labelled = [(e, rev) for e, rev in fitting if label_ok(e["label"], want_label)]
            if not labelled:
                return False, t["rel_label"].format(a=qa, b=qb, got=fitting[0][0]["label"] or "—", exp=want_label)
            last = None
            for e, rev in labelled:
                ma, mb = (e["toMult"], e["fromMult"]) if rev else (e["fromMult"], e["toMult"])
                if mult_ok(ma, check.get("mult_a", "")) and mult_ok(mb, check.get("mult_b", "")):
                    return True, t["rel_ok"].format(a=qa, b=qb)
                last = (ma, mb)
            return False, t["rel_mult"].format(a=qa, b=qb, got_a=last[0] or "—", got_b=last[1] or "—",
                                               exp_a=check.get("mult_a") or "—", exp_b=check.get("mult_b") or "—")
        if c == "order":
            first, then = check["first"], check["then"]
            e1, e2 = _messages(d, first), _messages(d, then)
            if not e1 or not e2:
                return False, t["no_msg"].format(msg=_msg_words(first if not e1 else then, lang))
            if min(e["y"] for e in e1) < max(e["y"] for e in e2):
                return True, t["order_ok"].format(a=_msg_words(first, lang), b=_msg_words(then, lang))
            return False, t["order_bad"].format(a=_msg_words(first, lang), b=_msg_words(then, lang))
        if c == "path":
            A, B = _find_nodes(d, check["a"], check.get("a_aliases")), _find_nodes(d, check["b"], check.get("b_aliases"))
            if not A or not B:
                return False, t["missing_node_for"].format(name=_q(check["a"] if not A else check["b"], lang))
            ok = bool(_reach(d, A) & {n["id"] for n in B})
            return ok, t["path_ok" if ok else "no_path"].format(a=_q(check["a"], lang), b=_q(check["b"], lang))
        if c == "reachable":
            starts = [n for n in d["nodes"] if n["type"] == "initial"]
            if not starts:
                return False, t["no_start"]
            seen = _reach(d, starts)
            missing = [n["name"] or kn.get(n["type"], n["type"]) for n in d["nodes"]
                       if n["id"] not in seen and n["type"] not in CONTAINERS]
            if missing:
                return False, t["unreachable"].format(list=", ".join(missing[:8]))
            return True, t["reach_ok"]
        if c == "count":
            typ = check.get("type")
            items = [x for x in d["nodes"] if (x["type"] == typ if typ else x["type"] not in PSEUDO | CONTAINERS)]
            n = len(items)
            lo, hi = check.get("min"), check.get("max")
            rng = f"{lo if lo is not None else 0}–{hi if hi is not None else '∞'}"
            of = _plural(typ, lang) if typ else t["nodes"]
            if (lo is not None and n < lo) or (hi is not None and n > hi):
                return False, t["count"].format(n=n, of=of, range=rng)
            return True, t["count_ok"].format(n=n, of=of)
    except (KeyError, TypeError, AttributeError):
        pass
    return False, t["bad_check"]


def _messages(d: dict, m: dict) -> list:
    """The messages from m["a"] to m["b"] (with the label, if given) of a sequence diagram."""
    ia = {n["id"] for n in _find_nodes(d, m["a"], m.get("a_aliases"))}
    ib = {n["id"] for n in _find_nodes(d, m["b"], m.get("b_aliases"))}
    return [e for e in d["edges"] if e["from"] in ia and e["to"] in ib and label_ok(e["label"], m.get("label", ""))
            and "y" in e]


def _msg_words(m: dict, lang: str) -> str:
    """A message in words: its label, or (no label) who sends it to whom."""
    return _q(m["label"], lang) if m.get("label") else f"{_q(m['a'], lang)} → {_q(m['b'], lang)}"


def _plural(typ: str, lang: str) -> str:
    mk = {"final": "крајни состојби", "initial": "почетни состојби", "actor": "актери", "usecase": "случаи на употреба",
          "decision": "одлуки", "fork": "разгранувања", "join": "спојувања", "table": "табели", "state": "состојби",
          "action": "активности", "flow_final": "краеви на тек"}
    en = {"final": "final nodes", "initial": "initial nodes", "actor": "actors", "usecase": "use cases", "decision": "decisions",
          "fork": "forks", "join": "joins", "table": "tables", "state": "states", "action": "actions", "flow_final": "flow finals"}
    return (mk if lang == "mk" else en).get(typ, typ)


def run_checks(code: str, test_cases: list[dict], language: str, lang: str = "mk") -> list[RunResult]:
    d = parse(code, language)
    out = []
    for tc in test_cases:
        try:
            check = json.loads(tc.get("test_code") or "{}")
        except ValueError:
            check = {}
        ok, what = evaluate(d, check if isinstance(check, dict) else {}, lang)
        out.append(RunResult(passed=ok, actual_output=what, expected_output=tc.get("expected_output") or describe(check, lang)))
    return out


# ---------------------------------------------------------------------------
# Tests from the teacher's diagram
# ---------------------------------------------------------------------------

D = {
    "mk": {"node": "Постои {name}", "node_t": "{name} е {type}", "attr": "{node} има {member} „{name}“",
           "attr_pk": "{node} има примарен клуч „{name}“", "attr_fk": "{node} има надворешен клуч „{name}“",
           "method": "{node} има метод „{name}“",
           "rel": "{kind} {a} – {b}", "rel_m": "{kind} {a} ({ma}) – {b} ({mb})", "rel_dir": "{kind} од {a} кон {b}",
           "rel_l": "{kind} од {a} кон {b}: „{label}“", "count": "Број на {of}: {range}",
           "path": "Од {a} може да се стигне до {b}", "reachable": "До секој елемент може да се стигне од почетокот",
           "has_initial": "Има почеток (почетна состојба)", "has_final": "Има крај (крајна состојба)", "label": "{text}: „{label}“",
           "order": "По {a} доаѓа {b}"},
    "en": {"node": "{name} exists", "node_t": "{name} is {type}", "attr": "{node} has the {member} “{name}”",
           "attr_pk": "{node} has the primary key “{name}”", "attr_fk": "{node} has the foreign key “{name}”",
           "method": "{node} has the method “{name}”",
           "rel": "{kind} {a} – {b}", "rel_m": "{kind} {a} ({ma}) – {b} ({mb})", "rel_dir": "{kind} from {a} to {b}",
           "rel_l": "{kind} from {a} to {b}: “{label}”", "count": "Number of {of}: {range}",
           "path": "{b} can be reached from {a}", "reachable": "Everything can be reached from the start",
           "has_initial": "There is a start (initial node)", "has_final": "There is an end (final node)", "label": "{text}: “{label}”",
           "order": "{a} is followed by {b}"},
}
REL_TITLE = {
    "mk": {"association": "Асоцијација", "aggregation": "Агрегација", "composition": "Композиција", "inheritance": "Наследување",
           "realization": "Реализација", "dependency": "Зависност", "relationship": "Релација", "include": "«include»",
           "extend": "«extend»", "transition": "Премин", "flow": "Тек", "import": "«import»", "merge": "«merge»",
           "deploy": "«deploy»", "foreign_key": "Надворешен клуч", "sync": "Порака", "async": "Асинхрона порака",
           "reply": "Одговор", "create": "Креирање", "": "Врска"},
    "en": {"association": "Association", "aggregation": "Aggregation", "composition": "Composition", "inheritance": "Inheritance",
           "realization": "Realization", "dependency": "Dependency", "relationship": "Relationship", "include": "«include»",
           "extend": "«extend»", "transition": "Transition", "flow": "Flow", "import": "«import»", "merge": "«merge»",
           "deploy": "«deploy»", "foreign_key": "Foreign key", "sync": "Message", "async": "Asynchronous message",
           "reply": "Reply", "create": "Create", "": "Link"},
}
_DEFAULT_TYPES = {"class", "entity", "usecase", "state", "action", "component", "package", "node", "table", "lifeline"}


def describe(check: dict, lang: str = "mk", kind: str = "") -> str:
    """The check in words — this is what students see as the test (instead of the JSON)."""
    t = D[lang]
    c = check.get("check") if isinstance(check, dict) else None
    q = lambda x: _q(x, lang)  # noqa: E731
    try:
        if c == "node":
            typ = check.get("type")
            if typ and typ not in _DEFAULT_TYPES:
                return t["node_t"].format(name=q(check["name"]), type=KIND_NAMES[lang].get(typ, typ))
            return t["node"].format(name=q(check["name"]))
        if c == "attribute":
            key = "attr_pk" if check.get("pk") else "attr_fk" if check.get("fk") else "attr"
            return t[key].format(node=q(check["node"]), name=check["name"], member=MEMBER[lang].get(kind, MEMBER[lang][""]))
        if c == "method":
            return t["method"].format(node=q(check["node"]), name=check["name"])
        if c == "relation":
            k = REL_TITLE[lang].get(check.get("kind") or "", REL_TITLE[lang][""])
            if check.get("label") and check.get("kind") in _DIRECTED:
                return t["rel_l"].format(kind=k, a=q(check["a"]), b=q(check["b"]), label=check["label"])
            if check.get("mult_a") or check.get("mult_b"):
                return t["rel_m"].format(kind=k, a=q(check["a"]), b=q(check["b"]), ma=check.get("mult_a") or "—", mb=check.get("mult_b") or "—")
            text = t["rel_dir" if check.get("kind") in _DIRECTED else "rel"].format(kind=k, a=q(check["a"]), b=q(check["b"]))
            return t["label"].format(text=text, label=check["label"]) if check.get("label") else text
        if c == "order":
            return t["order"].format(a=_msg_words(check["first"], lang), b=_msg_words(check["then"], lang))
        if c == "path":
            return t["path"].format(a=q(check["a"]), b=q(check["b"]))
        if c == "reachable":
            return t["reachable"]
        if c == "count":
            if check.get("type") in ("initial", "final") and check.get("min") == 1 and check.get("max") is None:
                return t["has_" + check["type"]]
            of = _plural(check["type"], lang) if check.get("type") else T[lang]["nodes"]
            return t["count"].format(of=of, range=f"{check.get('min', 0)}–{check.get('max', '∞')}")
    except KeyError:
        pass
    return "?"


def _ref(n: dict, counts: dict) -> str:
    """How a check refers to a node: its name, or "@type" for an unnamed pseudo-node that is the only one of its type."""
    if n["name"]:
        return n["name"]
    return f"@{n['type']}" if counts.get(n["type"], 0) == 1 or n["type"] in ("initial", "final", "flow_final") else ""


def generate_checks(d: dict, lang: str = "mk", methods: bool = True) -> list[dict]:
    """One test per element of the teacher's diagram: named boxes, their attributes / columns / activities, methods,
    links (with multiplicities and labels), how many start / end nodes there are, and that everything is reachable.
    Aliases written in the diagram (node or member field "aliases") are carried into the checks."""
    kind = d["kind"]
    by_id = {n["id"]: n for n in d["nodes"]}
    counts: dict[str, int] = {}
    for n in d["nodes"]:
        counts[n["type"]] = counts.get(n["type"], 0) + 1
    checks = []

    def add(ch):
        checks.append({"test_code": json.dumps(ch, ensure_ascii=False), "expected_output": describe(ch, lang, kind)})
    for n in d["nodes"]:
        if not n["name"]:
            continue
        ch = {"check": "node", "name": n["name"]}
        if n.get("aliases"):
            ch["aliases"] = n["aliases"]
        if n["type"] not in _DEFAULT_TYPES:
            ch["type"] = n["type"]
        add(ch)
    for typ in ("initial", "final"):  # a start and an end must be drawn
        if counts.get(typ):
            add({"check": "count", "type": typ, "min": 1})
    for n in d["nodes"]:
        if not n["name"]:
            continue
        for a in n["attributes"]:
            ch = {"check": "attribute", "node": n["name"], "name": a["name"]}
            if a.get("aliases"):
                ch["aliases"] = a["aliases"]
            if n.get("aliases"):
                ch["node_aliases"] = n["aliases"]
            if kind in ("er", "relational") and a.get("pk"):
                ch["pk"] = True
            if kind == "relational" and a.get("fk") and not a.get("pk"):
                ch["fk"] = True
            add(ch)
        if methods:
            for m in n["methods"]:
                add({"check": "method", "node": n["name"], "name": m["name"], **({"node_aliases": n["aliases"]} if n.get("aliases") else {})})
    for e in d["edges"]:
        a, b = by_id.get(e["from"]), by_id.get(e["to"])
        if not a or not b:
            continue
        ra, rb = _ref(a, counts), _ref(b, counts)
        if not ra or not rb:
            continue  # between two unnamed pseudo-nodes of a kind that appears many times: "reachable" covers it
        ch = {"check": "relation", "a": ra, "b": rb, "kind": e["kind"]}
        if a.get("aliases"):
            ch["a_aliases"] = a["aliases"]
        if b.get("aliases"):
            ch["b_aliases"] = b["aliases"]
        if e.get("fromMult"):
            ch["mult_a"] = e["fromMult"]
        if e.get("toMult"):
            ch["mult_b"] = e["toMult"]
        if e.get("label") and (e["kind"] in ("transition", "flow") or (kind == "deployment" and e["kind"] == "association")
                               or kind == "sequence"):
            ch["label"] = e["label"]
        add(ch)
    if kind == "sequence":  # the order of the messages: each one comes after the one before it
        def msg(e):
            a, b = by_id.get(e["from"]), by_id.get(e["to"])
            m = {"a": a["name"], "b": b["name"]}
            if e.get("label"):
                m["label"] = e["label"]
            return m
        seq = sorted((e for e in d["edges"] if by_id.get(e["from"], {}).get("name") and by_id.get(e["to"], {}).get("name")),
                     key=lambda e: e.get("y", 0))
        for e1, e2 in zip(seq, seq[1:]):
            add({"check": "order", "first": msg(e1), "then": msg(e2)})
    if KIND_SPEC[kind].get("flow") and counts.get("initial"):
        add({"check": "reachable"})
    return checks


def summary(d: dict) -> str:
    """The diagram in short text (for the AI tutor and for reading prompts)."""
    by_id = {n["id"]: n for n in d["nodes"]}
    lines = []
    for n in d["nodes"]:
        attrs = ", ".join(("PK " if a["pk"] else "") + ("FK " if a["fk"] else "") + a["name"] + (f": {a['type']}" if a["type"] else "")
                          for a in n["attributes"])
        meths = ", ".join(m["name"] + "()" for m in n["methods"])
        lines.append(f"{n['type']} {n['name'] or '(unnamed)'}: [{attrs}]" + (f" methods: [{meths}]" if meths else ""))
    for e in d["edges"]:
        a = by_id.get(e["from"], {}).get("name") or by_id.get(e["from"], {}).get("type", "?")
        b = by_id.get(e["to"], {}).get("name") or by_id.get(e["to"], {}).get("type", "?")
        lines.append(f"{e['kind']} {a} ({e['fromMult'] or '-'}) -> {b} ({e['toMult'] or '-'})" + (f" '{e['label']}'" if e["label"] else ""))
    return "\n".join(lines) or "(empty diagram)"


# ---------------------------------------------------------------------------
# Similar diagrams (plagiarism check)
# ---------------------------------------------------------------------------

def _elements(d: dict) -> dict[str, str]:
    """{canonical element: how to show it}. Canonical = normalized names, so "Член"/"clen" are the same."""
    by_id = {n["id"]: n for n in d["nodes"]}
    key = lambda n: loose(norm(n["name"])) or f"@{n['type']}"  # noqa: E731
    out = {}
    for n in d["nodes"]:
        if not n["name"]:
            continue
        out[f"n:{key(n)}"] = n["name"]
        for a in n["attributes"]:
            out[f"a:{key(n)}.{loose(norm(a['name']))}:{norm(a['type'])}"] = f"{n['name']}.{a['name']}" + (f": {a['type']}" if a["type"] else "")
        for m in n["methods"]:
            out[f"m:{key(n)}.{loose(norm(m['name']))}"] = f"{n['name']}.{m['name']}()"
    for e in d["edges"]:
        a, b = by_id[e["from"]], by_id[e["to"]]
        out[f"e:{e['kind']}:{key(a)}>{key(b)}:{e['fromMult']}:{e['toMult']}:{loose(norm(e['label']))}"] = \
            f"{a['name'] or a['type']} → {b['name'] or b['type']}" + (f" ({e['label']})" if e["label"] else "")
    return out


def _layout(d: dict) -> dict[str, tuple[float, float]]:
    """Positions of named boxes, scaled to the diagram's own bounding box (0..1), so moving / zooming doesn't hide it."""
    pts = {loose(norm(n["name"])): (n["x"], n["y"]) for n in d["nodes"] if n["name"] and n["type"] not in CONTAINERS}
    if len(pts) < 3:
        return {}
    xs, ys = [p[0] for p in pts.values()], [p[1] for p in pts.values()]
    w, h = (max(xs) - min(xs)) or 1, (max(ys) - min(ys)) or 1
    return {k: ((x - min(xs)) / w, (y - min(ys)) / h) for k, (x, y) in pts.items()}


def compare_all(codes: dict[str, str], kind: str, threshold: float = 0.6, model: str = "", starter: str = "",
                limit: int = 200) -> list[dict]:
    """Pairs of similar diagrams. Elements every correct solution has (the model solution's, the starting diagram's)
    count little; what two students share beyond them (the same extra attributes, the same misspelled names, the same
    mistakes) and an almost identical layout count a lot. Information for the teacher, not a verdict."""
    expected = set(_elements(parse(model, kind))) | set(_elements(parse(starter, kind)))
    docs = {k: parse(v, kind) for k, v in codes.items()}
    els = {k: _elements(d) for k, d in docs.items()}
    lays = {k: _layout(d) for k, d in docs.items()}
    out = []
    keys = sorted(docs)
    for i, ka in enumerate(keys):
        for kb in keys[i + 1:]:
            ea, eb = els[ka], els[kb]
            if len(ea) < 4 or len(eb) < 4:
                continue
            weight = lambda x: 0.25 if x in expected else 1.0  # noqa: E731
            shared = ea.keys() & eb.keys()
            union = ea.keys() | eb.keys()
            content = sum(weight(x) for x in shared) / (sum(weight(x) for x in union) or 1)
            la, lb = lays[ka], lays[kb]
            common = la.keys() & lb.keys()
            if len(common) >= 3:
                close = sum(1 for x in common if abs(la[x][0] - lb[x][0]) < 0.04 and abs(la[x][1] - lb[x][1]) < 0.04)
                lay = close / len(common)
                sim = 0.55 * content + 0.45 * lay
            else:
                lay, sim = None, content
            if sim >= threshold:
                unusual = sorted(ea[x] for x in shared if x not in expected)
                out.append({"a": ka, "b": kb, "similarity": round(sim, 3), "lines_a": [], "lines_b": [],
                            "shared": unusual[:30], "layout": None if lay is None else round(lay, 2)})
    out.sort(key=lambda x: -x["similarity"])
    return out[:limit]
