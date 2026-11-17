"""Tabular profiling and anomaly detection engine powered by DuckDB and Pandas."""

import asyncio
import concurrent.futures
import hashlib
import io
import logging
from pathlib import Path
from typing import Any, Optional
from uuid import UUID, uuid4
import pandas as pd

from agentiq_core.engine.base import BaseEngine
from agentiq_core.engine.detectors import ALL_DETECTORS, DetectionResult
from agentiq_core.engine.profiling import (
    ColumnProfile,
    DatasetProfileSummary,
    compute_dataset_quality_score,
    profile_dataframe,
)
from agentiq_core.engine.risk import RiskTier, is_auto_applicable
from agentiq_core.schemas.base import utc_now
from agentiq_core.schemas.finding import FindingResponse, SuggestedAction
from agentiq_core.schemas.run import RunSummaryResponse
from agentiq_core.storage.base import BaseStorageService, StorageFileNotFoundError
from agentiq_core.storage.local import LocalStorageService
from agentiq_core.storage.parser import DatasetParser

logger = logging.getLogger("agentiq.engine.tabular")


class TabularEngine(BaseEngine):
    """Production tabular data intelligence engine for AgentIQ v2."""

    def __init__(
        self,
        storage: Optional[BaseStorageService] = None,
        detectors: Optional[list[type]] = None,
    ) -> None:
        self.storage = storage or LocalStorageService()
        self.detector_classes = detectors or ALL_DETECTORS

    def _read_bytes_from_storage(self, key: str) -> bytes:
        """Read full byte stream from storage abstraction in a safe synchronous manner."""
        if isinstance(self.storage, LocalStorageService):
            try:
                resolved = self.storage._resolve_path(key)
                if resolved.is_file():
                    with open(resolved, "rb") as f:
                        return f.read()
            except Exception:
                pass

            direct_path = Path(key)
            if direct_path.is_file():
                with open(direct_path, "rb") as f:
                    return f.read()

        # Generic async stream consumption through BaseStorageService interface
        async def _collect():
            chunks = []
            async for chunk in self.storage.read_stream(key):
                chunks.append(chunk)
            return b"".join(chunks)

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(asyncio.run, _collect()).result()
        else:
            return asyncio.run(_collect())

    def _save_bytes_to_storage(self, key: str, data: bytes) -> tuple[str, str, int]:
        """Save byte content to storage abstraction in a safe synchronous manner."""
        hasher = hashlib.sha256(data)
        file_hash = hasher.hexdigest()
        total_bytes = len(data)

        if isinstance(self.storage, LocalStorageService):
            target_path = self.storage._resolve_path(key)
            target_path.parent.mkdir(parents=True, exist_ok=True)
            with open(target_path, "wb") as f:
                f.write(data)
            return key, file_hash, total_bytes

        async def _save():
            async def _gen():
                yield data
            return await self.storage.save_stream(key, _gen())

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(asyncio.run, _save()).result()
        else:
            return asyncio.run(_save())

    def _load_dataframe_from_storage(
        self, storage_key: str
    ) -> tuple[pd.DataFrame, str]:
        """Read dataset from storage abstraction and compute initial SHA-256."""
        raw_bytes = self._read_bytes_from_storage(storage_key)
        sha256_before = hashlib.sha256(raw_bytes).hexdigest()

        parse_stream = io.BytesIO(raw_bytes)
        ext = Path(storage_key).suffix.lower()
        if ext in (".xlsx", ".xlsm"):
            df = pd.read_excel(parse_stream)
        elif ext in (".parquet", ".pq"):
            df = pd.read_parquet(parse_stream)
        else:
            encoding = DatasetParser.detect_encoding(parse_stream)
            parse_stream.seek(0)
            df = pd.read_csv(parse_stream, encoding=encoding, low_memory=False)

        return df, sha256_before

    def profile_dataset(
        self,
        storage_path: str,
        sample_size: Optional[int] = None,
        run_id: Optional[UUID] = None,
        options: Optional[dict[str, Any]] = None,
    ) -> tuple[RunSummaryResponse, list[FindingResponse]]:
        """Profile dataset at storage_path / storage_key and return real summary metrics and detected findings.
        
        Strictly enforces file immutability by verifying SHA-256 before and after.
        """
        run_uuid = run_id or uuid4()
        storage_key = storage_path
        options = options or {}

        # 1. Load DataFrame via storage abstraction
        df, sha256_before = self._load_dataframe_from_storage(storage_key)

        # 2. Re-verify SHA-256 immediately to guarantee read operation did not mutate source
        verify_bytes = self._read_bytes_from_storage(storage_key)
        sha256_after = hashlib.sha256(verify_bytes).hexdigest()

        if sha256_before != sha256_after:
            raise RuntimeError(
                f"Dataset mutation detected during read! SHA-256 mismatch: "
                f"before={sha256_before}, after={sha256_after}"
            )

        # 3. Optional sample slice if specified
        total_rows_full = len(df)
        total_cols = len(df.columns)
        if sample_size and total_rows_full > sample_size:
            df = df.head(sample_size).copy()

        active_rows = len(df)

        # 4. Run all eight detectors
        all_detections: list[DetectionResult] = []
        for detector_cls in self.detector_classes:
            detector = detector_cls()
            detector_detections = detector.detect(df, options=options)
            all_detections.extend(detector_detections)

        # 5. Calculate dirty rows (distinct row indices containing at least one anomaly)
        dirty_row_indices: set[int] = set()
        findings_by_severity: dict[str, int] = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        findings_by_category: dict[str, int] = {}

        for d in all_detections:
            dirty_row_indices.update(d.affected_row_indices)
            findings_by_severity[d.severity] = findings_by_severity.get(d.severity, 0) + 1
            findings_by_category[d.category] = findings_by_category.get(d.category, 0) + 1

        dirty_rows = len(dirty_row_indices)
        clean_rows = max(0, active_rows - dirty_rows)

        # 6. Calculate evidence-based quality score
        quality_score = compute_dataset_quality_score(
            total_rows=active_rows,
            dirty_row_count=dirty_rows,
            findings_by_severity=findings_by_severity,
        )

        # 7. Convert DetectionResult objects to FindingResponse contracts
        finding_responses: list[FindingResponse] = []
        for d in all_detections:
            suggested_action = None
            if d.suggested_action:
                suggested_action = SuggestedAction(
                    action_type=d.suggested_action.get("action_type", "transform"),
                    parameters=d.suggested_action.get("parameters", {}),
                    rationale=d.suggested_action.get("rationale"),
                )

            impact = (d.affected_row_count / active_rows) if active_rows > 0 else 0.0

            finding_responses.append(
                FindingResponse(
                    id=uuid4(),
                    run_id=run_uuid,
                    row_index=d.affected_row_indices[0] if d.affected_row_indices else None,
                    column_name=d.column_name,
                    category=d.category,  # type: ignore
                    severity=d.severity,  # type: ignore
                    description=d.description,
                    affected_value=d.sample_before[0]["value"] if d.sample_before else None,
                    suggested_action=suggested_action,
                    is_resolved=False,
                    issue_title=d.issue_title,
                    affected_row_count=d.affected_row_count,
                    affected_row_indices=d.affected_row_indices[:50],  # Bounded preview (max 50)
                    confidence=d.confidence,
                    risk_tier=int(d.risk_tier),
                    impact_estimate=round(impact, 4),
                    sample_before=d.sample_before[:5],
                    sample_after=d.sample_after[:5],
                    detection_rule=d.detection_rule,
                    created_at=utc_now(),
                )
            )

        summary = RunSummaryResponse(
            run_id=run_uuid,
            total_rows=total_rows_full,
            total_columns=total_cols,
            dirty_rows=dirty_rows,
            clean_rows=clean_rows,
            total_findings=len(finding_responses),
            findings_by_severity=findings_by_severity,
            findings_by_category=findings_by_category,
            estimated_quality_score=quality_score,
        )

        return summary, finding_responses

    def apply_decisions(
        self,
        storage_path: str,
        decisions: list[dict[str, Any]],
        output_path: str,
    ) -> dict[str, Any]:
        """Apply approved remediation decisions and emit cleaned dataset to output_path.
        
        Strictly enforces risk tiers: Tier 3 actions require explicit human approval.
        Original dataset is never overwritten.
        """
        # Load dataset
        df, sha256_before = self._load_dataframe_from_storage(storage_path)
        cleaned_df = df.copy()

        applied_count = 0
        skipped_count = 0

        for dec in decisions:
            action_type = dec.get("action_type")
            risk_tier = int(dec.get("risk_tier", RiskTier.TIER_3_HIGH))
            is_approved = dec.get("is_approved", False)

            # Strict Tier 3 enforcement: Never auto-apply without explicit approval
            if risk_tier == RiskTier.TIER_3_HIGH and not is_approved:
                logger.warning(f"Skipping unapproved Tier 3 action: {action_type}")
                skipped_count += 1
                continue

            params = dec.get("parameters", {})
            col = params.get("column")

            # Apply safe / approved transformations
            if action_type == "trim_whitespace" and col in cleaned_df.columns:
                cleaned_df[col] = cleaned_df[col].astype(str).str.strip()
                applied_count += 1
            elif action_type == "drop_row" and is_approved:
                # Deduplication keep_first
                if params.get("strategy") == "keep_first":
                    cleaned_df = cleaned_df.drop_duplicates(keep="first")
                    applied_count += 1

        # Save cleaned dataset to output_path using storage abstraction
        out_buf = io.BytesIO()
        cleaned_df.to_csv(out_buf, index=False)
        out_bytes = out_buf.getvalue()
        self._save_bytes_to_storage(output_path, out_bytes)

        # Verify original file was NOT modified
        verify_bytes = self._read_bytes_from_storage(storage_path)
        sha256_after = hashlib.sha256(verify_bytes).hexdigest()

        if sha256_before != sha256_after:
            raise RuntimeError("Original dataset was corrupted during decision application!")

        return {
            "applied_decisions_count": applied_count,
            "skipped_decisions_count": skipped_count,
            "original_rows": len(df),
            "cleaned_rows": len(cleaned_df),
            "output_storage_key": output_path,
        }
