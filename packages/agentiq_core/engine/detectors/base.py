"""Base detector contract and detection result structures."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional
import pandas as pd
from agentiq_core.engine.risk import RiskTier


@dataclass
class DetectionResult:
    """Grouped card-level representation of a detected data quality issue."""

    detector_id: str
    category: str
    severity: str  # "low", "medium", "high", "critical"
    issue_title: str
    description: str
    column_name: Optional[str]
    affected_row_count: int
    affected_row_indices: list[int]  # Bounded preview (max 50)
    sample_before: list[dict[str, Any]] = field(default_factory=list)  # Max 5 examples
    sample_after: list[dict[str, Any]] = field(default_factory=list)  # Suggested transform preview
    suggested_action: Optional[dict[str, Any]] = None
    confidence: float = 1.0  # Evidence-based (0.0 - 1.0)
    risk_tier: RiskTier = RiskTier.TIER_1_LOW
    detection_rule: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert detection result to serializable dictionary."""
        return {
            "detector_id": self.detector_id,
            "category": self.category,
            "severity": self.severity,
            "issue_title": self.issue_title,
            "description": self.description,
            "column_name": self.column_name,
            "affected_row_count": self.affected_row_count,
            "affected_row_indices": self.affected_row_indices[:50],  # Enforce max 50 bounded preview
            "sample_before": self.sample_before[:5],
            "sample_after": self.sample_after[:5],
            "suggested_action": self.suggested_action,
            "confidence": round(self.confidence, 4),
            "risk_tier": int(self.risk_tier),
            "detection_rule": self.detection_rule,
            "metadata": self.metadata,
        }


class BaseDetector(ABC):
    """Abstract contract for data quality anomaly detectors."""

    @property
    @abstractmethod
    def detector_id(self) -> str:
        """Unique identifier for the detector (e.g., 'missing_values')."""
        raise NotImplementedError

    @abstractmethod
    def detect(self, df: pd.DataFrame, options: Optional[dict[str, Any]] = None) -> list[DetectionResult]:
        """Analyze DataFrame and return card-level grouped anomaly detections.
        
        Args:
            df: The pandas DataFrame representing the dataset.
            options: Optional detector-specific configuration.
            
        Returns:
            List of DetectionResult card objects. Never mutates input DataFrame.
        """
        raise NotImplementedError
