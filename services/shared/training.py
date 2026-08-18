"""Human training of agents, and whether one is ready to go to production.

Readiness here is derived, never declared. "Ready" is the answer to five
questions that each have a fact behind them — is there an owner, is there a
trainer, has training actually happened, did it measure well, did the POC's own
acceptance criteria pass — rather than a flag somebody set optimistically. The
unmet gates are returned with the score, because "62%" tells nobody what to do
next and "no owner, accuracy 71% against a 90% bar" does.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

__all__ = [
    "TRAINING_KINDS", "GATES", "BANDS", "DEFAULT_ACCURACY_TARGET",
    "latest_round", "measured_accuracy", "readiness", "suggest_trainers",
]

# What a human actually gives an agent. A short fixed list rather than free
# text, so six agents stuck waiting for the same thing are visible as such.
TRAINING_KINDS = [
    "Examples — show it what good looks like",
    "Corrections — fix what it got wrong",
    "Edge cases — the awkward ones it will meet",
    "Acceptance review — decide if the output is usable",
]

DEFAULT_ACCURACY_TARGET = 90.0

# (key, label, why it is a gate)
GATES: list[tuple[str, str]] = [
    ("owner", "Has an owner"),
    ("trainer", "Has at least one trainer"),
    ("trained", "Training has actually happened"),
    ("accuracy", "Measured accuracy meets the bar"),
    ("acceptance", "POC acceptance criteria pass"),
]

BANDS: list[tuple[float, str, str]] = [
    (100.0, "ready", "Ready for production"),
    (60.0, "training", "In training"),
    (0.0, "early", "Not started"),
]


def _rounds(record: Mapping[str, Any]) -> list[dict]:
    rounds = record.get("rounds")
    return [r for r in rounds if isinstance(r, Mapping)] if isinstance(rounds, list) else []


def latest_round(record: Mapping[str, Any]) -> dict | None:
    """The most recent training round, by recorded date."""
    rounds = _rounds(record)
    if not rounds:
        return None
    return sorted(rounds, key=lambda r: str(r.get("date") or ""))[-1]


def measured_accuracy(record: Mapping[str, Any]) -> float | None:
    """Accuracy from the latest round that recorded one.

    Rounds without a measurement are skipped rather than counted as zero: a
    session where somebody supplied examples but did not re-measure is not
    evidence that the agent got worse.
    """
    for entry in sorted(_rounds(record), key=lambda r: str(r.get("date") or ""), reverse=True):
        value = entry.get("accuracy")
        if value in (None, ""):
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _acceptance_met(poc: Mapping[str, Any] | None) -> bool | None:
    """True/False if the POC has criteria, None if there is no POC to judge."""
    if not isinstance(poc, Mapping):
        return None
    criteria = poc.get("acceptance")
    if not isinstance(criteria, list) or not criteria:
        return None
    return all(bool(c.get("met")) for c in criteria if isinstance(c, Mapping))


def readiness(
    record: Mapping[str, Any],
    poc: Mapping[str, Any] | None = None,
    accuracy_target: float = DEFAULT_ACCURACY_TARGET,
) -> dict[str, Any]:
    """Which production gates this agent passes, and what is blocking it."""
    trainers = record.get("trainers")
    trainers = [t for t in trainers if str(t).strip()] if isinstance(trainers, list) else []
    rounds = _rounds(record)
    accuracy = measured_accuracy(record)
    acceptance = _acceptance_met(poc)

    results: dict[str, dict[str, Any]] = {
        "owner": {
            "met": bool(str(record.get("owner") or "").strip()),
            "detail": str(record.get("owner") or "") or "nobody owns this yet",
        },
        "trainer": {
            "met": bool(trainers),
            "detail": f"{len(trainers)} signed up" if trainers else "no trainers yet",
        },
        "trained": {
            "met": bool(rounds),
            "detail": f"{len(rounds)} round(s) logged" if rounds else "no training logged",
        },
        "accuracy": {
            "met": accuracy is not None and accuracy >= accuracy_target,
            "detail": (f"{accuracy:.0f}% against a {accuracy_target:.0f}% bar"
                       if accuracy is not None else "never measured"),
        },
        "acceptance": {
            # No POC means nothing to pass, so this cannot be claimed as met.
            "met": bool(acceptance),
            "detail": ("all criteria pass" if acceptance
                       else "criteria not all met" if acceptance is False
                       else "no POC acceptance criteria recorded"),
        },
    }

    gates = [{"key": key, "label": label, **results[key]} for key, label in GATES]
    met = sum(1 for gate in gates if gate["met"])
    score = round(met / len(GATES) * 100.0, 1)

    band_key, band_label = "early", "Not started"
    for floor, key, label in BANDS:
        if score >= floor:
            band_key, band_label = key, label
            break

    return {
        "score": score,
        "gates_met": met,
        "gates_total": len(GATES),
        "band": band_key,
        "band_label": band_label,
        "gates": gates,
        "blockers": [gate["label"] for gate in gates if not gate["met"]],
        "accuracy": accuracy,
        "trainers": trainers,
        "rounds": len(rounds),
    }


def suggest_trainers(
    unit: str,
    submitter: str,
    humans: Iterable[Mapping[str, Any]],
    limit: int = 4,
) -> list[dict[str, str]]:
    """Who is worth asking to train this agent.

    The person who reported the painpoint is the domain expert for the agent
    that fixes it, so they lead; everyone else in that unit follows. Arriving
    with names beside each row is the difference between a page people use and
    a form people ignore.
    """
    unit_norm = str(unit or "").strip().lower()
    submitter_norm = str(submitter or "").strip().lower()

    suggestions: list[dict[str, str]] = []
    seen: set[str] = set()

    def add(person: Mapping[str, Any], why: str) -> None:
        name = str(person.get("name") or "").strip()
        if not name or name.lower() in seen:
            return
        seen.add(name.lower())
        suggestions.append({"name": name,
                            "department": str(person.get("department") or ""),
                            "why": why})

    people = [p for p in humans if isinstance(p, Mapping)]
    for person in people:
        if submitter_norm and str(person.get("name") or "").strip().lower() == submitter_norm:
            add(person, "reported the painpoint this fixes")
    for person in people:
        if unit_norm and str(person.get("department") or "").strip().lower() == unit_norm:
            add(person, f"works in {person.get('department')}")

    # Name the submitter even when they have no profile — they are still the
    # most obvious person to ask, and an unmatched name is more useful here
    # than a silently shorter list.
    if submitter_norm and submitter_norm not in seen and str(submitter or "").strip():
        suggestions.insert(0, {"name": str(submitter).strip(), "department": unit or "",
                               "why": "reported the painpoint this fixes"})

    return suggestions[:limit]
