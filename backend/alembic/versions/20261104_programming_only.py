"""The catalogue keeps only subjects with a programming language or programming logic

Revision ID: 20261104_prog
Revises: 20261103_electives
Create Date: 2026-11-04

The FINKI subjects without programming (mathematics, business, pedagogy, networks theory, …) are removed — but only
those that have no tasks and no courses, so nothing anyone made is lost. Students' elective choices of a removed
subject go with it (cascade). The admin can always add a subject again.
"""
import sqlalchemy as sa
from alembic import op

revision = "20261104_prog"
down_revision = "20261103_electives"
branch_labels = None
depends_on = None

REMOVED = [
    "F23L1W005", "F23L1W041", "F23L1W031", "F23L1W035", "F23L1W033", "F23L1W002", "F23L1W070", "F23L1W018",
    "F23L1W052", "F23L1W004", "F23L1W049", "F23L2S023", "F23L2S011", "F23L1S032", "F23L1S034", "F23L1S045",
    "F23L2S001", "F23L1S052", "F23L1S116", "F23L2S066", "F23L2W046", "F23L2W014", "F23L3W001", "F23L2W006",
    "F23L2W096", "F23L2W100", "F23L2W104", "F23L2W055", "F23L2W147", "F23L2W067", "F23L2W165", "F23L2W167",
    "F23L2S002", "F23L3S100", "F23L2S061", "F23L2S084", "F23L2S090", "F23L2S099", "F23L2S042", "F23L2S051",
    "F23L2S119", "F23L2S026", "F23L2S124", "F23L2S164", "F23L3W050", "F23L3W043", "F23L3W044", "F23L3W053",
    "F23L3W035", "F23L3W134", "F23L3W148", "F23L3W056", "F23L3W065", "F23L3W158", "F23L3S010", "F23L3S059",
    "F23L3S087", "F23L3S091", "F23L3S093", "F23L3S094", "F23L3S025", "F23L3S113", "F23L3S115", "F23L3S125",
    "F23L3S135", "F23L3S047", "F23L3S071", "F23L3S057", "F23L3S159", "F23L3S166", "F23L3W076", "F23L3W072",
    "F23L3W088", "F23L3W092", "F23L3W105", "F23L3W117", "F23L3W027", "F23L3W126", "F23L3W128", "F23L3W133",
    "F23L3W137", "F23L3W145", "F23L3W200", "F23L3W156", "F23L3S168", "F23L3S028", "F23L3S022", "F23L3S086",
    "F23L3S063", "F23L3S102", "F23L3S070", "F23L3S054", "F23L3S130", "F23L3S132", "F23L3S144", "F23L3S162",
]


def upgrade() -> None:
    op.get_bind().execute(sa.text("""
        DELETE FROM subjects s
        WHERE s.finki_code = ANY(:codes)
          AND NOT EXISTS (SELECT 1 FROM tasks t WHERE t.subject_id = s.id)
          AND NOT EXISTS (SELECT 1 FROM courses c WHERE c.subject_id = s.id)
    """), {"codes": REMOVED})


def downgrade() -> None:
    pass   # the seed doesn't bring them back; the admin can add a subject again
