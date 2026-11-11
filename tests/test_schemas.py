"""Tests for Pydantic v2 schemas and data validation."""

from datetime import datetime, timezone
from uuid import uuid4
import pytest
from pydantic import ValidationError

from agentiq_core.schemas import (
    ErrorDetail,
    ErrorResponse,
    FindingDecisionCreate,
    FindingResponse,
    HealthResponse,
    ProjectCreate,
    ProjectResponse,
    RunConfig,
    RunCreate,
    RunProgress,
    RunResponse,
    RunSummaryResponse,
    SuggestedAction,
    UploadResponse,
)


def test_error_response_conforms_to_convention():
    error_resp = ErrorResponse(
        error=ErrorDetail(
            code="UNAUTHORIZED",
            message="Invalid token",
            details={"field": "authorization"},
        )
    )
    dumped = error_resp.model_dump()
    assert dumped == {
        "error": {
            "code": "UNAUTHORIZED",
            "message": "Invalid token",
            "details": {"field": "authorization"},
        }
    }


def test_run_create_and_response():
    proj_id = uuid4()
    upload_id = uuid4()
    run_req = RunCreate(
        project_id=proj_id,
        upload_id=upload_id,
        config=RunConfig(enable_ai_explanations=True, anomaly_threshold=0.85),
    )
    assert run_req.config.anomaly_threshold == 0.85

    run_resp = RunResponse(
        id=uuid4(),
        project_id=proj_id,
        upload_id=upload_id,
        status="processing",
        stage="detecting",
        progress=RunProgress(
            current_stage="detecting",
            stage_percent=50,
            total_percent=40,
            message="Profiling columns...",
        ),
        created_at=datetime.now(timezone.utc),
    )
    assert run_resp.status == "processing"
    assert run_resp.progress.stage_percent == 50


def test_finding_and_decision():
    finding_id = uuid4()
    run_id = uuid4()
    finding = FindingResponse(
        id=finding_id,
        run_id=run_id,
        row_index=12,
        column_name="salary",
        category="outlier",
        severity="high",
        description="Value 9999999 exceeds 3 IQR bounds",
        affected_value="9999999",
        suggested_action=SuggestedAction(
            action_type="impute",
            parameters={"strategy": "median"},
            rationale="Statistical outlier detected in salary column.",
        ),
        created_at=datetime.now(timezone.utc),
    )
    assert finding.severity == "high"
    assert finding.suggested_action.action_type == "impute"

    decision = FindingDecisionCreate(
        action_type="impute",
        custom_parameters={"strategy": "median"},
        notes="Approved AI suggestion",
    )
    assert decision.action_type == "impute"


def test_invalid_category_raises_validation_error():
    with pytest.raises(ValidationError):
        FindingResponse(
            id=uuid4(),
            run_id=uuid4(),
            category="non_existent_category",  # Invalid
            severity="critical",
            description="test",
            created_at=datetime.now(timezone.utc),
        )
