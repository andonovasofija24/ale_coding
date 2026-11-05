"""Sprint 15: LTI 1.3 — ALE inside the faculty's Moodle (courses.finki): sign-in, courses, roles, grades back

Revision ID: 20261030_lti
Revises: 20261029_sequence
Create Date: 2026-10-30
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "20261030_lti"
down_revision = "20261029_sequence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lti_platforms",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False, server_default="Moodle"),
        sa.Column("issuer", sa.String(500), nullable=False),
        sa.Column("client_id", sa.String(200), nullable=False),
        sa.Column("deployment_ids", JSONB, nullable=False, server_default="[]"),
        sa.Column("auth_login_url", sa.String(500), nullable=False),
        sa.Column("auth_token_url", sa.String(500), nullable=False),
        sa.Column("jwks_url", sa.String(500), nullable=False),
        sa.Column("link_by_email", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.UniqueConstraint("issuer", "client_id", name="uq_lti_platform"),
    )
    op.create_table(
        "lti_tool_keys",
        sa.Column("kid", sa.String(64), primary_key=True),
        sa.Column("private_pem_encrypted", sa.Text, nullable=False),
        sa.Column("public_jwk", JSONB, nullable=False),
        sa.Column("active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime, nullable=True),
    )
    op.create_table(
        "lti_users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("platform_id", UUID(as_uuid=True), sa.ForeignKey("lti_platforms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sub", sa.String(255), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("last_launch_at", sa.DateTime, nullable=True),
        sa.UniqueConstraint("platform_id", "sub", name="uq_lti_user"),
    )
    op.create_table(
        "lti_contexts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("platform_id", UUID(as_uuid=True), sa.ForeignKey("lti_platforms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("context_id", sa.String(255), nullable=False),
        sa.Column("deployment_id", sa.String(255), nullable=False, server_default=""),
        sa.Column("label", sa.String(255), nullable=False, server_default=""),
        sa.Column("title", sa.String(500), nullable=False, server_default=""),
        sa.Column("course_id", UUID(as_uuid=True), sa.ForeignKey("courses.id", ondelete="SET NULL"), nullable=True),
        sa.Column("lineitems_url", sa.String(500), nullable=False, server_default=""),
        sa.Column("ags_scopes", JSONB, nullable=False, server_default="[]"),
        sa.Column("memberships_url", sa.String(500), nullable=False, server_default=""),
        sa.Column("last_roster_sync", sa.DateTime, nullable=True),
        sa.Column("last_grade_sync", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.UniqueConstraint("platform_id", "context_id", name="uq_lti_context"),
    )
    op.create_index("ix_lti_contexts_course", "lti_contexts", ["course_id"])
    op.create_table(
        "lti_line_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("context_id", UUID(as_uuid=True), sa.ForeignKey("lti_contexts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assignment_id", UUID(as_uuid=True), sa.ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.UniqueConstraint("context_id", "assignment_id", name="uq_lti_line_item"),
    )
    op.create_table(
        "lti_nonces",
        sa.Column("nonce", sa.String(255), primary_key=True),
        sa.Column("expires_at", sa.DateTime, nullable=False),
    )
    op.create_table(
        "lti_registrations",
        sa.Column("token", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False, server_default="Moodle"),
        sa.Column("expires_at", sa.DateTime, nullable=False),
        sa.Column("used_at", sa.DateTime, nullable=True),
        sa.Column("platform_id", UUID(as_uuid=True), sa.ForeignKey("lti_platforms.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )


def downgrade() -> None:
    for t in ("lti_registrations", "lti_nonces", "lti_line_items", "lti_contexts", "lti_users", "lti_tool_keys", "lti_platforms"):
        op.drop_table(t)
