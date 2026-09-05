from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


class PaperworkState(TypedDict, total=False):
    run_id: str
    mode: str
    source_text: str
    source_name: str
    profile: dict[str, str]
    simulate_failure: bool
    failure_scenario: str
    dependency_status: dict[str, Any]
    fallback_used: bool
    model_calls: int
    safety_flags: list[dict[str, str]]
    extraction: dict[str, Any]
    required_fields: list[dict[str, Any]]
    documents: list[dict[str, Any]]
    warnings: list[dict[str, str]]
    ambiguities: list[dict[str, str]]
    evidence_coverage: int
    human_decision: dict[str, str]
    review_history: Annotated[list[dict[str, str]], operator.add]
    analysis: dict[str, Any]
    status: str
    error: str
    trace: Annotated[list[dict[str, Any]], operator.add]
