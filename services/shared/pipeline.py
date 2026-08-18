"""The one workflow the whole lab runs on.

    ontology + pain point  ->  POC  ->  proven  ->  agent in the library

Four stages, one direction, nothing optional. Each step is a pure function of
the record before it, so the pipeline can be recomputed from stored data at any
time and never drifts out of sync with what the UI shows.

The interesting part is how a pain point becomes a POC without anybody writing
a design doc. ``pain_metrics.classify_pain_point`` already sorts free text into
one of twelve pain types; this module gives every one of those types an
*ontology blueprint* — which ontology objects it touches, which agent pattern
solves it, what tools that needs and what "working" would have to mean. Drafting
a POC is then a join: blueprint (what this kind of problem always needs) plus
the submitter's own baseline and chosen outcomes (what this instance must beat).

No model call is involved. That is deliberate: the draft has to be instant,
free, and identical for the same input, or nobody trusts it enough to build on.
"""

from __future__ import annotations

import copy
import re
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

__all__ = [
    "STAGES",
    "STAGE_KEYS",
    "POC_STATUSES",
    "POC_PLATFORMS",
    "ONTOLOGY_BLUEPRINTS",
    "blueprint_for",
    "draft_poc",
    "poc_progress",
    "promote_to_agent",
    "stage_of",
    "pipeline_counts",
    "pipeline_rows",
    "next_action",
]


# --------------------------------------------------------------------------
# Stages
# --------------------------------------------------------------------------

# (key, label, one-line meaning, icon)
STAGES: tuple[tuple[str, str, str, str], ...] = (
    ("captured",  "Pain point", "Scored, and matched to an ontology blueprint.", "🎯"),
    ("poc",       "POC",        "Blueprint drafted. Acceptance criteria set.",   "🧪"),
    ("proven",    "Proven",     "Criteria met against the real baseline.",       "📈"),
    ("published", "Agent",      "Reusable in the AI Agent Library.",             "🚀"),
)

STAGE_KEYS: tuple[str, ...] = tuple(stage[0] for stage in STAGES)

# Where the build itself has got to — independent of the pipeline stage, which
# tracks whether it is proven. A POC can be Live and still not proven, and that
# distinction is the point: running is not the same as working.
POC_STATUSES: tuple[str, ...] = (
    "Not started", "Building", "Testing", "Live", "Parked",
)

# Common places a POC ends up running. Free text is still allowed — this is the
# pick-list, not a constraint.
POC_PLATFORMS: tuple[str, ...] = (
    "Local only", "Streamlit", "Hugging Face Spaces", "Docker", "Kubernetes",
    "OpenStack", "Serverless", "Other",
)

# A POC counts as proven once this share of its acceptance criteria are met.
# Not 100%: the last criterion is usually the one that needs a quarter of real
# traffic to measure, and holding the whole pipeline for it helps nobody.
PROVEN_THRESHOLD = 0.7


# --------------------------------------------------------------------------
# Ontology blueprints — one per pain type in pain_metrics.PAIN_TYPES
# --------------------------------------------------------------------------
#
# objects      the ontology types the agent reads or writes (ontology/objects.py)
# pattern      the agent archetype, as a pipeline of verbs
# capabilities what it must be able to do, in the submitter's language
# tools        what has to be wired up for it to run
# guardrail    the one rule that keeps it safe to switch on
# sector/industry  where it lands in the agent library

