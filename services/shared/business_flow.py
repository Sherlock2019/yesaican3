"""The Business Flow Ontology: four layers, one rule.

    BU → performs Activity → produces Business Object
       → becomes input to another BU → triggers its next Activity

An org chart tells you who reports to whom, which is no help at all when the
question is "where does the work get stuck". This models the company as a value
chain instead: units own activities, activities emit objects, and an object
landing in another unit's inbox is what starts their next activity.

The payoff is the FlowEdge. Once a pain point is attached to an edge rather
than to a department, the questions that matter become countable — which
handoff is slow, which object gets reworked, which unit is a bottleneck for
everyone downstream. ``edge_load`` and ``bottlenecks`` do exactly that.

Two deliberate choices worth knowing about:

* The nine units keep the six already in the Digital Twin
  (``services/ui/utils/ontology_flow.BUSINESS_UNITS``) and add the three the
  flow genuinely needs — Legal & Commercial, Billing & Finance and Support.
  A generic SaaS value chain would have replaced the real names with textbook
  ones and quietly detached the model from the company it describes.
* Edges are seeded, not user-authored. Anyone can attach a pain point to an
  edge; proposing a *new* edge is a deliberate act, because an ontology that
  everyone can extend on the fly is one nobody can aggregate over.
"""

from __future__ import annotations

import re
from typing import Any, Iterable, Mapping

__all__ = [
    "BUSINESS_UNITS",
    "BUSINESS_OBJECTS",
    "FLOW_EDGES",
    "LAYERS",
    "CORE_RULE",
    "unit",
    "unit_names",
    "business_object",
    "object_names",
    "edge",
    "edge_id",
    "edges_from",
    "edges_into",
    "edge_between",
    "destination_names",
    "edge_choices",
    "edge_load",
    "bottlenecks",
    "chain_order",
    "all_edges",
    "register_extras",
    "validate_edge",
    "build_edge",
    "is_proposed",
    "is_edited",
    "canonical_id",
    "EDITABLE_FIELDS",
    "activity_names",
    "custom_activities",
    "validate_activity",
]

CORE_RULE = (
    "BU → performs Activity → produces Business Object "
    "→ becomes input to another BU → triggers its next Activity"
)

LAYERS: tuple[tuple[str, str, str], ...] = (
    ("Organization", "Who does the work", "Business Unit → Department → Team → Role"),
    ("Work", "What they do", "BU → Activity → Task → Pain Point → KPI"),
    ("Object", "What the work produces", "Object → schema → sensitivity → system of record"),
    ("Flow", "How it moves", "Producer BU → Output Object → Consumer BU → Triggered Activity"),
)


# --------------------------------------------------------------------------
# Layer 1 — Business units
# --------------------------------------------------------------------------
# ``twin`` names the matching unit in the Digital Twin, or None where this is a
# function the twin does not model yet. Keeping the link explicit means the two
# models can be reconciled instead of silently diverging.

BUSINESS_UNITS: list[dict[str, Any]] = [
    {
        "id": "marketing",
        "name": "Marketing",
        "twin": "Sales & Marketing",
        "owner": "Avery Chen",
        "activities": ["Run campaign", "Produce qualified lead", "Nurture prospect"],
        "kpis": ["MQL volume", "Cost per lead", "Campaign conversion"],
    },
    {
        "id": "sales",
        "name": "Sales",
        "twin": "Sales & Marketing",
        "owner": "Avery Chen",
        "activities": ["Qualify opportunity", "Create proposal", "Hand off to delivery"],
        "kpis": ["Pipeline coverage", "Win rate", "Time to proposal"],
    },
    {
        "id": "legal",
        "name": "Legal",
        "twin": None,
        "owner": "Unassigned",
        "activities": ["Review contract", "Issue contract", "Countersign"],
        "kpis": ["Contract cycle time", "Redline rounds", "Approval SLA"],
    },
    {
        "id": "billing",
        "name": "Billing",
        "twin": None,
        "owner": "Unassigned",
        "activities": ["Create invoice", "Issue invoice", "Apply credit note"],
        "kpis": ["Invoice error rate", "Rework per cycle", "Time to invoice"],
    },
    {
        "id": "finance",
        "name": "Finance",
        "twin": None,
        "owner": "Unassigned",
        "activities": ["Collect payment", "Reconcile ledger", "Chase overdue"],
        "kpis": ["Days sales outstanding", "Reconciliation breaks", "Collection rate"],
    },
    {
        "id": "service_delivery",
        "name": "Service Delivery",
        "twin": "Engineering & Delivery",
        "owner": "George Harrison",
        "activities": ["Provision service", "Confirm provisioning", "Release to production"],
        "kpis": ["Lead time", "Provisioning success rate", "Deployment frequency"],
    },
    {
        "id": "success",
        "name": "Customer Success",
        "twin": "Customer Success",
        "owner": "Nia Thompson",
        "activities": ["Onboard customer", "Drive adoption", "Raise support case",
                       "Renew account"],
        "kpis": ["Time to value", "Adoption rate", "Net revenue retention"],
    },
    {
        "id": "support",
        "name": "Support",
        "twin": "Operations / Cloud Services",
        "owner": "Kenji Yamamoto",
        "activities": ["Resolve issue", "Capture feedback", "Publish knowledge"],
        "kpis": ["First response time", "Resolution time", "Escalation rate"],
    },
    {
        "id": "product",
        "name": "Product",
        "twin": "Product & Solutions",
        "owner": "Mia Patel",
        "activities": ["Prioritize improvement", "Design solution", "Release feature"],
        "kpis": ["Prototype velocity", "Pattern reuse", "Feedback cycle time"],
    },
]


