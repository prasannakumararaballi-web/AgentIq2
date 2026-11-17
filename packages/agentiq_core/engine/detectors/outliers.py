"""Detector 5: Outliers - IQR statistical outliers and domain bound violations."""

from typing import Any, Optional
import numpy as np
import pandas as pd
from agentiq_core.engine.detectors.base import BaseDetector, DetectionResult
from agentiq_core.engine.risk import RiskTier


class OutliersDetector(BaseDetector):
    """Detects statistical outliers using IQR and domain-contextual violations."""

    @property
    def detector_id(self) -> str:
        return "outliers"

    def detect(self, df: pd.DataFrame, options: Optional[dict[str, Any]] = None) -> list[DetectionResult]:
        options = options or {}
        iqr_multiplier = float(options.get("iqr_multiplier", 1.5))
        results: list[DetectionResult] = []
        total_rows = len(df)
        if total_rows == 0:
            return results

        # 1. Inspect numeric columns for IQR Statistical Outliers
        for col in df.columns:
            series = df[col]
            if not pd.api.types.is_numeric_dtype(series) or pd.api.types.is_bool_dtype(series):
                continue

            clean_series = series.dropna()
            n_clean = len(clean_series)
            # Safe small-sample check: Need at least 15 numeric points for statistical validity
            if n_clean < 15:
                continue

            q1 = float(clean_series.quantile(0.25))
            q3 = float(clean_series.quantile(0.75))
            iqr = q3 - q1

            # Safe zero-IQR handling: If IQR is 0 (constant or identical median values), skip IQR to prevent false positives
            if iqr <= 1e-9:
                continue

            lower_bound = q1 - (iqr_multiplier * iqr)
            upper_bound = q3 + (iqr_multiplier * iqr)

            outlier_mask = (clean_series < lower_bound) | (clean_series > upper_bound)
            outlier_indices = clean_series[outlier_mask].index.tolist()
            outlier_count = len(outlier_indices)

            if outlier_count > 0:
                outlier_ratio = outlier_count / n_clean
                sample_before = []
                for idx in outlier_indices[:5]:
                    val = clean_series.at[idx]
                    sample_before.append({"row": int(idx), "value": f"{val} (Bounds: [{lower_bound:.2f}, {upper_bound:.2f}])"})

                results.append(
                    DetectionResult(
                        detector_id=self.detector_id,
                        category="outlier",
                        severity="high" if outlier_ratio > 0.05 else "medium",
                        issue_title=f"Statistical outliers in '{col}' ({outlier_count} values outside IQR bounds)",
                        description=(
                            f"Column '{col}' has {outlier_count} statistical outliers outside "
                            f"[{lower_bound:.2f}, {upper_bound:.2f}] based on {iqr_multiplier}x IQR "
                            f"(Q1={q1:.2f}, Q3={q3:.2f}, IQR={iqr:.2f})."
                        ),
                        column_name=str(col),
                        affected_row_count=outlier_count,
                        affected_row_indices=[int(i) for i in outlier_indices[:50]],
                        sample_before=sample_before,
                        sample_after=[],
                        suggested_action={
                            "action_type": "replace",
                            "parameters": {"operation": "cap_outliers", "lower": lower_bound, "upper": upper_bound, "column": col},
                            "rationale": "Review or cap values exceeding interquartile distribution thresholds.",
                        },
                        confidence=0.85,
                        risk_tier=RiskTier.TIER_2_MEDIUM,
                        detection_rule="IQR_STATISTICAL_OUTLIER",
                        metadata={
                            "q1": q1,
                            "q3": q3,
                            "iqr": iqr,
                            "lower_bound": lower_bound,
                            "upper_bound": upper_bound,
                            "outlier_count": outlier_count,
                        },
                    )
                )

        # 2. Domain-Contextual Bound Violations (Domain Rules kept separate from statistical IQR)
        domain_rules = options.get("domain_rules", {})
        # Built-in contextual heuristics if not overridden
        col_lower_map = {str(c).lower(): c for c in df.columns}
        
        # Check for Age columns
        for key in ["age", "customer_age", "user_age"]:
            if key in col_lower_map:
                actual_col = col_lower_map[key]
                if pd.api.types.is_numeric_dtype(df[actual_col]):
                    age_series = df[actual_col].dropna()
                    # Age < 0 or Age > 125 is physically impossible in human customer demographics
                    invalid_mask = (age_series < 0) | (age_series > 125)
                    if invalid_mask.any():
                        bad_indices = age_series[invalid_mask].index.tolist()
                        sample_before = [{"row": int(i), "value": f"Age = {age_series.at[i]}"} for i in bad_indices[:5]]
                        results.append(
                            DetectionResult(
                                detector_id=self.detector_id,
                                category="outlier",
                                severity="high",
                                issue_title=f"Physically impossible age values in '{actual_col}' ({len(bad_indices)} rows)",
                                description=f"Column '{actual_col}' contains {len(bad_indices)} records with age < 0 or > 125.",
                                column_name=str(actual_col),
                                affected_row_count=len(bad_indices),
                                affected_row_indices=[int(i) for i in bad_indices[:50]],
                                sample_before=sample_before,
                                sample_after=[],
                                suggested_action={
                                    "action_type": "replace",
                                    "parameters": {"operation": "flag_invalid_age", "column": actual_col},
                                    "rationale": "Correct or set invalid negative/extreme ages to NULL for manual inspection.",
                                },
                                confidence=1.0,  # Exact domain bound failure
                                risk_tier=RiskTier.TIER_3_HIGH,  # Correcting domain data is high risk
                                detection_rule="DOMAIN_AGE_BOUNDS",
                                metadata={"invalid_count": len(bad_indices)},
                            )
                        )

        return results
