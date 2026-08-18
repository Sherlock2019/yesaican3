"""Finding painpoints one agent could close, and cures worth reusing.

The naive question is "do these two painpoints read alike". It is the wrong one:
Billing says "invoice layout" and Finance says "reconciliation break" about jobs
that want the same fix, while two unrelated problems can share plenty of words.
Token overlap therefore misses exactly the pairs worth finding.

The question this module asks instead is **"would the same agent close both?"**,
which decomposes into a four-part signature the intake form already captures:

===============  ==========================================================
Input artifact   what arrives — a PDF, an export, a ticket, a dashboard query
Transformation   what is done to it — extract, convert, reconcile, route,
                 assemble, approve, search, summarise. This is the AI
                 capability, and it is the single strongest signal.
Destination      where the result goes — the ontology's flow object and the
                 consuming unit
Failure mode     what goes wrong — errors, waiting, repetition
===============  ==========================================================

Everything is a keyword lexicon over fields already on the record: deterministic,
testable and fast, in the same shape as ``pain_metrics.PAIN_TYPES``. Text overlap
survives only as a tie-breaker worth a tenth of the score. Swapping that one
component for embeddings (``embeddinggemma`` is the obvious local candidate) is
the natural next step and needs no other change here — but the structural
signals should stay lexical, because "was this a PDF" is a fact rather than a
judgement, and an embedding would only make it fuzzier and harder to test.
"""

from __future__ import annotations

import re
from typing import Any, Iterable, Mapping

__all__ = [
    "VERBS", "ARTIFACTS", "MATURITY", "BANDS",
    "signature", "score_painpoints", "similar_painpoints", "painpoint_pairs",
    "score_cures", "similar_cures", "band",
]

# --------------------------------------------------------------------------
# weights - they sum to 100 so a score reads as a percentage
# --------------------------------------------------------------------------

W_VERB = 30        # the capability being built
W_ARTIFACT = 20    # "PDF in" is a shared parser
W_PAIN_TYPE = 15   # already computed at intake
W_FLOW = 15        # the ontology edge - the signal nobody else's search has
W_TASK = 10        # twin_context.task
W_TEXT = 10        # tie-breaker only

# Two teams with the same problem in *different* units is worth more than two
# people in one unit: the first is a shared fix that ships twice, the second is
# a duplicate to merge. So a cross-unit match ranks higher, not merely flagged.
CROSS_UNIT_MULTIPLIER = 1.25

W_CAPABILITY = 35   # what the cure actually builds
W_PATTERN = 25      # does it serve the same signature
W_TOOLS = 20        # same stack
W_SURFACE = 10      # same source -> target systems
W_DIFFICULTY = 10

# Reuse value is similarity x maturity. Nobody wants to be pointed at a draft,
# so a shipped cure at 50% beats an unstarted one at 70%.
MATURITY: dict[str, float] = {
    "draft": 0.6,
    "idea": 0.6,
    "prototype": 0.8,
    "building": 0.9,
    "testing": 0.9,
    "mvp": 1.0,
    "live": 1.3,
    "in production": 1.3,
    "production": 1.3,
}
DEFAULT_MATURITY = 1.0

BANDS: list[tuple[float, str, str]] = [
    (70.0, "duplicate", "Likely the same problem - merge or co-sponsor"),
    (45.0, "pattern", "Same pattern, different context - one agent could serve both"),
    (25.0, "look", "Worth a look"),
]
MIN_SCORE = 25.0

# --------------------------------------------------------------------------
# lexicons
# --------------------------------------------------------------------------

