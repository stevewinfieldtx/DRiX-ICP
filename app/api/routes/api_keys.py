from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.api_key import ApiKey
from app.models.user import User
from app.services import api_keys as svc

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


class ApiKeyCreate(BaseModel):
    name: str


@router.post("")
def create_key(
    payload: ApiKeyCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    raw, prefix, hashed = svc.generate_key()
    key = ApiKey(owner_id=user.id, name=payload.name, prefix=prefix, hashed_key=hashed)
    db.add(key)
    db.commit()
    # raw key shown ONCE
    return {"id": str(key.id), "name": key.name, "api_key": raw, "prefix": prefix}


@router.get("")
def list_keys(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.execute(select(ApiKey).where(ApiKey.owner_id == user.id)).scalars().all()
    return [{"id": str(k.id), "name": k.name, "prefix": k.prefix, "active": k.is_active} for k in rows]
