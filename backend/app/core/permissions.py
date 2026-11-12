"""
What a teacher may do in a subject — permissions the admin gives to each teacher, per subject (like Moodle's
capabilities). There are no course roles: only accounts (student | teacher | admin) and these permissions.

The templates are only shortcuts for ticking the boxes ("like a professor / an assistant / a лаборант"); they are
not stored — a teacher's permissions can always be changed one by one.
"""

# group: (permission, …)
GROUPS: dict[str, tuple[str, ...]] = {
    "labs": ("labs.view", "labs.manage", "labs.grade"),          # labs and practice: look, make / edit, grade
    "exams": ("exams.view", "exams.manage", "exams.grade"),      # colloquia, exams and homework: the same
    "grades": ("grades.view", "grades.final", "grades.rules"),   # all points + standing; final grades; grading rules
    "other": ("people.view", "materials.manage", "mail.send", "activity.view", "practice.view"),
}
ALL: tuple[str, ...] = tuple(p for g in GROUPS.values() for p in g)

TEMPLATES: dict[str, tuple[str, ...]] = {
    "professor": ALL,
    "assistant": ("labs.view", "labs.manage", "labs.grade", "exams.view", "exams.manage", "exams.grade",
                  "grades.view", "people.view", "materials.manage", "mail.send", "activity.view", "practice.view"),
    "lab": ("labs.view", "labs.manage", "labs.grade", "practice.view"),
}
# the old course roles (and Moodle's roles) map to a template
LEGACY = {"teacher": "professor", "assistant": "assistant", "lab": "lab"}

LAB_KINDS = ("lab", "practice")          # → the "labs" permissions
EXAM_KINDS = ("exam", "homework")        # → the "exams" permissions
LAB_CATEGORIES = (None, "labs", "none")  # where an assignment made with only the labs permissions may count


def clean(perms) -> list[str]:
    """Known permissions, in the canonical order; *.manage and *.grade imply *.view."""
    s = {p for p in (perms or []) if p in ALL}
    for g in ("labs", "exams"):
        if f"{g}.manage" in s or f"{g}.grade" in s:
            s.add(f"{g}.view")
    if s & {"grades.final", "grades.rules"}:
        s.add("grades.view")
    return [p for p in ALL if p in s]


def template(name: str) -> list[str]:
    return list(TEMPLATES.get(LEGACY.get(name, name), ()))


def template_of(perms) -> str | None:
    """The template these permissions are exactly (for a short label), or None (their own mix)."""
    s = set(perms or [])
    for name, t in TEMPLATES.items():
        if s == set(t):
            return name
    return None


def group_of_kind(kind: str) -> str:
    return "labs" if kind in LAB_KINDS else "exams"


def can(perms, perm: str) -> bool:
    return perm in (perms or ())


def can_kind(perms, kind: str, action: str) -> bool:
    """action: view | manage | grade, for an assignment of this kind."""
    return f"{group_of_kind(kind)}.{action}" in (perms or ())
