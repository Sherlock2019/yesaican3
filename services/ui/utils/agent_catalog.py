"""Canonical agent catalog plus reuse matching.

Single source of truth for "which existing agents could serve this pain point".
Both the home-page matrix and the challenge intake form read from here, so a
challenge is never credited with reuse of an agent that does not exist.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

__all__ = [
    "DEFAULT_AGENT_CATALOG",
    "agent_profiles",
    "suggest_similar_agents",
]

_DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "agents.json"

# (sector, industry, name, description, status, emoji, requires_login, author, created_at, version)
DEFAULT_AGENT_CATALOG: list[tuple] = [
    (
        "Agent Factory",
        "🧩 Agent Builder",
        "🧩 Agent Builder",
        "Build custom agents by combining functions from HF and existing agents like LEGO blocks.",
        "Available",
        "🧩",
        True,
        "dzoan.nguyen@rackspace.com",
        "2025-11-27",
        "v1.0.0",
    ),
    (
        "Model Operations",
        "🤖 Hugging Face Tools",
        "🤖 HF Agent Wrapper",
        "Pure HuggingFace operations — Local HF models + HF API. Lightweight, HF-focused solution for all HF tasks.",
        "Available",
        "🤖",
        False,
        "dzoan.nguyen@rackspace.com",
        "2025-11-27",
        "v1.0.0",
    ),
    (
        "Executive Dashboards",
        "🚗 Boardroom Intelligence",
        "🚗 CEO driver DASHBOARD",
        "Real-time AI cockpit for CEOs to steer revenue, cash, ops, and market moves.",
        "Available",
        "🚗",
        False,
        "dzoan.nguyen@rackspace.com",
        "2025-11-27",
        "v1.0.0",
    ),
    (
        "Retail Banking Suite",
        "Retail Banking Suite",
        "💬 Chatbot Assistant",
        "Context-aware embedded assistant.",
        "Available",
        "💬",
        False,
        "dzoan.nguyen@rackspace.com",
        "2025-11-27",
        "v1.0.0",
    ),
    (
        "Support & Security",
        "🧠 Troubleshooting",
        "🧠 IT Troubleshooter Agent",
        "First-principles + case-memory incident solver.",
        "Available",
        "🧠",
        False,
        "dzoan.nguyen@rackspace.com",
        "2025-11-27",
        "v1.0.0",
    ),
]

# Extra vocabulary per agent, keyed by a distinctive fragment of the agent name.
# Descriptions alone are short, so these widen recall without inventing agents.
_AGENT_KEYWORDS: dict[str, set[str]] = {
    "agent builder": {"build", "prototype", "workflow", "automation", "custom", "compose", "template"},
    "hf agent wrapper": {"model", "huggingface", "inference", "embedding", "nlp", "summarize", "classify"},
    # Deliberately excludes "billing"/"invoice": a boardroom cockpit reports on
    # finance, it does not process invoices. Including them made the catalog
    # confidently recommend this agent for billing-conversion work.
    "ceo driver dashboard": {
        "dashboard", "executive", "revenue", "cash", "forecast", "kpi", "report",
        "metric", "cost", "spend", "finance", "boardroom",
    },
    "chatbot assistant": {"chat", "conversation", "faq", "support", "assistant", "onboarding", "question"},
    "it troubleshooter agent": {
        "ticket", "incident", "escalation", "support", "troubleshoot", "outage",
        "root", "cause", "log", "alert", "infra",
    },
}

_STOPWORDS = {
    "a", "an", "and", "any", "are", "as", "at", "be", "but", "by", "can", "could", "customer",
    "customers", "data", "do", "for", "from", "has", "have", "how", "in", "into", "is", "it",
    "its", "make", "more", "need", "needs", "of", "on", "or", "our", "so", "some", "system",
    "that", "the", "their", "them", "then", "there", "these", "they", "this", "to", "up", "use",
    "want", "was", "we", "what", "when", "which", "who", "will", "with", "would", "you", "your",
}


def _stem(word: str) -> str:
    """Crude singulariser so "tickets" and "ticket" count as the same term."""
    for suffix in ("ies", "es", "s"):
        if len(word) > 4 and word.endswith(suffix):
            return word[: -len(suffix)] + ("y" if suffix == "ies" else "")
    return word


def _tokenize(text: Any) -> set[str]:
    words = re.findall(r"[a-z]{3,}", str(text or "").lower())
    return {_stem(word) for word in words if word not in _STOPWORDS}


def _load_raw_catalog() -> list[dict]:
    """Agent records from data/agents.json, falling back to the built-in catalog."""
    if _DATA_PATH.exists():
        try:
            with open(_DATA_PATH, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, list) and data:
                return [entry for entry in data if isinstance(entry, dict)]
        except Exception:
            pass
    return [
        {"sector": row[0], "industry": row[1], "agent": row[2], "description": row[3], "status": row[4]}
        for row in DEFAULT_AGENT_CATALOG
    ]


def agent_profiles() -> list[dict]:
    """Matchable view of the catalog: display name, description, search tokens."""
    profiles: list[dict] = []
    for entry in _load_raw_catalog():
        name = str(entry.get("agent") or entry.get("name") or "").strip()
        if not name:
            continue
        description = str(entry.get("description") or "")
        # Strip leading emoji/punctuation so stored names stay readable.
        plain = re.sub(r"^[^\w]+", "", name).strip()
        tokens = _tokenize(f"{plain} {description} {entry.get('sector', '')} {entry.get('industry', '')}")
        for fragment, extra in _AGENT_KEYWORDS.items():
            if fragment in plain.lower():
                tokens |= extra
        profiles.append({"name": plain or name, "description": description, "tokens": tokens})
    return profiles


def suggest_similar_agents(
    text: str,
    limit: int = 3,
    profiles: Iterable[dict] | None = None,
) -> list[str]:
    """Existing agents whose vocabulary genuinely overlaps this pain point.

    Returns an empty list when nothing matches. That is the point: an empty
    result means "no reuse available", which is real information. A canned
    default here is what made every submission look like it shared a build.
    """
    query = _tokenize(text)
    if not query:
        return []
    scored: list[tuple[float, str]] = []
    for profile in profiles if profiles is not None else agent_profiles():
        tokens = profile.get("tokens") or set()
        if not tokens:
            continue
        overlap = query & tokens
        if len(overlap) < 2:
            # One shared word is coincidence, not reuse.
            continue
        scored.append((len(overlap) / (len(query) ** 0.5), profile["name"]))
    scored.sort(key=lambda pair: (-pair[0], pair[1]))
    return [name for _, name in scored[:limit]]
