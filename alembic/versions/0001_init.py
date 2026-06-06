"""initial schema

Revision ID: 0001_init
Revises:
Create Date: 2026-06-06
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_init"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

tier = sa.Enum("light", "deep", name="tier")
colour = sa.Enum("dark_green", "green", "yellow", "unqualified", name="leadcolour")
lead_status = sa.Enum("new", "assigned", "contacted", "disqualified", name="leadstatus")
doc_status = sa.Enum("uploaded", "extracting", "extracted", "failed", name="documentstatus")
spec_status = sa.Enum(
    "pending", "running", "complete", "partial", "failed", name="speculativestatus"
)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(), nullable=False, unique=True, index=True),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("stripe_customer_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), index=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("tier", tier, nullable=False, server_default="light"),
        sa.Column("rubric", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), index=True
        ),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("content_type", sa.String(), nullable=True),
        sa.Column("storage_path", sa.String(), nullable=True),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("status", doc_status, nullable=False, server_default="uploaded"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "leads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), index=True
        ),
        sa.Column("company_name", sa.String(), nullable=False),
        sa.Column("domain", sa.String(), nullable=True, index=True),
        sa.Column("enriched_data", postgresql.JSONB(), nullable=True),
        sa.Column("signals", postgresql.JSONB(), nullable=True),
        sa.Column("speculative_data", postgresql.JSONB(), nullable=True),
        sa.Column("speculative_status", spec_status, nullable=False, server_default="pending"),
        sa.Column("score", sa.Numeric(5, 2), nullable=True),
        sa.Column("colour", colour, nullable=True),
        sa.Column(
            "assigned_to", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True,
            index=True,
        ),
        sa.Column("status", lead_status, nullable=False, server_default="new"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), index=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("prefix", sa.String(), nullable=False, index=True),
        sa.Column("hashed_key", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    for t in ("api_keys", "leads", "documents", "projects", "users"):
        op.drop_table(t)
    for e in (spec_status, doc_status, lead_status, colour, tier):
        e.drop(op.get_bind(), checkfirst=True)
