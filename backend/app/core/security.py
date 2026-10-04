from fastapi import Depends
from passlib.context import CryptContext

from app.core.exceptions import AuthorizationError

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


async def get_current_user():
    # NOTE: This is a **development-only** stub.
    # In production this function must be replaced with proper authentication
    # (OAuth2/JWT, LDAP, etc.) and must NOT return a hard-coded user.
    return {"id": "1", "username": "dev_clinician", "role": "clinician"}


def require_role(required_role: str):
    async def role_checker(user: dict = Depends(get_current_user)):
        if user.get("role") != required_role:
            raise AuthorizationError(f"Requires {required_role} role")
        return user

    return role_checker
