"""Abstract interface for the data profiling and cleaning engine."""

from abc import ABC, abstractmethod
from typing import Any, Optional
from uuid import UUID
from agentiq_core.schemas.run import RunSummaryResponse
from agentiq_core.schemas.finding import FindingResponse


class BaseEngine(ABC):
    """Abstract base class defining the contract for tabular data processing engines."""

    @abstractmethod
    def profile_dataset(
        self, storage_path: str, sample_size: Optional[int] = None
    ) -> tuple[RunSummaryResponse, list[FindingResponse]]:
        """Profile dataset at storage_path and return summary metrics and detected findings."""
        raise NotImplementedError

    @abstractmethod
    def apply_decisions(
        self,
        storage_path: str,
        decisions: list[dict[str, Any]],
        output_path: str,
    ) -> dict[str, Any]:
        """Apply approved remediation decisions and emit cleaned dataset."""
        raise NotImplementedError

