"""Reusable FastAPI dependencies."""
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import get_db
from app.models.api_key import ApiKey
from app.models.user import User
from app.services import api_keys as api_key_service

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def get_api_key_owner(
    x_api_key: str | None = Header(default=None), db: Session = Depends(get_db)
) -> User:
    """Auth for the external/public API via X-API-Key header."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")
    prefix = x_api_key[:12]
    rows = db.execute(select(ApiKey).where(ApiKey.prefix == prefix, ApiKey.is_active)).scalars()
    for row in rows:
        if api_key_service.verify_key(x_api_key, row.hashed_key):
            user = db.get(User, row.owner_id)
            if user and user.is_active:
                return user
    raise HTTPException(status_code=401, detail="Invalid API key")
