import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, created_at_col, uuid_pk
from app.models.enums import Tier


class Project(Base):
    __tablename__ = "projects"

    id = uuid_pk()
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str]
    tier: Mapped[Tier] = mapped_column(default=Tier.light)
    # Generated ICP rubric: list of weighted signals. Shape documented in schemas/rubric.py
    rubric: Mapped[dict | None] = mapped_column(JSONB, default=None)
    created_at = created_at_col()

    owner: Mapped["User"] = relationship(back_populates="projects")  # noqa: F821
    documents: Mapped[list["Document"]] = relationship(  # noqa: F821
        back_populates="project", cascade="all, delete-orphan"
    )
    leads: Mapped[list["Lead"]] = relationship(  # noqa: F821
        back_populates="project", cascade="all, delete-orphan"
    )
