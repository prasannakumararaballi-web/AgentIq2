"""Detector 3: Standardization - inconsistent casing, whitespace, and date representations."""

import re
from typing import Any, Optional
import pandas as pd
from agentiq_core.engine.detectors.base import BaseDetector, DetectionResult
from agentiq_core.engine.risk import RiskTier


class StandardizationDetector(BaseDetector):
    """Detects inconsistent casing, excessive whitespace, and mixed date formats."""

    @property
    def detector_id(self) -> str:
        return "standardization"

    def detect(self, df: pd.DataFrame, options: Optional[dict[str, Any]] = None) -> list[DetectionResult]:
        options = options or {}
        results: list[DetectionResult] = []
        total_rows = len(df)
        if total_rows == 0:
            return results

        for col in df.columns:
            series = df[col]
            if not (series.dtype == object or pd.api.types.is_string_dtype(series)):
                continue

            str_series = series.dropna().astype(str)
            if len(str_series) == 0:
                continue

            # 1. Inconsistent Casing in Categorical / Low-Cardinality Fields
            # If the column has between 2 and 50 unique lowercased values, check if any group has multiple casings
            lower_series = str_series.str.strip().str.lower()
            n_unique_lower = lower_series.nunique()
            if 1 < n_unique_lower <= 50:
                # Group by lower and see if raw values have variations
                casing_inconsistencies = {}
                for lower_val, group in str_series.groupby(lower_series):
                    unique_casings = group.unique()
                    if len(unique_casings) > 1:
                        # e.g., ["CA", "ca", "Ca"]
                        casing_inconsistencies[lower_val] = list(unique_casings)

                if casing_inconsistencies:
                    affected_mask = lower_series.isin(casing_inconsistencies.keys())
                    affected_indices = str_series[affected_mask].index.tolist()
                    sample_before = []
                    sample_after = []
                    for lower_val, variants in list(casing_inconsistencies.items())[:3]:
                        # Majority vote for canonical casing
                        majority_variant = str_series[lower_series == lower_val].mode().iloc[0]
                        for v in variants:
                            if v != majority_variant:
                                sample_before.append({"row": -1, "value": v})
                                sample_after.append({"row": -1, "value": majority_variant})
                                if len(sample_before) >= 5:
                                    break
                        if len(sample_before) >= 5:
                            break

                    results.append(
                        DetectionResult(
                            detector_id=self.detector_id,
                            category="format_inconsistency",
                            severity="low",
                            issue_title=f"Inconsistent casing in '{col}' ({len(casing_inconsistencies)} categorical groups)",
                            description=(
                                f"Column '{col}' has {len(casing_inconsistencies)} categories with mixed capitalization "
                                f"(e.g., {list(casing_inconsistencies.values())[0]})."
                            ),
                            column_name=str(col),
                            affected_row_count=len(affected_indices),
                            affected_row_indices=[int(i) for i in affected_indices[:50]],
                            sample_before=sample_before,
                            sample_after=sample_after,
                            suggested_action={
                                "action_type": "transform",
                                "parameters": {"operation": "standardize_casing", "strategy": "uppercase" if all(len(k) <= 3 for k in casing_inconsistencies) else "titlecase", "column": col},
                                "rationale": "Standardize category casing across all records.",
                            },
                            confidence=1.0,
                            risk_tier=RiskTier.TIER_0_SAFE,
                            detection_rule="INCONSISTENT_CASING",
                            metadata={"inconsistent_groups": casing_inconsistencies},
                        )
                    )

            # 2. Inconsistent Whitespace (leading, trailing, or multiple consecutive internal spaces)
            ws_pattern = re.compile(r"^\s+|\s+$|\s{2,}")
            ws_mask = str_series.str.contains(ws_pattern, regex=True, na=False)
            if ws_mask.any():
                ws_indices = str_series[ws_mask].index.tolist()
                sample_before = []
                sample_after = []
                for idx in ws_indices[:5]:
                    orig_val = str_series.at[idx]
                    cleaned_val = re.sub(r"\s+", " ", orig_val).strip()
                    sample_before.append({"row": int(idx), "value": repr(orig_val)})
                    sample_after.append({"row": int(idx), "value": repr(cleaned_val)})

                results.append(
                    DetectionResult(
                        detector_id=self.detector_id,
                        category="format_inconsistency",
                        severity="low",
                        issue_title=f"Excessive whitespace in '{col}' ({len(ws_indices)} rows)",
                        description=(
                            f"Column '{col}' contains {len(ws_indices)} entries with leading, trailing, "
                            f"or repeated whitespace characters."
                        ),
                        column_name=str(col),
                        affected_row_count=len(ws_indices),
                        affected_row_indices=[int(i) for i in ws_indices[:50]],
                        sample_before=sample_before,
                        sample_after=sample_after,
                        suggested_action={
                            "action_type": "transform",
                            "parameters": {"operation": "trim_and_normalize_spaces", "column": col},
                            "rationale": "Trim leading/trailing whitespace and collapse internal spaces.",
                        },
                        confidence=1.0,
                        risk_tier=RiskTier.TIER_0_SAFE,
                        detection_rule="EXCESS_WHITESPACE",
                        metadata={"whitespace_count": len(ws_indices)},
                    )
                )

            # 3. Mixed Date Representations
            # If column name suggests date or sample strings match common date patterns
            is_date_col = any(keyword in col.lower() for keyword in ["date", "time", "created", "birth", "day", "updated"])
            date_patterns = {
                "ISO_8601": re.compile(r"^\d{4}-\d{2}-\d{2}$"),
                "US_SLASH": re.compile(r"^\d{1,2}/\d{1,2}/\d{4}$"),
                "EU_DASH": re.compile(r"^\d{1,2}-\d{1,2}-\d{4}$"),
                "TEXT_DATE": re.compile(r"^\d{1,2}-[A-Za-z]{3}-\d{4}$"),
            }
            if is_date_col or len(str_series) > 10:
                pattern_counts = {}
                for name, pat in date_patterns.items():
                    m_count = int(str_series.str.match(pat).sum())
                    if m_count > 0:
                        pattern_counts[name] = m_count

                # If more than one date pattern was detected in the column
                if len(pattern_counts) > 1:
                    total_dates = sum(pattern_counts.values())
                    # Majority pattern
                    dominant_pattern = max(pattern_counts, key=pattern_counts.get)
                    mixed_indices = []
                    sample_before = []
                    sample_after = []
                    for idx, val in str_series.items():
                        for pat_name, pat in date_patterns.items():
                            if pat_name != dominant_pattern and pat.match(val):
                                mixed_indices.append(idx)
                                sample_before.append({"row": int(idx), "value": val})
                                sample_after.append({"row": int(idx), "value": "YYYY-MM-DD"})
                                break
                        if len(sample_before) >= 5:
                            break

                    results.append(
                        DetectionResult(
                            detector_id=self.detector_id,
                            category="format_inconsistency",
                            severity="medium",
                            issue_title=f"Mixed date formats in '{col}' ({len(pattern_counts)} formats detected)",
                            description=(
                                f"Column '{col}' mixes multiple date representations: "
                                f"{', '.join(f'{k}: {v}' for k, v in pattern_counts.items())}."
                            ),
                            column_name=str(col),
                            affected_row_count=len(mixed_indices),
                            affected_row_indices=[int(i) for i in mixed_indices[:50]],
                            sample_before=sample_before,
                            sample_after=sample_after,
                            suggested_action={
                                "action_type": "transform",
                                "parameters": {"operation": "standardize_iso_date", "column": col, "target_format": "YYYY-MM-DD"},
                                "rationale": "Standardize all date representations into ISO 8601 (YYYY-MM-DD).",
                            },
                            confidence=0.95,
                            risk_tier=RiskTier.TIER_1_LOW,
                            detection_rule="MIXED_DATE_FORMATS",
                            metadata={"format_breakdown": pattern_counts},
                        )
                    )

        return results
