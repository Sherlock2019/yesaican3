"""Pain-point quantification: classification, scoring, and metric recommendation.

The intake flow asks six things — what hurts, how many steps, how long, how
often, what should improve, who is affected — and everything else is derived
here. Keeping the derivation in one importable module (rather than inside the
Streamlit page) means the numbers can be tested and reused by the home-page
matrix without booting a UI.

The core insight the scoring encodes: a task is worth automating in proportion
to ``time per task × annual volume``, not to how annoying it feels. Five
minutes done 100,000 times a year dwarfs an hour done twenty times.
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable, Iterable

__all__ = [
    "FREQUENCY_UNITS",
    "OUTCOMES",
    "PAIN_TYPES",
    "WHO_AFFECTED",
    "IMPROVEMENT_TARGETS",
    "annual_volume",
    "classify_pain_point",
    "compute_opportunity",
    "compute_pain",
    "estimated_improvement",
    "generate_workflow_steps",
    "metric_definition",
    "recommend_metrics",
    "summarise_metrics",
]


# --------------------------------------------------------------------------
# Volume
# --------------------------------------------------------------------------

# Working-time multipliers: 250 working days, 48 working weeks a year.
FREQUENCY_UNITS: dict[str, float] = {
    "per day": 250.0,
    "per week": 48.0,
    "per month": 12.0,
    "per quarter": 4.0,
    "per year": 1.0,
}

WHO_AFFECTED: dict[str, float] = {
    "Just me": 1.0,
    "My team": 1.35,
    "My department": 1.7,
    "Several departments": 2.0,
    "Our customers": 2.2,
}


def annual_volume(frequency: float, unit: str) -> float:
    """Tasks per year from a rate and its unit."""
    return max(0.0, float(frequency or 0)) * FREQUENCY_UNITS.get(unit, 12.0)


# --------------------------------------------------------------------------
# Metric library
# --------------------------------------------------------------------------
# group: "human"  -> shown to every submitter
#        "technical" -> collapsed behind the AI-engineering panel
# better: "lower" or "higher"; used for target derivation and later comparison.

_METRICS: dict[str, dict[str, Any]] = {
    # --- human / business -------------------------------------------------
    "time_per_task":        {"label": "Human time / task",      "icon": "⏱",  "unit": "min",   "group": "human", "better": "lower"},
    "steps_per_task":       {"label": "Steps / task",           "icon": "👣", "unit": "steps", "group": "human", "better": "lower"},
    "manual_interventions": {"label": "Manual interventions",   "icon": "✋", "unit": "/task", "group": "human", "better": "lower"},
    "accuracy":             {"label": "Accuracy",               "icon": "🎯", "unit": "%",     "group": "human", "better": "higher"},
    "error_rate":           {"label": "Error rate",             "icon": "⚠️", "unit": "%",     "group": "human", "better": "lower"},
    "rework_rate":          {"label": "Rework rate",            "icon": "🔄", "unit": "%",     "group": "human", "better": "lower"},
    "cost_per_task":        {"label": "Cost / task",            "icon": "💰", "unit": "$",     "group": "human", "better": "lower"},
    "satisfaction":         {"label": "User satisfaction",      "icon": "😊", "unit": "/5",    "group": "human", "better": "higher"},
    "cycle_time":           {"label": "Cycle time",             "icon": "🕒", "unit": "h",     "group": "human", "better": "lower"},
    "waiting_time":         {"label": "Waiting time",           "icon": "⏳", "unit": "h",     "group": "human", "better": "lower"},
    "response_time":        {"label": "Response time",          "icon": "📨", "unit": "min",   "group": "human", "better": "lower"},
    "resolution_time":      {"label": "Resolution time",        "icon": "✅", "unit": "h",     "group": "human", "better": "lower"},
    "escalation_rate":      {"label": "Escalation rate",        "icon": "⬆️", "unit": "%",     "group": "human", "better": "lower"},
    "extraction_accuracy":  {"label": "Extraction accuracy",    "icon": "🔍", "unit": "%",     "group": "human", "better": "higher"},
    "corrections":          {"label": "Corrections / item",     "icon": "✏️", "unit": "count", "group": "human", "better": "lower"},
    "throughput":           {"label": "Items processed / month", "icon": "📦", "unit": "count", "group": "human", "better": "higher"},
    "dev_time":             {"label": "Dev time / change",      "icon": "💻", "unit": "h",     "group": "human", "better": "lower"},
    "defects":              {"label": "Defects / release",      "icon": "🐞", "unit": "count", "group": "human", "better": "lower"},
    "test_coverage":        {"label": "Test coverage",          "icon": "🧪", "unit": "%",     "group": "human", "better": "higher"},
    "pr_cycle_time":        {"label": "PR cycle time",          "icon": "🔀", "unit": "h",     "group": "human", "better": "lower"},
    "analyst_hours":        {"label": "Analyst hours / report", "icon": "📊", "unit": "h",     "group": "human", "better": "lower"},
    "query_time":           {"label": "Query time",             "icon": "🔎", "unit": "min",   "group": "human", "better": "lower"},
    "reports_produced":     {"label": "Reports produced / month", "icon": "📄", "unit": "count", "group": "human", "better": "higher"},
    "time_to_answer":       {"label": "Time to answer",         "icon": "❓", "unit": "min",   "group": "human", "better": "lower"},
    "retrieval_success":    {"label": "Successful retrieval",   "icon": "📚", "unit": "%",     "group": "human", "better": "higher"},
    "approvals":            {"label": "Approvals / item",       "icon": "🖊️", "unit": "count", "group": "human", "better": "lower"},
    "mttr":                 {"label": "MTTR",                   "icon": "🚑", "unit": "min",   "group": "human", "better": "lower"},
    "incidents":            {"label": "Incidents / month",      "icon": "🔔", "unit": "count", "group": "human", "better": "lower"},
    "automation_rate":      {"label": "Automation rate",        "icon": "🤖", "unit": "%",     "group": "human", "better": "higher"},
    "leads_processed":      {"label": "Leads processed / month", "icon": "🧲", "unit": "count", "group": "human", "better": "higher"},
    "conversion":           {"label": "Conversion rate",        "icon": "📈", "unit": "%",     "group": "human", "better": "higher"},
    "revenue":              {"label": "Revenue impact",         "icon": "💵", "unit": "$",     "group": "human", "better": "higher"},
    "completion_rate":      {"label": "Completion rate",        "icon": "☑️", "unit": "%",     "group": "human", "better": "higher"},
    "compliance_rate":      {"label": "Compliance rate",        "icon": "📋", "unit": "%",     "group": "human", "better": "higher"},
    # --- AI / technical ---------------------------------------------------
    "model":                {"label": "Model",                  "icon": "🤖", "unit": "",      "group": "technical", "better": "higher"},
    "tokens":               {"label": "Tokens / task",          "icon": "🧠", "unit": "count", "group": "technical", "better": "lower"},
    "latency":              {"label": "Latency",                "icon": "⚡", "unit": "s",     "group": "technical", "better": "lower"},
    "inference_cost":       {"label": "Inference cost / task",  "icon": "💵", "unit": "$",     "group": "technical", "better": "lower"},
    "hosting":              {"label": "Local / Private / Public", "icon": "☁", "unit": "",     "group": "technical", "better": "higher"},
    "success_rate":         {"label": "Success rate",           "icon": "🎯", "unit": "%",     "group": "technical", "better": "higher"},
    "retries":              {"label": "Retries / task",         "icon": "🔄", "unit": "count", "group": "technical", "better": "lower"},
    "human_corrections":    {"label": "Human corrections",      "icon": "✋", "unit": "%",     "group": "technical", "better": "lower"},
}


def metric_definition(key: str) -> dict[str, Any]:
    return _METRICS.get(key, {"label": key, "icon": "•", "unit": "", "group": "human", "better": "lower"})


# --------------------------------------------------------------------------
# Pain-point types and their metric templates
# --------------------------------------------------------------------------

PAIN_TYPES: dict[str, dict[str, Any]] = {
    "repetitive": {
        "label": "Repetitive manual work",
        "keywords": ["repetitive", "manual", "copy", "paste", "re-type", "retype", "every month",
                     "every week", "each time", "by hand", "spreadsheet", "tedious"],
        "metrics": ["time_per_task", "steps_per_task", "manual_interventions"],
    },
    "document": {
        "label": "Document processing",
        "keywords": ["document", "pdf", "scan", "ocr", "contract", "form", "invoice file",
                     "extract", "attachment", "paperwork"],
        "metrics": ["time_per_task", "accuracy", "extraction_accuracy", "corrections"],
    },
    "support": {
        "label": "Customer support",
        "keywords": ["ticket", "support", "customer request", "helpdesk", "escalation",
                     "chat", "sla", "complaint"],
        "metrics": ["response_time", "resolution_time", "escalation_rate", "satisfaction"],
    },
    "coding": {
        "label": "Coding",
        "keywords": ["code", "coding", "developer", "repository", "pull request", "deploy",
                     "unit test", "refactor", "bug"],
        "metrics": ["dev_time", "defects", "test_coverage", "pr_cycle_time"],
    },
    "billing": {
        "label": "Billing",
        "keywords": ["billing", "invoice", "ledger", "payment", "reconcile", "reconciliation",
                     "charge", "credit note", "dunning"],
        "metrics": ["time_per_task", "error_rate", "corrections", "cost_per_task"],
    },
    "analysis": {
        "label": "Data analysis",
        "keywords": ["analysis", "analyst", "report", "dashboard", "query", "sql", "insight",
                     "metrics", "forecast"],
        "metrics": ["analyst_hours", "query_time", "accuracy", "reports_produced"],
    },
    "knowledge": {
        "label": "Search / knowledge",
        "keywords": ["search", "find", "knowledge", "documentation", "wiki", "who knows",
                     "directory", "repository of", "lookup", "portfolio"],
        "metrics": ["time_to_answer", "accuracy", "retrieval_success"],
    },
    "approval": {
        "label": "Approval workflow",
        "keywords": ["approval", "approve", "sign-off", "signoff", "authorise", "authorize",
                     "review cycle", "gate"],
        "metrics": ["cycle_time", "steps_per_task", "waiting_time", "approvals"],
    },
    "itops": {
        "label": "IT operations",
        "keywords": ["incident", "outage", "monitoring", "alert", "server", "infrastructure",
                     "capacity", "runbook", "on-call", "mttr"],
        "metrics": ["mttr", "incidents", "manual_interventions", "automation_rate"],
    },
    "sales": {
        "label": "Sales",
        "keywords": ["lead", "prospect", "pipeline", "crm", "quote", "renewal", "churn",
                     "opportunity", "deal"],
        "metrics": ["leads_processed", "response_time", "conversion", "revenue"],
    },
    "hr": {
        "label": "HR",
        "keywords": ["onboarding", "employee", "hr", "recruit", "candidate", "payroll",
                     "leave request", "people ops"],
        "metrics": ["time_per_task", "steps_per_task", "completion_rate"],
    },
    "agent": {
        "label": "AI agent",
        "keywords": ["agent", "chatbot", "llm", "prompt", "copilot", "assistant", "rag"],
        "metrics": ["success_rate", "human_corrections", "latency", "inference_cost"],
    },
}

_DEFAULT_TYPE = "repetitive"


def classify_pain_point(text: str) -> tuple[str, str]:
    """Best-matching pain-point type for a free-text description.

    Returns ``(key, label)``. Falls back to repetitive manual work, which is
    both the most common case and the one whose metrics (time, steps, manual
    touches) apply almost universally.
    """
    haystack = f" {str(text or '').lower()} "
    best_key, best_score = _DEFAULT_TYPE, 0.0
    for key, spec in PAIN_TYPES.items():
        hits = sum(1 for word in spec["keywords"] if word in haystack)
        if not hits:
            continue
        # "Repetitive manual work" is the catch-all: almost every description
        # says "manual" or "every month", so it must lose ties to a domain
        # type that matched just as strongly. A billing task is billing first
        # and repetitive second.
        score = hits * (0.7 if key == _DEFAULT_TYPE else 1.0)
        if score > best_score:
            best_key, best_score = key, score
    return best_key, PAIN_TYPES[best_key]["label"]


# --------------------------------------------------------------------------
# Outcomes -> metrics
# --------------------------------------------------------------------------

OUTCOMES: list[dict[str, Any]] = [
    {"key": "save_time",       "label": "Save time",                    "metrics": ["time_per_task"]},
    {"key": "fewer_steps",     "label": "Fewer manual steps",           "metrics": ["steps_per_task", "manual_interventions"]},
    {"key": "reduce_errors",   "label": "Reduce errors",                "metrics": ["error_rate", "rework_rate"]},
    {"key": "improve_quality", "label": "Improve quality",              "metrics": ["accuracy", "rework_rate"]},
    {"key": "reduce_cost",     "label": "Reduce cost",                  "metrics": ["cost_per_task"]},
    {"key": "faster_response", "label": "Faster response to customer",  "metrics": ["response_time", "satisfaction"]},
    {"key": "increase_revenue","label": "Increase revenue",             "metrics": ["conversion", "revenue"]},
    {"key": "compliance",      "label": "Improve compliance",           "metrics": ["compliance_rate", "accuracy"]},
    {"key": "avoid_repetition","label": "Avoid repetitive work",        "metrics": ["manual_interventions", "automation_rate"]},
    {"key": "data_privacy",    "label": "Keep sensitive data private",  "metrics": ["hosting"]},
]

_OUTCOME_BY_KEY = {item["key"]: item for item in OUTCOMES}
_OUTCOME_BY_LABEL = {item["label"]: item for item in OUTCOMES}


def _outcome_metrics(outcomes: Iterable[str]) -> list[str]:
    keys: list[str] = []
    for outcome in outcomes or []:
        spec = _OUTCOME_BY_KEY.get(outcome) or _OUTCOME_BY_LABEL.get(outcome)
        for key in (spec or {}).get("metrics", []):
            if key not in keys:
                keys.append(key)
    return keys


# --------------------------------------------------------------------------
# Pain size
# --------------------------------------------------------------------------

def compute_pain(
    steps: int,
    minutes_per_task: float,
    frequency: float,
    frequency_unit: str = "per month",
    who_affected: str = "Just me",
) -> dict[str, Any]:
    """Size of the pain today, from the three baseline questions.

    ``Steps × Time × Frequency`` is the whole point: it converts a subjective
    complaint into hours per year, which is the only figure that lets two
    unrelated pain points be compared.
    """
    steps = max(0, int(steps or 0))
    minutes = max(0.0, float(minutes_per_task or 0.0))
    per_year = annual_volume(frequency, frequency_unit)

    annual_hours = (minutes * per_year) / 60.0
    monthly_hours = annual_hours / 12.0

    if annual_hours >= 5000:
        level, colour = "SEVERE", "critical"
    elif annual_hours >= 600:
        level, colour = "HIGH", "high"
    elif annual_hours >= 100:
        level, colour = "MODERATE", "moderate"
    else:
        level, colour = "LOW", "low"

    reach = WHO_AFFECTED.get(who_affected, 1.0)

    # A 0-100 severity number for the gauge. Log-scaled on annual hours so the
    # scale stays useful across four orders of magnitude: 20 h/yr ≈ 30,
    # 2,250 h/yr ≈ 78, 8,300 h/yr ≈ 91. Breadth of impact nudges it up a little.
    if annual_hours <= 0:
        pain_score = 0.0
    else:
        pain_score = 23.0 * _log10(max(annual_hours, 1.0)) + (reach - 1.0) * 3.0
    pain_score = max(0.0, min(100.0, pain_score))

    return {
        "steps": steps,
        "minutes_per_task": minutes,
        "frequency": float(frequency or 0),
        "frequency_unit": frequency_unit,
        "who_affected": who_affected,
        "reach_multiplier": reach,
        "tasks_per_year": round(per_year, 1),
        "tasks_per_month": round(per_year / 12.0, 1),
        "monthly_hours": round(monthly_hours, 1),
        "annual_hours": round(annual_hours, 1),
        # Hours returned if a fix only ever achieves half of the target.
        "annual_hours_at_half": round(annual_hours * 0.5, 1),
        "pain_score": int(round(pain_score)),
        "level": level,
        "level_class": colour,
    }


# Target multipliers for the improvement preview. Lower is better for all of
# these, so the multiplier is the fraction of the baseline we aim to keep.
IMPROVEMENT_TARGETS = {
    "time_per_task": 0.18,
    "steps_per_task": 0.35,
    "manual_interventions": 0.30,
}


def estimated_improvement(pain: dict[str, Any]) -> list[dict[str, Any]]:
    """Before → after → percentage rows for the AI preview panel.

    These are *targets*, not measurements. Everything here is derived from the
    three baseline answers, so a row only appears when its baseline is known.
    """
    minutes = float(pain.get("minutes_per_task") or 0)
    steps = int(pain.get("steps") or 0)
    rows: list[dict[str, Any]] = []

    def add(label: str, before: float, after: float, unit: str = "", prefix: str = "") -> None:
        if before <= 0:
            return
        pct = int(round((before - after) / before * 100))
        fmt = (lambda v: f"{prefix}{v:g}{unit}")
        rows.append({"label": label, "before": fmt(before), "after": fmt(after), "pct": pct})

    if minutes:
        add("Time per task", minutes, max(1, round(minutes * IMPROVEMENT_TARGETS["time_per_task"])), " min")
    if steps:
        add("Steps per task", steps, max(1, round(steps * IMPROVEMENT_TARGETS["steps_per_task"])))
        manual_before = max(1, round(steps * 0.7))
        add("Manual interventions", manual_before,
            max(1, round(manual_before * IMPROVEMENT_TARGETS["manual_interventions"])))
    # Error and cost have no measured baseline; shown as typical targets and
    # labelled as such by the caller.
    rows.append({"label": "Error rate", "before": "8%", "after": "<2%", "pct": 75, "assumed": True})
    rows.append({"label": "Cost per task", "before": "$12", "after": "$4", "pct": 67, "assumed": True})
    return rows


# --------------------------------------------------------------------------
# Recommended metrics (BEFORE / TARGET)
# --------------------------------------------------------------------------

def _target_for(key: str, pain: dict[str, Any]) -> tuple[str, str]:
    """(before, target) display strings for a metric, given the baseline.

    Only metrics the three questions actually measure get a numeric BEFORE.
    Everything else shows an em dash rather than a fabricated number — an
    invented baseline is the fastest way to make the ACTUAL column meaningless.
    """
    minutes = pain.get("minutes_per_task") or 0
    steps = pain.get("steps") or 0

    if key == "time_per_task" and minutes:
        return f"{minutes:g} min", f"<{max(1, round(minutes * 0.2)):g} min"
    if key == "steps_per_task" and steps:
        return f"{steps:g}", f"<{max(1, round(steps * 0.35)):g}"
    if key == "manual_interventions" and steps:
        before = max(1, round(steps * 0.7))
        return f"{before:g}", f"<{max(1, round(before * 0.3)):g}"
    defaults = {
        "accuracy": ("—", ">98%"),
        "extraction_accuracy": ("—", ">97%"),
        "retrieval_success": ("—", ">95%"),
        "error_rate": ("—", "<2%"),
        "rework_rate": ("—", "<2%"),
        "escalation_rate": ("—", "<10%"),
        "satisfaction": ("—", ">4/5"),
        "compliance_rate": ("—", "100%"),
        "completion_rate": ("—", ">95%"),
        "test_coverage": ("—", ">80%"),
        "automation_rate": ("—", ">70%"),
        "success_rate": ("—", ">95%"),
        "human_corrections": ("—", "<5%"),
        "latency": ("—", "<3 s"),
        "retries": ("—", "<1"),
        "hosting": ("—", "Local / Private"),
    }
    return defaults.get(key, ("—", "—"))


def recommend_metrics(
    pain_type: str,
    outcomes: Iterable[str],
    pain: dict[str, Any] | None = None,
    include_technical: bool = True,
) -> list[dict[str, Any]]:
    """Metrics to measure, pre-ticked where they follow from the answers.

    Order: the pain type's own template first (these are the metrics that
    define the category), then anything the chosen outcomes add. Metrics from
    both sources are pre-selected; a small technical tail is offered unticked.
    """
    pain = pain or {}
    template = list(PAIN_TYPES.get(pain_type, PAIN_TYPES[_DEFAULT_TYPE])["metrics"])
    from_outcomes = _outcome_metrics(outcomes)

    ordered: list[str] = []
    for key in template + from_outcomes:
        if key not in ordered:
            ordered.append(key)

    # Always worth offering, never forced on.
    optional = ["cost_per_task", "satisfaction"]
    technical_tail = ["model", "success_rate", "latency", "inference_cost", "human_corrections"]

    rows: list[dict[str, Any]] = []
    for key in ordered:
        before, target = _target_for(key, pain)
        spec = metric_definition(key)
        rows.append({
            "key": key, "label": spec["label"], "icon": spec["icon"], "unit": spec["unit"],
            "group": spec["group"], "better": spec["better"],
            # Only pre-tick a metric we can actually state a baseline or a
            # target for. Ticking one that reads "— → —" asks the submitter to
            # commit to measuring something nobody has defined.
            "before": before, "target": target, "actual": "—",
            "selected": not (before == "—" and target == "—"),
        })
    for key in optional:
        if key in ordered:
            continue
        before, target = _target_for(key, pain)
        spec = metric_definition(key)
        rows.append({
            "key": key, "label": spec["label"], "icon": spec["icon"], "unit": spec["unit"],
            "group": spec["group"], "better": spec["better"],
            "before": before, "target": target, "actual": "—", "selected": False,
        })
    if include_technical:
        for key in technical_tail:
            if key in ordered:
                continue
            before, target = _target_for(key, pain)
            spec = metric_definition(key)
            rows.append({
                "key": key, "label": spec["label"], "icon": spec["icon"], "unit": spec["unit"],
                "group": spec["group"], "better": spec["better"],
                "before": before, "target": target, "actual": "—", "selected": False,
            })
    return rows


def summarise_metrics(metrics: Iterable[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Split metrics into the two audiences: business submitter vs AI engineer."""
    human, technical = [], []
    for row in metrics or []:
        (technical if row.get("group") == "technical" else human).append(row)
    return {"human": human, "technical": technical}


