"""Linking solutions to the challenges they solve.

Historically a solution pointed at its challenge by copying the title string,
so a typo or a trailing space silently orphaned contributed work. Records now
carry `challenge_id`; these helpers resolve the link, backfill it for older
records, and — importantly — let the UI *show* an unlinked solution rather
than dropping it on the floor.
"""

from __future__ import annotations

from typing import Any, Iterable

__all__ = [
    "normalize_title",
    "challenge_id_of",
    "backfill_challenge_ids",
    "resolve_challenge",
    "solutions_by_challenge",
]


def normalize_title(value: Any) -> str:
    """Whitespace- and case-insensitive form of a title, for legacy matching."""
    return " ".join(str(value or "").split()).lower()


def challenge_id_of(record: Any) -> str:
    if not isinstance(record, dict):
        return ""
    return str(record.get("id") or record.get("challenge_id") or "").strip()


def _title_index(submissions: Iterable[dict]) -> dict[str, dict]:
    index: dict[str, dict] = {}
    for submission in submissions:
        if not isinstance(submission, dict):
            continue
        key = normalize_title(submission.get("title"))
        if key and key not in index:
            index[key] = submission
    return index


def resolve_challenge(solution: dict, submissions: list[dict]) -> dict | None:
    """The challenge a solution belongs to, by id first and title second."""
    if not isinstance(solution, dict):
        return None
    wanted = str(solution.get("challenge_id") or "").strip()
    if wanted:
        for submission in submissions:
            if isinstance(submission, dict) and str(submission.get("id") or "").strip() == wanted:
                return submission
    return _title_index(submissions).get(normalize_title(solution.get("challenge")))


def backfill_challenge_ids(submissions: list[dict], solutions: list[dict]) -> bool:
    """Stamp `challenge_id` onto older solutions. Returns True if any changed.

    Only an exact whitespace/case-insensitive title match is accepted. A near
    miss is left unlinked on purpose — a wrong link is worse than a visible
    orphan, and the UI now surfaces orphans instead of hiding them.
    """
    index = _title_index(submissions)
    changed = False
    for solution in solutions:
        if not isinstance(solution, dict) or str(solution.get("challenge_id") or "").strip():
            continue
        match = index.get(normalize_title(solution.get("challenge")))
        match_id = str((match or {}).get("id") or "").strip()
        if match_id:
            solution["challenge_id"] = match_id
            changed = True
    return changed


def solutions_by_challenge(submissions: list[dict], solutions: list[dict]) -> dict[str, list[dict]]:
    """Map challenge id -> its solutions. Orphans collect under the "" key."""
    grouped: dict[str, list[dict]] = {}
    for solution in solutions:
        if not isinstance(solution, dict):
            continue
        match = resolve_challenge(solution, submissions)
        key = str((match or {}).get("id") or "").strip()
        grouped.setdefault(key, []).append(solution)
    return grouped
