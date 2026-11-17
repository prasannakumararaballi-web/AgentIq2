"""Detector 4: Type validation - stringified numerics, currencies, percentages, booleans, and mixed types."""

import re
from typing import Any, Optional
import pandas as pd
from agentiq_core.engine.detectors.base import BaseDetector, DetectionResult
from agentiq_core.engine.risk import RiskTier

# Precompiled regexes
RE_CURRENCY = re.compile(r"^[\$\€\£\¥]\s*[-+]?[0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?$")
RE_PERCENTAGE = re.compile(r"^[-+]?[0-9]+(?:\.[0-9]+)?\s*\%$")
RE_NUMERIC_STRING = re.compile(r"^[-+]?[0-9]+(?:\.[0-9]+)?$")
RE_BOOLEAN = re.compile(r"^(?:true|false|yes|no|y|n|t|f)$", re.IGNORECASE)


class TypeValidationDetector(BaseDetector):
    """Detects numbers, currencies, percentages, and booleans stored as text, as well as mixed types."""

    @property
    def detector_id(self) -> str:
        return "type_validation"

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

            non_null_series = series.dropna()
            total_non_null = len(non_null_series)
            if total_non_null < 3:
                continue

            str_series = non_null_series.astype(str).str.strip()

            # 1. Currency formatted strings
            currency_mask = str_series.str.match(RE_CURRENCY)
            currency_count = int(currency_mask.sum())
            if currency_count > 0:
                curr_ratio = currency_count / total_non_null
                # If a substantial portion are currency formatted
                if curr_ratio >= 0.5 or currency_count >= 5:
                    affected_indices = str_series[currency_mask].index.tolist()
                    sample_before = []
                    sample_after = []
                    for idx in affected_indices[:5]:
                        val = str_series.at[idx]
                        clean_num = re.sub(r"[\$\€\£\¥\s,]", "", val)
                        sample_before.append({"row": int(idx), "value": val})
                        sample_after.append({"row": int(idx), "value": clean_num})

                    results.append(
                        DetectionResult(
                            detector_id=self.detector_id,
                            category="type_mismatch",
                            severity="medium",
                            issue_title=f"Currency strings stored as text in '{col}' ({currency_count} rows, {curr_ratio:.0%})",
                            description=(
                                f"Column '{col}' is typed as text but contains {currency_count} "
                                f"currency-formatted numeric entries ({curr_ratio:.0%} parse success rate)."
                            ),
                            column_name=str(col),
                            affected_row_count=currency_count,
                            affected_row_indices=[int(i) for i in affected_indices[:50]],
                            sample_before=sample_before,
                            sample_after=sample_after,
                            suggested_action={
                                "action_type": "transform",
                                "parameters": {"operation": "cast_to_numeric", "strip_symbols": ["$", ",", "€", "£"], "column": col},
                                "rationale": "Strip currency symbols/commas and cast to numeric float.",
                            },
                            confidence=round(curr_ratio, 2),
                            risk_tier=RiskTier.TIER_1_LOW if curr_ratio >= 0.95 else RiskTier.TIER_2_MEDIUM,
                            detection_rule="STRINGIFIED_CURRENCY",
                            metadata={"currency_count": currency_count, "parse_rate": round(curr_ratio, 4)},
                        )
                    )
                    continue

            # 2. Percentage formatted strings
            pct_mask = str_series.str.match(RE_PERCENTAGE)
            pct_count = int(pct_mask.sum())
            if pct_count > 0 and (pct_count / total_non_null >= 0.5 or pct_count >= 5):
                pct_ratio = pct_count / total_non_null
                affected_indices = str_series[pct_mask].index.tolist()
                sample_before = []
                sample_after = []
                for idx in affected_indices[:5]:
                    val = str_series.at[idx]
                    clean_pct = str(float(val.replace("%", "").strip()) / 100.0)
                    sample_before.append({"row": int(idx), "value": val})
                    sample_after.append({"row": int(idx), "value": clean_pct})

                results.append(
                    DetectionResult(
                        detector_id=self.detector_id,
                        category="type_mismatch",
                        severity="medium",
                        issue_title=f"Percentages stored as text in '{col}' ({pct_count} rows)",
                        description=(
                            f"Column '{col}' contains {pct_count} percentage-formatted strings "
                            f"({pct_ratio:.0%} parse success rate)."
                        ),
                        column_name=str(col),
                        affected_row_count=pct_count,
                        affected_row_indices=[int(i) for i in affected_indices[:50]],
                        sample_before=sample_before,
                        sample_after=sample_after,
                        suggested_action={
                            "action_type": "transform",
                            "parameters": {"operation": "cast_to_decimal_percentage", "column": col},
                            "rationale": "Convert percentage strings to decimal numbers.",
                        },
                        confidence=round(pct_ratio, 2),
                        risk_tier=RiskTier.TIER_1_LOW if pct_ratio >= 0.95 else RiskTier.TIER_2_MEDIUM,
                        detection_rule="STRINGIFIED_PERCENTAGE",
                        metadata={"percentage_count": pct_count, "parse_rate": round(pct_ratio, 4)},
                    )
                )
                continue

            # 3. Pure numeric strings in object column (numbers stored as text)
            numeric_mask = str_series.str.match(RE_NUMERIC_STRING)
            numeric_count = int(numeric_mask.sum())
            if numeric_count > 0 and numeric_count / total_non_null >= 0.7:
                num_ratio = numeric_count / total_non_null
                affected_indices = str_series[numeric_mask].index.tolist()
                sample_before = [{"row": int(i), "value": repr(str_series.at[i])} for i in affected_indices[:5]]

                # Check if there are non-numeric entries creating mixed types
                non_num_count = total_non_null - numeric_count
                severity = "medium" if non_num_count > 0 else "low"
                results.append(
                    DetectionResult(
                        detector_id=self.detector_id,
                        category="type_mismatch",
                        severity=severity,
                        issue_title=f"Numeric values stored as text in '{col}' ({numeric_count}/{total_non_null} rows)",
                        description=(
                            f"Column '{col}' has text type but {numeric_count} values ({num_ratio:.0%}) "
                            f"are valid numbers."
                            + (f" Found {non_num_count} non-numeric values causing type pollution." if non_num_count > 0 else "")
                        ),
                        column_name=str(col),
                        affected_row_count=numeric_count,
                        affected_row_indices=[int(i) for i in affected_indices[:50]],
                        sample_before=sample_before,
                        sample_after=[],
                        suggested_action={
                            "action_type": "transform",
                            "parameters": {"operation": "cast_to_numeric", "column": col, "errors": "coerce"},
                            "rationale": "Cast clean string numbers to numeric column type.",
                        },
                        confidence=round(num_ratio, 2),
                        risk_tier=RiskTier.TIER_1_LOW if non_num_count == 0 else RiskTier.TIER_2_MEDIUM,
                        detection_rule="STRINGIFIED_NUMERIC",
                        metadata={"numeric_count": numeric_count, "parse_rate": round(num_ratio, 4), "non_numeric_count": non_num_count},
                    )
                )
                continue

            # 4. Booleans stored as text
            bool_mask = str_series.str.match(RE_BOOLEAN)
            bool_count = int(bool_mask.sum())
            if bool_count > 0 and bool_count / total_non_null >= 0.8:
                bool_ratio = bool_count / total_non_null
                affected_indices = str_series[bool_mask].index.tolist()
                sample_before = [{"row": int(i), "value": str_series.at[i]} for i in affected_indices[:5]]
                sample_after = [{"row": int(i), "value": str(str_series.at[i].lower() in ("true", "yes", "y", "t", "1"))} for i in affected_indices[:5]]

                results.append(
                    DetectionResult(
                        detector_id=self.detector_id,
                        category="type_mismatch",
                        severity="low",
                        issue_title=f"Boolean flags stored as text in '{col}' ({bool_count} rows, {bool_ratio:.0%})",
                        description=f"Column '{col}' contains text boolean flags like 'yes', 'no', 'true', or 'false'.",
                        column_name=str(col),
                        affected_row_count=bool_count,
                        affected_row_indices=[int(i) for i in affected_indices[:50]],
                        sample_before=sample_before,
                        sample_after=sample_after,
                        suggested_action={
                            "action_type": "transform",
                            "parameters": {"operation": "cast_to_boolean", "column": col},
                            "rationale": "Normalize string boolean tokens to native boolean type.",
                        },
                        confidence=round(bool_ratio, 2),
                        risk_tier=RiskTier.TIER_1_LOW,
                        detection_rule="STRINGIFIED_BOOLEAN",
                        metadata={"bool_count": bool_count, "parse_rate": round(bool_ratio, 4)},
                    )
                )

        return results