VERBS: dict[str, dict[str, Any]] = {
    # Keywords are matched as substrings, so an inflected form whose stem is
    # already listed ("retyped" beside "retype") would score the same word
    # twice. Stems only — a test enforces this across the whole lexicon.
    "extract": {
        "label": "Extract fields from a document",
        "keywords": ["retype", "re-type", "re-key", "rekey", "keyed",
                     "key in", "transcribe", "extract", "read off", "data entry",
                     "copy the fields", "copy the terms", "type them into"],
    },
    "convert": {
        "label": "Convert between formats",
        "keywords": ["reformat", "convert", "different layout", "different format",
                     "own format", "template", "mapping", "restructure", "transform",
                     "rebuild it", "column names"],
    },
    "reconcile": {
        "label": "Match and reconcile records",
        "keywords": ["reconcile", "reconciliation", "tie out", "does not match",
                     "doesn't match", "discrepancy", "mismatch", "unmatched",
                     "difference came from", "breaks"],
    },
    "route": {
        "label": "Classify and route",
        "keywords": ["triage", "classify", "route", "categorise",
                     "categorize", "assign", "escalate", "prioritise", "prioritize"],
    },
    "assemble": {
        "label": "Assemble a view from many sources",
        "keywords": ["assemble", "aggregate", "compile", "collate", "consolidate",
                     "paste the metrics", "build the report", "roll up", "dashboards",
                     "trackers", "five tools", "across four", "side by side"],
    },
    "approve": {
        "label": "Move something through an approval gate",
        "keywords": ["approval", "approve", "sign-off", "signoff", "sign off",
                     "authorise", "authorize", "review cycle", "gate", "chase",
                     "waiting on"],
    },
    "search": {
        "label": "Find the current answer",
        "keywords": ["search", "look up", "lookup", "where is", "find out",
                     "who knows", "which version", "current version",
                     "version is current", "latest version", "say right now",
                     # "diff" alone also matches "difference" and "different",
                     # which belong to reconcile and convert respectively.
                     "diff the", "diffing"],
    },
    "summarise": {
        "label": "Summarise and theme free text",
        "keywords": ["summarise", "summarize", "read through", "tally", "themes",
                     "cluster", "sentiment", "label it"],
    },
}

ARTIFACTS: dict[str, dict[str, Any]] = {
    "document": {
        "label": "Document / PDF",
        "keywords": ["pdf", "scan", "contract", "form", "attachment", "paperwork",
                     "document", "spec sheet", "letter", "certificate", "redline",
                     "warranty"],
    },
    "export": {
        "label": "Export / spreadsheet",
        "keywords": ["export", "spreadsheet", "csv", "excel", "billing run",
                     "backlog", "statement", "extract file", "register"],
    },
    "ticket": {
        "label": "Ticket / case",
        "keywords": ["ticket", "case", "complaint", "helpdesk", "incident",
                     "support request"],
    },
    "record": {
        "label": "System of record",
        # "catalog" covers "catalogue" by substring, so only the stem is listed.
        "keywords": ["crm", "ledger", "cmdb", "catalog", "erp",
                     "system of record", "database", "asset register"],
    },
    "dashboard": {
        "label": "Dashboard / tracker",
        "keywords": ["dashboard", "tracker", "portal", "console", "report"],
    },
    "message": {
        # No bare "mail": it is a substring of "email", so every mention scored
        # twice and pulled records towards this class on one word.
        "label": "Email / chat thread",
        "keywords": ["email", "chat", "thread", "inbox", "slack"],
    },
    "feedback": {
        # No bare "review" either — it caught "review cycle" and read approval
        # chasing as customer feedback.
        "label": "Feedback / survey",
        "keywords": ["feedback", "survey", "nps", "voice of the customer",
                     "customer review"],
    },
}

_STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "have", "has", "our",
    "are", "was", "were", "not", "into", "each", "every", "when", "then", "all",
    "any", "can", "get", "got", "how", "its", "out", "too", "who", "why", "you",
    "your", "their", "them", "they", "there", "these", "those", "manual",
    "manually", "time", "need", "needs", "want", "would", "could", "then",
}


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------

def _text(value: Any) -> str:
    return f" {str(value or '').lower()} "


