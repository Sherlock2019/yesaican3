"""Analysis over everything submitted: what is moving, who is doing it, where it hurts.

Pure functions over the three stores the app already writes — submissions,
solutions and the agent library — plus the business-flow ontology for anything
that needs to know how units connect. Nothing here reads a file or touches
Streamlit, so every number on the dashboard is reproducible and testable.

The interesting question this answers is the last one: which painpoints reach
the most business units. A painpoint that costs one team 200 hours is worth
less than the same painpoint felt by five teams, and only the ontology can tell
you that — the submitter has no idea who else has it.
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Mapping

from services.shared import business_flow as bf

__all__ = [
    "overview",
    "most_active_people",
    "by_business_unit",
    "similar_pairs",
    "cross_department",
    "top_reach",
    "analyse",
]

_STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "have", "has", "our",
    "are", "was", "were", "not", "但", "into", "each", "every", "when", "then",
    "們", "all", "any", "can", "get", "got", "how", "its", "out", "too", "who",
    "why", "you", "your", "their", "them", "they", "there", "these", "those",
    "manual", "manually", "time", "need", "needs", "want", "would", "could",
}
NEW_WINDOW_DAYS = 30


def _tokens(text: Any) -> set[str]:
    words = re.findall(r"[a-z]{3,}", str(text or "").lower())
    return {w for w in words if w not in _STOPWORDS}


def _created(record: Mapping[str, Any]) -> datetime | None:
    raw = str(record.get("created_at") or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _unit_of(record: Mapping[str, Any]) -> str:
    """Which unit a painpoint belongs to.

    The twin context is the answer when intake captured one. Falling back to the
    submitter's department matters: everything submitted before that field
    existed would otherwise vanish from every per-unit count.
    """
    context = record.get("twin_context") or {}
    unit = str(context.get("business_unit") or "").strip()
    if unit:
        return unit
    department = str((record.get("submitter") or {}).get("department") or "").strip()
    return department or "Unassigned"


def _solved_ids(solutions: Iterable[Mapping[str, Any]]) -> set[str]:
    ids: set[str] = set()
    for solution in solutions:
        identifier = str(solution.get("challenge_id") or "").strip()
        if identifier:
            ids.add(identifier)
    return ids


# --------------------------------------------------------------------------
# headline counts
# --------------------------------------------------------------------------

def overview(
    submissions: list[dict],
    solutions: list[dict],
    agents: list[dict],
    now: datetime | None = None,
) -> dict[str, Any]:
    """The numbers people ask for first."""
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=NEW_WINDOW_DAYS)
    solved = _solved_ids(solutions)

    fresh = 0
    for record in submissions:
        created = _created(record)
        if created and created >= cutoff:
            fresh += 1

    with_poc = [r for r in submissions if r.get("poc")]
    published = [r for r in submissions if r.get("published_agent")]
    from_painpoint = [a for a in agents if a.get("origin_challenge")]

    hours = sum(float((r.get("baseline") or {}).get("annual_hours") or 0) for r in submissions)
    solved_hours = sum(
        float((r.get("baseline") or {}).get("annual_hours") or 0)
        for r in submissions if str(r.get("id") or "") in solved
    )

    return {
        "painpoints_total": len(submissions),
        "painpoints_new": fresh,
        "painpoints_solved": sum(1 for r in submissions if str(r.get("id") or "") in solved),
        "painpoints_open": sum(1 for r in submissions if str(r.get("id") or "") not in solved),
        "cures_proposed": len(solutions),
        "pocs_current": len(with_poc),
        "pocs_proven": sum(
            1 for r in with_poc
            if (r.get("poc") or {}).get("acceptance")
            and all(c.get("met") for c in r["poc"]["acceptance"])
        ),
        "in_production_library": len(from_painpoint) or len(published),
        "agents_total": len(agents),
        "hours_on_the_board": hours,
        "hours_addressed": solved_hours,
    }


# --------------------------------------------------------------------------
# people and units
# --------------------------------------------------------------------------

def most_active_people(
    submissions: list[dict],
    solutions: list[dict],
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Who is doing the work — submitting painpoints and proposing cures.

    Both count. A community where the same few people do all the helping looks
    healthy on a submission count alone.
    """
    submitted: Counter[str] = Counter()
    helped: Counter[str] = Counter()

    for record in submissions:
        name = str((record.get("submitter") or {}).get("name") or "").strip()
        if name and name.lower() != "anonymous":
            submitted[name] += 1
    for solution in solutions:
        name = str(solution.get("helper") or solution.get("author") or "").strip()
        if name:
            helped[name] += 1

    people = sorted(set(submitted) | set(helped))
    rows = [
        {
            "name": name,
            "submitted": submitted.get(name, 0),
            "cures": helped.get(name, 0),
            "total": submitted.get(name, 0) + helped.get(name, 0),
        }
        for name in people
    ]
    rows.sort(key=lambda row: (-row["total"], row["name"]))
    return rows[:limit]


