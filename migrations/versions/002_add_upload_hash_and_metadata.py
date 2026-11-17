"""Add file_hash and metadata columns to uploads table.

Revision ID: 002_add_upload_hash_and_metadata
Revises: 001_initial_schema
Create Date: 2026-11-17 19:20:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "002_add_upload_hash_and_metadata"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add file_hash as nullable for backward-compatibility with existing records
    op.add_column(
        "uploads",
        sa.Column("file_hash", sa.String(length=64), nullable=True),
    )
    op.create_index("ix_uploads_file_hash", "uploads", ["file_hash"])

    # 2. Add metadata JSON column for sheet names, detected encoding, headers, warnings
    op.add_column(
        "uploads",
        sa.Column("metadata", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_index("ix_uploads_file_hash", table_name="uploads")
    op.drop_column("uploads", "metadata")
    op.drop_column("uploads", "file_hash")
