"""
The subjects (предмети) of FINKI that programming / design tasks belong to. Tasks, courses (one run of a subject,
e.g. "СП 2026/27 зимски") and AI practice are grouped by them.

Taken from FINKI's study programmes (KN23 / SIIS23: mandatory courses by semester) and its elective courses that
have programming or modelling labs. `languages`: what tasks of the subject are written in (the first one is the
main one; existing tasks with no subject get the subject whose list starts with their language — see DEFAULT_FOR).
A semester of None = an elective offered in any semester; electives can also have a semester (Subject.elective).
"""

SUBJECTS = [
    # code, Macedonian name, English name, semester (KN23; None = elective), languages, icon (lucide), colour
    ("SP", "Структурно програмирање", "Structured Programming", 1, ["c", "cpp", "python"], "braces", "#2747C9"),
    ("OOP", "Објектно-ориентирано програмирање", "Object-Oriented Programming", 2, ["cpp", "uml"], "boxes", "#7048E8"),
    ("AOK", "Архитектура и организација на компјутери", "Computer Architecture and Organization", 2, ["asm", "c"], "cpu", "#495057"),
    ("APS", "Алгоритми и податочни структури", "Algorithms and Data Structures", 3, ["python", "java", "cpp", "c"], "git-fork", "#0CA678"),
    ("OS", "Оперативни системи", "Operating Systems", 4, ["bash", "c", "java"], "terminal", "#343A40"),
    ("SI", "Софтверско инженерство", "Software Engineering", 4, ["java"], "drafting-compass", "#F08C00"),
    ("VI", "Вештачка интелигенција", "Artificial Intelligence", 4, ["python"], "brain", "#D6336C"),
    # 3rd year, summer semester, mandatory (finki.ukim.mk: Objektno_orientirana_analiza_i_dizajn.pdf) — all UML diagrams
    ("OOAID", "Објектно-ориентирана анализа и дизајн", "Object-Oriented Analysis and Design", 6,
     ["uml", "usecase", "sequence", "state", "activity", "component", "package", "deployment"], "shapes", "#0B7285"),
    ("BP", "Бази на податоци", "Databases", 5, ["sql", "postgresql", "er", "relational"], "database", "#2B8A3E"),
    ("VP", "Веб програмирање", "Web Programming", 5, ["java", "web", "javascript", "typescript"], "globe", "#1971C2"),
    ("NP", "Напредно програмирање", "Advanced Programming", 5, ["java", "kotlin"], "rocket", "#C2255C"),
    ("PP", "Програмски парадигми", "Programming Paradigms", 7, ["prolog", "lisp", "python", "kotlin"], "infinity", "#862E9C"),
    ("DIANS", "Дизајн и архитектура на софтвер", "Software Design and Architecture", None,
     ["component", "package", "deployment", "uml"], "layers", "#E8590C"),
    ("ONVD", "Основи на веб дизајн", "Fundamentals of Web Design", None, ["web"], "palette", "#FF6B6B"),
    ("IPNKS", "Интернет програмирање на клиентска страна", "Client-Side Internet Programming", None,
     ["javascript", "web", "typescript"], "mouse-pointer-click", "#F59F00"),
    ("IT", "Интернет технологии", "Internet Technologies", None, ["csharp", "web"], "server", "#5C7CFA"),
    ("ISSOK", "Имплементација на системи со слободен и отворен код", "Implementation of Free and Open Source Systems", None,
     ["php", "web", "postgresql"], "unlock", "#40C057"),
    ("MPP", "Мобилни платформи и програмирање", "Mobile Platforms and Programming", None, ["kotlin", "java"], "smartphone", "#12B886"),
]