def by_business_unit(submissions: list[dict], limit: int = 10) -> list[dict[str, Any]]:
    """Painpoints and hours per unit, worst first."""
    counts: Counter[str] = Counter()
    hours: Counter[str] = Counter()
    for record in submissions:
        unit = _unit_of(record)
        counts[unit] += 1
        hours[unit] += float((record.get("baseline") or {}).get("annual_hours") or 0)

    rows = [
        {"unit": unit, "painpoints": count, "annual_hours": hours.get(unit, 0.0)}
        for unit, count in counts.items()
    ]
    rows.sort(key=lambda row: (-row["painpoints"], -row["annual_hours"], row["unit"]))
    return rows[:limit]


# --------------------------------------------------------------------------
# similarity and spread
# --------------------------------------------------------------------------

def similar_pairs(
    submissions: list[dict],
    limit: int = 10,
    threshold: float = 0.18,
) -> list[dict[str, Any]]:
    """Painpoints that look like each other — candidates for one shared fix.

    Jaccard over title+description tokens. Crude on purpose: the job is to
    surface pairs a human should look at, not to decide they are duplicates.
    Same pain type is a strong hint, so it lifts the score rather than being
    required — two teams often describe the same job in different words.
    """
    prepared = []
    for record in submissions:
        tokens = _tokens(f"{record.get('title', '')} {record.get('description', '')}")
        if tokens:
            prepared.append((record, tokens))

    pairs: list[dict[str, Any]] = []
    for i in range(len(prepared)):
        left, left_tokens = prepared[i]
        for j in range(i + 1, len(prepared)):
            right, right_tokens = prepared[j]
            union = left_tokens | right_tokens
            if not union:
                continue
            score = len(left_tokens & right_tokens) / len(union)
            if left.get("pain_type") and left.get("pain_type") == right.get("pain_type"):
                score += 0.15
            if score < threshold:
                continue
            pairs.append({
                "a": left.get("title") or "Untitled",
                "b": right.get("title") or "Untitled",
                "a_unit": _unit_of(left),
                "b_unit": _unit_of(right),
                "score": round(min(score, 1.0), 3),
                "same_type": left.get("pain_type") == right.get("pain_type"),
                "cross_unit": _unit_of(left) != _unit_of(right),
            })
    pairs.sort(key=lambda row: -row["score"])
    return pairs[:limit]


def _reach_units(record: Mapping[str, Any], by_type: Mapping[str, set[str]]) -> set[str]:
    """Every unit this painpoint plausibly touches.

    Three sources, and each is a different kind of evidence: the unit that
    submitted it, the two ends of the flow edge it sits on (the ontology's own
    answer), and any other unit that reported the same kind of pain.
    """
    units = {_unit_of(record)}

    context = record.get("twin_context") or {}
    edge = bf.edge(str(context.get("flow_edge") or "")) if context.get("flow_edge") else None
    if edge:
        for key in ("producer", "consumer"):
            found = bf.unit(str(edge.get(key)))
            if found:
                units.add(found["name"])
    destination = str(context.get("output_to") or "").strip()
    if destination and bf.unit(destination):
        units.add(bf.unit(destination)["name"])

    pain_type = str(record.get("pain_type") or "")
    units |= by_type.get(pain_type, set())
    return {u for u in units if u and u != "Unassigned"}


def cross_department(submissions: list[dict], limit: int = 10) -> list[dict[str, Any]]:
    """Painpoints felt in more than one unit, most-shared first."""
    return [row for row in top_reach(submissions, limit=len(submissions) or 1)
            if row["units"] > 1][:limit]


def top_reach(submissions: list[dict], limit: int = 10) -> list[dict[str, Any]]:
    """The painpoints that touch the most units — the ones worth fixing once.

    Ranked by unit reach first, then by hours: a problem five teams have beats
    a bigger one that only ever bothers a single team, because the fix ships to
    five inboxes.
    """
    by_type: dict[str, set[str]] = {}
    for record in submissions:
        pain_type = str(record.get("pain_type") or "")
        if pain_type:
            by_type.setdefault(pain_type, set()).add(_unit_of(record))

    rows = []
    for record in submissions:
        units = _reach_units(record, by_type)
        hours = float((record.get("baseline") or {}).get("annual_hours") or 0)
        rows.append({
            "title": record.get("title") or "Untitled",
            "unit": _unit_of(record),
            "pain_type": record.get("pain_type") or "—",
            "units": len(units),
            "unit_names": sorted(units),
            "annual_hours": hours,
            # Hours felt once, times the number of teams that feel it.
            "reach_hours": hours * max(1, len(units)),
            "score": int((record.get("opportunity") or {}).get("score") or 0),
        })
    rows.sort(key=lambda row: (-row["units"], -row["reach_hours"], row["title"]))
    return rows[:limit]


def analyse(
    submissions: list[dict],
    solutions: list[dict],
    agents: list[dict],
    now: datetime | None = None,
) -> dict[str, Any]:
    """Everything the dashboard's analysis button reports, in one call."""
    return {
        "overview": overview(submissions, solutions, agents, now=now),
        "people": most_active_people(submissions, solutions),
        "units": by_business_unit(submissions),
        "similar": similar_pairs(submissions),
        "cross_department": cross_department(submissions),
        "top_reach": top_reach(submissions, limit=10),
    }
