"""Admin: user accounts and their type (student | teacher | admin). What a teacher may do is set per subject
(course members' permissions), not here."""
import uuid
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_admin
from app.database import get_db
from app.models.user import User

router = APIRouter(prefix="/admin/users", tags=["admin-users"])


class RoleIn(BaseModel):
    # student | teacher | admin ("assistant" / "professor" are old names of a teacher account)
    role: Literal["student", "teacher", "assistant", "professor", "admin"]


def _out(u: User) -> dict:
    return {"id": str(u.id), "name": u.name, "email": u.email, "role": u.role,
            "auth_provider": u.auth_provider, "created_at": u.created_at.isoformat() + "Z"}


@router.get("")
async def list_users(q: str = "", role: Optional[str] = None, limit: int = Query(100, le=500), offset: int = 0,
                     db: AsyncSession = Depends(get_db), _: User = Depends(get_current_admin)):
    stmt = select(User)
    if q.strip():
        like = f"%{q.strip().lower()}%"
        stmt = stmt.where(or_(func.lower(User.name).like(like), func.lower(User.email).like(like)))
    if role:
        stmt = stmt.where(User.role == role)
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    users = (await db.execute(stmt.order_by(User.created_at.desc()).limit(limit).offset(offset))).scalars().all()
    counts = dict((await db.execute(select(User.role, func.count()).group_by(User.role))).all())
    return {"total": total, "users": [_out(u) for u in users], "by_role": counts}


@router.patch("/{user_id}")
async def set_role(user_id: uuid.UUID, body: RoleIn, db: AsyncSession = Depends(get_db),
                   admin: User = Depends(get_current_admin)):
    u = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if u is None:
        raise HTTPException(status_code=404, detail="User not found")
    if u.id == admin.id and body.role != "admin":
        raise HTTPException(status_code=409, detail="You can't remove your own admin role")
    old = u.role
    new = "teacher" if body.role in ("assistant", "professor") else body.role
    u.role = new
    from app.services import spaces
    await db.flush()
    await spaces.sync_students(db, u.id)       # a student is in the spaces of their plan; others are not
    await db.commit()
    from app.services import observability
    await observability.activity("user_role", member=u.id, email=u.email, old=old, new=new)
    return _out(u)