# The subject an existing task without one goes to, by its language.
DEFAULT_FOR = {
    "c": "SP", "cpp": "OOP", "asm": "AOK", "python": "APS", "java": "NP", "bash": "OS",
    "uml": "OOAID", "usecase": "OOAID", "sequence": "OOAID", "state": "OOAID", "activity": "OOAID",
    "sql": "BP", "postgresql": "BP", "er": "BP", "relational": "BP",
    "web": "ONVD", "javascript": "IPNKS", "typescript": "IPNKS",
    "prolog": "PP", "lisp": "PP", "component": "OOAID", "package": "OOAID", "deployment": "OOAID",
    "csharp": "IT", "php": "ISSOK", "kotlin": "MPP",
}


# ---------------------------------------------------------------------------------------------------------------------
# The whole FINKI catalogue (study programmes 2023): code, name, recommended semester, mandatory / elective —
# finki_subjects.csv. The subjects above are matched to their row by FINKI_CODE; the rest are added with the extras
# below (languages tasks are written in, icon, colour). The admin can later move an elective to another semester.

FINKI_CODE = {
    "SP": "F23L1W020", "OOP": "F23L1S016", "AOK": "F23L1S003", "APS": "F23L2W001", "OS": "F23L2S017", "SI": "F23L2S029",
    "VI": "F23L2S030", "BP": "F23L3W004", "VP": "F23L3W024", "NP": "F23L3W140", "PP": "F23L3W038", "DIANS": "F23L3W009",
    "ONVD": "F23L1S146", "IPNKS": "F23L2W109", "IT": "F23L2S110", "ISSOK": "F23L3W103", "MPP": "F23L3W129",
    "OOAID": "F23L2S015",
}

DEVOPS = ["git", "bash", "dockerfile", "yaml", "terraform"]

# finki code: (name override or None, English name, languages, icon, colour)
EXTRAS = {
    "F23L3S118": ("Континуирана интеграција и испорака (DevOps)", "Continuous Integration and Delivery (DevOps)", DEVOPS, "git-branch", "#1864AB"),
    "F23L3S111": (None, "Infrastructure Programming", ["terraform", "yaml", "dockerfile", "bash", "git"], "cloud", "#5F3DC4"),
    "F23L3W060": (None, "System Administration", ["bash", "git", "dockerfile"], "terminal", "#343A40"),
    "F23L3S062": (None, "Virtualization", ["dockerfile", "yaml", "bash"], "container", "#0B7285"),
    "F23L3W068": (None, "Cloud Computing", ["terraform", "yaml", "dockerfile"], "cloud", "#1971C2"),
    "F23L3W021": (None, "Team Project", ["git", "yaml", "dockerfile"], "git-branch", "#C2255C"),
    "F23L1W007": (None, "Introduction to Computer Science", ["python"], "book-open", "#2747C9"),
    "F23L2W201": (None, "Applied Algorithms and Data Structures", ["python", "cpp", "java"], "git-fork", "#0CA678"),
    "F23L2S097": (None, "Algorithm Design", ["python", "cpp"], "git-fork", "#0CA678"),
    "F23L3W008": (None, "Introduction to Data Science", ["python", "sql"], "database", "#2B8A3E"),
    "F23L3S036": (None, "Machine Learning", ["python"], "brain", "#D6336C"),
    "F23L3S163": (None, "Process Automation with Machine Learning", ["python"], "brain", "#D6336C"),
    "F23L3S019": (None, "Software Quality and Testing", ["java", "python"], "shield", "#E8590C"),
    "F23L2W033": (None, "Software Testing", ["java", "python"], "shield", "#E8590C"),
    "F23L3S138": (None, "Advanced Databases", ["postgresql", "sql", "er"], "database", "#2B8A3E"),
    "F23L3W074": (None, "Database Administration", ["postgresql", "sql", "bash"], "database", "#2B8A3E"),
    "F23L3S157": (None, "Data Warehouses and OLAP", ["sql", "postgresql"], "database", "#2B8A3E"),
    "F23L3S149": (None, "Parallel Programming", ["c", "cpp"], "cpu", "#495057"),
    "F23L3W037": (None, "Parallel and Distributed Processing", ["c", "java"], "cpu", "#495057"),
    "F23L3W064": (None, "Distributed Systems", ["java", "yaml", "dockerfile"], "network", "#1971C2"),
    "F23L3S112": (None, "Programming Languages and Compilers", ["python", "c"], "braces", "#862E9C"),
    "F23L3S127": (None, "Mobile Applications", ["kotlin", "java"], "smartphone", "#12B886"),
    "F23L3W136": (None, "Advanced Web Design", ["web", "javascript"], "palette", "#FF6B6B"),
    "F23L3W079": (None, "Web-based Systems", ["java", "web", "javascript"], "globe", "#1971C2"),
    "F23L2S082": (None, "Visual Programming", ["csharp"], "mouse-pointer-click", "#5C7CFA"),
    "F23L2S002": (None, "Software Requirements Analysis", ["usecase", "uml", "activity"], "drafting-compass", "#F08C00"),
    "F23L3W075": (None, "Analysis and Design of Information Systems", ["uml", "er", "usecase"], "drafting-compass", "#F08C00"),
    "F23L3S130": (None, "Business Process Modelling and Management", ["activity", "uml"], "drafting-compass", "#F08C00"),
    "F23L3S101": (None, "Ethical Hacking", ["bash", "python"], "shield", "#C92A2A"),
    "F23L3W065": (None, "Cyber Security", ["bash", "python"], "shield", "#C92A2A"),
    "F23L2S066": (None, "Fundamentals of Cyber Security", ["bash", "python"], "shield", "#C92A2A"),
    "F23L3W152": (None, "Video Game Programming", ["python", "csharp"], "bot", "#862E9C"),
    "F23L3S139": (None, "Web3 Applications", ["javascript", "typescript"], "globe", "#1971C2"),
}

