"""
LTI 1.3 / LTI Advantage — ALE as a tool inside the faculty's Moodle (courses.finki).

    LtiPlatform      a registered Moodle (issuer + client id + its endpoints), added by the admin by hand or by
                     dynamic registration (the Moodle admin pastes one URL)
    LtiToolKey       ALE's own RSA key pair: Moodle checks ALE's messages (deep links, service tokens) with it
    LtiUser          a Moodle user (platform + "sub") ↔ an ALE user
    LtiContext       a Moodle course (platform + context id) ↔ an ALE course, with its service URLs
    LtiLineItem      an ALE assignment ↔ a Moodle grade item (where its points are sent)
    LtiNonce         nonces already used (a launch can't be replayed)
    LtiRegistration  one-time links for dynamic registration, made by the admin
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LtiPlatform(Base):
    __tablename__ = "lti_platforms"
    __table_args__ = (UniqueConstraint("issuer", "client_id", name="uq_lti_platform"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False, default="Moodle")
    issuer: Mapped[str] = mapped_column(String(500), nullable=False)          # Moodle's wwwroot, e.g. https://courses.finki.ukim.mk
    client_id: Mapped[str] = mapped_column(String(200), nullable=False)
    deployment_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)  # [] = accept any
    auth_login_url: Mapped[str] = mapped_column(String(500), nullable=False)  # …/mod/lti/auth.php
    auth_token_url: Mapped[str] = mapped_column(String(500), nullable=False)  # …/mod/lti/token.php
    jwks_url: Mapped[str] = mapped_column(String(500), nullable=False)        # …/mod/lti/certs.php
    # Accounts: link a Moodle user to an existing ALE account with the same e-mail (the faculty's own Moodle)
    link_by_email: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class LtiToolKey(Base):
    __tablename__ = "lti_tool_keys"

    kid: Mapped[str] = mapped_column(String(64), primary_key=True)
    private_pem_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    public_jwk: Mapped[dict] = mapped_column(JSONB, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class LtiUser(Base):
    __tablename__ = "lti_users"
    __table_args__ = (UniqueConstraint("platform_id", "sub", name="uq_lti_user"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    platform_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("lti_platforms.id", ondelete="CASCADE"), nullable=False)
    sub: Mapped[str] = mapped_column(String(255), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    last_launch_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class LtiContext(Base):
    __tablename__ = "lti_contexts"
    __table_args__ = (UniqueConstraint("platform_id", "context_id", name="uq_lti_context"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    platform_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("lti_platforms.id", ondelete="CASCADE"), nullable=False)
    context_id: Mapped[str] = mapped_column(String(255), nullable=False)
    deployment_id: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    label: Mapped[str] = mapped_column(String(255), nullable=False, default="")   # Moodle short name, e.g. "СП-2026"
    title: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    course_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("courses.id", ondelete="SET NULL"), nullable=True)
    lineitems_url: Mapped[str] = mapped_column(String(500), nullable=False, default="")   # AGS
    ags_scopes: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    memberships_url: Mapped[str] = mapped_column(String(500), nullable=False, default="")  # NRPS
    last_roster_sync: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_grade_sync: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class LtiLineItem(Base):
    __tablename__ = "lti_line_items"
    __table_args__ = (UniqueConstraint("context_id", "assignment_id", name="uq_lti_line_item"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    context_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("lti_contexts.id", ondelete="CASCADE"), nullable=False)
    assignment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class LtiNonce(Base):
    __tablename__ = "lti_nonces"

    nonce: Mapped[str] = mapped_column(String(255), primary_key=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class LtiRegistration(Base):
    __tablename__ = "lti_registrations"

    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, default="Moodle")
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    platform_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("lti_platforms.id", ondelete="SET NULL"), nullable=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
