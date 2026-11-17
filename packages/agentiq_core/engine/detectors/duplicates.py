"""Detector 2: Exact duplicate rows, key column duplicates, and near-duplicates."""

import difflib
from typing import Any, Optional
import pandas as pd
from agentiq_core.engine.detectors.base import BaseDetector, DetectionResult
from agentiq_core.engine.risk import RiskTier


class DuplicatesDetector(BaseDetector):
    """Detects exact duplicate rows, key-column duplicates, and near-duplicate text entries."""

    @property
    def detector_id(self) -> str:
        return "duplicates"

    def detect(self, df: pd.DataFrame, options: Optional[dict[str, Any]] = None) -> list[DetectionResult]:
        options = options or {}
        key_columns = options.get("key_columns")  # list of column names, if specified
        near_duplicate_cols = options.get("near_duplicate_columns")  # list of text columns to inspect
        similarity_threshold = float(options.get("similarity_threshold", 0.88))

        results: list[DetectionResult] = []
        total_rows = len(df)
        if total_rows < 2:
            return results

        # 1. Exact Duplicate Rows across all columns
        # keep=False marks all duplicate instances (both original and copies) for index reporting
        dup_mask = df.duplicated(keep=False)
        if dup_mask.any():
            affected_indices = df[dup_mask].index.tolist()
            # Also calculate redundant copies (keep='first')
            redundant_count = int(df.duplicated(keep="first").sum())
            total_affected = len(affected_indices)

            sample_before = []
            for idx in affected_indices[:5]:
                # Provide a compact string summary of row values
                row_dict = df.loc[idx].head(5).to_dict()
                compact_repr = ", ".join(f"{k}={v}" for k, v in row_dict.items())
                sample_before.append({"row": int(idx), "value": compact_repr})

            results.append(
                DetectionResult(
                    detector_id=self.detector_id,
                    category="duplicate",
                    severity="high" if redundant_count > 10 else "medium",
                    issue_title=f"Exact duplicate rows detected ({redundant_count} redundant rows)",
                    description=(
                        f"Found {total_affected} rows involved in exact row duplicates "
                        f"({redundant_count} redundant duplicate rows out of {total_rows} total rows)."
                    ),
                    column_name=None,
                    affected_row_count=total_affected,
                    affected_row_indices=[int(i) for i in affected_indices[:50]],
                    sample_before=sample_before,
                    sample_after=[],
                    suggested_action={
                        "action_type": "drop_row",
                        "parameters": {"strategy": "keep_first"},
                        "rationale": "Deduplicate dataset by keeping the first occurrence and dropping exact subsequent copies.",
                    },
                    confidence=1.0,  # Exact bitwise/value identity
                    risk_tier=RiskTier.TIER_3_HIGH,  # Row deletion is destructive -> TIER 3
                    detection_rule="EXACT_ROW_DUPLICATE",
                    metadata={
                        "redundant_rows_count": redundant_count,
                        "total_affected_rows": total_affected,
                    },
                )
            )

        # 2. Key column duplicates (if configured)
        if key_columns:
            valid_keys = [c for c in key_columns if c in df.columns]
            if valid_keys:
                key_dup_mask = df.duplicated(subset=valid_keys, keep=False)
                if key_dup_mask.any():
                    key_indices = df[key_dup_mask].index.tolist()
                    key_redundant = int(df.duplicated(subset=valid_keys, keep="first").sum())
                    sample_before = []
                    for idx in key_indices[:5]:
                        sample_val = ", ".join(f"{k}={df.at[idx, k]}" for k in valid_keys)
                        sample_before.append({"row": int(idx), "value": sample_val})

                    results.append(
                        DetectionResult(
                            detector_id=self.detector_id,
                            category="duplicate",
                            severity="critical" if key_redundant > 5 else "high",
                            issue_title=f"Duplicate business key violation on {valid_keys} ({key_redundant} conflicts)",
                            description=(
                                f"Columns {valid_keys} expected unique values but contain {key_redundant} "
                                f"conflicting rows."
                            ),
                            column_name=",".join(valid_keys),
                            affected_row_count=len(key_indices),
                            affected_row_indices=[int(i) for i in key_indices[:50]],
                            sample_before=sample_before,
                            sample_after=[],
                            suggested_action={
                                "action_type": "drop_row",
                                "parameters": {"strategy": "review_key_conflicts", "keys": valid_keys},
                                "rationale": "Review conflicting business key records and resolve duplicates.",
                            },
                            confidence=1.0,
                            risk_tier=RiskTier.TIER_3_HIGH,
                            detection_rule="KEY_COLUMN_DUPLICATE",
                            metadata={"key_columns": valid_keys, "conflicts_count": key_redundant},
                        )
                    )

        # 3. Near-Duplicates (separate from exact duplicates)
        # Inspect target text columns or auto-detect candidate string columns with moderate cardinality
        candidate_cols = []
        if near_duplicate_cols:
            candidate_cols = [c for c in near_duplicate_cols if c in df.columns]
        else:
            # Inspect string columns where distinct count is between 10 and 500
            for col in df.columns:
                if df[col].dtype == object or pd.api.types.is_string_dtype(df[col]):
                    n_unique = df[col].nunique(dropna=True)
                    if 10 < n_unique <= 500:
                        candidate_cols.append(col)

        for col in candidate_cols[:2]:  # Limit to 2 columns to keep analysis bounded and deterministic
            clean_series = df[col].dropna().astype(str).str.strip().str.lower()
            unique_vals = list(clean_series.unique())
            # Find pairwise near-matches using difflib
            near_pairs = []
            seen = set()
            for i, val1 in enumerate(unique_vals):
                if len(val1) < 4:
                    continue
                for val2 in unique_vals[i + 1 :]:
                    if len(val2) < 4:
                        continue
                    if abs(len(val1) - len(val2)) > 3:
                        continue
                    sim = difflib.SequenceMatcher(None, val1, val2).ratio()
                    if sim >= similarity_threshold and val1 != val2:
                        pair_key = tuple(sorted([val1, val2]))
                        if pair_key not in seen:
                            seen.add(pair_key)
                            near_pairs.append((val1, val2, sim))
                            if len(near_pairs) >= 10:
                                break
                if len(near_pairs) >= 10:
                    break

            if near_pairs:
                affected_vals = {p[0] for p in near_pairs} | {p[1] for p in near_pairs}
                near_mask = clean_series.isin(affected_vals)
                affected_indices = df[near_mask].index.tolist()
                sample_before = []
                for val1, val2, sim in near_pairs[:5]:
                    sample_before.append({
                        "row": -1,
                        "value": f"'{val1}' vs '{val2}' (similarity: {sim:.0%})",
                    })

                avg_conf = sum(p[2] for p in near_pairs) / len(near_pairs)
                results.append(
                    DetectionResult(
                        detector_id=self.detector_id,
                        category="duplicate",
                        severity="medium",
                        issue_title=f"Near-duplicate text values in '{col}' ({len(near_pairs)} candidate pairs)",
                        description=(
                            f"Detected {len(near_pairs)} pairs of near-duplicate text values in column '{col}' "
                            f"with similarity >= {similarity_threshold:.0%}."
                        ),
                        column_name=str(col),
                        affected_row_count=len(affected_indices),
                        affected_row_indices=[int(i) for i in affected_indices[:50]],
                        sample_before=sample_before,
                        sample_after=[],
                        suggested_action={
                            "action_type": "replace",
                            "parameters": {"column": col, "strategy": "canonical_name"},
                            "rationale": "Standardize near-duplicate variants into canonical representation.",
                        },
                        confidence=round(avg_conf, 2),
                        risk_tier=RiskTier.TIER_2_MEDIUM,
                        detection_rule="NEAR_DUPLICATE_SIMILARITY",
                        metadata={"candidate_pairs": [{"val1": p[0], "val2": p[1], "similarity": round(p[2], 3)} for p in near_pairs]},
                    )
                )

        return results
