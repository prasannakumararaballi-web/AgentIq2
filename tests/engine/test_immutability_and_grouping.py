"""Tests for storage integration, SHA-256 immutability, card grouping, and risk tiers."""

import hashlib
import io
from pathlib import Path
from uuid import uuid4
import pandas as pd
import pytest

from agentiq_core.engine.risk import RiskTier
from agentiq_core.engine.tabular import TabularEngine
from agentiq_core.storage.local import LocalStorageService


@pytest.fixture
def temp_storage(tmp_path: Path) -> LocalStorageService:
    return LocalStorageService(base_path=str(tmp_path))


def test_tabular_engine_immutability_and_grouping(temp_storage: LocalStorageService):
    """Verify SHA-256 remains 100% identical before and after profiling and preview is bounded."""
    rows = []
    for i in range(200):
        rows.append({
            "id": i,
            "email": "invalid@@domain.com" if i % 2 == 0 else f"user{i}@example.com",
            "state": "ca" if i % 3 == 0 else "CA",
            "age": -5 if i == 10 else 30,
        })
    df = pd.DataFrame(rows)
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    raw_bytes = buf.getvalue()

    storage_key = "workspaces/ws1/projects/p1/test_dataset.csv"
    engine = TabularEngine(storage=temp_storage)
    _, original_sha256, _ = engine._save_bytes_to_storage(storage_key, raw_bytes)

    summary, findings = engine.profile_dataset(storage_key)

    # 1. Verify SHA-256 of stored file is untouched
    verify_bytes = engine._read_bytes_from_storage(storage_key)
    after_sha256 = hashlib.sha256(verify_bytes).hexdigest()
    assert original_sha256 == after_sha256

    # 2. Verify summary metrics are computed from real data
    assert summary.total_rows == 200
    assert summary.total_columns == 4
    assert summary.total_findings > 0
    assert 0.0 <= summary.estimated_quality_score <= 100.0

    # 3. Verify card grouping: 100 invalid emails consolidated into 1 card with bounded preview <= 50
    email_finding = next(f for f in findings if f.column_name == "email" and f.detection_rule == "RFC_EMAIL_SYNTAX")
    assert email_finding.affected_row_count == 100
    assert len(email_finding.affected_row_indices) == 50  # Bounded preview capped at 50!
    assert len(email_finding.sample_before) <= 5


def test_apply_decisions_risk_tier_gating(temp_storage: LocalStorageService):
    """Verify unapproved Tier 3 actions are rejected and original file is preserved."""
    df = pd.DataFrame({
        "id": [1, 2, 2, 3],
        "name": ["  Alice ", "Bob", "Bob", "Charlie"],
    })
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    raw_bytes = buf.getvalue()

    storage_key = "workspaces/ws1/test_gating.csv"
    engine = TabularEngine(storage=temp_storage)
    _, orig_hash, _ = engine._save_bytes_to_storage(storage_key, raw_bytes)

    output_key = "workspaces/ws1/cleaned.csv"

    # Decisions: 1 Tier 0 (whitespace), 1 unapproved Tier 3 (drop_row)
    decisions = [
        {
            "action_type": "trim_whitespace",
            "risk_tier": RiskTier.TIER_0_SAFE,
            "is_approved": False,  # Tier 0 is safe/auto
            "parameters": {"column": "name"},
        },
        {
            "action_type": "drop_row",
            "risk_tier": RiskTier.TIER_3_HIGH,
            "is_approved": False,  # Tier 3 MUST have approval
            "parameters": {"strategy": "keep_first"},
        },
    ]

    result = engine.apply_decisions(storage_key, decisions, output_key)

    # 1. Unapproved Tier 3 was skipped
    assert result["skipped_decisions_count"] == 1
    assert result["applied_decisions_count"] == 1

    # 2. Original file unchanged
    verify_bytes = engine._read_bytes_from_storage(storage_key)
    assert hashlib.sha256(verify_bytes).hexdigest() == orig_hash

    # 3. Cleaned file exists and was trimmed
    cleaned_bytes = engine._read_bytes_from_storage(output_key)
    cleaned_df = pd.read_csv(io.BytesIO(cleaned_bytes))
    assert cleaned_df.at[0, "name"] == "Alice"  # Trimmed!
    assert len(cleaned_df) == 4  # Duplicate was NOT dropped because unapproved!