def _tokens(value: Any) -> set[str]:
    words = re.findall(r"[a-z]{3,}", str(value or "").lower())
    return {w for w in words if w not in _STOPWORDS}


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def _best(lexicon: Mapping[str, Mapping[str, Any]], haystack: str) -> str:
    """Highest-scoring lexicon key, or "" when nothing matches.

    Longer keywords win ties: "order form" is a better answer than "form".
    """
    best_key, best_score = "", 0.0
    for key, spec in lexicon.items():
        score = 0.0
        for word in spec["keywords"]:
            if word in haystack:
                score += 1.0 + len(word) / 100.0
        if score > best_score:
            best_key, best_score = key, score
    return best_key


def _context(record: Mapping[str, Any]) -> Mapping[str, Any]:
    value = record.get("twin_context")
    return value if isinstance(value, Mapping) else {}


def _unit_of(record: Mapping[str, Any]) -> str:
    unit = str(_context(record).get("business_unit") or "").strip()
    if unit:
        return unit
    submitter = record.get("submitter")
    if isinstance(submitter, Mapping):
        return str(submitter.get("department") or "").strip()
    return ""


def _norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


# --------------------------------------------------------------------------
# the signature
# --------------------------------------------------------------------------

def signature(record: Mapping[str, Any]) -> dict[str, str]:
    """The four-part answer to "what kind of job is this".

    Reads the whole record - title, description, workflow and twin context -
    because people describe the artifact in the form field and the verb in the
    prose, or the other way round.
    """
    context = _context(record)
    workflow = record.get("current_workflow")
    workflow_text = " ".join(str(s) for s in workflow) if isinstance(workflow, list) else ""

    prose = _text(f"{record.get('title', '')} {record.get('description', '')} {workflow_text}")
    # The declared input names the artifact far more reliably than the prose,
    # so it is weighted by being searched first and falling back second.
    artifact_text = _text(f"{context.get('input', '')} {context.get('input_from', '')}")

    verb = _best(VERBS, prose)
    artifact = _best(ARTIFACTS, artifact_text) or _best(ARTIFACTS, prose)

    outcomes = record.get("outcomes")
    failure = ", ".join(str(o) for o in outcomes) if isinstance(outcomes, list) else ""

    return {
        "verb": verb,
        "verb_label": VERBS.get(verb, {}).get("label", ""),
        "artifact": artifact,
        "artifact_label": ARTIFACTS.get(artifact, {}).get("label", ""),
        "destination": _norm(context.get("output_to")),
        "flow_object": _norm(context.get("flow_object")),
        "task": _norm(context.get("task")),
        "pain_type": _norm(record.get("pain_type")),
        "failure_mode": failure,
        "unit": _unit_of(record),
    }


def band(score: float) -> tuple[str, str]:
    """Which advice band a score falls in. Below the floor: ("", "")."""
    for floor, key, label in BANDS:
        if score >= floor:
            return key, label
    return "", ""


# --------------------------------------------------------------------------
# painpoint <-> painpoint
# --------------------------------------------------------------------------