SEMESTER_COLOUR = {1: "#2747C9", 2: "#7048E8", 3: "#0CA678", 4: "#F08C00", 5: "#2B8A3E", 6: "#0B7285", 7: "#C2255C", 8: "#495057"}


def _icon_for(name: str) -> str:
    n = name.lower()
    for words, icon in ((("математ", "калкулус", "алгебра", "статист", "веројатност", "дискретн", "графови", "операциони"), "sigma"),
                        (("мреж",), "network"), (("безбедност", "форензик", "криптограф", "хакирање"), "shield"),
                        (("податоц", "бази"), "database"), (("веб", "интернет"), "globe"), (("робот",), "bot"),
                        (("графика", "анимација", "дизајн", "мултимеди", "визуел", "слика"), "palette"),
                        (("бизнис", "менаџмент", "маркетинг", "претприемништво", "економија", "трговија", "деловна"), "briefcase"),
                        (("педагог", "психолог", "учење", "образов", "методика", "ученици"), "graduation-cap"),
                        (("архитект", "електрон", "кола", "микропроцес", "вградлив", "компоненти", "физика", "сигнал"), "cpu"),
                        (("интелиген", "машинск", "когнитив", "длабоко", "агент"), "brain")):
        if any(w in n for w in words):
            return icon
    return "book-open"


def finki_catalogue() -> list[dict]:
    """Every row of finki_subjects.csv with its extras: {code, name, name_en, semester, elective, languages, icon, color}."""
    import csv
    import os
    out = []
    with open(os.path.join(os.path.dirname(__file__), "finki_subjects.csv"), encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name, en, langs, icon, color = EXTRAS.get(row["code"], (None, "", [], None, None))
            sem = int(row["semester"])
            out.append({"code": row["code"], "name": name or row["name"], "name_en": en, "semester": sem,
                        "elective": row["type"] == "elective", "languages": langs,
                        "icon": icon or _icon_for(row["name"]), "color": color or SEMESTER_COLOUR.get(sem, "#2747C9")})
    return out
