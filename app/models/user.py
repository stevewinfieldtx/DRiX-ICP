from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, created_at_col, uuid_pk


class User(Base):
    __tablename__ = "users"

    id = uuid_pk()
    email: Mapped[str] = mapped_column(unique=True, index=True)
    hashed_password: Mapped[str]
    full_name: Mapped[str | None] = mapped_column(default=None)
    is_active: Mapped[bool] = mapped_column(default=True)
    stripe_customer_id: Mapped[str | None] = mapped_column(default=None)
    created_at = created_at_col()

    projects: Mapped[list["Project"]] = relationship(back_populates="owner")  # noqa: F821