def score_painpoints(left: Mapping[str, Any], right: Mapping[str, Any]) -> dict[str, Any]:
    """How alike two painpoints are, 0-100, with the reasons why.

    The reasons matter as much as the number: "same verb, same input, different
    unit" is actionable, while "68%" on its own is not.
    """
    a, b = signature(left), signature(right)
    score = 0.0
    reasons: list[str] = []

    if a["verb"] and a["verb"] == b["verb"]:
        score += W_VERB
        reasons.append(f"Same job: {a['verb_label'].lower()}")

    if a["artifact"] and a["artifact"] == b["artifact"]:
        score += W_ARTIFACT
        reasons.append(f"Same input: {a['artifact_label'].lower()}")

    if a["pain_type"] and a["pain_type"] == b["pain_type"]:
        score += W_PAIN_TYPE
        reasons.append("Same kind of pain")

    # The ontology's own answer to "do these meet". A shared business object is
    # a stronger claim than merely pointing at the same consuming unit.
    if a["flow_object"] and a["flow_object"] == b["flow_object"]:
        score += W_FLOW
        reasons.append(f"Same business object: {a['flow_object']}")
    elif a["destination"] and a["destination"] == b["destination"]:
        score += W_FLOW * 0.5
        reasons.append(f"Output goes to the same place: {a['destination']}")

    if a["task"] and a["task"] == b["task"]:
        score += W_TASK
        reasons.append(f"Same task: {a['task']}")

    text = _jaccard(
        _tokens(f"{left.get('title', '')} {left.get('description', '')}"),
        _tokens(f"{right.get('title', '')} {right.get('description', '')}"),
    )
    score += W_TEXT * text

    cross_unit = bool(a["unit"] and b["unit"] and a["unit"] != b["unit"])
    if cross_unit:
        score *= CROSS_UNIT_MULTIPLIER
        reasons.append(f"Felt in two units: {a['unit']} and {b['unit']}")

    score = round(min(score, 100.0), 1)

    # "Would one agent close both?" - the verb has to match, and the thing it
    # reads or the place it writes has to match too. Same verb on a different
    # artifact going somewhere else is a shared technique, not a shared build.
    reusable = bool(
        a["verb"] and a["verb"] == b["verb"]
        and ((a["artifact"] and a["artifact"] == b["artifact"])
             or (a["flow_object"] and a["flow_object"] == b["flow_object"])
             or (a["destination"] and a["destination"] == b["destination"]))
    )
    band_key, band_label = band(score)
    return {
        "score": score,
        "band": band_key,
        "band_label": band_label,
        "reasons": reasons,
        "cross_unit": cross_unit,
        "reusable": reusable,
        "same_verb": bool(a["verb"] and a["verb"] == b["verb"]),
        "text_overlap": round(text, 3),
    }


def similar_painpoints(
    target: Mapping[str, Any],
    candidates: Iterable[Mapping[str, Any]],
    limit: int = 5,
    min_score: float = MIN_SCORE,
) -> list[dict[str, Any]]:
    """The painpoints most like ``target``, best first.

    ``target`` need not be saved yet - this is what makes the check work on the
    submit form, where catching a duplicate is worth most.
    """
    target_id = str(target.get("id") or "")
    rows = []
    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            continue
        candidate_id = str(candidate.get("id") or "")
        if candidate_id and candidate_id == target_id:
            continue
        result = score_painpoints(target, candidate)
        if result["score"] < min_score:
            continue
        rows.append({
            "id": candidate_id,
            "title": str(candidate.get("title") or "Untitled"),
            "unit": _unit_of(candidate),
            "submitter": str((candidate.get("submitter") or {}).get("name") or "")
            if isinstance(candidate.get("submitter"), Mapping) else "",
            "record": candidate,
            **result,
        })
    rows.sort(key=lambda row: row["score"], reverse=True)
    return rows[:limit]


def painpoint_pairs(
    submissions: list[dict],
    limit: int = 10,
    min_score: float = MIN_SCORE,
) -> list[dict[str, Any]]:
    """Every similar pair across the board, best first - the dashboard view."""
    records = [r for r in submissions if isinstance(r, Mapping)]
    pairs: list[dict[str, Any]] = []
    for i in range(len(records)):
        for j in range(i + 1, len(records)):
            left, right = records[i], records[j]
            result = score_painpoints(left, right)
            if result["score"] < min_score:
                continue
            pairs.append({
                "a": str(left.get("title") or "Untitled"),
                "b": str(right.get("title") or "Untitled"),
                "a_id": str(left.get("id") or ""),
                "b_id": str(right.get("id") or ""),
                "a_unit": _unit_of(left),
                "b_unit": _unit_of(right),
                **result,
            })
    pairs.sort(key=lambda row: row["score"], reverse=True)
    return pairs[:limit]


# --------------------------------------------------------------------------
# cure <-> cure
# --------------------------------------------------------------------------