# --------------------------------------------------------------------------
# Opportunity scoring
# --------------------------------------------------------------------------

def compute_opportunity(
    pain: dict[str, Any],
    outcomes: Iterable[str] | None = None,
    reusable_agents: Iterable[str] | None = None,
    attachments: int = 0,
    confidentiality: str = "Internal",
) -> dict[str, Any]:
    """Impact, remaining complexity, readiness and the headline opportunity score.

    Impact is driven by annual hours, because that is the honest measure of
    what a fix is worth. Complexity rises with process length and data
    plumbing and falls when an existing agent already covers the ground.
    """
    outcomes = list(outcomes or [])
    agents = list(reusable_agents or [])
    annual_hours = float(pain.get("annual_hours") or 0.0)
    steps = int(pain.get("steps") or 0)
    reach = float(pain.get("reach_multiplier") or 1.0)

    # Impact: log-shaped in annual hours (100h ≈ 50, 1k ≈ 70, 10k ≈ 90),
    # nudged by how many people the fix reaches.
    if annual_hours <= 0:
        impact = 10.0
    else:
        impact = 10.0 + 20.0 * (max(annual_hours, 1.0) ** 0.0) * _log10(max(annual_hours, 1.0))
    impact *= min(1.25, 0.85 + 0.2 * reach)
    impact = _clamp(impact, 5, 100)

    # Complexity: long processes and many input formats are what actually
    # make these builds expensive.
    complexity = 15.0
    complexity += min(25.0, steps * 1.5)
    complexity += min(15.0, max(0, attachments - 1) * 5.0)
    if str(confidentiality).strip().lower().startswith("private"):
        complexity += 8.0
    if any(key in outcomes for key in ("increase_revenue", "compliance")):
        complexity += 6.0
    if agents:
        complexity -= 18.0
    complexity = _clamp(complexity, 5, 100)

    # Readiness: can we start now? Reuse and a well-understood process help.
    readiness = 55.0
    if agents:
        readiness += 20.0
    if steps:
        readiness += 10.0
    if annual_hours >= 100:
        readiness += 10.0
    readiness -= min(20.0, max(0, attachments - 1) * 6.0)
    readiness = _clamp(readiness, 5, 100)

    score = 0.5 * impact + 0.3 * readiness + 0.2 * (100 - complexity)
    score = int(round(_clamp(score, 0, 100)))

    if score >= 70 and complexity <= 40:
        classification = "QUICK WIN"
    elif score >= 70:
        classification = "BIG BET"
    elif complexity <= 40:
        classification = "FILL-IN"
    else:
        classification = "NEEDS RESEARCH"

    # Bands line up with the classification threshold: anything the classifier
    # calls low complexity (<= 40) should also read as fast to first value,
    # otherwise the two panels contradict each other on the same input.
    if complexity <= 40:
        ttfv = "2 weeks"
    elif complexity <= 60:
        ttfv = "4-6 weeks"
    else:
        ttfv = "8-12 weeks"

    # What a realistic fix returns, using the same 80% reduction the default
    # time target assumes.
    projected_saving = round(annual_hours * 0.8, 1)

    return {
        "impact": int(round(impact)),
        "complexity": int(round(complexity)),
        "readiness": int(round(readiness)),
        "score": score,
        "classification": classification,
        "time_to_first_value": ttfv,
        "projected_annual_hours_saved": projected_saving,
        "reusable_agents": agents,
    }


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _log10(value: float) -> float:
    import math

    return math.log10(value)


