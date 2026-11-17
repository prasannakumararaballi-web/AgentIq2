"""Detector 8: Formatting - invisible zero-width characters, non-breaking spaces, control chars, and mojibake."""

import re
import unicodedata
from typing import Any, Optional
import pandas as pd
from agentiq_core.engine.detectors.base import BaseDetector, DetectionResult
from agentiq_core.engine.risk import RiskTier

# Regexes for formatting artifacts
RE_ZERO_WIDTH = re.compile(r"[\u200B\u200C\u200D\uFEFF\u2060]")
RE_NBSP = re.compile(r"[\u00A0\u202F]")
RE_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")
# Common mojibake sequences arising from UTF-8 decoded as Windows-1252 / Latin-1
RE_MOJIBAKE = re.compile(r"(?:Ã©|Ã¨|Ã |Ã±|Ã§|â€™|â€œ|â€\x9d|â€“|â€”|Â©|Â®|Ã¼|Ã¶|Ã¤)")

MOJIBAKE_MAP = {
    "Ã©": "é",
    "Ã¨": "è",
    "Ã ": "à",
    "Ã±": "ñ",
    "Ã§": "ç",
    "â€™": "’",
    "â€œ": "“",
    "â€“": "–",
    "â€”": "—",
    "Â©": "©",
    "Â®": "®",
    "Ã¼": "ü",
    "Ã¶": "ö",
    "Ã¤": "ä",
}


class FormattingDetector(BaseDetector):
    """Detects invisible characters, non-breaking spaces, control characters, and common mojibake encoding artifacts."""

    @property
    def detector_id(self) -> str:
        return "formatting"

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

            # 1. Zero-width and invisible control characters
            zw_mask = str_series.str.contains(RE_ZERO_WIDTH, regex=True)
            zw_count = int(zw_mask.sum())
            if zw_count > 0:
                bad_indices = str_series[zw_mask].index.tolist()
                sample_before = []
                sample_after = []
                for idx in bad_indices[:5]:
                    orig = str_series.at[idx]
                    cleaned = RE_ZERO_WIDTH.sub("", orig)
                    sample_before.append({"row": int(idx), "value": repr(orig)})
                    sample_after.append({"row": int(idx), "value": repr(cleaned)})

                results.append(
                    DetectionResult(
                        detector_id=self.detector_id,
                        category="format_inconsistency",
                        severity="low",
                        issue_title=f"Zero-width / invisible characters in '{col}' ({zw_count} rows)",
                        description=(
                            f"Column '{col}' contains {zw_count} entries with invisible zero-width spaces "
                            f"(U+200B-U+200D, U+FEFF) that can break string equality and search."
                        ),
                        column_name=str(col),
                        affected_row_count=zw_count,
                        affected_row_indices=[int(i) for i in bad_indices[:50]],
                        sample_before=sample_before,
                        sample_after=sample_after,
                        suggested_action={
                            "action_type": "transform",
                            "parameters": {"operation": "strip_zero_width_chars", "column": col},
                            "rationale": "Strip invisible zero-width unicode characters.",
                        },
                        confidence=1.0,
                        risk_tier=RiskTier.TIER_0_SAFE,
                        detection_rule="ZERO_WIDTH_INVISIBLE_CHARS",
                        metadata={"zero_width_count": zw_count},
                    )
                )

            # 2. Non-breaking spaces (NBSP: \u00a0)
            nbsp_mask = str_series.str.contains(RE_NBSP, regex=True)
            nbsp_count = int(nbsp_mask.sum())
            if nbsp_count > 0:
                bad_indices = str_series[nbsp_mask].index.tolist()
                sample_before = [{"row": int(i), "value": repr(str_series.at[i])} for i in bad_indices[:5]]
                sample_after = [{"row": int(i), "value": repr(RE_NBSP.sub(" ", str_series.at[i]))} for i in bad_indices[:5]]

                results.append(
                    DetectionResult(
                        detector_id=self.detector_id,
                        category="format_inconsistency",
                        severity="low",
                        issue_title=f"Non-breaking spaces (NBSP) in '{col}' ({nbsp_count} rows)",
                        description=f"Column '{col}' contains {nbsp_count} entries with non-breaking spaces (U+00A0).",
                        column_name=str(col),
                        affected_row_count=nbsp_count,
                        affected_row_indices=[int(i) for i in bad_indices[:50]],
                        sample_before=sample_before,
                        sample_after=sample_after,
                        suggested_action={
                            "action_type": "transform",
                            "parameters": {"operation": "replace_nbsp_with_standard_space", "column": col},
                            "rationale": "Convert non-breaking spaces to standard ASCII spaces.",
                        },
                        confidence=1.0,
                        risk_tier=RiskTier.TIER_0_SAFE,
                        detection_rule="NON_BREAKING_SPACE_NBSP",
                        metadata={"nbsp_count": nbsp_count},
                    )
                )

            # 3. Mojibake Encoding Artifacts
            mojibake_mask = str_series.str.contains(RE_MOJIBAKE, regex=True)
            mojibake_count = int(mojibake_mask.sum())
            if mojibake_count > 0:
                bad_indices = str_series[mojibake_mask].index.tolist()
                sample_before = []
                sample_after = []
                for idx in bad_indices[:5]:
                    orig = str_series.at[idx]
                    cleaned = orig
                    for k, v in MOJIBAKE_MAP.items():
                        cleaned = cleaned.replace(k, v)
                    sample_before.append({"row": int(idx), "value": orig})
                    sample_after.append({"row": int(idx), "value": cleaned})

                results.append(
                    DetectionResult(
                        detector_id=self.detector_id,
                        category="format_inconsistency",
                        severity="medium",
                        issue_title=f"Mojibake encoding artifacts in '{col}' ({mojibake_count} rows)",
                        description=(
                            f"Column '{col}' contains {mojibake_count} entries with corrupted UTF-8 byte sequences "
                            f"(e.g., 'Ã©' instead of 'é', 'â€™' instead of '’')."
                        ),
                        column_name=str(col),
                        affected_row_count=mojibake_count,
                        affected_row_indices=[int(i) for i in bad_indices[:50]],
                        sample_before=sample_before,
                        sample_after=sample_after,
                        suggested_action={
                            "action_type": "transform",
                            "parameters": {"operation": "repair_mojibake_encoding", "column": col},
                            "rationale": "Repair corrupted UTF-8 double-encoding artifacts.",
                        },
                        confidence=1.0,
                        risk_tier=RiskTier.TIER_0_SAFE,
                        detection_rule="MOJIBAKE_ENCODING_ARTIFACT",
                        metadata={"mojibake_count": mojibake_count},
                    )
                )

        return results
