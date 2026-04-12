"""Shared schemas used across services."""

from __future__ import annotations

from pydantic import BaseModel, Field


class KeywordRule(BaseModel):
    """Rule set for keyword based scoring and filtering."""

    include: list[str] = Field(default_factory=list)
    exclude: list[str] = Field(default_factory=list)
    priority: list[str] = Field(default_factory=list)


class OpportunityScoreBreakdown(BaseModel):
    """Human-readable score breakdown for alerts and exports."""

    score: float
    reasons: list[str] = Field(default_factory=list)
