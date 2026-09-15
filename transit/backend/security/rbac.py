from fastapi import Depends, HTTPException, status
from backend.models_db.user import User, Role
from backend.api.deps import get_current_user
from typing import Callable

def require_role(required_role: Role) -> Callable:
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Requires {required_role.value} role."
            )
        return current_user
    return role_checker