def _maturity(cure: Mapping[str, Any]) -> float:
    return MATURITY.get(_norm(cure.get("status")), DEFAULT_MATURITY)


def _cure_text(cure: Mapping[str, Any]) -> str:
    return " ".join(str(cure.get(key) or "") for key in
                    ("what_features", "how_components", "approach"))


def score_cures(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
    painpoints: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """How reusable ``right`` is for whoever is looking at ``left``.

    Deliberately asymmetric in spirit: the question is not "are these the same"
    but "could I reuse that one", which is why maturity scales the result. Pass
    ``painpoints`` keyed by id to let the pattern signal contribute.
    """
    score = 0.0
    reasons: list[str] = []

    capability = _jaccard(_tokens(_cure_text(left)), _tokens(_cure_text(right)))
    score += W_CAPABILITY * capability
    if capability >= 0.15:
        reasons.append("Builds much the same thing")

    tools = _jaccard(_tokens(left.get("ai_tools_used")), _tokens(right.get("ai_tools_used")))
    score += W_TOOLS * tools
    if tools >= 0.2:
        reasons.append("Same tools")

    if painpoints:
        left_pp = painpoints.get(str(left.get("challenge_id") or ""))
        right_pp = painpoints.get(str(right.get("challenge_id") or ""))
        if left_pp and right_pp:
            a, b = signature(left_pp), signature(right_pp)
            if a["verb"] and a["verb"] == b["verb"]:
                score += W_PATTERN * 0.6
                reasons.append(f"Serves the same job: {a['verb_label'].lower()}")
            if a["artifact"] and a["artifact"] == b["artifact"]:
                score += W_PATTERN * 0.4
                reasons.append(f"Same input: {a['artifact_label'].lower()}")
            # Same systems at both ends - the integration work transfers.
            if a["artifact"] and a["artifact"] == b["artifact"] \
                    and a["destination"] and a["destination"] == b["destination"]:
                score += W_SURFACE
                reasons.append("Same systems at both ends")

    if _norm(left.get("difficulty")) and _norm(left.get("difficulty")) == _norm(right.get("difficulty")):
        score += W_DIFFICULTY
        reasons.append(f"Similar effort ({_norm(left.get('difficulty'))})")

    maturity = _maturity(right)
    score = round(min(score * maturity, 100.0), 1)

    # Somebody agreeing with themselves is not a second opinion.
    same_author = bool(_norm(left.get("helper")) and
                       _norm(left.get("helper")) == _norm(right.get("helper")))
    band_key, band_label = band(score)
    return {
        "score": score,
        "band": band_key,
        "band_label": band_label,
        "reasons": reasons,
        "maturity": maturity,
        "status": str(right.get("status") or ""),
        "same_author": same_author,
    }


def similar_cures(
    target: Mapping[str, Any],
    candidates: Iterable[Mapping[str, Any]],
    painpoints: Mapping[str, Mapping[str, Any]] | None = None,
    limit: int = 5,
    min_score: float = MIN_SCORE,
    include_same_author: bool = False,
) -> list[dict[str, Any]]:
    """Cures worth reusing instead of rebuilding, best first."""
    target_id = str(target.get("id") or "")
    rows = []
    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            continue
        candidate_id = str(candidate.get("id") or "")
        if candidate_id and candidate_id == target_id:
            continue
        result = score_cures(target, candidate, painpoints)
        if result["score"] < min_score:
            continue
        if result["same_author"] and not include_same_author:
            continue
        rows.append({
            "id": candidate_id,
            "title": str(candidate.get("what_features") or candidate.get("challenge") or "Cure"),
            "challenge": str(candidate.get("challenge") or ""),
            "helper": str(candidate.get("helper") or candidate.get("author") or ""),
            "helper_department": str(candidate.get("helper_department") or ""),
            "record": candidate,
            **result,
        })
    rows.sort(key=lambda row: row["score"], reverse=True)
    return rows[:limit]