# --------------------------------------------------------------------------
# Layer 3 — Business objects
# --------------------------------------------------------------------------
# ``sensitivity`` and ``system_of_record`` are here because they decide what an
# agent is allowed to do with the object. A POC that touches a Restricted
# object needs a different guardrail from one that moves a Proposal around,
# and that has to be knowable before anyone starts building.

BUSINESS_OBJECTS: list[dict[str, Any]] = [
    {"id": "qualified_lead", "name": "Qualified Lead", "type": "Record",
     "sensitivity": "Internal", "system_of_record": "CRM"},
    {"id": "proposal", "name": "Proposal", "type": "Document",
     "sensitivity": "Confidential", "system_of_record": "CRM"},
    {"id": "contract", "name": "Contract", "type": "Document",
     "sensitivity": "Confidential", "system_of_record": "Contract vault"},
    {"id": "invoice", "name": "Invoice", "type": "Financial record",
     "sensitivity": "Restricted", "system_of_record": "Billing ledger"},
    {"id": "service_handoff", "name": "Service Handoff", "type": "Work order",
     "sensitivity": "Internal", "system_of_record": "Delivery board"},
    {"id": "provisioned_service", "name": "Provisioned Service", "type": "Configuration",
     "sensitivity": "Internal", "system_of_record": "Control plane"},
    {"id": "support_case", "name": "Support Case", "type": "Ticket",
     "sensitivity": "Confidential", "system_of_record": "Ticket system"},
    {"id": "feedback", "name": "Customer Feedback", "type": "Signal",
     "sensitivity": "Internal", "system_of_record": "Feedback store"},
]


# --------------------------------------------------------------------------
# Layer 4 — Flow edges: the spine of the whole model
# --------------------------------------------------------------------------

FLOW_EDGES: list[dict[str, Any]] = [
    {"producer": "marketing", "activity": "Produce qualified lead", "object": "qualified_lead",
     "consumer": "sales", "triggers": "Qualify opportunity"},
    {"producer": "sales", "activity": "Create proposal", "object": "proposal",
     "consumer": "legal", "triggers": "Review contract"},
    {"producer": "legal", "activity": "Issue contract", "object": "contract",
     "consumer": "billing", "triggers": "Create invoice"},
    {"producer": "billing", "activity": "Issue invoice", "object": "invoice",
     "consumer": "finance", "triggers": "Collect payment"},
    {"producer": "sales", "activity": "Hand off to delivery", "object": "service_handoff",
     "consumer": "service_delivery", "triggers": "Provision service"},
    {"producer": "service_delivery", "activity": "Confirm provisioning",
     "object": "provisioned_service",
     "consumer": "success", "triggers": "Onboard customer"},
    {"producer": "success", "activity": "Raise support case", "object": "support_case",
     "consumer": "support", "triggers": "Resolve issue"},
    {"producer": "support", "activity": "Capture feedback", "object": "feedback",
     "consumer": "product", "triggers": "Prioritize improvement"},
]

# The order the chain is drawn in: commercial front to back, then delivery,
# then the service side. Note the chain currently ends at Product — nothing
# carries a released improvement back to Marketing, so the loop is open.
chain_order: tuple[str, ...] = (
    "marketing", "sales", "legal", "billing", "finance",
    "service_delivery", "success", "support", "product",
)


