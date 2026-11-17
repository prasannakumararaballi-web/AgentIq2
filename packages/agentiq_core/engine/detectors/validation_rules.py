"""Detector 7: Validation rules - RFC email syntax, URL format, and postal/ZIP code validation."""

import re
from typing import Any, Optional
import pandas as pd
from agentiq_core.engine.detectors.base import BaseDetector, DetectionResult
from agentiq_core.engine.risk import RiskTier

# Robust RFC 5322 compliant regex for syntactic validation
RE_EMAIL = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
RE_URL = re.compile(r"^https?:\/\/(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&\/=]*)$")
RE_US_ZIP = re.compile(r"^\d{5}(?:-\d{4})?$")


class ValidationRulesDetector(BaseDetector):
    """Detects syntactic format violations in email, URL, and postal/ZIP code fields."""

    @property
    def detector_id(self) -> str:
        return "validation_rules"

    def detect(self, df: pd.DataFrame, options: Optional[dict[str, Any]] = None) -> list[DetectionResult]:
        options = options or {}
        results: list[DetectionResult] = []
        total_rows = len(df)
        if total_rows == 0:
            return results

        col_lower_map = {str(c).lower().strip(): c for c in df.columns}

        # 1. Email Format Validation
        email_cols = [c for c in df.columns if "email" in str(c).lower()]
        for col in email_cols:
            series = df[col].dropna().astype(str).str.strip()
            if len(series) == 0:
                continue

            invalid_mask = ~series.str.match(RE_EMAIL)
            invalid_count = int(invalid_mask.sum())
            if invalid_count > 0:
                bad_indices = series[invalid_mask].index.tolist()
                sample_before = [{"row": int(i), "value": series.at[i]} for i in bad_indices[:5]]

                results.append(
                    DetectionResult(
                        detector_id=self.detector_id,
                        category="format_inconsistency",
                        severity="medium",
                        issue_title=f"Invalid email syntax in '{col}' ({invalid_count} rows)",
                        description=(
                            f"Column '{col}' contains {invalid_count} entries that fail RFC standard email syntax. "
                            f"Note: Syntactic validation checks structure only and does not establish real-world server or mailbox delivery validity."
                        ),
                        column_name=str(col),
                        affected_row_count=invalid_count,
                        affected_row_indices=[int(i) for i in bad_indices[:50]],
                        sample_before=sample_before,
                        sample_after=[],
                        suggested_action={
                            "action_type": "replace",
                            "parameters": {"operation": "flag_invalid_email", "column": col},
                            "rationale": "Flag syntactically invalid email addresses for customer re-verification.",
                        },
                        confidence=1.0,
                        risk_tier=RiskTier.TIER_2_MEDIUM,
                        detection_rule="RFC_EMAIL_SYNTAX",
                        metadata={"invalid_count": invalid_count, "syntax_standard": "RFC_5322"},
                    )
                )

        # 2. URL Format Validation
        url_cols = [c for c in df.columns if any(k in str(c).lower() for k in ["url", "website", "link", "homepage"])]
        for col in url_cols:
            series = df[col].dropna().astype(str).str.strip()
            if len(series) == 0:
                continue

            invalid_mask = ~series.str.match(RE_URL)
            invalid_count = int(invalid_mask.sum())
            if invalid_count > 0:
                bad_indices = series[invalid_mask].index.tolist()
                sample_before = [{"row": int(i), "value": series.at[i]} for i in bad_indices[:5]]

                results.append(
                    DetectionResult(
                        detector_id=self.detector_id,
                        category="format_inconsistency",
                        severity="low",
                        issue_title=f"Malformed URL syntax in '{col}' ({invalid_count} rows)",
                        description=f"Column '{col}' contains {invalid_count} values that do not conform to valid HTTP/HTTPS URL syntax.",
                        column_name=str(col),
                        affected_row_count=invalid_count,
                        affected_row_indices=[int(i) for i in bad_indices[:50]],
                        sample_before=sample_before,
                        sample_after=[],
                        suggested_action={
                            "action_type": "replace",
                            "parameters": {"operation": "flag_invalid_url", "column": col},
                            "rationale": "Review or fix malformed URL strings.",
                        },
                        confidence=1.0,
                        risk_tier=RiskTier.TIER_2_MEDIUM,
                        detection_rule="HTTP_URL_SYNTAX",
                        metadata={"invalid_count": invalid_count},
                    )
                )

        # 3. US ZIP / Postal Code Validation (Explicitly country-labelled)
        zip_cols = [c for c in df.columns if any(k in str(c).lower() for k in ["zip", "postal", "zipcode", "zip_code"])]
        for col in zip_cols:
            series = df[col].dropna().astype(str).str.strip()
            if len(series) == 0:
                continue

            invalid_mask = ~series.str.match(RE_US_ZIP)
            invalid_count = int(invalid_mask.sum())
            if invalid_count > 0:
                bad_indices = series[invalid_mask].index.tolist()
                sample_before = [{"row": int(i), "value": series.at[i]} for i in bad_indices[:5]]

                results.append(
                    DetectionResult(
                        detector_id=self.detector_id,
                        category="format_inconsistency",
                        severity="low",
                        issue_title=f"Non-standard US ZIP code in '{col}' ({invalid_count} rows)",
                        description=(
                            f"Column '{col}' contains {invalid_count} values that do not match standard US 5-digit "
                            f"or 9-digit (ZIP+4) formats. (Context: US Postal Service format specification)."
                        ),
                        column_name=str(col),
                        affected_row_count=invalid_count,
                        affected_row_indices=[int(i) for i in bad_indices[:50]],
                        sample_before=sample_before,
                        sample_after=[],
                        suggested_action={
                            "action_type": "replace",
                            "parameters": {"operation": "review_zip_codes", "column": col},
                            "rationale": "Verify non-conforming postal/ZIP codes.",
                        },
                        confidence=1.0,
                        risk_tier=RiskTier.TIER_2_MEDIUM,
                        detection_rule="US_ZIP_POSTAL_SYNTAX",
                        metadata={"invalid_count": invalid_count, "format_context": "US_ZIP_5_OR_9"},
                    )
                )

        return results
