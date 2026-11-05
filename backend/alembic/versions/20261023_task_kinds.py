"""Task translations (MK/EN), task kinds (code / document / project / offline), rubrics, uploaded files,
reference solutions, comments on project files, attendance

Revision ID: 20261023_task_kinds
Revises: 20261022_profiles
Create Date: 2026-10-23
"""
import json
import re

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261023_task_kinds"
down_revision = "20261022_profiles"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB
CYRILLIC = re.compile(r"[Ѐ-ӿ]")


def upgrade() -> None:
    op.add_column("tasks", sa.Column("kind", sa.String(12), nullable=False, server_default="code"))
    op.add_column("tasks", sa.Column("content_lang", sa.String(2), nullable=False, server_default="en"))
    op.add_column("tasks", sa.Column("translations", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")))
    op.add_column("tasks", sa.Column("rubric", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")))
    op.alter_column("tasks", "model_solution", server_default="")
    op.create_table(
        "task_files",
        sa.Column("task_id", UUID, sa.ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("size", sa.Integer, nullable=False),
        sa.Column("data", sa.LargeBinary, nullable=False),
        sa.Column("uploaded_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.add_column("submissions", sa.Column("file_name", sa.String(255), nullable=False, server_default=""))
    op.add_column("submissions", sa.Column("file_type", sa.String(100), nullable=False, server_default=""))
    op.add_column("submissions", sa.Column("file_size", sa.Integer, nullable=False, server_default="0"))
    op.create_table(
        "submission_files",
        sa.Column("submission_id", UUID, sa.ForeignKey("submissions.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("data", sa.LargeBinary, nullable=False),
    )
    op.add_column("task_grades", sa.Column("rubric_scores", JSONB, nullable=True))
    op.add_column("code_comments", sa.Column("path", sa.String(500), nullable=False, server_default=""))
    op.create_table(
        "attendance",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("assignment_id", UUID, sa.ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("updated_by", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("assignment_id", "user_id", name="uq_attendance"),
    )

    # Existing tasks: written in Macedonian if the title or description uses Cyrillic; the sample tasks get
    # their Macedonian translation.
    from app.data.task_translations_mk import MK
    conn = op.get_bind()
    for tid, title, desc in conn.execute(sa.text("SELECT id, title, description FROM tasks")).all():
        if CYRILLIC.search(title or "") or CYRILLIC.search(desc or ""):
            conn.execute(sa.text("UPDATE tasks SET content_lang = 'mk' WHERE id = :id"), {"id": tid})
        elif title in MK:
            conn.execute(sa.text("UPDATE tasks SET translations = CAST(:t AS jsonb) WHERE id = :id"),
                         {"id": tid, "t": json.dumps({"mk": MK[title]}, ensure_ascii=False)})


def downgrade() -> None:
    op.drop_table("attendance")
    op.drop_column("code_comments", "path")
    op.drop_column("task_grades", "rubric_scores")
    op.drop_table("submission_files")
    for c in ("file_size", "file_type", "file_name"):
        op.drop_column("submissions", c)
    op.drop_table("task_files")
    op.alter_column("tasks", "model_solution", server_default=None)
    for c in ("rubric", "translations", "content_lang", "kind"):
        op.drop_column("tasks", c)
