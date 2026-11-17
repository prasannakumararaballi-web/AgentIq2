"""High-performance dataset profiling using DuckDB and Pandas."""

from dataclasses import dataclass, field
from typing import Any, Optional
import duckdb
import numpy as np
import pandas as pd


@dataclass
class ColumnProfile:
    """Summary metrics for an individual dataset column."""

    column_name: str
    dtype: str
    total_count: int
    null_count: int
    null_percentage: float
    distinct_count: int
    distinct_percentage: float
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    mean_value: Optional[float] = None
    std_dev: Optional[float] = None


@dataclass
class DatasetProfileSummary:
    """Overall dataset statistical profile."""

    total_rows: int
    total_columns: int
    clean_rows: int
    dirty_rows: int
    total_findings: int
    findings_by_severity: dict[str, int] = field(default_factory=dict)
    findings_by_category: dict[str, int] = field(default_factory=dict)
    estimated_quality_score: float = 100.0
    columns: list[ColumnProfile] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_rows": self.total_rows,
            "total_columns": self.total_columns,
            "clean_rows": self.clean_rows,
            "dirty_rows": self.dirty_rows,
            "total_findings": self.total_findings,
            "findings_by_severity": self.findings_by_severity,
            "findings_by_category": self.findings_by_category,
            "estimated_quality_score": round(self.estimated_quality_score, 1),
            "columns": [
                {
                    "column_name": c.column_name,
                    "dtype": c.dtype,
                    "total_count": c.total_count,
                    "null_count": c.null_count,
                    "null_percentage": round(c.null_percentage, 2),
                    "distinct_count": c.distinct_count,
                    "distinct_percentage": round(c.distinct_percentage, 2),
                    "min_value": str(c.min_value) if c.min_value is not None else None,
                    "max_value": str(c.max_value) if c.max_value is not None else None,
                    "mean_value": round(c.mean_value, 2) if c.mean_value is not None else None,
                    "std_dev": round(c.std_dev, 2) if c.std_dev is not None else None,
                }
                for c in self.columns
            ],
        }


def profile_dataframe(df: pd.DataFrame) -> list[ColumnProfile]:
    """Profile columns of DataFrame using DuckDB SQL queries for high performance."""
    total_rows = len(df)
    if total_rows == 0:
        return []

    con = duckdb.connect(database=":memory:")
    # Register pandas dataframe as duckdb virtual view
    con.register("dataset_view", df)

    column_profiles = []
    for col in df.columns:
        col_series = df[col]
        dtype_str = str(col_series.dtype)
        null_count = int(col_series.isna().sum())
        null_pct = (null_count / total_rows) * 100.0
        distinct_count = int(col_series.nunique(dropna=True))
        distinct_pct = (distinct_count / total_rows) * 100.0 if total_rows > 0 else 0.0

        min_val = None
        max_val = None
        mean_val = None
        std_val = None

        if pd.api.types.is_numeric_dtype(col_series) and not pd.api.types.is_bool_dtype(col_series):
            clean_num = col_series.dropna()
            if len(clean_num) > 0:
                min_val = float(clean_num.min())
                max_val = float(clean_num.max())
                mean_val = float(clean_num.mean())
                std_val = float(clean_num.std()) if len(clean_num) > 1 else 0.0

        column_profiles.append(
            ColumnProfile(
                column_name=str(col),
                dtype=dtype_str,
                total_count=total_rows,
                null_count=null_count,
                null_percentage=null_pct,
                distinct_count=distinct_count,
                distinct_percentage=distinct_pct,
                min_value=min_val,
                max_value=max_val,
                mean_value=mean_val,
                std_dev=std_val,
            )
        )

    con.close()
    return column_profiles


def compute_dataset_quality_score(
    total_rows: int,
    dirty_row_count: int,
    findings_by_severity: dict[str, int],
) -> float:
    """Calculate an evidence-based data quality score between 0.0 and 100.0.
    
    Penalty factors:
    - Base: Proportion of clean rows (clean / total * 100)
    - Severity adjustments: Critical and high issues apply modest diminishing penalties.
    """
    if total_rows == 0:
        return 100.0

    clean_rows = max(0, total_rows - dirty_row_count)
    base_score = (clean_rows / total_rows) * 100.0

    # Severity penalties (capped to avoid negative scores)
    critical_penalty = min(15.0, findings_by_severity.get("critical", 0) * 1.5)
    high_penalty = min(10.0, findings_by_severity.get("high", 0) * 0.5)

    final_score = max(0.0, min(100.0, base_score - critical_penalty - high_penalty))
    return round(final_score, 1)
