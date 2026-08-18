"""Opportunity scoring and value measurement — pure functions, no Streamlit.

Implements the V1 transparent scoring model:

    ease  = 100 - remaining_complexity
    score = expected_result * 0.45 + readiness * 0.30 + ease * 0.25

Two deliberate rules run through this module:

* **Unknown is not zero.** Every calculator returns ``None`` when its inputs
  are missing, so callers can render "Not measured" instead of a confident 0.
* **Estimates are labelled.** Anything inferred rather than measured carries a
  ``source`` of ``"estimated"``, so a prediction is never displayed as evidence.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

__all__ = [
    "AUTOMATION_ESTIMATE_NOTE",
    "CLASSIFICATIONS",
    "CONFIDENCE_SIGNALS",
    "DIFFICULTY_SCORE",
    "IMPACT_SCORE",
    "SCORE_WEIGHTS",
    "THRESHOLDS",
    "build_opportunity_assessment",
    "calculate_assessment_confidence",
    "calculate_automation_rate",
    "calculate_cost_metrics",
    "calculate_opportunity_score",
    "calculate_roi_metrics",
    "calculate_step_reduction",
    "calculate_time_saving",
    "calculate_token_metrics",
    "classify_opportunity",
    "difficulty_to_score",
    "impact_to_score",
    "normalize_score",
    "round_half_up",
]


# --------------------------------------------------------------------------
# Tunables — kept at the top so the model can be recalibrated in one place.
# --------------------------------------------------------------------------

SCORE_WEIGHTS = {"expected_result": 0.45, "readiness": 0.30, "ease": 0.25}

THRESHOLDS = {
    "high_result": 70,
    "low_complexity": 40,
    "quick_win_readiness": 65,
    "strategic_readiness": 60,
}

DIFFICULTY_SCORE = {"easy": 25, "medium": 50, "hard": 75, "critical": 95}
IMPACT_SCORE = {"low": 25, "medium": 50, "high": 75, "critical": 95}

CLASSIFICATIONS = (
    "QUICK WIN",
    "STRATEGIC BET",
    "UNBLOCK FIRST",
    "EASY IMPROVEMENT",
    "DEFER",
)

AUTOMATION_ESTIMATE_NOTE = (
    "Estimated from time and step reduction; no automated-step count recorded."
)

# Weighted evidence signals for assessment confidence. Sums to 100.
CONFIDENCE_SIGNALS = {
    "baseline_human_time": 10,
    "after_human_time": 12,
    "baseline_steps": 8,
    "after_steps": 8,
    "task_volume": 10,
    "model_telemetry": 12,
    "token_metrics": 10,
    "actual_cost": 10,
    "business_owner_validated": 10,
    "pilot_completed": 10,
}


# --------------------------------------------------------------------------
# Primitives
# --------------------------------------------------------------------------

def _number(value: Any) -> float | None:
    """Coerce to float, or None for anything unusable. Booleans are not numbers."""
    if value is None or isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return None if result != result or result in (float("inf"), float("-inf")) else result


def round_half_up(value: float | None) -> int | None:
    """Round .5 away from zero.

    Python's built-in round() is banker's rounding, so round(84.5) is 84. The
    scoring brief expects 84.5 to display as 85, and a score that reads one
    point low at every half-point is a needless source of doubt.
    """
    if value is None:
        return None
    import math

    return int(math.floor(value + 0.5)) if value >= 0 else int(math.ceil(value - 0.5))


def normalize_score(value: Any, default: float | None = None) -> float | None:
    """Clamp any input onto the 0-100 scale, or return ``default`` if unusable."""
    number = _number(value)
    if number is None:
        return default
    return max(0.0, min(100.0, number))


def difficulty_to_score(label: Any, default: float | None = None) -> float | None:
    """Easy/Medium/Hard/Critical → 25/50/75/95. Numbers pass through normalized."""
    number = _number(label)
    if number is not None:
        return normalize_score(number)
    return DIFFICULTY_SCORE.get(str(label or "").strip().lower(), default)


def impact_to_score(label: Any, default: float | None = None) -> float | None:
    """Low/Medium/High/Critical → 25/50/75/95. Numbers pass through normalized."""
    number = _number(label)
    if number is not None:
        return normalize_score(number)
    return IMPACT_SCORE.get(str(label or "").strip().lower(), default)


# --------------------------------------------------------------------------
# Opportunity score and classification
# --------------------------------------------------------------------------

def calculate_opportunity_score(
    expected_result: Any,
    readiness: Any,
    remaining_complexity: Any,
) -> float | None:
    """The headline 0-100 score, or None when any input is missing.

    Confidence is deliberately excluded: multiplying an uncertain estimate by a
    certainty factor makes a shaky number look precise. Show confidence beside
    the score instead.
    """
    result = normalize_score(expected_result)
    ready = normalize_score(readiness)
    complexity = normalize_score(remaining_complexity)
    if result is None or ready is None or complexity is None:
        return None
    ease = 100.0 - complexity
    score = (
        result * SCORE_WEIGHTS["expected_result"]
        + ready * SCORE_WEIGHTS["readiness"]
        + ease * SCORE_WEIGHTS["ease"]
    )
    return max(0.0, min(100.0, score))


def classify_opportunity(
    expected_result: Any,
    remaining_complexity: Any,
    readiness: Any,
) -> str | None:
    """One of CLASSIFICATIONS, or None when the inputs cannot support a call."""
    result = normalize_score(expected_result)
    complexity = normalize_score(remaining_complexity)
    ready = normalize_score(readiness)
    if result is None or complexity is None or ready is None:
        return None

    high_result = result >= THRESHOLDS["high_result"]
    low_complexity = complexity <= THRESHOLDS["low_complexity"]

    # Structured as a nested decision rather than the brief's flat elif chain,
    # which has a hole: a high-value, low-complexity item with readiness
    # between 60 and 64 matches none of its branches and falls through to
    # DEFER. Deferring something valuable and easy purely because readiness is
    # one point short is the opposite of the intended call — it is exactly an
    # UNBLOCK FIRST. Every worked example in the brief still classifies the
    # same way; only the gap behaves differently.
    if high_result:
        if low_complexity and ready >= THRESHOLDS["quick_win_readiness"]:
            return "QUICK WIN"
        if not low_complexity and ready >= THRESHOLDS["strategic_readiness"]:
            return "STRATEGIC BET"
        return "UNBLOCK FIRST"
    if low_complexity:
        return "EASY IMPROVEMENT"
    return "DEFER"


# --------------------------------------------------------------------------
# Workflow value: time, steps, automation
# --------------------------------------------------------------------------

def calculate_time_saving(baseline_minutes: Any, after_minutes: Any) -> dict[str, Any]:
    """Human touch time saved per task.

    Human time, not elapsed time: a workflow can finish faster in wall-clock
    terms while costing a person exactly as much attention.
    """
    before = _number(baseline_minutes)
    after = _number(after_minutes)
    if before is None or after is None:
        return {"time_saved_minutes": None, "time_saved_pct": None}
    saved = before - after
    pct = (saved / before * 100.0) if before > 0 else None
    return {"time_saved_minutes": saved, "time_saved_pct": pct}


def calculate_step_reduction(baseline_steps: Any, after_steps: Any) -> dict[str, Any]:
    """Steps removed per task, guarding against a zero baseline."""
    before = _number(baseline_steps)
    after = _number(after_steps)
    if before is None or after is None:
        return {"steps_removed": None, "step_reduction_pct": None}
    removed = before - after
    pct = (removed / before * 100.0) if before > 0 else None
    return {"steps_removed": removed, "step_reduction_pct": pct}


def calculate_automation_rate(
    automated_steps: Any = None,
    total_steps: Any = None,
    time_saved_pct: Any = None,
    step_reduction_pct: Any = None,
    allow_estimate: bool = False,
) -> dict[str, Any]:
    """Share of the workflow AI actually performs.

    Measured whenever an automated-step count exists. The ``allow_estimate``
    fallback (max of time and step reduction) is opt-in and always tagged
    ``estimated``, because taking the larger of two different measures flatters
    the result — a workflow that halved its steps but saved no time would
    otherwise report 50% automation.
    """
    automated = _number(automated_steps)
    total = _number(total_steps)
    if automated is not None and total is not None and total > 0:
        rate = max(0.0, min(100.0, automated / total * 100.0))
        return {"automation_rate_pct": rate, "source": "measured", "note": None}

    if not allow_estimate:
        return {"automation_rate_pct": None, "source": None, "note": None}

    candidates = [value for value in (_number(time_saved_pct), _number(step_reduction_pct))
                  if value is not None]
    if not candidates:
        return {"automation_rate_pct": None, "source": None, "note": None}
    rate = max(0.0, min(100.0, max(candidates)))
    return {"automation_rate_pct": rate, "source": "estimated", "note": AUTOMATION_ESTIMATE_NOTE}


# --------------------------------------------------------------------------
# Money
# --------------------------------------------------------------------------

def calculate_cost_metrics(
    baseline_cost_per_task: Any,
    after_cost_per_task: Any,
    tasks_per_month: Any = None,
) -> dict[str, Any]:
    """Per-task, monthly and annual savings. Missing costs yield None, not zero."""
    before = _number(baseline_cost_per_task)
    after = _number(after_cost_per_task)
    volume = _number(tasks_per_month)

    if before is None or after is None:
        return {"cost_saved_per_task": None, "monthly_cost_saving": None,
                "annual_cost_saving": None}

    per_task = before - after
    monthly = per_task * volume if volume is not None else None
    annual = monthly * 12 if monthly is not None else None
    return {"cost_saved_per_task": per_task, "monthly_cost_saving": monthly,
            "annual_cost_saving": annual}


def calculate_token_metrics(consumption: Mapping[str, Any] | None) -> dict[str, Any]:
    """Derived token and cost-efficiency figures from an ai_consumption block.

    ``token_efficiency`` is successful tasks per 1,000 tokens. Fewer tokens is
    not automatically better — a cheap run that produces an unusable answer
    costs more than an expensive one that works — so efficiency is expressed
    against *successful* outcomes.
    """
    data = consumption or {}
    total = _number(data.get("total_tokens"))
    if total is None:
        parts = [_number(data.get(key)) for key in ("input_tokens", "output_tokens")]
        known = [value for value in parts if value is not None]
        total = sum(known) if known else None

    runs = _number(data.get("runs"))
    successful = _number(data.get("successful_runs"))
    total_cost = _number(data.get("total_ai_cost"))
    if total_cost is None:
        costs = [_number(data.get(key)) for key in ("api_cost", "local_compute_cost")]
        known_costs = [value for value in costs if value is not None]
        total_cost = sum(known_costs) if known_costs else None

    out: dict[str, Any] = {
        "total_tokens": total,
        "tokens_per_task": (total / runs) if total is not None and runs else None,
        "tokens_per_successful_task": (total / successful) if total is not None and successful else None,
        "token_efficiency": (successful / (total / 1000.0)) if successful is not None and total else None,
        "success_rate_pct": (successful / runs * 100.0) if successful is not None and runs else None,
        "total_ai_cost": total_cost,
        "cost_per_task": (total_cost / runs) if total_cost is not None and runs else None,
        "cost_per_successful_task": (total_cost / successful) if total_cost is not None and successful else None,
    }
    return out


def calculate_roi_metrics(business_value: Mapping[str, Any] | None) -> dict[str, Any]:
    """ROI percentage, only when both value created and AI cost are known.

    Never manufactured: a missing cost or a missing value returns None rather
    than an impressive-looking number derived from one half of a ratio.
    """
    data = business_value or {}
    monthly_value = _number(data.get("monthly_value_created"))
    annual_value = _number(data.get("annual_value_created"))
    monthly_cost = _number(data.get("ai_operating_cost_monthly"))

    if annual_value is None and monthly_value is not None:
        annual_value = monthly_value * 12
    annual_cost = monthly_cost * 12 if monthly_cost is not None else None

    roi = None
    if annual_value is not None and annual_cost is not None and annual_cost > 0:
        roi = (annual_value - annual_cost) / annual_cost * 100.0

    return {"annual_value_created": annual_value, "annual_ai_cost": annual_cost,
            "net_annual_value": (annual_value - annual_cost)
            if annual_value is not None and annual_cost is not None else None,
            "roi_pct": roi}


# --------------------------------------------------------------------------
# Confidence
# --------------------------------------------------------------------------

def _has_number(container: Mapping[str, Any] | None, key: str) -> bool:
    return _number((container or {}).get(key)) is not None


def calculate_assessment_confidence(record: Mapping[str, Any] | None) -> dict[str, Any]:
    """How much real evidence stands behind this assessment, 0-100.

    Not a probability of success — it answers "should we trust these numbers?".
    Deterministic: each satisfied signal contributes its fixed weight.
    """
    data = record or {}
    value_metrics = data.get("value_metrics") or {}
    baseline = value_metrics.get("baseline") or {}
    after = value_metrics.get("after_ai") or {}
    volume = value_metrics.get("volume") or {}
    consumption = data.get("ai_consumption") or {}
    readiness = data.get("delivery_readiness") or {}

    met: dict[str, bool] = {
        "baseline_human_time": _has_number(baseline, "human_time_minutes"),
        "after_human_time": _has_number(after, "human_time_minutes"),
        "baseline_steps": _has_number(baseline, "steps"),
        "after_steps": _has_number(after, "steps"),
        "task_volume": _has_number(volume, "tasks_per_month") or _has_number(volume, "tasks_per_day"),
        "model_telemetry": bool(data.get("model_usage")),
        "token_metrics": _has_number(consumption, "total_tokens")
        or _has_number(consumption, "input_tokens"),
        "actual_cost": _has_number(consumption, "total_ai_cost")
        or _has_number(consumption, "api_cost")
        or _has_number(baseline, "cost_per_task"),
        "business_owner_validated": bool(readiness.get("business_owner_available")),
        "pilot_completed": str(data.get("phase") or data.get("status") or "").strip().lower()
        in {"mvp", "mvp ready", "pilot", "production", "prototype"},
    }
    score = sum(weight for key, weight in CONFIDENCE_SIGNALS.items() if met.get(key))
    return {
        "confidence": max(0, min(100, int(round(score)))),
        "signals_met": [key for key, hit in met.items() if hit],
        "signals_missing": [key for key, hit in met.items() if not hit],
    }


# --------------------------------------------------------------------------
# Assembly
# --------------------------------------------------------------------------

def build_opportunity_assessment(record: Mapping[str, Any] | None) -> dict[str, Any]:
    """Full assessment for one challenge or project record.

    Tolerates records written before any of these fields existed: every lookup
    is defensive and every unknown stays None.
    """
    data = record or {}
    metrics = data.get("opportunity_metrics") or {}

    expected_result = normalize_score(metrics.get("expected_result"))
    if expected_result is None:
        expected_result = impact_to_score(data.get("impact_level") or data.get("impact"))

    remaining = normalize_score(metrics.get("remaining_complexity"))
    if remaining is None:
        remaining = normalize_score(metrics.get("solution_complexity"))
    if remaining is None:
        remaining = difficulty_to_score(data.get("difficulty"))

    readiness = normalize_score(metrics.get("readiness"))

    score = calculate_opportunity_score(expected_result, readiness, remaining)
    classification = classify_opportunity(expected_result, remaining, readiness)

    value_metrics = data.get("value_metrics") or {}
    baseline = value_metrics.get("baseline") or {}
    after = value_metrics.get("after_ai") or {}
    volume = value_metrics.get("volume") or {}

    time = calculate_time_saving(baseline.get("human_time_minutes"), after.get("human_time_minutes"))
    steps = calculate_step_reduction(baseline.get("steps"), after.get("steps"))
    automation = calculate_automation_rate(
        after.get("automated_steps"), baseline.get("steps"),
        time.get("time_saved_pct"), steps.get("step_reduction_pct"),
        allow_estimate=bool(value_metrics.get("allow_automation_estimate")),
    )
    cost = calculate_cost_metrics(baseline.get("cost_per_task"), after.get("cost_per_task"),
                                 volume.get("tasks_per_month"))
    tokens = calculate_token_metrics(data.get("ai_consumption"))
    roi = calculate_roi_metrics(data.get("business_value"))
    confidence = calculate_assessment_confidence(data)

    tasks_per_month = _number(volume.get("tasks_per_month"))
    saved_minutes = time.get("time_saved_minutes")
    monthly_hours = (saved_minutes * tasks_per_month / 60.0
                     if saved_minutes is not None and tasks_per_month is not None else None)

    return {
        "expected_result": expected_result,
        "remaining_complexity": remaining,
        "readiness": readiness,
        "opportunity_score": score,
        "opportunity_score_display": round_half_up(score),
        "classification": classification,
        "confidence": confidence["confidence"],
        "confidence_detail": confidence,
        "time": time,
        "steps": steps,
        "automation": automation,
        "cost": cost,
        "tokens": tokens,
        "roi": roi,
        "monthly_hours_saved": monthly_hours,
        "annual_hours_saved": monthly_hours * 12 if monthly_hours is not None else None,
        "time_to_value_days": _number(metrics.get("time_to_value_days")),
        "main_blocker": metrics.get("main_blocker") or None,
        "next_best_action": metrics.get("next_best_action") or None,
    }
