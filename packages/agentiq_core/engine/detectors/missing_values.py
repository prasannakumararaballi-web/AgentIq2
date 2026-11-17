"""Detector 1: Missing values, nulls, whitespace-only, and configured placeholder tokens."""

from typing import Any, Optional
import numpy as np
import pandas as pd
from agentiq_core.engine.detectors.base import BaseDetector, DetectionResult
from agentiq_core.engine.risk import RiskTier

DEFAULT_MISSING_TOKENS = {
    "n/a",
    "na",
    "null",
    "unknown",
    "-",
    "--",
    "#n/a",
    "none",
    "nil",
    "<null>",
    "<na>",
    "nan",
}


class MissingValuesDetector(BaseDetector):
    """Detects missing, null, empty, whitespace-only, and placeholder values while strictly preserving 0, 0.0, and False."""

    @property
    def detector_id(self) -> str:
        return "missing_values"

    def detect(self, df: pd.DataFrame, options: Optional[dict[str, Any]] = None) -> list[DetectionResult]:
        options = options or {}
        custom_tokens = set(t.lower() for t in options.get("missing_tokens", []))
        missing_tokens = DEFAULT_MISSING_TOKENS | custom_tokens

        results: list[DetectionResult] = []
        total_rows = len(df)
        if total_rows == 0:
            return results

        for col in df.columns:
            series = df[col]
            missing_mask = pd.Series(False, index=series.index)

            # 1. Standard pandas / numpy null & NaN
            # Note: series.isna() correctly preserves 0, 0.0, and False
            missing_mask |= series.isna()

            # 2. String-level checks for objects/strings
            # Carefully avoid converting numbers or booleans to strings!
            if series.dtype == object or pd.api.types.is_string_dtype(series):
                for idx, val in series.items():
                    if missing_mask.at[idx]:
                        continue
                    # Explicit check: If val is bool, int, or float (e.g. 0 or False), it is NOT missing!
                    if isinstance(val, (bool, int, float)) and not (isinstance(val, float) and np.isnan(val)):
                        continue
                    if isinstance(val, str):
                        stripped = val.strip()
                        if len(stripped) == 0:
                            missing_mask.at[idx] = True
                        elif stripped.lower() in missing_tokens:
                            missing_mask.at[idx] = True

            affected_indices = missing_mask[missing_mask].index.tolist()
            count = len(affected_indices)
            if count == 0:
                continue

            ratio = count / total_rows
            if ratio >= 0.5:
                severity = "critical" if ratio >= 0.8 else "high"
            elif ratio >= 0.1:
                severity = "medium"
            else:
                severity = "low"

            sample_before = []
            for idx in affected_indices[:5]:
                raw_val = series.at[idx]
                if pd.isna(raw_val):
                    display_val = "NULL"
                else:
                    display_val = str(raw_val)
                sample_before.append({"row": int(idx), "value": display_val})

            # Formulate suggested action
            if pd.api.types.is_numeric_dtype(series):
                suggested_action = {
                    "action_type": "impute",
                    "parameters": {"strategy": "median", "column": col},
                    "rationale": f"Impute missing numeric values using column median.",
                }
                risk_tier = RiskTier.TIER_2_MEDIUM
            else:
                suggested_action = {
                    "action_type": "replace",
                    "parameters": {"value": "Unknown", "column": col},
                    "rationale": f"Replace missing text entries with 'Unknown' placeholder.",
                }
                risk_tier = RiskTier.TIER_2_MEDIUM

            results.append(
                DetectionResult(
                    detector_id=self.detector_id,
                    category="missing_value",
                    severity=severity,
                    issue_title=f"Missing values in column '{col}' ({count} rows, {ratio:.1%})",
                    description=(
                        f"Column '{col}' contains {count} missing, empty, or placeholder entries "
                        f"({ratio:.1%} of {total_rows} total rows)."
                    ),
                    column_name=str(col),
                    affected_row_count=count,
                    affected_row_indices=[int(i) for i in affected_indices[:50]],
                    sample_before=sample_before,
                    sample_after=[],
                    suggested_action=suggested_action,
                    confidence=1.0,  # Exact evidence-based detection
                    risk_tier=risk_tier,
                    detection_rule="MISSING_NULL_TOKEN",
                    metadata={
                        "missing_count": count,
                        "missing_ratio": round(ratio, 4),
                        "column_dtype": str(series.dtype),
                    },
                )
            )

        return results
