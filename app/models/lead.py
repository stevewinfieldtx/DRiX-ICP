import uuid

from sqlalchemy import ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, created_at_col, uuid_pk
from app.models.enums import LeadColour, LeadStatus, SpeculativeStatus


class Lead(Base):
    """A scored prospect. Matches Brief v1.1 Section 4 (updated)."""

    __tablename__ = "leads"

    id = uuid_pk()
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), index=True)
    company_name: Mapped[str]
    domain: Mapped[str | None] = mapped_column(default=None, index=True)

    # raw API responses used for scoring (Tier 2)
    enriched_data: Mapped[dict | None] = mapped_column(JSONB, default=None)
    # resolved signal values, e.g. {"industry": 15, "employee_count": 10}
    signals: Mapped[dict | None] = mapped_column(JSONB, default=None)
    # Section 8: ALL extra data harvested for future pattern mining (compliant sources only)
    speculative_data: Mapped[dict | None] = mapped_column(JSONB, default=None)
    speculative_status: Mapped[SpeculativeStatus] = mapped_column(default=SpeculativeStatus.pending)

    score: Mapped[float | None] = mapped_column(Numeric(5, 2), default=None)
    colour: Mapped[LeadColour | None] = mapped_column(default=None)

    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), default=None, index=True
    )
    status: Mapped[LeadStatus] = mapped_column(default=LeadStatus.new)
    created_at = created_at_col()

    project: Mapped["Project"] = relationship(back_populates="leads")  # noqa: F821