ONTOLOGY_BLUEPRINTS: dict[str, dict[str, Any]] = {
    "repetitive": {
        "objects": ["Workflow", "System", "Dataset"],
        "pattern": "Observe → Map → Replay → Verify",
        "capabilities": [
            "Read the source record in whatever format it arrives",
            "Apply the same mapping a person applies by hand",
            "Write the result into the destination system",
            "Flag anything that does not match the known shape",
        ],
        "tools": ["Source system connector", "Field mapping table", "Destination writer", "Run log"],
        "guardrail": "Every write is reversible and logged against the run that produced it.",
        "sector": "Process Automation",
        "industry": "🔁 Repetitive Work",
    },
    "document": {
        "objects": ["Document", "Dataset", "Policy"],
        "pattern": "Ingest → Extract → Validate → Emit",
        "capabilities": [
            "Accept PDFs, scans and images without pre-sorting",
            "Pull the named fields out with a confidence score",
            "Check each field against its expected type and range",
            "Route low-confidence extractions to a human queue",
        ],
        "tools": ["OCR / document parser", "Field schema", "Confidence thresholds", "Review queue"],
        "guardrail": "Below the confidence threshold the agent asks; it never guesses.",
        "sector": "Document Intelligence",
        "industry": "📄 Document Processing",
    },
    "support": {
        "objects": ["Ticket", "Customer", "Policy", "Human"],
        "pattern": "Classify → Draft → Route → Escalate",
        "capabilities": [
            "Read the incoming ticket and classify intent and urgency",
            "Draft a reply grounded in the knowledge base",
            "Route to the queue or SME who actually owns it",
            "Escalate on SLA risk before the breach, not after",
        ],
        "tools": ["Ticket system API", "Knowledge base index", "Routing rules", "SLA clock"],
        "guardrail": "Drafts to customers are proposed, never sent unreviewed.",
        "sector": "Customer Operations",
        "industry": "🎧 Support",
    },
    "coding": {
        "objects": ["Workflow", "System", "Asset"],
        "pattern": "Read → Propose → Test → Open PR",
        "capabilities": [
            "Read the repository and the failing case",
            "Propose the smallest change that fixes it",
            "Run the existing test suite against the change",
            "Open a pull request with the reasoning attached",
        ],
        "tools": ["Repo access", "CI runner", "Test suite", "PR API"],
        "guardrail": "Nothing merges without a green suite and a human approval.",
        "sector": "Engineering",
        "industry": "💻 Coding",
    },
    "billing": {
        "objects": ["Dataset", "Customer", "Policy", "Event"],
        "pattern": "Normalise → Reconcile → Explain → Post",
        "capabilities": [
            "Normalise each customer's layout to the internal schema",
            "Reconcile line by line and isolate the deltas",
            "Explain every delta in one sentence a human can check",
            "Post only what reconciles; hold the rest",
        ],
        "tools": ["Layout templates", "Ledger read access", "Reconciliation rules", "Exception report"],
        "guardrail": "An unexplained delta blocks the post. Silence is never treated as agreement.",
        "sector": "Finance Operations",
        "industry": "💳 Billing",
    },
    "analysis": {
        "objects": ["Dataset", "Decision", "Event"],
        "pattern": "Query → Aggregate → Narrate → Publish",
        "capabilities": [
            "Run the recurring query set without being asked",
            "Aggregate to the grain the audience actually reads",
            "Narrate what changed and why it plausibly changed",
            "Publish on a schedule to where people already look",
        ],
        "tools": ["Warehouse credentials", "Query library", "Chart renderer", "Delivery channel"],
        "guardrail": "Every number carries the query and the run time that produced it.",
        "sector": "Analytics",
        "industry": "📊 Data Analysis",
    },
    "knowledge": {
        "objects": ["Human", "Skill", "Asset", "Team"],
        "pattern": "Index → Retrieve → Rank → Cite",
        "capabilities": [
            "Index the sources people currently search by hand",
            "Retrieve on meaning, not just keyword match",
            "Rank by who or what is actually current",
            "Cite the source so the answer can be checked",
        ],
        "tools": ["Source crawlers", "Vector index", "Freshness signal", "Citation renderer"],
        "guardrail": "An answer without a citation is not returned.",
        "sector": "Knowledge",
        "industry": "🔍 Search & Discovery",
    },
    "approval": {
        "objects": ["Decision", "Policy", "Human", "Event"],
        "pattern": "Check → Gather → Nudge → Record",
        "capabilities": [
            "Check the request against the policy before anyone is asked",
            "Gather the evidence an approver always ends up asking for",
            "Nudge the one person the request is actually waiting on",
            "Record the decision and the reason against the object",
        ],
        "tools": ["Policy rules", "Approver directory", "Notification channel", "Decision log"],
        "guardrail": "The agent prepares and chases decisions. It never makes them.",
        "sector": "Governance",
        "industry": "✅ Approvals",
    },
    "itops": {
        "objects": ["System", "Event", "RiskFactor", "Asset"],
        "pattern": "Watch → Correlate → Diagnose → Runbook",
        "capabilities": [
            "Watch the signals that precede the incident, not just the alert",
            "Correlate across hosts and services into one story",
            "Propose the most likely cause with its evidence",
            "Execute the approved runbook step, then re-check",
        ],
        "tools": ["Metrics/logs access", "Topology map", "Runbook library", "Change log"],
        "guardrail": "Read-only by default; each write step is individually enabled.",
        "sector": "Infrastructure",
        "industry": "🛠 IT Operations",
    },
    "sales": {
        "objects": ["Customer", "Event", "Decision", "RiskFactor"],
        "pattern": "Score → Prioritise → Draft → Track",
        "capabilities": [
            "Score accounts on the signals that historically preceded a move",
            "Prioritise the list a rep opens each morning",
            "Draft the outreach with the account's own context in it",
            "Track what actually happened and feed it back into the score",
        ],
        "tools": ["CRM access", "Signal feeds", "Template library", "Outcome tracking"],
        "guardrail": "Customer-facing text is drafted for a named human to send.",
        "sector": "Revenue",
        "industry": "📈 Sales",
    },
    "hr": {
        "objects": ["Human", "Workflow", "Policy", "Team"],
        "pattern": "Trigger → Prepare → Sequence → Confirm",
        "capabilities": [
            "Trigger from the joiner/mover/leaver event, not a reminder",
            "Prepare every artefact the step needs in advance",
            "Sequence the tasks across the teams that own them",
            "Confirm completion and chase what is outstanding",
        ],
        "tools": ["HRIS events", "Task templates", "Team directory", "Completion tracking"],
        "guardrail": "Personal data stays inside the systems that already hold it.",
        "sector": "People Operations",
        "industry": "👥 HR",
    },
    "agent": {
        "objects": ["Agent", "Dataset", "Policy", "Event"],
        "pattern": "Ground → Reason → Act → Evaluate",
        "capabilities": [
            "Ground every answer in a retrievable source",
            "Reason over the tools it is allowed to call",
            "Act within an explicit permission boundary",
            "Evaluate itself against a held-out set on every change",
        ],
        "tools": ["Model endpoint", "Retrieval index", "Tool permissions", "Eval harness"],
        "guardrail": "A change that drops the eval score does not ship.",
        "sector": "Agent Factory",
        "industry": "🤖 AI Agents",
    },
}