# --------------------------------------------------------------------------
# Workflow step generation
# --------------------------------------------------------------------------

_WORKFLOW_SKELETONS: dict[str, list[str]] = {
    "billing": [
        "Receive customer billing request", "Download source billing file",
        "Open customer billing template", "Compare required fields",
        "Copy customer information", "Convert date format", "Convert currency fields",
        "Reformat line items", "Validate totals", "Check tax information",
        "Generate invoice", "Review invoice", "Email invoice", "Archive copy",
    ],
    "document": [
        "Receive the document", "Open and read it", "Identify the fields that matter",
        "Copy each field into the system", "Fix formatting differences",
        "Cross-check against the source", "Flag anything ambiguous",
        "Ask the owner for clarification", "Apply the correction",
        "Approve the record", "File the document",
    ],
    "support": [
        "Ticket arrives in the queue", "Read and understand the request",
        "Search past tickets for similar cases", "Decide the category and priority",
        "Gather account context", "Draft a reply", "Check it against policy",
        "Send the reply", "Wait for the customer", "Escalate if unresolved",
        "Close and tag the ticket",
    ],
    "approval": [
        "Request is submitted", "Check the request is complete",
        "Look up the applicable policy", "Route to the first approver",
        "Chase for a response", "Collect the approval", "Route to the next approver",
        "Record the decision", "Notify the requester", "File the audit trail",
    ],
    "analysis": [
        "Receive the question", "Locate the right data source", "Export the raw data",
        "Clean and reconcile it", "Write the query", "Check the numbers look right",
        "Build the chart or table", "Write the commentary", "Review with a colleague",
        "Publish the report",
    ],
    "knowledge": [
        "Someone asks a question", "Try to remember who would know",
        "Search chat and email history", "Ask around for a pointer",
        "Wait for a reply", "Find a partially relevant document",
        "Verify it is still current", "Pass the answer back",
    ],
    "itops": [
        "Alert fires", "Acknowledge and triage", "Open the runbook",
        "Check dashboards and logs", "Identify the failing component",
        "Apply the manual fix", "Verify recovery", "Write the incident note",
        "Close the incident",
    ],
    "hr": [
        "Request arrives", "Check the employee record", "Confirm eligibility",
        "Collect the missing paperwork", "Enter the details into the HR system",
        "Notify the manager", "Track completion", "File the record",
    ],
    "sales": [
        "Lead arrives", "Check it against the CRM", "Research the account",
        "Qualify the opportunity", "Draft the outreach", "Send and log it",
        "Follow up", "Update the pipeline stage",
    ],
    "coding": [
        "Pick up the ticket", "Reproduce the behaviour", "Find the relevant code",
        "Write the change", "Write or update tests", "Run the suite locally",
        "Open the pull request", "Address review comments", "Merge and deploy",
    ],
    "agent": [
        "Collect the user request", "Assemble the prompt context",
        "Call the model", "Check the output is usable", "Correct it by hand",
        "Pass it downstream", "Log the outcome",
    ],
    "repetitive": [
        "Notice the task is due", "Gather the inputs", "Open the working file",
        "Copy the data across", "Reformat it to match", "Check for mistakes",
        "Fix what is wrong", "Save the result", "Send it on", "File a copy",
    ],
}

