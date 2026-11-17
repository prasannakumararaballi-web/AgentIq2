"""Risk tier classification and gating rules for data quality actions.

Fix what is safe automatically, ask a human only about what is risky,
and make every change reversible and recorded.
"""

from enum import IntEnum
from typing import Any, Optional


class RiskTier(IntEnum):
    """Conservative risk tiers defining remediation boundaries.
    
    Tier 0: Safe, unambiguous, deterministic, fully reversible (e.g., trim whitespace).
    Tier 1: Low risk, deterministic type conversions with strong evidence (e.g., ISO date parsing).
    Tier 2: Medium risk, statistical or ambiguous transformations requiring human awareness (e.g., imputation).
    Tier 3: High risk, destructive (e.g., row drops, cross-column overrides). NEVER auto-applied.
    """

    TIER_0_SAFE = 0
    TIER_1_LOW = 1
    TIER_2_MEDIUM = 2
    TIER_3_HIGH = 3


def is_auto_applicable(tier: int | RiskTier) -> bool:
    """Determine whether an action of the given tier may be automatically applied."""
    numeric_tier = int(tier)
    # Only Tier 0 is eligible for unsupervised execution
    return numeric_tier == RiskTier.TIER_0_SAFE


def assess_action_risk(action_type: str, context: Optional[dict[str, Any]] = None) -> RiskTier:
    """Assess and return the conservative risk tier for a proposed remediation action."""
    action = (action_type or "").lower().strip()
    ctx = context or {}

    if action in ("trim_whitespace", "normalize_casing", "strip_invisible_chars"):
        return RiskTier.TIER_0_SAFE

    if action in ("cast_type", "parse_date", "standardize_format"):
        # If conversion has 100% confidence with zero parse errors, it's Tier 1
        confidence = float(ctx.get("confidence", 1.0))
        if confidence >= 0.95:
            return RiskTier.TIER_1_LOW
        return RiskTier.TIER_2_MEDIUM

    if action in ("impute", "replace_placeholder", "merge_near_duplicate"):
        return RiskTier.TIER_2_MEDIUM

    if action in ("drop_row", "delete_record", "override_inconsistency", "hard_delete"):
        return RiskTier.TIER_3_HIGH

    # Conservative default
    return RiskTier.TIER_3_HIGH
