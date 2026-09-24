"""Deterministic composition helpers for the external-agent workflow CLI."""

from workflow.contract import (
    FAILURE_KINDS,
    NEXT_ACTIONS,
    SCHEMA_VERSION,
    STAGES,
    STATUSES,
    build_response,
    emit_response,
    make_failure,
)
from workflow.state import (
    classify_manifest_state,
    classify_runner_state,
    manifest_failures,
    manifest_validation_errors,
    summarize_manifest,
)

__all__ = [
    "FAILURE_KINDS",
    "NEXT_ACTIONS",
    "SCHEMA_VERSION",
    "STAGES",
    "STATUSES",
    "build_response",
    "classify_manifest_state",
    "classify_runner_state",
    "emit_response",
    "make_failure",
    "manifest_failures",
    "manifest_validation_errors",
    "summarize_manifest",
]
