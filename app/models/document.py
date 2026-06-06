import uuid

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, created_at_col, uuid_pk
from app.models.enums import DocumentStatus


class Document(Base):
    """Uploaded solution material; text is extracted to feed rubric generation."""

    __tablename__ = "documents"

    id = uuid_pk()
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), index=True)
    filename: Mapped[str]
    content_type: Mapped[str | None] = mapped_column(default=None)
    storage_path: Mapped[str | None] = mapped_column(default=None)
    extracted_text: Mapped[str | None] = mapped_column(Text, default=None)
    status: Mapped[DocumentStatus] = mapped_column(default=DocumentStatus.uploaded)
    created_at = created_at_col()

    project: Mapped["Project"] = relationship(back_populates="documents")  # noqa: F821
