from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.api.deps import get_current_user, get_db
from backend.models_db.user import Role, User
from backend.security.rbac import require_role

router = APIRouter()


class RoleUpdate(BaseModel):
    role: Role


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "email": current_user.email, "role": current_user.role.value}


@router.get("")
def list_users(db: Session = Depends(get_db), admin: User = Depends(require_role(Role.admin))):
    return [{"id": u.id, "email": u.email, "role": u.role.value} for u in db.query(User).order_by(User.email).all()]


@router.patch("/{user_id}/role")
def set_role(user_id: str, body: RoleUpdate, db: Session = Depends(get_db), admin: User = Depends(require_role(Role.admin))):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "User not found")
    if user.id == admin.id and body.role != Role.admin:
        raise HTTPException(400, "Admins cannot demote themselves.")
    user.role = body.role
    db.commit()
    return {"id": user.id, "email": user.email, "role": user.role.value}