# --------------------------------------------------------------------------
# Proposed extensions
# --------------------------------------------------------------------------
# Edges and objects people add through the flow builder. Held separately from
# the canonical seed and tagged ``proposed``, so a chain someone drew this
# morning is never silently mistaken for the modelled company — and so the two
# can be told apart in any aggregate.
#
# Storage belongs to the caller: this module stays free of file paths, and the
# UI registers what it loaded at the top of each run.

_EXTRA_EDGES: list[dict[str, Any]] = []
_EXTRA_OBJECTS: list[dict[str, Any]] = []
_OVERRIDES: dict[str, dict[str, Any]] = {}
# Workflows a unit added for itself, keyed by unit id. Kept apart from the
# seeded activities so "what did we ship with" is still answerable, and so a
# custom workflow can be removed without guessing which ones were original.
_EXTRA_ACTIVITIES: dict[str, list[str]] = {}

# Fields an edit may change. The canonical record is never mutated — an
# override is stored against its id and applied on read, so "reset to
# canonical" is a delete rather than a guess at what the original was.
EDITABLE_FIELDS = ("producer", "activity", "object", "consumer", "triggers")


def register_extras(
    edges: Iterable[Mapping[str, Any]] | None = None,
    objects: Iterable[Mapping[str, Any]] | None = None,
    overrides: Mapping[str, Mapping[str, Any]] | None = None,
    activities: Mapping[str, Iterable[str]] | None = None,
) -> None:
    """Replace the proposed/edited set. Called once per run, never appended to."""
    _EXTRA_EDGES[:] = [dict(record) for record in (edges or [])]
    _EXTRA_OBJECTS[:] = [dict(record) for record in (objects or [])]
    _OVERRIDES.clear()
    for key, patch in (overrides or {}).items():
        _OVERRIDES[str(key)] = dict(patch)
    _EXTRA_ACTIVITIES.clear()
    for key, names in (activities or {}).items():
        _EXTRA_ACTIVITIES[str(key)] = [str(name) for name in names]


def canonical_id(record: Mapping[str, Any]) -> str:
    """The id an edge had before anyone edited it — the key overrides use."""
    return str(record.get("canonical_id") or edge_id(record))


def all_edges() -> list[dict[str, Any]]:
    """The chain as it stands: canonical, with edits applied, plus additions."""
    edges: list[dict[str, Any]] = []
    for record in FLOW_EDGES:
        base = edge_id(record)
        patch = _OVERRIDES.get(base)
        if not patch:
            edges.append(dict(record))
            continue
        edited = dict(record)
        edited.update({k: v for k, v in patch.items() if k in EDITABLE_FIELDS})
        edited["origin"] = "edited"
        edited["canonical_id"] = base
        edges.append(edited)
    edges.extend(dict(record) for record in _EXTRA_EDGES)
    return edges


def is_edited(record: Mapping[str, Any]) -> bool:
    return str(record.get("origin") or "") == "edited"


def _all_objects() -> list[dict[str, Any]]:
    return list(BUSINESS_OBJECTS) + list(_EXTRA_OBJECTS)


def is_proposed(record: Mapping[str, Any]) -> bool:
    return str(record.get("origin") or "canonical") == "proposed"


# --------------------------------------------------------------------------
# Lookups
# --------------------------------------------------------------------------

def unit(key: str) -> dict[str, Any] | None:
    """A unit by id or by display name — callers have whichever is to hand."""
    target = str(key or "").strip()
    return next(
        (u for u in BUSINESS_UNITS if u["id"] == target or u["name"] == target),
        None,
    )


def unit_names() -> list[str]:
    return [u["name"] for u in BUSINESS_UNITS]


def destination_names(extra: Iterable[str] = ()) -> list[str]:
    """Everywhere work can go: the value-chain units, then the wider org.

    The chain models the commercial flow, but plenty of work is handed to a
    department that is not on it — governance, operations, an external party.
    Offering only the nine chain units would push all of that into free text,
    where it stops being countable at all.
    """
    names = unit_names()
    for name in extra:
        cleaned = str(name).strip()
        if cleaned and cleaned not in names:
            names.append(cleaned)
    return names


def business_object(key: str) -> dict[str, Any] | None:
    target = str(key or "").strip()
    return next(
        (o for o in _all_objects() if o["id"] == target or o["name"] == target),
        None,
    )


def object_names() -> list[str]:
    return [o["name"] for o in _all_objects()]


