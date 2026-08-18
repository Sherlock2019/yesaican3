"""Record plumbing shared by the challenge and project flows.

The reason this module exists: challenge → project conversion used to copy a
hardcoded list of keys, in two separate functions, neither of which knew about
the opportunity and value fields. Anything the intake captured was silently
dropped the moment a challenge became a project. Conversion now copies a named
block, so adding a field does not require remembering two call sites.
"""

from __future__ import annotations

import copy
from typing import Any, Iterable, Mapping

__all__ = [
    "OPPORTUNITY_CARRY_FIELDS",
    "carry_opportunity_fields",
    "normalize_challenge_record",
    "normalize_project_record",
]

# Everything that describes the *opportunity* rather than the prose of a
# challenge. These survive conversion intact.
OPPORTUNITY_CARRY_FIELDS: tuple[str, ...] = (
    # quick-capture intake
    "pain_type",
    "twin_context",
    "baseline",
    "opportunity",
    "outcomes",
    "metrics",
    "current_workflow",
    "workflow_source",
    # the fuller opportunity/value model
    "opportunity_metrics",
    "value_metrics",
    "ai_consumption",
    "model_usage",
    "data_governance",
    "business_value",
    "gap_analysis",
    "delivery_readiness",
    # signals
    "community_interest",
    "similar_agents",
    "ai_baseline",
)


def carry_opportunity_fields(
    source: Mapping[str, Any] | None,
    target: dict[str, Any] | None = None,
    fields: Iterable[str] = OPPORTUNITY_CARRY_FIELDS,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Copy the opportunity block from one record onto another.

    Values are deep-copied so a later edit to the project cannot mutate the
    originating challenge. Empty values are skipped: carrying ``None`` over an
    existing value would be a silent downgrade.
    """
    result: dict[str, Any] = target if target is not None else {}
    if not source:
        return result
    for key in fields:
        if key not in source:
            continue
        value = source.get(key)
        if value in (None, "", [], {}):
            continue
        if not overwrite and result.get(key) not in (None, "", [], {}):
            continue
        result[key] = copy.deepcopy(value)
    return result


def _defaults(record: Mapping[str, Any] | None, extra: Mapping[str, Any]) -> dict[str, Any]:
    """Shallow copy with defaults filled in. Never mutates the input."""
    normalized = dict(record or {})
    for key, value in extra.items():
        normalized.setdefault(key, copy.deepcopy(value))
    return normalized


def normalize_challenge_record(record: Mapping[str, Any] | None) -> dict[str, Any]:
    """In-memory view of a challenge with every optional field present.

    Returns a copy. Records written before these fields existed keep loading,
    and the original file is never rewritten just to add defaults.
    """
    return _defaults(record, {
        "title": "",
        "description": "",
        "submitter": {},
        "attachments": [],
        "tags": [],
        "upvotes": 0,
        "comments": 0,
        "community_interest": 0,
        "similar_agents": [],
        "opportunity_metrics": {},
        "value_metrics": {},
        "outcomes": [],
        "metrics": [],
        "current_workflow": [],
    })


def normalize_project_record(record: Mapping[str, Any] | None) -> dict[str, Any]:
    """In-memory view of a project with every optional field present."""
    return _defaults(record, {
        "title": "",
        "summary": "",
        "status": "Incubation",
        "phase": "Incubation",
        "authors": [],
        "tags": [],
        "stars": 0,
        "upvotes": 0,
        "comments": 0,
        "community_interest": 0,
        "opportunity_metrics": {},
        "value_metrics": {},
        "ai_consumption": {},
        "model_usage": [],
        "business_value": {},
        "gap_analysis": {},
        "delivery_readiness": {},
        "metrics": [],
    })