_WORKFLOW_PROMPT = """You are a process analyst. Break this task into exactly {count} short steps as done TODAY, by hand.

Task: {description}

Reply with ONLY a JSON array of {count} strings, each a short imperative step (max 8 words).
Example: ["Receive customer request", "Download source file"]"""


def generate_workflow_steps(
    description: str,
    step_count: int,
    pain_type: str | None = None,
    llm_call: Callable[[str], str] | None = None,
) -> tuple[list[str], str]:
    """Best guess at the manual steps behind a pain point.

    Returns ``(steps, source)`` where source is ``"llm"`` or ``"template"``.
    Always returns exactly ``step_count`` steps so the list lines up with the
    number the submitter gave; the user is expected to correct it.
    """
    count = max(1, min(40, int(step_count or 1)))
    key = pain_type or classify_pain_point(description)[0]

    if llm_call and str(description or "").strip():
        try:
            raw = llm_call(_WORKFLOW_PROMPT.format(count=count, description=description.strip()[:2000]))
            steps = _parse_step_list(raw)
            if len(steps) >= max(2, count // 2):
                return _fit(steps, count), "llm"
        except Exception:
            pass

    skeleton = _WORKFLOW_SKELETONS.get(key, _WORKFLOW_SKELETONS["repetitive"])
    return _fit(list(skeleton), count), "template"


def _parse_step_list(raw: str) -> list[str]:
    text = str(raw or "").strip()
    if not text:
        return []
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    start, end = text.find("["), text.rfind("]")
    if start != -1 and end > start:
        try:
            parsed = json.loads(text[start : end + 1])
            if isinstance(parsed, list):
                return [str(item).strip(" -•\t") for item in parsed if str(item).strip()]
        except Exception:
            pass
    # Fall back to numbered or bulleted lines.
    lines = [re.sub(r"^\s*(?:\d+[.)]|[-*•])\s*", "", line).strip() for line in text.splitlines()]
    return [line for line in lines if line and len(line) < 120]


def _fit(steps: list[str], count: int) -> list[str]:
    """Pad or trim to exactly ``count`` entries."""
    steps = [step for step in steps if step][:count]
    while len(steps) < count:
        steps.append(f"Additional manual step {len(steps) + 1}")
    return steps