def activity_names(unit_key: str = "") -> list[str]:
    """Workflows a unit owns: the seeded ones, then any it added for itself.

    These are the only values "My task workflow" offers, so a task recorded
    against a pain point is always one the ontology knows about and can count.
    """
    if unit_key:
        found = unit(unit_key)
        if not found:
            return []
        names = list(found.get("activities") or [])
        for extra in _EXTRA_ACTIVITIES.get(found["id"], []):
            if extra not in names:
                names.append(extra)
        return names
    seen: list[str] = []
    for record in BUSINESS_UNITS:
        for activity in activity_names(record["id"]):
            if activity not in seen:
                seen.append(activity)
    return seen


def custom_activities(unit_key: str) -> list[str]:
    """Only the workflows this unit added — the removable ones."""
    found = unit(unit_key)
    return list(_EXTRA_ACTIVITIES.get((found or {}).get("id", ""), []))


def validate_activity(unit_key: str, name: str) -> str | None:
    """Why this workflow cannot be added to the unit, or None if it can."""
    found = unit(unit_key)
    if not found:
        return "Pick a business unit first."
    cleaned = " ".join(str(name or "").split())
    if not cleaned:
        return "Name the workflow."
    if len(cleaned) > 60:
        return "Keep the workflow name under 60 characters."
    # Case-insensitive, because "Create invoice" and "create invoice" as two
    # workflows would split every count that mentions either.
    for existing in activity_names(found["id"]):
        if existing.strip().lower() == cleaned.lower():
            return f"“{existing}” is already one of {found['name']}'s workflows."
    return None


def edge_id(record: Mapping[str, Any]) -> str:
    """Stable identifier for an edge — what a pain point actually attaches to."""
    return f"{record.get('producer')}>{record.get('object')}>{record.get('consumer')}"


def edge(identifier: str) -> dict[str, Any] | None:
    return next((e for e in all_edges() if edge_id(e) == identifier), None)


def edges_from(unit_key: str) -> list[dict[str, Any]]:
    """What this unit hands onward."""
    found = unit(unit_key)
    return [e for e in all_edges() if found and e["producer"] == found["id"]]


def edges_into(unit_key: str) -> list[dict[str, Any]]:
    """What lands in this unit's inbox."""
    found = unit(unit_key)
    return [e for e in all_edges() if found and e["consumer"] == found["id"]]


def edge_between(producer: str, consumer: str) -> dict[str, Any] | None:
    """The handoff from one unit to another, if the chain has one.

    Lets intake ask the plain question — where does your output go? — and
    recover the modelled edge behind the answer, instead of making somebody
    pick a handoff by name. No edge is a real answer: it means the work leaves
    the chain, and the pain point is still recorded, just not aggregated.
    """
    source, target = unit(producer), unit(consumer)
    if not source or not target:
        return None
    return next(
        (e for e in all_edges()
         if e["producer"] == source["id"] and e["consumer"] == target["id"]),
        None,
    )


def _label(record: Mapping[str, Any]) -> str:
    producer = unit(str(record.get("producer")))
    consumer = unit(str(record.get("consumer")))
    obj = business_object(str(record.get("object")))
    return (
        f"{producer['name'] if producer else record.get('producer')}"
        f"  →  {obj['name'] if obj else record.get('object')}  →  "
        f"{consumer['name'] if consumer else record.get('consumer')}"
    )


def edge_choices(unit_key: str = "") -> list[tuple[str, str]]:
    """``(edge_id, human label)`` pairs, narrowed to one unit when given.

    Both directions are offered: a pain point is just as often about the mess
    arriving in your inbox as about what you hand on.
    """
    if unit_key:
        records = edges_from(unit_key) + edges_into(unit_key)
    else:
        records = all_edges()
    seen: set[str] = set()
    choices: list[tuple[str, str]] = []
    for record in records:
        identifier = edge_id(record)
        if identifier in seen:
            continue
        seen.add(identifier)
        choices.append((identifier, _label(record)))
    return choices


# --------------------------------------------------------------------------
# Adding a flow
# --------------------------------------------------------------------------

def _object_slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(name or "").strip().lower()).strip("_")


