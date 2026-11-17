"""Data quality detector suite for AgentIQ v2."""

from agentiq_core.engine.detectors.base import BaseDetector, DetectionResult
from agentiq_core.engine.detectors.missing_values import MissingValuesDetector
from agentiq_core.engine.detectors.duplicates import DuplicatesDetector
from agentiq_core.engine.detectors.standardization import StandardizationDetector
from agentiq_core.engine.detectors.type_validation import TypeValidationDetector
from agentiq_core.engine.detectors.outliers import OutliersDetector
from agentiq_core.engine.detectors.inconsistencies import InconsistenciesDetector
from agentiq_core.engine.detectors.validation_rules import ValidationRulesDetector
from agentiq_core.engine.detectors.formatting import FormattingDetector

ALL_DETECTORS = [
    MissingValuesDetector,
    DuplicatesDetector,
    StandardizationDetector,
    TypeValidationDetector,
    OutliersDetector,
    InconsistenciesDetector,
    ValidationRulesDetector,
    FormattingDetector,
]

__all__ = [
    "BaseDetector",
    "DetectionResult",
    "MissingValuesDetector",
    "DuplicatesDetector",
    "StandardizationDetector",
    "TypeValidationDetector",
    "OutliersDetector",
    "InconsistenciesDetector",
    "ValidationRulesDetector",
    "FormattingDetector",
    "ALL_DETECTORS",
]
