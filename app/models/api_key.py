import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, created_at_col, uuid_pk


class ApiKey(Base):
    """Hashed external API keys for the public scoring API."""

    __tablename__ = "api_keys"

    id = uuid_pk()
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str]
    prefix: Mapped[str] = mapped_column(index=True)  # shown to user, e.g. fs_live_ab12
    hashed_key: Mapped[str]
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at = created_at_col()
