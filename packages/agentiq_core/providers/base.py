"""Abstract interface for AI and LLM reasoning providers."""

from abc import ABC, abstractmethod
from typing import Any, Optional


class BaseAIProvider(ABC):
    """Abstract interface hiding LLM API interactions behind a provider boundary."""

    @abstractmethod
    async def explain_anomaly(
        self,
        column_name: str,
        detected_issue: str,
        sample_values: list[Any],
        context: Optional[dict[str, Any]] = None,
    ) -> str:
        """Generate human-readable explanation of why a data pattern is anomalous."""
        raise NotImplementedError

    @abstractmethod
    async def suggest_remediation(
        self,
        finding_category: str,
        column_metadata: dict[str, Any],
        sample_errors: list[Any],
    ) -> dict[str, Any]:
        """Propose structured remediation action and parameters."""
        raise NotImplementedError

