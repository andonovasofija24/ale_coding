"""
The grade sheet (.xlsx): one row per student — index, name, group, each lab, homework, colloquia, exam, total %,
signature, exam eligibility, exemption, proposed grade and the reasons — plus a sheet with the course's rules.
Headers are in the course's teaching language.
"""
import io
import re
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Assignment, Course
from app.services import standing

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

H = {
    "mk": {"index": "Индекс", "name": "Име и презиме", "email": "Е-пошта", "group": "Група", "homework": "Домашни",
           "k1": "К1", "k2": "К2", "exam": "Испит", "total": "Вкупно %", "signature": "Потпис", "eligible": "Право на испит",
           "exempt": "Ослободен (кв. дел)", "grade": "Предлог оценка", "final": "Оценка", "notes": "Забелешка", "yes": "да", "no": "не",
           "sheet": "Оценки", "rules": "Правила", "weights": "Тежини", "thresholds": "Прагови за оценка",
           "rule": "Правило", "on": "Важи", "value": "Вредност", "generated": "Изготвено",
           "labs": "Лабораториски", "category": "Дел", "weight": "Тежина %", "grade_n": "Оценка", "from": "од %"},
    "en": {"index": "Index", "name": "Name", "email": "E-mail", "group": "Group", "homework": "Homework",
           "k1": "C1", "k2": "C2", "exam": "Exam", "total": "Total %", "signature": "Signature", "eligible": "May take exam",
           "exempt": "Exempt (qual. part)", "grade": "Proposed grade", "final": "Grade", "notes": "Notes", "yes": "yes", "no": "no",
           "sheet": "Grades", "rules": "Rules", "weights": "Weights", "thresholds": "Grade thresholds",
           "rule": "Rule", "on": "Applies", "value": "Value", "generated": "Generated",
           "labs": "Labs", "category": "Part", "weight": "Weight %", "grade_n": "Grade", "from": "from %"},
}
RULE_NAMES = {
    "mk": {"max_missed_labs": "Дозволени пропуштени лабораториски", "min_labs_signature": "Минимум % од лабораториски за потпис",
           "min_colloquium": "Минимум % на колоквиум за положен", "k1_exempt_qualifying": "Минимум % на К1 за ослободување од квалификациски дел",
           "signature_for_exam": "Потребен потпис за испит"},
    "en": {"max_missed_labs": "Labs that may be missed", "min_labs_signature": "Minimum % of lab points for the signature",
           "min_colloquium": "Minimum % to pass a colloquium", "k1_exempt_qualifying": "Minimum % on C1 for exemption from the qualifying part",
           "signature_for_exam": "Signature needed for the exam"},
}

HEAD_FILL = PatternFill("solid", fgColor="1A2233")
BAD_FILL = PatternFill("solid", fgColor="FBEAEA")
OK_FILL = PatternFill("solid", fgColor="E3F5EC")
THIN = Side(style="thin", color="D9DEE7")


def file_name(course: Course, a: Assignment | None = None) -> str:
    base = f"{course.code}-ocenki" + (f"-{a.title}" if a else "")
    return re.sub(r"[^\w.-]+", "_", base)[:120] + ".xlsx"


async def build(db: AsyncSession, course: Course, group: str | None = None) -> bytes:
    from app.routers.assignments import gradebook_data  # here, to avoid an import cycle
    gb = await gradebook_data(db, course.id)
    st = await standing.compute(db, course, gb)
    lang = "en" if course.language == "en" else "mk"
    h = H[lang]
    by_user = {s["user_id"]: s for s in gb["students"]}
    cats = {x["id"]: x["category"] for x in st["assignments"]}
    labs = [a for a in gb["assignments"] if cats.get(a["id"]) == "labs"]
    other = {c: [a for a in gb["assignments"] if cats.get(a["id"]) == c] for c in ("homework", "k1", "k2", "exam")}

    wb = Workbook()
    ws = wb.active
    ws.title = h["sheet"]
    cols = [h["index"], h["name"], h["email"], h["group"]] + [a["title"] for a in labs]
    cols += [h[c] for c in ("homework", "k1", "k2", "exam") if other[c]]
    cols += [h["total"], h["signature"], h["eligible"], h["exempt"], h["grade"], h["final"], h["notes"]]
    ws.append(cols)
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = HEAD_FILL
        c.alignment = Alignment(wrap_text=True, vertical="center")
    yn = lambda v: "" if v is None else (h["yes"] if v else h["no"])  # noqa: E731

    students = [s for s in st["students"] if not group or s["group"] == group]
    for s in sorted(students, key=lambda x: (x["index"] or "~", x["name"])):
        scores = by_user[s["user_id"]]["scores"]
        row = [s["index"], s["name"], s["email"], s["group"] or ""]
        row += [scores[a["id"]]["score"] if scores[a["id"]]["applies"] else "" for a in labs]
        for c in ("homework", "k1", "k2", "exam"):
            if other[c]:
                vals = [scores[a["id"]]["score"] for a in other[c] if scores[a["id"]]["applies"] and scores[a["id"]]["score"] is not None]
                row.append(round(sum(vals), 2) if vals else "")
        row += [s["total"], yn(s["signature"]), yn(s["eligible_exam"]), yn(s["exempt"]), s["grade"] or "", s.get("final_grade") or "",
                "; ".join(standing.reason_text(r, lang) for r in s["reasons"] if r["key"] != "incomplete")]
        ws.append(row)
        r = ws.max_row
        for col, val in ((cols.index(h["signature"]) + 1, s["signature"]), (cols.index(h["eligible"]) + 1, s["eligible_exam"])):
            if val is False:
                ws.cell(r, col).fill = BAD_FILL
            elif val is True:
                ws.cell(r, col).fill = OK_FILL
    for row in ws.iter_rows(min_row=1, max_row=ws.max_row):
        for c in row:
            c.border = Border(top=THIN, bottom=THIN, left=THIN, right=THIN)
    widths = {h["name"]: 26, h["email"]: 30, h["group"]: 18, h["notes"]: 50}
    for i, name in enumerate(cols, start=1):
        ws.column_dimensions[get_column_letter(i)].width = widths.get(name, max(10, min(18, len(str(name)) + 2)))
    ws.row_dimensions[1].height = 34
    ws.freeze_panes = "C2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(cols))}{ws.max_row}"

    # the rules sheet: what the analysis above is based on
    rs = wb.create_sheet(h["rules"])
    sch = st["scheme"]
    rs.append([f"{course.code} — {course.name}", f"{h['generated']}: {datetime.now():%d.%m.%Y %H:%M}"])
    rs.append([])
    rs.append([h["weights"]])
    rs.append([h["category"], h["weight"]])
    for c in standing.CATEGORIES:
        rs.append([h["labs"] if c == "labs" else h[c], sch["weights"].get(c, 0)])
    rs.append([])
    rs.append([h["thresholds"]])
    rs.append([h["grade_n"], h["from"]])
    for i, th in enumerate(sch["thresholds"]):
        rs.append([6 + i, th])
    rs.append([])
    rs.append([h["rule"], h["on"], h["value"]])
    for r in sch["rules"]:
        rs.append([RULE_NAMES[lang][r["type"]], h["yes"] if r["enabled"] else h["no"], "" if r["value"] is None else r["value"]])
    for row in rs.iter_rows():
        for c in row:
            if isinstance(c.value, str) and c.value in (h["weights"], h["thresholds"], h["rule"], h["category"], h["grade_n"]):
                c.font = Font(bold=True)
    rs.column_dimensions["A"].width = 58
    rs.column_dimensions["B"].width = 16
    rs.column_dimensions["C"].width = 12

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