def validate_edge(
    producer: str,
    object_name: str,
    consumer: str,
    triggers: str,
    editing: str = "",
) -> str | None:
    """Why this edge cannot be added, or None if it can.

    Every rule here exists because breaking it makes the aggregates lie:
    a self-loop is not a handoff, a duplicate splits one edge's pain across
    two rows, an activity the receiving unit does not own means the trigger
    never fires, and a near-duplicate object name ("Invoice" / "invoice")
    quietly halves every count that mentions it.
    """
    producer_unit, consumer_unit = unit(producer), unit(consumer)
    if not producer_unit:
        return "Pick the business unit the work comes from."
    if not consumer_unit:
        return "Pick the business unit that receives it."
    if producer_unit["id"] == consumer_unit["id"]:
        return (f"{producer_unit['name']} cannot hand work to itself — "
                "that is an activity inside the unit, not a flow between units.")

    name = str(object_name or "").strip()
    if not name:
        return "Name the business object that gets handed over."

    existing = business_object(name)
    if existing is None:
        clash = next(
            (o for o in _all_objects() if o["name"].strip().lower() == name.lower()),
            None,
        )
        if clash:
            return f"“{clash['name']}” already exists — pick it rather than adding a second spelling."

    if not str(triggers or "").strip():
        return "Pick the activity this triggers in the receiving unit."
    # activity_names, not the seeded list: a workflow a unit added for itself
    # is just as valid a trigger as one it shipped with.
    if triggers not in activity_names(consumer_unit["id"]):
        return (f"“{triggers}” is not something {consumer_unit['name']} does. "
                "The trigger has to be one of the receiving unit's own activities.")

    object_id = (existing or {}).get("id") or _object_slug(name)
    candidate = {"producer": producer_unit["id"], "object": object_id,
                 "consumer": consumer_unit["id"]}
    clash = edge(edge_id(candidate))
    # When editing, an edge colliding with itself is not a clash — it just
    # means the identity fields were left alone and only the trigger changed.
    if clash is not None and canonical_id(clash) != str(editing or ""):
        return "That handoff is already in the chain."
    return None


def build_edge(
    producer: str,
    object_name: str,
    consumer: str,
    triggers: str,
    activity: str = "",
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """The edge record, plus a new object record when one had to be created.

    Assumes ``validate_edge`` already passed. Returns the object as a separate
    value so the caller stores it alongside the edge — an edge referencing an
    object nobody saved would vanish from every lookup on the next run.
    """
    producer_unit = unit(producer) or {}
    consumer_unit = unit(consumer) or {}
    name = str(object_name).strip()
    existing = business_object(name)

    new_object: dict[str, Any] | None = None
    if existing is None:
        new_object = {
            "id": _object_slug(name),
            "name": name,
            "type": "Business object",
            # Conservative defaults: an unclassified object is treated as the
            # more restricted case until someone says otherwise.
            "sensitivity": "Internal",
            "system_of_record": "Unassigned",
            "origin": "proposed",
        }

    chosen_activity = str(activity or "").strip()
    if chosen_activity not in (producer_unit.get("activities") or []):
        chosen_activity = (producer_unit.get("activities") or ["Produces output"])[0]

    record = {
        "producer": producer_unit.get("id"),
        "activity": chosen_activity,
        "object": (existing or new_object or {}).get("id"),
        "consumer": consumer_unit.get("id"),
        "triggers": str(triggers).strip(),
        "origin": "proposed",
    }
    return record, new_object


# --------------------------------------------------------------------------
# The reason the model exists: counting pain against the flow
# --------------------------------------------------------------------------

def edge_load(challenges: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    """Aggregate submitted pain onto each flow edge.

    Returns one entry per edge that has any pain attached, carrying the count,
    the annual hours behind it and the titles — enough to answer "which handoff
    is costing us most" without opening a single submission.
    """
    load: dict[str, dict[str, Any]] = {}
    for challenge in challenges:
        context = challenge.get("twin_context") or {}
        identifier = str(context.get("flow_edge") or "").strip()
        if not identifier:
            continue
        record = edge(identifier)
        if record is None:
            continue
        entry = load.setdefault(identifier, {
            "edge": record,
            "label": _label(record),
            "count": 0,
            "annual_hours": 0.0,
            "titles": [],
        })
        entry["count"] += 1
        entry["annual_hours"] += float((challenge.get("baseline") or {}).get("annual_hours") or 0.0)
        title = str(challenge.get("title") or "").strip()
        if title:
            entry["titles"].append(title)
    return load


def bottlenecks(challenges: Iterable[Mapping[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    """Edges carrying the most pain, worst first.

    Sorted by hours rather than by count: three submissions worth twenty hours
    a year matter less than one worth two thousand, and ranking by count alone
    is how a loud team beats an expensive problem.
    """
    entries = list(edge_load(challenges).values())
    entries.sort(key=lambda item: (-item["annual_hours"], -item["count"], item["label"]))
    return entries[:limit]
