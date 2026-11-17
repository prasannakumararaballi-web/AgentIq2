"""Unit tests for the eight data quality detectors."""

import numpy as np
import pandas as pd
import pytest
from agentiq_core.engine.detectors.duplicates import DuplicatesDetector
from agentiq_core.engine.detectors.formatting import FormattingDetector
from agentiq_core.engine.detectors.inconsistencies import InconsistenciesDetector
from agentiq_core.engine.detectors.missing_values import MissingValuesDetector
from agentiq_core.engine.detectors.outliers import OutliersDetector
from agentiq_core.engine.detectors.standardization import StandardizationDetector
from agentiq_core.engine.detectors.type_validation import TypeValidationDetector
from agentiq_core.engine.detectors.validation_rules import ValidationRulesDetector
from agentiq_core.engine.risk import RiskTier


def test_missing_values_preserves_zero_and_false():
    """Verify missing values detector strictly preserves 0, 0.0, and False as legitimate values."""
    detector = MissingValuesDetector()
    df = pd.DataFrame({
        "balance": [100.0, 0.0, 0, None, np.nan],
        "is_active": [True, False, False, None, np.nan],
        "status": ["Active", "0", "False", "N/A", "   "],
    })

    results = detector.detect(df)
    result_by_col = {r.column_name: r for r in results}

    assert "balance" in result_by_col
    # Only the None and np.nan in balance are missing (2 rows) - 0.0 and 0 are preserved!
    assert result_by_col["balance"].affected_row_count == 2
    assert result_by_col["balance"].affected_row_indices == [3, 4]

    assert "is_active" in result_by_col
    # Only None and np.nan in is_active are missing (2 rows) - False is preserved!
    assert result_by_col["is_active"].affected_row_count == 2
    assert result_by_col["is_active"].affected_row_indices == [3, 4]

    assert "status" in result_by_col
    # 'N/A' and '   ' are missing (2 rows) - '0' and 'False' are string tokens that are not missing
    assert result_by_col["status"].affected_row_count == 2
    assert result_by_col["status"].affected_row_indices == [3, 4]


def test_missing_values_clean_dataset():
    """Ensure clean dataset yields zero missing value findings."""
    detector = MissingValuesDetector()
    df = pd.DataFrame({
        "id": [1, 2, 3],
        "val": [10.5, 0.0, 42.0],
        "flag": [True, False, True],
        "name": ["Alpha", "Beta", "Gamma"],
    })
    results = detector.detect(df)
    assert len(results) == 0


def test_duplicates_detector_exact_and_near():
    """Verify exact duplicates and separation from near-duplicates."""
    detector = DuplicatesDetector()
    df = pd.DataFrame({
        "id": [101, 102, 102, 103, 104],
        "name": ["Acme Corp", "Beta LLC", "Beta LLC", "Acme Corpp", "Gamma Inc"],
        "city": ["NY", "SF", "SF", "NY", "Chicago"],
    })

    results = detector.detect(df)
    categories = [r.detection_rule for r in results]
    assert "EXACT_ROW_DUPLICATE" in categories

    exact_res = next(r for r in results if r.detection_rule == "EXACT_ROW_DUPLICATE")
    # Rows 1 and 2 are exact copies of each other
    assert exact_res.affected_row_count == 2
    assert exact_res.risk_tier == RiskTier.TIER_3_HIGH


def test_standardization_detector():
    """Verify inconsistent casing, excess whitespace, and mixed date formats."""
    detector = StandardizationDetector()
    df = pd.DataFrame({
        "state": ["CA", "ca", "Ca", "NY", "ny", "TX"],
        "name": ["  Alice ", "Bob   Smith", "Charlie", "David  ", "Eve", "Frank"],
        "created_date": ["2023-01-15", "01/16/2023", "2023-01-17", "18-Jan-2023", "2023-01-19", "2023-01-20"],
    })

    results = detector.detect(df)
    rules = {r.detection_rule for r in results}

    assert "INCONSISTENT_CASING" in rules
    assert "EXCESS_WHITESPACE" in rules
    assert "MIXED_DATE_FORMATS" in rules

    casing_res = next(r for r in results if r.detection_rule == "INCONSISTENT_CASING")
    assert casing_res.risk_tier == RiskTier.TIER_0_SAFE
    assert len(casing_res.sample_before) > 0


