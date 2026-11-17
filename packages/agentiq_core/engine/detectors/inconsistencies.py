"""Detector 6: Inconsistencies - cross-column logic and arithmetic violations."""

from typing import Any, Optional
import numpy as np
import pandas as pd
from agentiq_core.engine.detectors.base import BaseDetector, DetectionResult
from agentiq_core.engine.risk import RiskTier


class InconsistenciesDetector(BaseDetector):
    """Detects cross-column contradictions and arithmetic violations based on explicit rules."""

    @property
    def detector_id(self) -> str:
        return "inconsistencies"

    def detect(self, df: pd.DataFrame, options: Optional[dict[str, Any]] = None) -> list[DetectionResult]:
        options = options or {}
        results: list[DetectionResult] = []
        total_rows = len(df)
        if total_rows == 0:
            return results

        col_map = {str(c).lower().strip(): c for c in df.columns}

        # 1. Temporal sequence checks (e.g., signup_date vs renewal_date, start_date vs end_date)
        candidate_date_pairs = [
            ("signup_date", "renewal_date"),
            ("start_date", "end_date"),
            ("created_at", "updated_at"),
            ("order_date", "ship_date"),
            ("valid_from", "valid_to"),
        ]

        # Add any user-configured date rules
        custom_pairs = options.get("date_sequence_rules", [])
        candidate_date_pairs.extend(custom_pairs)

        for start_key, end_key in candidate_date_pairs:
            if start_key in col_map and end_key in col_map:
                col_start = col_map[start_key]
                col_end = col_map[end_key]

                # Convert to datetime safely with errors='coerce'
                dt_start = pd.to_datetime(df[col_start], errors="coerce")
                dt_end = pd.to_datetime(df[col_end], errors="coerce")

                valid_mask = dt_start.notna() & dt_end.notna()
                if not valid_mask.any():
                    continue

                # Contradiction: Start Date strictly greater than End Date
                conflict_mask = valid_mask & (dt_start > dt_end)
                if conflict_mask.any():
                    bad_indices = df[conflict_mask].index.tolist()
                    count = len(bad_indices)
                    sample_before = []
                    for idx in bad_indices[:5]:
                        s_val = str(df.at[idx, col_start])
                        e_val = str(df.at[idx, col_end])
                        sample_before.append({
                            "row": int(idx),
                            "value": f"{col_start}='{s_val}' > {col_end}='{e_val}'",
                        })

                    results.append(
                        DetectionResult(
                            detector_id=self.detector_id,
                            category="business_rule_violation",
                            severity="high",
                            issue_title=f"Temporal inconsistency: '{col_start}' > '{col_end}' ({count} rows)",
                            description=(
                                f"In {count} rows, '{col_start}' is chronologically later than '{col_end}', "
                                f"violating the expected temporal progression."
                            ),
                            column_name=f"{col_start},{col_end}",
                            affected_row_count=count,
                            affected_row_indices=[int(i) for i in bad_indices[:50]],
                            sample_before=sample_before,
                            sample_after=[],
                            suggested_action={
                                "action_type": "replace",
                                "parameters": {"operation": "review_temporal_order", "columns": [col_start, col_end]},
                                "rationale": "Inspect and rectify reversed start and end dates.",
                            },
                            confidence=1.0,
                            risk_tier=RiskTier.TIER_3_HIGH,  # Business contradictions must never be auto-resolved
                            detection_rule="TEMPORAL_SEQUENCE_CONTRADICTION",
                            metadata={"col_start": col_start, "col_end": col_end, "violation_count": count},
                        )
                    )

        # 2. Arithmetic consistency checks (e.g., subtotal + tax == total / total_spent)
        math_rule = None
        subtotal_col = next((col_map[k] for k in ["subtotal", "sub_total"] if k in col_map), None)
        tax_col = next((col_map[k] for k in ["tax", "tax_amount"] if k in col_map), None)
        total_col = next((col_map[k] for k in ["total", "total_spent", "total_amount", "grand_total"] if k in col_map), None)

        if subtotal_col and tax_col and total_col:
            math_rule = (subtotal_col, tax_col, total_col, f"{subtotal_col} + {tax_col} == {total_col}")
        elif "price" in col_map and "quantity" in col_map and "total_amount" in col_map:
            math_rule = (col_map["price"], col_map["quantity"], col_map["total_amount"], "price * quantity == total_amount")

        # Custom arithmetic rules
        custom_math_rules = options.get("arithmetic_rules", [])
        all_math_rules = ([math_rule] if math_rule else []) + custom_math_rules

        for rule in all_math_rules:
            if not rule:
                continue
            col_a, col_b, col_target, formula = rule
            if col_a in df.columns and col_b in df.columns and col_target in df.columns:
                num_a = pd.to_numeric(df[col_a], errors="coerce")
                num_b = pd.to_numeric(df[col_b], errors="coerce")
                num_t = pd.to_numeric(df[col_target], errors="coerce")

                valid = num_a.notna() & num_b.notna() & num_t.notna()
                if not valid.any():
                    continue

                if "+" in formula:
                    expected = num_a + num_b
                elif "*" in formula:
                    expected = num_a * num_b
                else:
                    continue

                # Float tolerance check: abs(expected - actual) > 0.02
                discrepancy_mask = valid & ((expected - num_t).abs() > 0.02)
                if discrepancy_mask.any():
                    disc_indices = df[discrepancy_mask].index.tolist()
                    count = len(disc_indices)
                    sample_before = []
                    for idx in disc_indices[:5]:
                        sample_before.append({
                            "row": int(idx),
                            "value": f"{col_a}={num_a.at[idx]}, {col_b}={num_b.at[idx]}, {col_target}={num_t.at[idx]} (Expected: {expected.at[idx]:.2f})",
                        })

                    results.append(
                        DetectionResult(
                            detector_id=self.detector_id,
                            category="business_rule_violation",
                            severity="high",
                            issue_title=f"Arithmetic mismatch: {formula} ({count} rows)",
                            description=(
                                f"In {count} rows, {col_target} does not match the computed result of "
                                f"{col_a} and {col_b}."
                            ),
                            column_name=col_target,
                            affected_row_count=count,
                            affected_row_indices=[int(i) for i in disc_indices[:50]],
                            sample_before=sample_before,
                            sample_after=[],
                            suggested_action={
                                "action_type": "replace",
                                "parameters": {"operation": "recalculate_total", "formula": formula, "target": col_target},
                                "rationale": "Recalculate or manually audit conflicting total values.",
                            },
                            confidence=1.0,
                            risk_tier=RiskTier.TIER_3_HIGH,
                            detection_rule="ARITHMETIC_MISMATCH",
                            metadata={"formula": formula, "violation_count": count},
                        )
                    )

        return results
