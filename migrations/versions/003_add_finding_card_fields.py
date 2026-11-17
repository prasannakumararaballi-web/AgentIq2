"""Add finding card fields for Phase 2 card aggregation and risk tiers.

Revision ID: 003_add_finding_card_fields
Revises: 002_add_upload_hash_and_metadata
Create Date: 2026-11-17 20:00:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "003_add_finding_card_fields"
down_revision: Union[str, None] = "002_add_upload_hash_and_metadata"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add card-level aggregation and risk tier columns to findings table
    op.add_column("findings", sa.Column("issue_title", sa.String(length=255), nullable=True))
    op.add_column("findings", sa.Column("affected_row_count", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("findings", sa.Column("affected_row_indices", sa.JSON(), nullable=True))
    op.add_column("findings", sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"))
    op.add_column("findings", sa.Column("risk_tier", sa.Integer(), nullable=False, server_default="1"))
    op.create_index("ix_findings_risk_tier", "findings", ["risk_tier"])
    op.add_column("findings", sa.Column("impact_estimate", sa.Float(), nullable=False, server_default="0.0"))
    op.add_column("findings", sa.Column("sample_before", sa.JSON(), nullable=True))
    op.add_column("findings", sa.Column("sample_after", sa.JSON(), nullable=True))
    op.add_column("findings", sa.Column("detection_rule", sa.String(length=100), nullable=True))
    op.create_index("ix_findings_detection_rule", "findings", ["detection_rule"])


def downgrade() -> None:
    op.drop_index("ix_findings_detection_rule", table_name="findings")
    op.drop_index("ix_findings_risk_tier", table_name="findings")
    op.drop_column("findings", "detection_rule")
    op.drop_column("findings", "sample_after")
    op.drop_column("findings", "sample_before")
    op.drop_column("findings", "impact_estimate")
    op.drop_column("findings", "risk_tier")
    op.drop_column("findings", "confidence")
    op.drop_column("findings", "affected_row_indices")
    op.drop_column("findings", "affected_row_count")
    op.drop_column("findings", "issue_title")
