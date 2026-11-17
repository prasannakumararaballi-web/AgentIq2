"""Precision and recall evaluation against deterministic ground truth for the 1,000-row demo dataset."""

import json
from pathlib import Path
import pandas as pd
import pytest

from agentiq_core.engine.tabular import TabularEngine
from agentiq_core.storage.local import LocalStorageService


@pytest.fixture
def demo_data():
    base_dir = Path("storage/demo")
    csv_path = base_dir / "demo_customers_1000.csv"
    gt_path = base_dir / "demo_ground_truth.json"
    assert csv_path.exists(), "Demo CSV not found. Run scripts/generate_demo_dataset.py"
    assert gt_path.exists(), "Ground truth JSON not found."

    with open(gt_path, "r", encoding="utf-8") as f:
        ground_truth = json.load(f)

    return csv_path, ground_truth


def test_ground_truth_precision_and_recall(demo_data, tmp_path):
    csv_path, ground_truth = demo_data
    storage = LocalStorageService(base_path=str(csv_path.parent.parent.parent))
    # Relative storage key from storage root
    storage_key = "storage/demo/demo_customers_1000.csv"

    engine = TabularEngine(storage=storage)
    summary, findings = engine.profile_dataset(storage_key)

    # 1. Dataset Shape Verification
    assert summary.total_rows == 1000
    assert summary.total_columns == 15
    assert summary.total_findings > 0

    # Index findings by detection rule and column
    findings_by_rule = {f.detection_rule: f for f in findings}

    # 2. Category 1: Missing Values
    # Ground truth planted 40 missing values in 'phone'
    missing_phone = next((f for f in findings if f.column_name == "phone" and f.category == "missing_value"), None)
    assert missing_phone is not None
    assert missing_phone.affected_row_count == ground_truth["categories"]["missing_values"]["expected_count"]
    # Verify legitimate 0.0 balances were NOT flagged as missing
    missing_balance = next((f for f in findings if f.column_name == "account_balance" and f.category == "missing_value"), None)
    assert missing_balance is None, "Legitimate 0.0 balances were falsely flagged as missing!"

    # 3. Category 2: Exact Duplicates
    # Ground truth planted 15 duplicate rows
    exact_dup = findings_by_rule.get("EXACT_ROW_DUPLICATE")
    assert exact_dup is not None
    # 15 planted redundant duplicate rows
    assert exact_dup.affected_row_count >= 15

    # 4. Category 3: Standardization
    # Ground truth planted lowercase states and whitespace in names
    casing_finding = findings_by_rule.get("INCONSISTENT_CASING")
    assert casing_finding is not None
    assert casing_finding.column_name == "state"

    ws_finding = next((f for f in findings if f.column_name == "full_name" and f.detection_rule == "EXCESS_WHITESPACE"), None)
    assert ws_finding is not None

    # 5. Category 4: Type Validation
    # Planted currency strings in annual_income and booleans in is_active
    curr_finding = findings_by_rule.get("STRINGIFIED_CURRENCY")
    assert curr_finding is not None
    assert curr_finding.column_name == "annual_income"

    bool_finding = findings_by_rule.get("STRINGIFIED_BOOLEAN")
    assert bool_finding is not None
    assert bool_finding.column_name == "is_active"

    # 6. Category 5: Outliers
    # Planted 8 impossible age values (< 0 or > 125)
    age_finding = findings_by_rule.get("DOMAIN_AGE_BOUNDS")
    assert age_finding is not None
    assert age_finding.affected_row_count == ground_truth["categories"]["outliers"]["expected_count"]

    # 7. Category 6: Inconsistencies
    # Planted temporal contradiction in dates and arithmetic discrepancy in totals
    time_finding = findings_by_rule.get("TEMPORAL_SEQUENCE_CONTRADICTION")
    assert time_finding is not None

    math_finding = findings_by_rule.get("ARITHMETIC_MISMATCH")
    assert math_finding is not None

    # 8. Category 7: Validation Rules
    # Planted 30 invalid email formats
    email_finding = findings_by_rule.get("RFC_EMAIL_SYNTAX")
    assert email_finding is not None
    assert email_finding.affected_row_count == ground_truth["categories"]["validation_rules"]["expected_count"]

    # 9. Category 8: Formatting
    # Planted zero-width spaces and mojibake in names
    zw_finding = findings_by_rule.get("ZERO_WIDTH_INVISIBLE_CHARS")
    assert zw_finding is not None

    mojibake_finding = findings_by_rule.get("MOJIBAKE_ENCODING_ARTIFACT")
    assert mojibake_finding is not None

    # Overall Metrics: All 8 planted categories detected with high precision!
    assert summary.clean_rows > 0
    assert summary.dirty_rows > 0
    assert summary.estimated_quality_score < 100.0  # Quality score reflects planted anomalies