_FALLBACK_TYPE = "repetitive"


def blueprint_for(pain_type: str | None) -> dict[str, Any]:
    """The ontology blueprint for a pain type, always returning something usable."""
    return copy.deepcopy(
        ONTOLOGY_BLUEPRINTS.get(str(pain_type or ""), ONTOLOGY_BLUEPRINTS[_FALLBACK_TYPE])
    )


# --------------------------------------------------------------------------
# Pain point -> POC
# --------------------------------------------------------------------------

def _slug(text: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(text or "").lower()).strip("-") or "poc"


def _agent_name(title: str, blueprint: Mapping[str, Any]) -> str:
    """A name that says what the agent does, not what the ticket was called."""
    verb = str(blueprint.get("pattern", "Run")).split("→")[0].strip() or "Run"
    words = [w for w in re.split(r"\s+", str(title or "").strip()) if w]
    subject = " ".join(words[:5]) or "Workflow"
    return f"{verb} — {subject.title()} Agent"


def _acceptance_from(challenge: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Acceptance criteria taken from the submitter's own chosen metrics.

    The point of using their metrics rather than a generic checklist: the POC
    is judged against the number the person who felt the pain already said
    mattered, so "proven" means something to them rather than to us.
    """
    criteria: list[dict[str, Any]] = []
    for metric in challenge.get("metrics") or []:
        if not isinstance(metric, Mapping):
            continue
        criteria.append({
            "key": str(metric.get("key") or _slug(metric.get("label"))),
            "label": str(metric.get("label") or metric.get("key") or "Metric"),
            "unit": str(metric.get("unit") or ""),
            "before": metric.get("before"),
            "target": metric.get("target"),
            "actual": metric.get("actual"),
            "better": str(metric.get("better") or "lower"),
            "met": False,
        })

    if not criteria:
        # Nothing was chosen at intake. Fall back to the two things every
        # automation has to beat to be worth switching on.
        baseline = challenge.get("baseline") or {}
        criteria = [
            {"key": "time_per_task", "label": "Time per task", "unit": "min",
             "before": baseline.get("minutes"), "target": None, "actual": None,
             "better": "lower", "met": False},
            {"key": "manual_interventions", "label": "Manual steps", "unit": "steps",
             "before": baseline.get("steps"), "target": None, "actual": None,
             "better": "lower", "met": False},
        ]

    # One criterion nobody chooses but everybody needs.
    criteria.append({
        "key": "human_review", "label": "Human review path works", "unit": "",
        "before": None, "target": "verified", "actual": None, "better": "higher", "met": False,
    })

    # The twin turns "where does this go next" into a testable handoff: if the
    # downstream unit will not take the output, the automation is not done,
    # however good its own numbers look.
    context = challenge.get("twin_context") or {}
    downstream = str(context.get("output_to") or "").strip()
    if downstream and not downstream.lower().startswith("nobody"):
        criteria.append({
            "key": "handoff_accepted",
            "label": f"Output accepted by {downstream}",
            "unit": "", "before": None, "target": "accepted", "actual": None,
            "better": "higher", "met": False,
        })
    return criteria


def _build_steps(challenge: Mapping[str, Any], blueprint: Mapping[str, Any]) -> list[str]:
    """The build plan: the blueprint's pattern, grounded in this person's workflow."""
    stages = [part.strip() for part in str(blueprint.get("pattern", "")).split("→") if part.strip()]
    workflow = [str(step) for step in (challenge.get("current_workflow") or []) if str(step).strip()]

    steps: list[str] = []
    for index, stage in enumerate(stages):
        # Pair each pattern stage with the slice of their real process it covers,
        # so the plan reads as "this is your step 3", not as generic advice.
        if workflow:
            # Split by cut points rather than a fixed span: a fixed span drops
            # the remainder, and the tail of a workflow (send it, file it) is
            # exactly the part people forget to automate.
            start = index * len(workflow) // len(stages)
            end = (index + 1) * len(workflow) // len(stages)
            covered = workflow[start:end] or workflow[-1:]
            steps.append(f"{stage}: {'; '.join(covered)}")
        else:
            steps.append(stage)
    if not steps:
        steps = ["Define inputs", "Build the mapping", "Run against real data", "Review with the submitter"]
    return steps


def _effort_days(challenge: Mapping[str, Any]) -> int:
    """Rough build effort, driven by the complexity the opportunity model found."""
    opportunity = challenge.get("opportunity") or {}
    complexity = float(opportunity.get("complexity") or 45.0)
    reuse = len(challenge.get("similar_agents") or [])
    days = 2 + complexity / 12.0
    days -= reuse * 1.5          # an existing agent is most of the build
    return int(max(2, round(days)))


def draft_poc(challenge: Mapping[str, Any]) -> dict[str, Any]:
    """Turn a captured pain point into a POC blueprint.

    Pure: same challenge in, same POC out. Nothing is written here — the caller
    decides whether to keep it.
    """
    pain_type = str(challenge.get("pain_type") or _FALLBACK_TYPE)
    blueprint = blueprint_for(pain_type)
    title = str(challenge.get("title") or "Untitled")
    context = challenge.get("twin_context") or {}

    return {
        # Where it plugs in, straight from the twin. A blueprint without its
        # two connection points is a diagram; with them it is a build ticket.
        "integration": {
            "owner": context.get("business_unit", ""),
            "task": context.get("task", ""),
            "input": context.get("input", ""),
            "input_from": context.get("input_from", ""),
            "output_to": context.get("output_to", ""),
            "handoff": context.get("output_flow", ""),
        },
        "id": f"poc_{_slug(title)[:40]}",
        "name": _agent_name(title, blueprint),
        "pain_type": pain_type,
        "pattern": blueprint["pattern"],
        "objects": blueprint["objects"],
        "capabilities": blueprint["capabilities"],
        "tools": blueprint["tools"],
        "guardrail": blueprint["guardrail"],
        "sector": blueprint["sector"],
        "industry": blueprint["industry"],
        "build_steps": _build_steps(challenge, blueprint),
        "acceptance": _acceptance_from(challenge),
        "effort_days": _effort_days(challenge),
        "reuse": list(challenge.get("similar_agents") or []),
        # Where the build actually lives and runs. All empty until somebody
        # starts it: a POC with a repo it never had implies work that does not
        # exist, and the table should say "not started" rather than guess.
        "github": "",
        "platform": "",
        "demo_url": "",
        "owner": "",
        "notes": "",
        "status": POC_STATUSES[0],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


# --------------------------------------------------------------------------
# POC -> proven -> agent
# --------------------------------------------------------------------------

def poc_progress(poc: Mapping[str, Any] | None) -> tuple[int, int]:
    """(criteria met, criteria total) for a POC."""
    criteria = list((poc or {}).get("acceptance") or [])
    met = sum(1 for c in criteria if c.get("met"))
    return met, len(criteria)


def stage_of(challenge: Mapping[str, Any]) -> str:
    """Which pipeline stage this pain point is in, derived from its own data."""
    if challenge.get("published_agent"):
        return "published"
    poc = challenge.get("poc")
    if poc:
        met, total = poc_progress(poc)
        if total and met / total >= PROVEN_THRESHOLD:
            return "proven"
        return "poc"
    return "captured"


def next_action(challenge: Mapping[str, Any]) -> str:
    """The single next thing that moves this record forward."""
    return {
        "captured":  "Draft the POC from its ontology blueprint",
        "poc":       "Run it and tick off the acceptance criteria",
        "proven":    "Publish it to the AI Agent Library",
        "published": "Reuse it on the next matching pain point",
    }[stage_of(challenge)]


def promote_to_agent(challenge: Mapping[str, Any], poc: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Build the Agent Library record for a proven POC.

    Shaped for services/ui/data/agents.json, which the library page and the
    reuse matcher both read — so a published agent is immediately offered as
    reuse against the next similar pain point. That closing of the loop is the
    whole reason the pipeline ends here.
    """
    poc = poc or challenge.get("poc") or draft_poc(challenge)
    baseline = challenge.get("baseline") or {}
    context = challenge.get("twin_context") or {}
    integration = poc.get("integration") or {}
    hours = float(baseline.get("annual_hours") or 0.0)

    owner = context.get("business_unit") or integration.get("owner") or ""
    task = context.get("task") or integration.get("task") or ""
    saved = f" Frees about {hours:,.0f} human hours a year at the originating team." if hours else ""
    # Say whose task it automates: that is what makes another unit with the
    # same task recognise it as reusable rather than scrolling past.
    placed = f" Automates “{task}” for {owner}." if task and owner else ""

    return {
        "sector": poc.get("sector", "Process Automation"),
        "industry": poc.get("industry", "🔁 Repetitive Work"),
        "agent": poc.get("name") or _agent_name(str(challenge.get("title") or ""), poc),
        "description": (
            f"{poc.get('pattern', '')}.{placed} "
            f"Built from the pain point “{challenge.get('title', 'Untitled')}”.{saved}"
        ).strip(),
        "status": "Available",
        "pattern": poc.get("pattern"),
        "objects": poc.get("objects", []),
        "capabilities": poc.get("capabilities", []),
        "tools": poc.get("tools", []),
        "guardrail": poc.get("guardrail"),
        "business_unit": owner,
        "task": task,
        "integration": integration,
        "origin_challenge": challenge.get("id"),
        "origin_title": challenge.get("title"),
        "published_at": datetime.now(timezone.utc).isoformat(),
    }


# --------------------------------------------------------------------------
# Board views
# --------------------------------------------------------------------------

def pipeline_counts(challenges: Iterable[Mapping[str, Any]]) -> dict[str, int]:
    """How many records sit in each stage."""
    counts = {key: 0 for key in STAGE_KEYS}
    for challenge in challenges:
        counts[stage_of(challenge)] += 1
    return counts


def pipeline_rows(challenges: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Flat, display-ready view of every record and where it sits."""
    rows: list[dict[str, Any]] = []
    for challenge in challenges:
        poc = challenge.get("poc") or {}
        met, total = poc_progress(poc)
        baseline = challenge.get("baseline") or {}
        opportunity = challenge.get("opportunity") or {}
        rows.append({
            "id": challenge.get("id"),
            "title": challenge.get("title") or "Untitled",
            "stage": stage_of(challenge),
            "pain_type": challenge.get("pain_type"),
            "category": challenge.get("category") or "",
            "annual_hours": float(baseline.get("annual_hours") or 0.0),
            "score": int(opportunity.get("score") or 0),
            "classification": opportunity.get("classification") or "",
            "poc_name": poc.get("name") or "",
            "pattern": poc.get("pattern") or "",
            "github": poc.get("github") or "",
            "platform": poc.get("platform") or "",
            "demo_url": poc.get("demo_url") or "",
            "owner": poc.get("owner") or "",
            "notes": poc.get("notes") or "",
            "capabilities": list(poc.get("capabilities") or []),
            "poc_status": poc.get("status") or "",
            "effort_days": poc.get("effort_days"),
            "met": met,
            "total": total,
            "next": next_action(challenge),
        })
    rows.sort(key=lambda row: (STAGE_KEYS.index(row["stage"]), -row["score"]))
    return rows
