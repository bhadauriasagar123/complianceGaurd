"""Fix audit_logs schema for ORM compatibility.

Revision ID: 002
Revises: 001
Create Date: 2026-05-21
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {col["name"]: col for col in inspector.get_columns("audit_logs")}

    if "created_at" not in columns:
        op.add_column(
            "audit_logs",
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )

    ip_col = columns.get("ip_address")
    if ip_col and isinstance(ip_col["type"], postgresql.INET):
        op.alter_column(
            "audit_logs",
            "ip_address",
            existing_type=postgresql.INET(),
            type_=sa.String(45),
            existing_nullable=True,
            postgresql_using="ip_address::text",
        )


def downgrade() -> None:
    op.alter_column(
        "audit_logs",
        "ip_address",
        existing_type=sa.String(45),
        type_=postgresql.INET(),
        existing_nullable=True,
        postgresql_using="ip_address::inet",
    )
    op.drop_column("audit_logs", "created_at")