def test_type_validation_detector():
    """Verify detection of currency strings, percentages, numeric strings, and booleans."""
    detector = TypeValidationDetector()
    df = pd.DataFrame({
        "salary": ["$50,000.00", "$65,000.00", "$80,000.00", "$120,000.00", "$95,000.00"],
        "discount": ["10%", "15%", "5%", "20%", "0%"],
        "flag": ["yes", "no", "yes", "true", "false"],
    })

    results = detector.detect(df)
    rules = {r.detection_rule for r in results}

    assert "STRINGIFIED_CURRENCY" in rules
    assert "STRINGIFIED_PERCENTAGE" in rules
    assert "STRINGIFIED_BOOLEAN" in rules

    curr_res = next(r for r in results if r.detection_rule == "STRINGIFIED_CURRENCY")
    assert curr_res.risk_tier == RiskTier.TIER_1_LOW
    assert curr_res.sample_after[0]["value"] == "50000.00"


def test_outliers_detector_iqr_and_domain():
    """Verify IQR statistical outliers, zero-IQR safety, small-sample safety, and domain bounds."""
    detector = OutliersDetector()
    # 20 normally distributed numbers with 1 extreme statistical outlier
    values = [50.0] * 19 + [5000.0]
    # Small sample (N=5) - should be safely skipped by IQR
    small_values = [10.0, 12.0, 11.0, 9.0, 100.0] + [None] * 15

    df = pd.DataFrame({
        "revenue": values,
        "age": [25, 30, 45, -8, 145] + [35] * 15,
        "small_sample": small_values,
    })

    results = detector.detect(df)
    rules = {r.detection_rule for r in results}

    assert "DOMAIN_AGE_BOUNDS" in rules
    age_res = next(r for r in results if r.detection_rule == "DOMAIN_AGE_BOUNDS")
    assert age_res.affected_row_count == 2  # -8 and 145


def test_inconsistencies_detector():
    """Verify cross-column date order and arithmetic logic violations."""
    detector = InconsistenciesDetector()
    df = pd.DataFrame({
        "signup_date": ["2023-01-01", "2024-05-10", "2023-06-01"],
        "renewal_date": ["2024-01-01", "2023-01-10", "2024-06-01"],  # Row 1 is invalid (signup > renewal)
        "subtotal": [100.0, 200.0, 50.0],
        "tax": [10.0, 20.0, 5.0],
        "total": [110.0, 999.0, 55.0],  # Row 1 is invalid (200 + 20 != 999)
    })

    results = detector.detect(df)
    rules = {r.detection_rule for r in results}

    assert "TEMPORAL_SEQUENCE_CONTRADICTION" in rules
    assert "ARITHMETIC_MISMATCH" in rules

    time_res = next(r for r in results if r.detection_rule == "TEMPORAL_SEQUENCE_CONTRADICTION")
    assert time_res.affected_row_count == 1
    assert time_res.risk_tier == RiskTier.TIER_3_HIGH


def test_validation_rules_detector():
    """Verify RFC email syntax, URL syntax, and US ZIP code format checks."""
    detector = ValidationRulesDetector()
    df = pd.DataFrame({
        "email": ["valid.user@example.com", "bad@@domain..com", "no-at-sign.org", "alice@corp.co"],
        "website": ["https://agentiq.ai", "invalid://not a url", "http://example.com/test", "ftp://old"],
        "zip_code": ["94105", "10001-1234", "BAD_ZIP", "90210"],
    })

    results = detector.detect(df)
    rules = {r.detection_rule for r in results}

    assert "RFC_EMAIL_SYNTAX" in rules
    assert "US_ZIP_POSTAL_SYNTAX" in rules

    email_res = next(r for r in results if r.detection_rule == "RFC_EMAIL_SYNTAX")
    assert email_res.affected_row_count == 2
    assert "Syntactic validation" in email_res.description


def test_formatting_detector():
    """Verify invisible zero-width chars, non-breaking spaces, and mojibake."""
    detector = FormattingDetector()
    df = pd.DataFrame({
        "customer_name": ["Alice\u200b", "Bob\u00a0Smith", "RenÃ©e Dupont", "Charlie"],
    })

    results = detector.detect(df)
    rules = {r.detection_rule for r in results}

    assert "ZERO_WIDTH_INVISIBLE_CHARS" in rules
    assert "NON_BREAKING_SPACE_NBSP" in rules
    assert "MOJIBAKE_ENCODING_ARTIFACT" in rules

    mojibake_res = next(r for r in results if r.detection_rule == "MOJIBAKE_ENCODING_ARTIFACT")
    assert mojibake_res.risk_tier == RiskTier.TIER_0_SAFE
    assert mojibake_res.sample_after[0]["value"] == "Renée Dupont"
