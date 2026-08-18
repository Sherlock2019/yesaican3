from __future__ import annotations

import json
import hashlib
import html
import math
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, List

import streamlit as st

# Backward-compat: ensure experimental_rerun exists even on Streamlit versions where it was removed.
if not getattr(st, "experimental_rerun", None):
    st.experimental_rerun = getattr(st, "rerun", lambda: None)

from services.ui.utils.agent_catalog import suggest_similar_agents
from services.ui.utils.auth_gate import require_auth
from services.shared.records import carry_opportunity_fields
from services.ui.utils.challenge_link import backfill_challenge_ids
from services.shared.pain_metrics import (
    FREQUENCY_UNITS,
    OUTCOMES,
    WHO_AFFECTED,
    classify_pain_point,
    compute_opportunity,
    compute_pain,
    estimated_improvement,
    generate_workflow_steps,
    recommend_metrics,
    summarise_metrics,
)
from services.shared import business_flow as bf
from services.shared import similarity
from services.ui.utils import embed_flags
from services.ui.utils.app_shell import render_shell
from services.ui.utils.ontology_flow import business_unit_names as twin_unit_names
from services.ui.utils.pain_capture_ui import (
    CAPTURE_CSS,
    baseline_caption,
    baseline_label,
    business_flow_section,
    recommends_panel,
    ai_opportunity_card,
    current_workflow_card,
    feature_strip,
    how_it_works,
    improvement_card,
    intro_section,
    next_action_card,
    next_after_submission,
    numbered_cell,
    page_header,
    pain_summary_rail,
    section_heading,
    section_title,
    step_heading,
    twin_chain,
)
from services.ui.utils.meta_store import load_json, save_json
from services.ui.human_stack import HumanStack

SUBMISSIONS_FILE = "how_ai_help_submissions.json"
SOLUTIONS_FILE = "how_ai_help_solutions.json"
PROJECTS_FILE = "projects.json"
ASSET_DIR = Path(__file__).resolve().parents[2] / ".sandbox_meta" / "how_ai_help_assets"
ASSET_DIR.mkdir(parents=True, exist_ok=True)

HUMAN_STACK_PATH = Path(__file__).resolve().parents[2] / "data" / "human_stack.json"
HUMAN_STACK = HumanStack(str(HUMAN_STACK_PATH))

def rerun_app() -> None:
    """Use whichever rerun API Streamlit exposes in this version."""
    try:
        # Streamlit ≥ 1.30
        st.rerun()
    except AttributeError:
        try:
            # Fallback for older versions that still provide experimental_rerun
            st.rerun()
        except Exception:
            pass  # Silent fallback to avoid crashes

DEFAULT_SUBMISSIONS: List[dict] = []
DEFAULT_SOLUTIONS: List[dict] = []


def ensure_submission_id(submission: dict) -> str:
    if submission.get("id"):
        return str(submission["id"])
    submitter = submission.get("submitter", {})
    raw = (
        f"{submission.get('title', '')}|"
        f"{submitter.get('name', '')}|"
        f"{submitter.get('department', '')}|"
        f"{(submission.get('description') or '')[:80]}"
    )
    digest = hashlib.sha1(raw.encode("utf-8", "ignore")).hexdigest()[:10]
    anchor = f"challenge_{digest}"
    submission["id"] = anchor
    return anchor


def ensure_solution_id(solution: dict) -> str:
    if solution.get("id"):
        return str(solution["id"])
    raw = (
        f"{solution.get('challenge', '')}|"
        f"{solution.get('author', '')}|"
        f"{(solution.get('approach') or '')[:80]}"
    )
    digest = hashlib.sha1(raw.encode("utf-8", "ignore")).hexdigest()[:10]
    anchor = f"solution_{digest}"
    solution["id"] = anchor
    return anchor


def build_skill_query(submission: dict) -> str:
    if not submission:
        return ""
    skills = submission.get("skills_needed")
    if isinstance(skills, str):
        skills = [skills]
    if not skills:
        tags = submission.get("tags")
        if isinstance(tags, str):
            return tags
        if isinstance(tags, list):
            skills = tags
    fallback = []
    for field in ("category", "difficulty", "task_type", "description"):
        val = submission.get(field)
        if isinstance(val, list):
            fallback.extend(val)
        elif isinstance(val, str):
            fallback.append(val)
    if not skills and fallback:
        skills = fallback
    normalized = [str(item).strip() for item in (skills or []) if str(item).strip()]
    return " ".join(normalized)


def badge_html(label: str) -> str:
    style = (
        "display:inline-flex;padding:0.15rem 0.65rem;margin:0.1rem 0.25rem;"
        "border-radius:999px;background:rgba(59,130,246,0.13);color:#0f172a;"
        "font-size:0.78rem;font-weight:600;"
    )
    return f"<span style=\"{style}\">{html.escape(label)}</span>"


def display_human_stack_matches(matches: list[dict]) -> None:
    if not matches:
        st.info("No Rackers found for the requested skills yet.")
        return
    st.markdown("#### 👥 Rackers Who Can Help")
    col_count = min(len(matches), 3) or 1
    cols = st.columns(col_count)
    for idx, profile in enumerate(matches):
        with cols[idx % col_count]:
            skills = profile.get("skills", [])
            superpowers = profile.get("superpowers", [])
            project_summary = profile.get("projects_built", [])
            st.markdown(
                f"""
                <div style="border:1px solid rgba(15,23,42,0.1);border-radius:14px;padding:1rem;background:rgba(15,23,42,0.03);min-height:220px;">
                    <h4 style="margin-bottom:0.3rem;">{html.escape(profile.get('name','–'))}</h4>
                    <p style="margin:0.2rem 0;"><strong>Dept:</strong> {html.escape(profile.get('department','–'))}</p>
                    <p style="margin:0.2rem 0;"><strong>Region:</strong> {html.escape(profile.get('region','–'))}</p>
                    <div style="margin:0.35rem 0;">
                        {''.join(badge_html(skill) for skill in skills)}
                    </div>
                    <div style="margin:0.35rem 0;">
                        {''.join(badge_html(power) for power in superpowers)}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if project_summary:
                st.caption(f"Projects built: {len(project_summary)}")


def find_submission_by_identifier(submissions: List[dict], identifier: str | None, fallback_title: str | None = None) -> dict | None:
    target = (identifier or "").strip()
    fallback = (fallback_title or "").strip().lower() if fallback_title else ""
    for submission in submissions:
        submission_id = ensure_submission_id(submission)
        if target and submission_id == target:
            return submission
        if fallback and submission.get("title", "").strip().lower() == fallback:
            return submission
    return None


def find_solution_by_identifier(solutions: List[dict], identifier: str | None, fallback_challenge: str | None = None) -> dict | None:
    target = (identifier or "").strip()
    fallback = (fallback_challenge or "").strip().lower() if fallback_challenge else ""
    for idea in solutions:
        solution_id = ensure_solution_id(idea)
        if target and solution_id == target:
            return idea
        if fallback and idea.get("challenge", "").strip().lower() == fallback:
            return idea
    return None


def _get_query_params() -> dict[str, list[str]]:
    raw = st.query_params
    params: dict[str, list[str]] = {}
    try:
        items = raw.items()
    except AttributeError:
        items = raw.to_dict().items()
    for key, value in items:
        if isinstance(value, (list, tuple)):
            params[key] = list(value)
        else:
            params[key] = [value]
    return params


def _set_query_params(params: dict[str, list[str] | str]) -> None:
    st.query_params = params


def clear_query_params(*keys: str) -> None:
    params = _get_query_params()
    mutated = False
    for key in keys:
        if key in params:
            params.pop(key, None)
            mutated = True
    if mutated:
        _set_query_params(params)


def render_leaderboard_and_blueprint(submissions: list[dict]) -> None:
    total = len(submissions)
    top = sorted(submissions, key=lambda x: x.get("upvotes", 0), reverse=True)[:3]
    highlights = "".join(
        f"<li><strong>{html.escape(item.get('title','—'))}</strong> — 👍 {item.get('upvotes',0)} | ⚡ {item.get('urgency',0):.1f} | 🎯 {item.get('impact_score',0):.1f}</li>"
        for item in top
    )
    st.markdown(
        f"""
        <div class="neon-table" style="margin-top:1rem;">
            <div class="neon-table-title">🏆 Kaggle-Style Leaderboard Signals</div>
            <ul style="color:rgba(15,23,42,0.85);line-height:1.6;margin-bottom:1rem;">
                {highlights}
            </ul>
            <p style="color:rgba(15,23,42,0.8);">
                Total challenges: <strong>{total}</strong> • Auto-computed ranking blends upvotes, urgency, impact, and discussion velocity.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="neon-table" style="margin-top:1rem;">
            <div class="neon-table-title">🤖 AI Auto-Blueprint</div>
            <p>Each submission triggers an AI baseline that drafts the A→F agent workflow, required datasets, risk notes, suggested UI/API surface, and a timeline estimate.</p>
            <ul>
                <li>🔍 Auto-detect similar agents & reusable patterns.</li>
                <li>🪄 Generate “Convert to Project” payload with owners + version 0.1.</li>
                <li>👥 Tag suggested Ambassadors & SMEs directly from the Human Stack.</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_solution_detail_card(idea: dict) -> None:
    st.markdown(
        f"""
        <div class="neon-table" style="margin:1rem 0;">
            <div class="neon-table-title">🧩 {idea.get('challenge', 'Challenge')}</div>
            <p><strong>Author:</strong> {idea.get('author', 'Unknown')}</p>
            <p><strong>Approach:</strong> {idea.get('approach', '')}</p>
            <p><strong>Difficulty:</strong> {idea.get('difficulty', 'Medium')} • ⭐ {idea.get('upvotes', 0)} • 💬 {idea.get('comments', 0)}</p>
            <p><strong>Status:</strong> {idea.get('status', 'Draft')}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _load_records(name: str, default: List[dict]) -> List[dict]:
    data = load_json(name, default)
    if isinstance(data, dict):
        for key in ("items", "records", "data"):
            if key in data and isinstance(data[key], list):
                return data[key]
        return [data]
    return data or []


def load_submissions() -> List[dict]:
    return _load_records(SUBMISSIONS_FILE, DEFAULT_SUBMISSIONS)


def save_submissions(records: List[dict]) -> None:
    save_json(SUBMISSIONS_FILE, records)


def load_solutions() -> List[dict]:
    return _load_records(SOLUTIONS_FILE, DEFAULT_SOLUTIONS)


def save_solutions(records: List[dict]) -> None:
    save_json(SOLUTIONS_FILE, records)


def save_projects(records: List[dict]) -> None:
    save_json(PROJECTS_FILE, records)


def load_projects() -> List[dict]:
    data = load_json(PROJECTS_FILE, [])
    return data or []


def store_attachments(files, token: str) -> List[dict]:
    stored = []
    for uploaded in files or []:
        suffix = Path(uploaded.name).suffix or ""
        dest = ASSET_DIR / f"{token}_{uploaded.name}"
        with open(dest, "wb") as handle:
            handle.write(uploaded.getbuffer())
        stored.append({"name": uploaded.name, "path": str(dest), "type": suffix.lstrip(".")})
    return stored


def comma_tags(raw: str) -> List[str]:
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


_BASELINE_PROMPT = """You are an AI solutions architect reviewing an internal automation request.

Title: {title}
Business area: {category}
Submitter's difficulty estimate: {difficulty}
Description: {description}

Reply with ONLY a JSON object, no prose, using exactly these keys:
{{
  "summary": "one sentence describing what would actually be built",
  "workflow": ["4 to 6 concrete steps specific to THIS request"],
  "required_data": ["the actual data sources this needs"],
  "risks": ["2 to 4 risks specific to THIS request"],
  "complexity": "Low" | "Medium" | "High",
  "timeline": "an estimate such as 2-3 weeks",
  "why_ai": "one sentence on why AI suits this particular task"
}}"""


def _call_baseline_llm(prompt: str) -> str:
    """Best-effort local model call. Returns "" when no model is already running.

    Deliberately talks to Ollama over plain HTTP instead of using
    services.api.llm.ollama_client: that helper will spawn `ollama serve` and
    block for up to 20s (and can trigger a model pull) when nothing is
    listening. Someone submitting a form must never wait on that, so this
    probes first and gives up quietly if the server is not already there.
    Set YESAICAN_BASELINE_LLM=0 to skip the model entirely.
    """
    if os.getenv("YESAICAN_BASELINE_LLM", "1").strip().lower() in {"0", "false", "no", "off"}:
        return ""

    base = (os.getenv("OLLAMA_URL") or "http://localhost:11434").rstrip("/")
    model = os.getenv("YESAICAN_BASELINE_MODEL") or os.getenv("OLLAMA_MODEL") or "phi3:latest"
    try:
        timeout = float(os.getenv("YESAICAN_BASELINE_TIMEOUT", "25"))
    except ValueError:
        timeout = 25.0

    try:
        import requests

        # Cheap liveness probe — never autostart a server from a form submit.
        requests.get(f"{base}/api/tags", timeout=2).raise_for_status()
        response = requests.post(
            f"{base}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False, "options": {"temperature": 0.2}},
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, dict):
            return str(payload.get("response") or "").strip()
    except Exception:
        pass
    return ""


def _parse_baseline_json(raw: str) -> dict:
    """Pull the JSON object out of a model reply, tolerating fences and prose."""
    if not raw:
        return {}
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return {}
    try:
        parsed = json.loads(text[start : end + 1])
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _string_list(value, limit: int = 6) -> List[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    cleaned = [str(item).strip() for item in value if str(item).strip()]
    return cleaned[:limit]


def _heuristic_baseline(title: str, description: str, category: str, difficulty: str) -> dict:
    """Description-derived plan used when no local model answers.

    Deliberately reads the submission: two different pain points must not
    produce the same plan, or the baseline is worse than useless.
    """
    text = f"{title} {description}".lower()

    data_needs: List[str] = []
    signals = [
        (("invoice", "billing", "ledger", "payment"), ["ERP exports", "Invoice CSV", "Ledger snapshots"]),
        (("ticket", "incident", "escalation", "helpdesk"), ["ServiceNow / Zendesk exports"]),
        (("contract", "document", "pdf", "scan", "ocr"), ["Sample source documents"]),
        (("resume", "skill", "profile", "directory", "talent"), ["HR/People directory export"]),
        (("log", "metric", "telemetry", "capacity", "monitor"), ["Monitoring and log exports"]),
        (("customer", "renewal", "churn", "crm", "sales"), ["CRM records"]),
    ]
    for keywords, sources in signals:
        if any(word in text for word in keywords):
            data_needs.extend(sources)
    if not data_needs:
        data_needs = ["Team-provided sample data"]

    workflow = ["Clarify the current manual steps with the submitter"]
    if any(word in text for word in ("pdf", "document", "contract", "scan", "format", "ocr")):
        workflow.append("Parse source documents into a structured schema")
    if any(word in text for word in ("predict", "forecast", "risk", "score", "escalation")):
        workflow.append("Train and back-test a scoring model on historical records")
    if any(word in text for word in ("route", "categor", "classif", "triage", "tag")):
        workflow.append("Classify and route each item to the right queue")
    if any(word in text for word in ("directory", "search", "repository", "knows", "portfolio")):
        workflow.append("Index the records for semantic search and retrieval")
    workflow.append("Human review of AI output before it takes effect")
    workflow.append("Pilot with one team, measure hours saved, then widen")

    risks = ["Source data quality and completeness"]
    if any(word in text for word in ("customer", "billing", "invoice", "contract", "payment")):
        risks.append("Errors reaching customers or finance records")
    if any(word in text for word in ("resume", "profile", "personal", "hr", "people", "talent")):
        risks.append("Personal data handling and consent")
    if any(word in text for word in ("predict", "score", "risk", "churn")):
        risks.append("Model drift once behaviour changes")
    risks.append("Adoption — the manual path must actually be retired")

    words = len(description.split())
    declared = (difficulty or "").strip().lower()
    if declared in {"hard", "critical"} or words > 160:
        complexity, timeline = "High", "6-8 weeks"
    elif declared == "easy" and words < 60:
        complexity, timeline = "Low", "1-2 weeks"
    else:
        complexity, timeline = "Medium", "3-4 weeks"

    if any(word in text for word in ("repetitive", "manual", "every month", "each week", "copy")):
        why = "The work is repetitive and rule-shaped, which is where automation pays back fastest."
    elif any(word in text for word in ("predict", "forecast", "risk", "escalation")):
        why = "The signal is buried in historical records that a model can weigh far faster than a person."
    elif any(word in text for word in ("search", "directory", "knows", "repository")):
        why = "The value is in retrieval across scattered records, which is a natural fit for embeddings."
    else:
        why = f"AI can take the mechanical part of this {category.lower()} workflow and leave judgement to the team."

    return {
        "summary": f"Plan for: {title.strip() or 'this request'}",
        "workflow": workflow[:6],
        "required_data": list(dict.fromkeys(data_needs))[:5],
        "risks": risks[:4],
        "complexity": complexity,
        "timeline": timeline,
        "why_ai": why,
    }


def generate_ai_baseline(title: str, description: str, category: str, difficulty: str) -> dict:
    """Per-submission AI plan.

    Asks the local model first and falls back to a description-derived plan.
    Either way the result is specific to this submission, and `generated_by`
    records which path produced it so the UI never implies more than it has.
    """
    fallback = _heuristic_baseline(title, description, category, difficulty)
    baseline = dict(fallback)
    source = "heuristic"

    if description.strip():
        parsed = _parse_baseline_json(
            _call_baseline_llm(
                _BASELINE_PROMPT.format(
                    title=title.strip(),
                    category=category,
                    difficulty=difficulty,
                    description=description.strip()[:4000],
                )
            )
        )
        if parsed:
            for key in ("summary", "complexity", "timeline", "why_ai"):
                value = str(parsed.get(key, "")).strip()
                if value:
                    baseline[key] = value
            for key in ("workflow", "required_data", "risks"):
                values = _string_list(parsed.get(key))
                if values:
                    baseline[key] = values
            source = "llm"

    baseline["category"] = category
    baseline["generated_by"] = source
    # Reuse candidates come from the real agent catalog — an empty list means
    # nothing in the library fits, which is information the matrix relies on.
    baseline["similar_agents"] = suggest_similar_agents(f"{title} {description}")
    return baseline


def score_from_effort(people_affected: int, hours_each_per_week: float, impact_level: str) -> tuple[float, float]:
    """Turn two answerable questions into the impact and urgency scores.

    People are bad at rating abstract impact 1-10 and good at estimating how
    many colleagues a problem touches and how long it costs them. Hours lost
    per week across the group is the honest measure, mapped onto the existing
    0-10 scales so nothing downstream has to change.
    """
    people = max(1, int(people_affected or 1))
    hours = max(0.0, float(hours_each_per_week or 0.0))
    weekly_hours = people * hours

    # 1h/week ≈ 3.0, 10h ≈ 5.5, 100h ≈ 8.0, 400h+ ≈ 10. Log scale, because the
    # step from 1 to 10 hours matters far more than 400 to 410.
    if weekly_hours <= 0:
        impact = 2.0
    else:
        impact = 3.0 + 2.5 * math.log10(max(weekly_hours, 1.0))
    impact = round(min(10.0, max(1.0, impact)), 1)

    # Urgency leans on the submitter's own read, nudged by breadth of blast radius.
    urgency_base = {"low": 3.0, "medium": 5.5, "high": 7.5, "critical": 9.0}.get(
        (impact_level or "").strip().lower(), 5.5
    )
    urgency = round(min(10.0, urgency_base + min(1.5, math.log10(people) if people > 1 else 0.0)), 1)
    return impact, urgency


LEDGER_CSS = """
<style>
.pp-ledger { border:1px solid rgba(148,163,184,0.25); border-radius:14px; padding:0.9rem 1.1rem;
             background:rgba(15,23,42,0.5); margin:0.6rem 0 0.9rem; }
.pp-ledger h5 { color:#f8fafc; margin:0 0 0.15rem; font-size:1rem; }
.pp-ledger .cap { color:#94a3b8; font-size:0.82rem; margin:0 0 0.7rem; }
.pp-ledger table { width:100%; border-collapse:collapse; font-size:0.9rem; }
.pp-ledger th { text-align:left; font-size:0.66rem; letter-spacing:0.09em; text-transform:uppercase;
                color:#94a3b8; padding:0 0.7rem 0.4rem 0; border-bottom:1px solid rgba(148,163,184,0.25); }
.pp-ledger td { padding:0.42rem 0.7rem 0.42rem 0; border-bottom:1px solid rgba(148,163,184,0.12);
                color:#e2e8f0; font-variant-numeric:tabular-nums; }
.pp-ledger td.lbl { font-variant-numeric:normal; }
.pp-ledger td.actual { font-weight:650; }
.pp-ledger .win  { color:#86efac; }
.pp-ledger .miss { color:#fca5a5; }
.pp-ledger .pending { color:#64748b; }
</style>
"""

_NUM = re.compile(r"-?\d+(?:\.\d+)?")


def _ledger_number(value: Any) -> float | None:
    """First number in a display string like "45 min", "<9 min", ">98%"."""
    match = _NUM.search(str(value or ""))
    return float(match.group()) if match else None


def _ledger_verdict(row: dict) -> tuple[str, str]:
    """(css class, note) comparing ACTUAL against TARGET."""
    actual = _ledger_number(row.get("actual"))
    if actual is None:
        return "pending", "not measured yet"
    target = _ledger_number(row.get("target"))
    if target is None:
        return "", "recorded"
    lower_is_better = row.get("better", "lower") == "lower"
    hit = actual <= target if lower_is_better else actual >= target
    return ("win", "target met") if hit else ("miss", "short of target")


def render_metrics_ledger(submission: dict, submissions: List[dict]) -> None:
    """BEFORE → TARGET → ACTUAL for one pain point.

    The three columns are the point: BEFORE is the measured baseline, TARGET is
    what we hoped AI would do, ACTUAL is evidence after a POC. Keeping them
    apart is what stops a prediction from being quietly reported as a result.
    """
    metrics = submission.get("metrics")
    if not isinstance(metrics, list) or not metrics:
        return

    st.markdown(LEDGER_CSS, unsafe_allow_html=True)
    human = [row for row in metrics if row.get("group") != "technical"]
    technical = [row for row in metrics if row.get("group") == "technical"]

    def table(rows: List[dict]) -> str:
        body = []
        for row in rows:
            css, note = _ledger_verdict(row)
            actual = html.escape(str(row.get("actual") or "—"))
            body.append(
                f"<tr><td class='lbl'>{row.get('icon','•')} {html.escape(str(row.get('label','')))}</td>"
                f"<td>{html.escape(str(row.get('before','—')))}</td>"
                f"<td>{html.escape(str(row.get('target','—')))}</td>"
                f"<td class='actual {css}'>{actual}</td>"
                f"<td class='{css}'>{note}</td></tr>"
            )
        return ("<table><thead><tr><th>Metric</th><th>Before</th><th>Target</th>"
                "<th>Actual</th><th></th></tr></thead><tbody>" + "".join(body) + "</tbody></table>")

    measured = sum(1 for row in metrics if _ledger_number(row.get("actual")) is not None)
    st.markdown(
        f"<div class='pp-ledger'><h5>📐 Before → Target → Actual</h5>"
        f"<p class='cap'>{measured} of {len(metrics)} metrics have evidence recorded. "
        f"Targets are predictions until the Actual column is filled in.</p>"
        f"{table(human)}</div>",
        unsafe_allow_html=True,
    )
    if technical:
        with st.expander("🤖 AI / technical metrics"):
            st.markdown(f"<div class='pp-ledger'>{table(technical)}</div>", unsafe_allow_html=True)

    with st.expander("📊 Record measured results (after a POC or production run)"):
        st.caption("Enter what you actually observed. Leave blank for anything not measured yet.")
        with st.form(f"ledger_form_{submission.get('id')}"):
            entered: dict[str, str] = {}
            for row in metrics:
                entered[row["key"]] = st.text_input(
                    f"{row.get('icon','•')} {row.get('label','')} "
                    f"(before {row.get('before','—')} → target {row.get('target','—')})",
                    value="" if str(row.get("actual", "—")) == "—" else str(row.get("actual")),
                    key=f"actual_{submission.get('id')}_{row['key']}",
                    placeholder=row.get("unit") or "measured value",
                )
            if st.form_submit_button("Save measured results", use_container_width=True):
                for row in metrics:
                    value = entered.get(row["key"], "").strip()
                    row["actual"] = value or "—"
                submission["metrics"] = metrics
                submission["results_updated_at"] = datetime.utcnow().isoformat()
                save_submissions(submissions)
                st.success("Measured results saved.")
                rerun_app()


def add_comment(submission: dict, author: str, note: str) -> None:
    submission.setdefault("comments_thread", []).append(
        {
            "author": author or "Anonymous",
            "note": note,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )


def convert_to_project(submission: dict) -> None:
    projects = load_projects()
    submission_id = submission.get("id")
    for proj in projects:
        if proj.get("source_submission_id") == submission_id:
            st.info("Project already exists for this challenge.")
            return
    project_entry = {
        "title": submission.get("title"),
        "authors": [submission.get("submitter", {}).get("name", "Unknown")],
        "business_area": submission.get("category", "General"),
        "summary": submission.get("description", ""),
        "status": "Incubation",
        "created_at": datetime.utcnow().isoformat(),
        "upvotes": submission.get("upvotes", 0),
        "comments": submission.get("comments", 0),
        "source_submission_id": submission_id,
    }
    # Everything the intake measured travels with the project. Without this the
    # scoring is discarded at the exact moment it becomes useful.
    carry_opportunity_fields(submission, project_entry)
    projects.append(project_entry)
    save_projects(projects)
    st.success("Project created in Project Hub metadata.")


def render_connection_panel() -> None:
    st.markdown(
        """
        ### 🤝 Connection Teams & Slack Channels
        - `#yesaican-lab` — Core coordination hub
        - `#ai-ambassadors` — Ambassador cohort + office hours
        - `#rex-integrations` — Feed ideas into REX 2.0 crew
        - Teams Chat: **YESAICAN Innovation Ops**
        - Teams Chat: **Customer Zero Project Leads**
        """
    )


def upvote_submission(submission: dict, submissions: List[dict]) -> None:
    """Record community interest.

    An upvote must not touch `urgency`. Urgency is a business-priority signal
    that feeds the opportunity ranking; letting popularity edit it means a
    well-liked minor annoyance quietly outranks an expensive one nobody has
    seen. Interest is tracked as its own number and stays out of the V1 score.
    """
    submission["upvotes"] = submission.get("upvotes", 0) + 1
    submission["comments"] = submission.get("comments", 0)
    submission["community_interest"] = submission.get("community_interest", 0) + 1
    save_submissions(submissions)
    st.toast("Upvote recorded!", icon="👍")


def render_submission_card(
    submission: dict,
    submissions: List[dict],
    solutions: List[dict],
    active_target: str | None,
):
    submitter = submission.get("submitter", {})
    is_editing = st.session_state.get("editing_submission_id") == submission.get("id")
    st.markdown(
        f"""
        <div class="neon-table" style="margin-top:1rem;">
            <div class="neon-table-title">📝 {submission.get('title','Untitled')}</div>
            <p>{submission.get('description','')}</p>
            {f"<p><strong>Product Features:</strong> {submission.get('product_features','')}</p>" if submission.get('product_features') else ""}
            <p><strong>Submitter:</strong> {submitter.get('name','Unknown')} — {submitter.get('department','')} / {submitter.get('region','')}</p>
            <p><strong>Signals:</strong> 👍 {submission.get('upvotes',0)} • 💬 {submission.get('comments',0)} • ⚡ {submission.get('urgency',0):.1f} • 🎯 {submission.get('impact_score',0):.1f}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_metrics_ledger(submission, submissions)

    cols = st.columns(5)
    if cols[0].button("👍 Upvote", key=f"upvote_{submission['id']}"):
        upvote_submission(submission, submissions)
        rerun_app()
    if cols[1].button("🚀 Convert to Project", key=f"convert_{submission['id']}"):
        convert_to_project(submission)
    if cols[2].button("➕ Add Solution", key=f"solution_{submission['id']}"):
        st.session_state["active_solution_target"] = submission["title"]
        rerun_app()
    if cols[3].button("✏️ Edit", key=f"edit_{submission['id']}"):
        st.session_state["editing_submission_id"] = submission["id"]
        rerun_app()
    if cols[4].button("🗑️ Delete", key=f"delete_{submission['id']}"):
        submissions[:] = [s for s in submissions if ensure_submission_id(s) != submission["id"]]
        save_submissions(submissions)
        st.success("Challenge deleted.")
        rerun_app()

    if is_editing:
        with st.expander("✏️ Change problem description", expanded=True):
            with st.form(f"edit_submission_form_{submission['id']}"):
                title = st.text_input("Challenge Title", value=submission.get("title", ""))
                description = st.text_area("Problem / Goal Description", value=submission.get("description", ""))
                product_features = st.text_area("Product Features", value=submission.get("product_features", ""))
                c1, c2, c3 = st.columns(3)
                category = c1.text_input("Department / Category", value=submission.get("category", ""))
                difficulty = c2.selectbox(
                    "Difficulty",
                    ["Easy", "Medium", "Hard", "Critical"],
                    index=["Easy", "Medium", "Hard", "Critical"].index(submission.get("difficulty", "Medium")) if submission.get("difficulty") in ["Easy", "Medium", "Hard", "Critical"] else 1,
                )
                impact_level = c3.selectbox(
                    "Impact",
                    ["Low", "Medium", "High", "Critical"],
                    index=["Low", "Medium", "High", "Critical"].index(submission.get("impact_level", "Medium")) if submission.get("impact_level") in ["Low", "Medium", "High", "Critical"] else 1,
                )
                task_type = st.multiselect(
                    "Task Type",
                    ["Repetitive", "Document-heavy", "Data-heavy", "Customer-facing", "Workflow", "Governance"],
                    default=submission.get("task_type", []),
                )
                tags = st.text_input("Tags (comma separated)", value=", ".join(submission.get("tags", [])))
                col_save, col_cancel = st.columns(2)
                save_edit = col_save.form_submit_button("Save changes", use_container_width=True)
                cancel_edit = col_cancel.form_submit_button("Cancel", use_container_width=True)
                if save_edit:
                    submission["title"] = title
                    submission["description"] = description
                    submission["product_features"] = product_features
                    submission["category"] = category
                    submission["difficulty"] = difficulty
                    submission["impact_level"] = impact_level
                    submission["task_type"] = task_type
                    submission["tags"] = comma_tags(tags)
                    save_submissions(submissions)
                    st.session_state.pop("editing_submission_id", None)
                    st.success("Challenge updated.")
                    rerun_app()
                if cancel_edit:
                    st.session_state.pop("editing_submission_id", None)
                    rerun_app()

    skill_query = build_skill_query(submission)
    if skill_query:
        if st.button("Find Rackers Who Can Help", key=f"find_rackers_{submission['id']}"):
            matches = HUMAN_STACK.search_people(skill_query)
            st.session_state["human_stack_matches_id"] = submission.get("id")
            st.session_state["human_stack_matches"] = matches
            rerun_app()

    with st.expander("🤖 AI Baseline"):
        baseline = submission.get("ai_baseline", {})
        st.json(baseline)

    with st.expander("💬 Discussion"):
        comments_thread = submission.get("comments_thread", [])
        if comments_thread:
            for comment in comments_thread:
                st.markdown(f"*{comment.get('author')}* — {comment.get('timestamp')}\n\n{comment.get('note')}")
        else:
            st.info("No comments yet.")
        author = st.text_input("Your name", key=f"comment_author_{submission['id']}")
        note = st.text_area("Add a comment", key=f"comment_note_{submission['id']}")
        if st.button("Submit Comment", key=f"submit_comment_{submission['id']}"):
            if note.strip():
                add_comment(submission, author, note)
                save_submissions(submissions)
                st.success("Comment added")
                rerun_app()
            else:
                st.warning("Please enter a comment before submitting.")

    current_matches_id = st.session_state.get("human_stack_matches_id")
    current_matches = st.session_state.get("human_stack_matches", [])
    if current_matches_id == submission.get("id"):
        display_human_stack_matches(current_matches)


_PP_DEFAULTS = {
    "pp_text": "",
    "pp_type": "repetitive",
    "pp_type_label": "Repetitive manual work",
    "pp_title": "",
    "pp_workflow": [],
    "pp_workflow_source": "",
    "pp_analyzed": False,
    # Where the task sits in the digital twin.
    "pp_bu": "",
    "pp_task": "",
    "pp_input": "",
    "pp_output_to": "",
    # How many numbered rows the two list inputs are showing.
    "pp_point_rows": 3,
    "pp_step_rows": 5,
}

PAINPOINT_PLACEHOLDERS = (
    "Every month I reformat customer billing files by hand",
    "The same figures get re-keyed into two systems",
    "Nobody can tell which version is current",
)


# Only the numbered cells — pp_point_0, pp_wf_3. A plain prefix match also
# caught pp_point_rows, the row counter, and blanking that made the next run
# raise on int("").
_LIST_CELL_KEY = re.compile(r"^pp_(?:point|wf)_\d+$")


def _list_widget_keys() -> list[str]:
    """Session keys backing the numbered painpoint and step inputs."""
    return [key for key in list(st.session_state) if _LIST_CELL_KEY.match(key)]


def _pp_state() -> None:
    """Seed defaults and apply anything staged for this run.

    Both deferred blocks below exist for the same reason: Streamlit refuses an
    assignment to a widget-backed session key once that widget has been drawn,
    and both a reset and an auto-drafted workflow are decided *after* the form
    is on screen. Applying them here — before a single widget exists — is what
    makes "submit without pressing Analyze first" work instead of raising.
    """
    if st.session_state.pop("pp_reset_pending", False):
        for key, value in _PP_DEFAULTS.items():
            st.session_state[key] = list(value) if isinstance(value, list) else value
        for key in _list_widget_keys():
            st.session_state[key] = ""
        for key in ("pp_task_pick", "pp_input_pick", "pp_output_pick",
                    "pp_task_custom", "pp_input_custom", "pp_output_custom"):
            st.session_state.pop(key, None)

    for key, value in _PP_DEFAULTS.items():
        st.session_state.setdefault(key, list(value) if isinstance(value, list) else value)

    pending = st.session_state.pop("pp_workflow_pending", None)
    if pending is not None:
        st.session_state["pp_workflow"] = list(pending)
        st.session_state["pp_step_rows"] = max(len(pending), 5)
        for index in range(int(st.session_state["pp_step_rows"])):
            st.session_state[f"pp_wf_{index}"] = pending[index] if index < len(pending) else ""


def _pp_reset() -> None:
    """Ask for a clean form on the next run — see _pp_state for why deferred."""
    st.session_state["pp_reset_pending"] = True


_TITLE_PROMPT = """Name this internal work problem in 2-4 words, like a project name.

Problem: {text}

Reply with ONLY the name. No quotes, no punctuation, no explanation.
Good: Custom Billing Conversion
Bad: A system to convert billing"""

# Scene-setting openers that carry no meaning in a title.
_TITLE_NOISE = re.compile(
    r"^(?:every\s+\w+|each\s+\w+|currently|today|right\s+now|at\s+the\s+moment|"
    r"i|we|our|my|the\s+team)\s+", re.IGNORECASE
)
_TITLE_VERBS = re.compile(r"^(?:have\s+to\s+|need\s+to\s+|has\s+to\s+|manually\s+|spend\s+\w+\s+)", re.IGNORECASE)


def _pp_title_from(text: str, use_llm: bool = True) -> str:
    """A short, name-like title for a pain point."""
    cleaned = " ".join(str(text or "").split())
    if not cleaned:
        return "Untitled pain point"

    if use_llm:
        raw = _call_baseline_llm(_TITLE_PROMPT.format(text=cleaned[:600]))
        candidate = " ".join(str(raw or "").strip().strip('"\'`.').split())
        candidate = candidate.splitlines()[0].strip() if candidate else ""
        if 0 < len(candidate.split()) <= 6 and len(candidate) <= 60:
            return candidate.title() if candidate.islower() else candidate

    first = re.split(r"[.;\n]", cleaned)[0].strip()
    for _ in range(3):
        trimmed = _TITLE_VERBS.sub("", _TITLE_NOISE.sub("", first)).strip()
        if trimmed == first:
            break
        first = trimmed
    words = first.split()
    return (" ".join(words[:6]) + ("…" if len(words) > 6 else "")).strip() or cleaned[:60]


def _fill_step_cells(steps: List[str]) -> None:
    """Stage a workflow for the numbered step inputs of step 2.

    Staged rather than written: Streamlit ignores a widget's ``value`` once its
    key exists, so the cells do have to be assigned — but assigning them in a
    run that already drew them raises. _pp_state applies this on the next run,
    before any widget exists.
    """
    st.session_state["pp_workflow"] = list(steps)
    st.session_state["pp_workflow_pending"] = list(steps)


def _pp_analyze(text: str) -> None:
    """Classify, name and draft the workflow for freshly written painpoints."""
    key, label = classify_pain_point(text)
    st.session_state["pp_type"] = key
    st.session_state["pp_type_label"] = label
    st.session_state["pp_title"] = _pp_title_from(text)
    steps_count = int(st.session_state.get("pp_steps", 5) or 5)
    generated, source = generate_workflow_steps(text, steps_count, key, llm_call=_call_baseline_llm)
    _fill_step_cells(generated)
    st.session_state["pp_workflow_source"] = source
    st.session_state["pp_analyzed"] = True


def _twin_context() -> dict[str, str]:
    """The submitter's place in the business flow, read from session state.

    The flow edge is the anchor. Picking one fixes the consumer unit, the
    object handed over and the activity it triggers, so ``output_to`` and
    ``output_flow`` are derived rather than typed — the same three answers, one
    decision, and every submission lands on an edge the aggregates can count.
    """
    unit_name = str(st.session_state.get("pp_bu") or "")
    destination = str(st.session_state.get("pp_output_to") or "").strip()

    # The edge is recovered from the answer rather than asked for. When the
    # chain has no handoff between these two the pain point is still recorded
    # in full — it just does not roll up into a value-chain bottleneck.
    record = bf.edge_between(unit_name, destination) if unit_name and destination else None

    identifier, object_name, output_flow = "", "", ""
    if record:
        identifier = bf.edge_id(record)
        object_name = (bf.business_object(record["object"]) or {}).get("name", "")
        output_flow = f"{object_name} → {record['triggers']}"

    return {
        "business_unit": unit_name,
        "task": str(st.session_state.get("pp_task") or ""),
        "input": str(st.session_state.get("pp_input") or ""),
        "input_from": str(st.session_state.get("pp_input") or ""),
        "flow_edge": identifier,
        "flow_object": object_name,
        "output_to": destination,
        "output_flow": output_flow,
    }


FLOW_EXTRAS_FILE = "business_flow_extras.json"


def load_flow_extras() -> dict:
    data = load_json(FLOW_EXTRAS_FILE, {})
    if not isinstance(data, dict):
        data = {}
    overrides = data.get("overrides")
    activities = data.get("activities")
    return {
        "edges": [e for e in data.get("edges", []) if isinstance(e, dict)],
        "objects": [o for o in data.get("objects", []) if isinstance(o, dict)],
        "overrides": overrides if isinstance(overrides, dict) else {},
        "activities": activities if isinstance(activities, dict) else {},
    }


def save_flow_extras(extras: dict) -> None:
    save_json(FLOW_EXTRAS_FILE, extras)


def render_flow_builder(extras: dict) -> None:
    """Edit any handoff in the chain, in place.

    Editing rather than only adding: the chain is seeded, so the common need is
    "this edge is not quite how we work" rather than "a whole handoff is
    missing". Every control is a picker over the model, and the trigger list is
    narrowed to the receiving unit's own activities — which is what keeps an
    edited edge countable alongside the untouched ones.

    Canonical records are never mutated. An edit is stored as an override
    against the original id, so reverting is a delete rather than a guess.
    """
    st.markdown(
        "<div class='pc-fb'><p class='pc-fb-t'>Interactive flow builder</p>"
        "<p class='pc-fb-s'>Pick a handoff and change it. Units, objects and trigger "
        "activities all come from the ontology. Changing the producer, object or "
        "consumer into a combination that does not exist yet adds it as a new "
        "flow, marked <b>proposed</b>.</p></div>",
        unsafe_allow_html=True)

    edges = bf.all_edges()
    choices = [bf.canonical_id(record) for record in edges]
    labels = {
        bf.canonical_id(record): (
            f"{(bf.unit(record['producer']) or {}).get('name', record['producer'])}"
            f"  →  {(bf.business_object(record['object']) or {}).get('name', record['object'])}"
            f"  →  {(bf.unit(record['consumer']) or {}).get('name', record['consumer'])}"
        )
        for record in edges
    }
    if st.session_state.get("fb_edge") not in choices:
        st.session_state["fb_edge"] = choices[0]

    st.markdown(baseline_label("🔀", "Flow to edit"), unsafe_allow_html=True)
    selected_id = st.selectbox("Flow", choices, key="fb_edge",
                               format_func=lambda i: labels.get(i, i),
                               label_visibility="collapsed")
    current = next((r for r in edges if bf.canonical_id(r) == selected_id), edges[0])

    units = bf.unit_names()
    objects = bf.object_names()
    NEW_OBJECT = "＋ New business object…"

    def _index(options: list, value, fallback: int = 0) -> int:
        return options.index(value) if value in options else fallback

    producer_name = (bf.unit(current["producer"]) or {}).get("name", units[0])
    consumer_name = (bf.unit(current["consumer"]) or {}).get("name", units[0])
    object_name_now = (bf.business_object(current["object"]) or {}).get("name", objects[0])

    c_from, c_obj, c_to, c_trig, c_btn = st.columns([1.1, 1.2, 1.1, 1.2, 0.85], gap="small")

    with c_from:
        st.markdown(baseline_label("🏢", "From business unit"), unsafe_allow_html=True)
        producer = st.selectbox("From", units, index=_index(units, producer_name),
                                key=f"fb_from_{selected_id}", label_visibility="collapsed")
    with c_obj:
        st.markdown(baseline_label("📦", "Output object"), unsafe_allow_html=True)
        options = objects + [NEW_OBJECT]
        chosen_object = st.selectbox("Object", options, index=_index(options, object_name_now),
                                     key=f"fb_object_{selected_id}",
                                     label_visibility="collapsed")
        if chosen_object == NEW_OBJECT:
            chosen_object = st.text_input("New object", key=f"fb_object_new_{selected_id}",
                                          placeholder="Renewal Notice",
                                          label_visibility="collapsed")
    with c_to:
        st.markdown(baseline_label("🏢", "To business unit"), unsafe_allow_html=True)
        consumer = st.selectbox("To", units, index=_index(units, consumer_name),
                                key=f"fb_to_{selected_id}", label_visibility="collapsed")
    with c_trig:
        # A trigger the consumer does not own is an activity that never fires.
        activities = bf.activity_names(consumer) or ["—"]
        st.markdown(baseline_label("⚡", "Triggers activity"), unsafe_allow_html=True)
        triggers = st.selectbox("Triggers", activities,
                                index=_index(activities, current.get("triggers")),
                                key=f"fb_triggers_{selected_id}",
                                label_visibility="collapsed")
    with c_btn:
        st.markdown("<div style='height:1.35rem'></div>", unsafe_allow_html=True)
        clicked = st.button("✎ Edit flow", key="fb_save", type="primary",
                            use_container_width=True)
        reverted = False
        if selected_id in extras.get("overrides", {}):
            reverted = st.button("Reset", key="fb_reset", use_container_width=True)

    if reverted:
        extras["overrides"].pop(selected_id, None)
        save_flow_extras(extras)
        st.session_state["pp_flow_flash"] = "Reset that handoff to the canonical chain."
        rerun_app()

    if clicked:
        problem = bf.validate_edge(producer, chosen_object, consumer, triggers,
                                   editing=selected_id)
        if problem:
            st.warning(problem)
        else:
            record, new_object = bf.build_edge(
                producer, chosen_object, consumer, triggers, current.get("activity", ""))
            if new_object:
                extras.setdefault("objects", []).append(new_object)

            if bf.is_proposed(current):
                # Editing an already-proposed edge rewrites it in place.
                extras["edges"] = [
                    record if bf.edge_id(e) == selected_id else e
                    for e in extras.get("edges", [])
                ]
                verb = "Updated"
            else:
                extras.setdefault("overrides", {})[selected_id] = {
                    field: record[field] for field in bf.EDITABLE_FIELDS
                }
                verb = "Edited"
            save_flow_extras(extras)
            st.session_state["pp_flow_flash"] = (
                f"{verb} **{producer} → {chosen_object} → {consumer}**, "
                f"triggering “{triggers}”."
            )
            rerun_app()


def render_business_flow(submissions: List[dict]) -> dict:
    """The ontology itself, with submitted pain counted onto each handoff.

    Returns the loaded extras so the sections below share one read of them
    rather than each loading the file again and racing each other's writes.
    """
    extras = load_flow_extras()
    bf.register_extras(extras["edges"], extras["objects"], extras["overrides"],
                       extras["activities"])

    flash = st.session_state.pop("pp_flow_flash", None)
    if flash:
        st.success(flash)

    load = bf.edge_load(submissions)
    edges = []
    for record in bf.all_edges():
        producer = bf.unit(record["producer"]) or {}
        consumer = bf.unit(record["consumer"]) or {}
        obj = bf.business_object(record["object"]) or {}
        edges.append({
            "id": bf.edge_id(record),
            "producer_name": producer.get("name", record["producer"]),
            "consumer_name": consumer.get("name", record["consumer"]),
            "object_name": obj.get("name", record["object"]),
            "activity": record["activity"],
            "triggers": record["triggers"],
            # Anything not straight from the seeded chain says so, so a handoff
            # somebody changed this morning is never read as the modelled one.
            "state": ("proposed" if bf.is_proposed(record)
                      else "edited" if bf.is_edited(record) else ""),
        })
    st.markdown(
        section_title(
            "🏢 My Company Workflows",
            "How work moves between business units — and where the pain sits on it. "
            "Pick the handoff your task feeds when you submit below."),
        unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown(
            business_flow_section(bf.LAYERS, bf.CORE_RULE, edges, load),
            unsafe_allow_html=True)
        render_flow_builder(extras)
    return extras


def render_twin_context(extras: dict) -> dict[str, str]:
    """The 'my task workflow' strip: business unit, task, input, downstream."""
    with st.container(border=True):
        st.markdown(
            "<div class='pc-step'><span class='pc-num' style='background:#0ea5e9'>🧬</span>"
            "<h3>My task workflow</h3></div>"
            "<p class='pc-sub'>Your task placed on the business flow, so a solution can be "
            "handed to the right unit and reused by anyone doing the same workflow.</p>",
            unsafe_allow_html=True)

        units = bf.unit_names()
        # Value-chain units first, then the wider org from the Digital Twin.
        destinations = bf.destination_names(twin_unit_names())
        CUSTOM = "＋ Something else…"
        col_bu, col_task, col_in, col_edge = st.columns([1.05, 1.15, 1.2, 1.2], gap="small")

        with col_bu:
            st.markdown(baseline_label("🏢", "My business unit"), unsafe_allow_html=True)
            st.selectbox("Business unit", [""] + units, key="pp_bu",
                         format_func=lambda name: name or "Select…",
                         label_visibility="collapsed")
        with col_task:
            # The predefined workflows this unit owns, so a task recorded here
            # is always one the ontology can count.
            unit_now = str(st.session_state.get("pp_bu") or "")
            workflows = bf.activity_names(unit_now)
            st.markdown(baseline_label("🎯", "My task workflow"), unsafe_allow_html=True)
            picked = st.selectbox("Task", [""] + workflows + [CUSTOM], key="pp_task_pick",
                                  format_func=lambda name: name or "Select a workflow…",
                                  label_visibility="collapsed")
            if picked == CUSTOM:
                st.session_state["pp_task"] = st.text_input(
                    "Custom task", value=str(st.session_state.get("pp_task") or ""),
                    key="pp_task_custom", placeholder="Reformat customer billing",
                    label_visibility="collapsed")
            else:
                st.session_state["pp_task"] = picked
        with col_in:
            # Every unit and department, not just the ones the chain says feed
            # this one: work arrives from all over, and narrowing the list
            # pushed everything else into free text where it stopped counting.
            st.markdown(baseline_label("📥", "My input comes from"), unsafe_allow_html=True)
            picked_in = st.selectbox(
                "Input", [""] + destinations + [CUSTOM], key="pp_input_pick",
                format_func=lambda name: name or "Select a business unit…",
                label_visibility="collapsed")
            if picked_in == CUSTOM:
                st.session_state["pp_input"] = st.text_input(
                    "Custom input", value=str(st.session_state.get("pp_input") or ""),
                    key="pp_input_custom", placeholder="A customer, a system, a supplier…",
                    label_visibility="collapsed")
            else:
                st.session_state["pp_input"] = picked_in
        with col_edge:
            # The plain question — where does your output go — rather than
            # asking somebody to name a handoff. The modelled edge is recovered
            # from the answer in _twin_context, so aggregation still works.
            st.markdown(baseline_label("📤", "My output flows to"), unsafe_allow_html=True)
            picked_out = st.selectbox(
                "Output to", [""] + destinations + [CUSTOM], key="pp_output_pick",
                format_func=lambda name: name or "Select a business unit…",
                label_visibility="collapsed",
                help="Where this task's output lands. When the value chain has a "
                     "handoff from your unit to that one, the pain point attaches "
                     "to it automatically.")
            if picked_out == CUSTOM:
                st.session_state["pp_output_to"] = st.text_input(
                    "Custom destination", value=str(st.session_state.get("pp_output_to") or ""),
                    key="pp_output_custom", placeholder="A customer, a regulator, nobody…",
                    label_visibility="collapsed")
            else:
                st.session_state["pp_output_to"] = picked_out

        context = _twin_context()
        st.markdown(twin_chain(context), unsafe_allow_html=True)
        if context.get("flow_edge"):
            st.markdown(
                f"<p class='pc-note' style='margin:.5rem 0 0'>🔀 Attached to the handoff "
                f"<b>{html.escape(context['flow_object'])}</b> → "
                f"<b>{html.escape(context['output_to'])}</b>, which triggers "
                f"“{html.escape(context['output_flow'].split('→')[-1].strip())}”.</p>",
                unsafe_allow_html=True)
        elif context.get("output_to"):
            st.markdown(
                f"<p class='pc-note' style='margin:.5rem 0 0'>ⓘ No modelled handoff from "
                f"<b>{html.escape(context['business_unit'] or 'your unit')}</b> to "
                f"<b>{html.escape(context['output_to'])}</b> — recorded, but it will not "
                f"count towards a value-chain bottleneck.</p>",
                unsafe_allow_html=True)
    return context


OUTCOME_SUBTITLES = {
    "save_time": "Finish faster",
    "fewer_steps": "Less repetitive work",
    "reduce_errors": "More accuracy",
    "improve_quality": "Better results",
    "reduce_cost": "Lower operating cost",
    "faster_response": "Response quicker",
    "increase_revenue": "Grow the business",
    "compliance": "Meet policies & rules",
    "avoid_repetition": "More meaningful work",
    "data_privacy": "Don't share sensitive data",
}


def render_pain_point_capture(submissions: List[dict], active: str = "how_can_ai_help") -> None:
    """Single-page pain-point capture, laid out to match bestui.png.

    Everything is visible at once and the summary rail plus AI preview
    recompute on every input change, so the person filling it in watches the
    size of their own problem while they describe it.

    ``active`` is the sidebar item to light up — the home page renders this
    same panel and wants Home highlighted, not Pain Points.
    """
    _pp_state()
    st.markdown(render_shell(active=active), unsafe_allow_html=True)
    st.markdown(CAPTURE_CSS, unsafe_allow_html=True)
    # Why / what / who first: a first-time visitor needs to know what they have
    # landed on before being asked what hurts.
    # how_it_works is rendered by intro_section, as its closing row.
    st.markdown(intro_section(), unsafe_allow_html=True)

    # The company's workflows come before the form: you pick the handoff your
    # task feeds while submitting, so the chain has to be on screen first.
    flow_extras = render_business_flow(submissions)

    st.markdown(page_header(), unsafe_allow_html=True)

    twin_context = render_twin_context(flow_extras)

    main, rail = st.columns([3.45, 1.0], gap="small")

    with main:
        # Step 3 carries ten outcome tiles plus the recommends panel, so it gets
        # the extra width; steps 1 and 2 hold far less.
        c1, c2, c3 = st.columns([1.0, 1.08, 1.5], gap="small")

        # ---------------------------------------------------------- step 1
        with c1:
            with st.container(border=True):
                st.markdown(
                    step_heading(1, "What are your painpoints?",
                                 "One line each. Add a row for every separate problem."),
                    unsafe_allow_html=True)
                st.markdown(
                    "<p class='pc-tip'>💡 Tip: Be specific. Focus on the problem, not the solution.</p>",
                    unsafe_allow_html=True)

                # Numbered rows rather than one free-text box: people rarely have
                # a single pain, and separate lines are what let the analyser and
                # the reader tell two problems apart instead of one long sentence.
                points: List[str] = []
                for index in range(int(st.session_state["pp_point_rows"])):
                    st.markdown(numbered_cell(index + 1), unsafe_allow_html=True)
                    value = st.text_input(
                        f"Painpoint {index + 1}", key=f"pp_point_{index}", max_chars=200,
                        # Rows past the worked examples get a neutral prompt —
                        # repeating the last example makes them look pre-filled.
                        placeholder=(PAINPOINT_PLACEHOLDERS[index]
                                     if index < len(PAINPOINT_PLACEHOLDERS)
                                     else "Another painpoint…"),
                        label_visibility="collapsed")
                    if str(value).strip():
                        points.append(str(value).strip())

                add_col, count_col = st.columns([1.5, 1], gap="small")
                if add_col.button("＋ Add painpoint", key="pp_add_point",
                                  use_container_width=True):
                    st.session_state["pp_point_rows"] += 1
                    rerun_app()
                count_col.markdown(
                    f"<p class='pc-note' style='text-align:right;margin-top:.55rem'>"
                    f"{len(points)} listed</p>", unsafe_allow_html=True)

                # Everything downstream — classification, title, scoring — reads
                # pp_text, so the numbered rows are joined into it rather than
                # threaded through every caller.
                st.session_state["pp_text"] = "\n".join(points)

                st.markdown(
                    "<div class='pc-eg'><p class='pc-eg-t'>Examples</p><ul>"
                    "<li>I spend hours copying data between systems.</li>"
                    "<li>It takes too long to create reports.</li>"
                    "<li>We manually review documents all day.</li>"
                    "</ul></div>", unsafe_allow_html=True)
                if st.button("✨  Analyze my painpoints", type="primary", use_container_width=True):
                    if not points:
                        st.warning("List at least one painpoint first.")
                    else:
                        with st.spinner("Reading your painpoints…"):
                            _pp_analyze(st.session_state["pp_text"])
                        rerun_app()

        # ---------------------------------------------------------- step 2
        with c2:
            with st.container(border=True):
                st.markdown(
                    step_heading(2, "How is it done today?", "Help us understand the baseline."),
                    unsafe_allow_html=True)
                # No nested bordered containers here: their padding squeezed the
                # sub-columns until the labels wrapped one character per line.
                b1, b2, b3 = st.columns(3, gap="small")
                with b1:
                    st.markdown(baseline_label("👣", "Steps"), unsafe_allow_html=True)
                    steps_count = st.number_input(
                        "Steps", min_value=1, max_value=200, value=14, step=1,
                        key="pp_steps", label_visibility="collapsed")
                    st.markdown(baseline_caption("to finish once"), unsafe_allow_html=True)
                with b2:
                    st.markdown(baseline_label("⏱", "Time"), unsafe_allow_html=True)
                    minutes = st.number_input(
                        "Minutes", min_value=0.5, max_value=2400.0, value=45.0, step=5.0,
                        key="pp_minutes", label_visibility="collapsed")
                    st.markdown(baseline_caption("minutes per task"), unsafe_allow_html=True)
                with b3:
                    st.markdown(baseline_label("🔁", "How often"), unsafe_allow_html=True)
                    freq = st.number_input(
                        "Frequency", min_value=1.0, max_value=1000000.0, value=250.0, step=1.0,
                        key="pp_freq", label_visibility="collapsed")
                    # Abbreviated for display only — the stored key stays
                    # "per month" so the scoring engine is unaffected. The full
                    # wording truncated to "p..." at this column width.
                    unit = st.selectbox(
                        "Unit", list(FREQUENCY_UNITS.keys()), index=2,
                        key="pp_freq_unit", label_visibility="collapsed",
                        format_func=lambda option: option.replace("per ", "/ "))
                who = st.session_state.get("pp_who", "My team")
                pain = compute_pain(steps_count, minutes, freq, unit, who)
                st.markdown(
                    f"<div class='pc-hint'>ⓘ Based on your input, you spend "
                    f"<b>~{pain['monthly_hours']:,.1f} human hours per month</b> on this task.</div>",
                    unsafe_allow_html=True)

                # The steps as the person actually does them. Analyse fills
                # these in as a draft; typing over a cell wins, because the
                # person doing the job knows their process better than we do.
                st.markdown(section_heading("Steps you do today"), unsafe_allow_html=True)
                workflow: List[str] = []
                drafted = list(st.session_state.get("pp_workflow") or [])
                rows = max(int(st.session_state["pp_step_rows"]), len(drafted))
                for index in range(rows):
                    default = drafted[index] if index < len(drafted) else ""
                    st.markdown(numbered_cell(index + 1), unsafe_allow_html=True)
                    value = st.text_input(
                        f"Step {index + 1}", value=default, key=f"pp_wf_{index}",
                        max_chars=120, placeholder="Open the billing template",
                        label_visibility="collapsed")
                    if str(value).strip():
                        workflow.append(str(value).strip())
                st.session_state["pp_workflow"] = workflow
                if workflow:
                    st.session_state["pp_workflow_source"] = "typed"

                if st.button("＋ Add step", key="pp_add_step", use_container_width=True):
                    st.session_state["pp_step_rows"] = rows + 1
                    rerun_app()

        # ---------------------------------------------------------- step 3
        with c3:
            with st.container(border=True):
                st.markdown(
                    step_heading(3, "Desired Outputs", "Select what matters most.", amber=True),
                    unsafe_allow_html=True)
                o_col, r_col = st.columns([1.75, 1])
                chosen: List[str] = []
                with o_col:
                    st.markdown(
                        "<p class='pc-note' style='margin:0 0 .3rem'>"
                        "Outcomes you care about <span style='color:#8b8ba7'>"
                        "(select all that apply)</span></p>",
                        unsafe_allow_html=True)
                    # A keyed container, not a bare <div class='pc-outcomes'>:
                    # Streamlit renders every element as a sibling, so an opening
                    # div emitted on its own is auto-closed and never actually
                    # wraps the checkboxes — the tile styling never reached them.
                    with st.container(key="pp_outcomes"):
                        # Two across, not three: three tiles in this column width
                        # wrapped the labels to one word per line.
                        grid = st.columns(2, gap="small")
                        for index, outcome in enumerate(OUTCOMES):
                            default = outcome["key"] in ("save_time", "fewer_steps", "reduce_errors")
                            label = (f"**{outcome['label']}**  \n"
                                     f"{OUTCOME_SUBTITLES.get(outcome['key'], '')}")
                            if grid[index % 2].checkbox(label, value=default,
                                                        key=f"pp_out_{outcome['key']}"):
                                chosen.append(outcome["key"])
                    st.button("＋ Add another outcome", use_container_width=True,
                              key="pp_add_outcome",
                              help="Tell us in the description if none of these fit.")

                metrics = recommend_metrics(st.session_state["pp_type"], chosen, pain)
                groups = summarise_metrics(metrics)
                with r_col:
                    st.markdown(
                        recommends_panel([r for r in groups["human"] if r["selected"]][:6]),
                        unsafe_allow_html=True)
                    with st.popover("Edit metrics", use_container_width=True):
                        st.caption("Untick anything you do not want tracked.")
                        for row in groups["human"]:
                            row["selected"] = st.checkbox(
                                f"{row['icon']} {row['label']} — target `{row['target']}`",
                                value=row["selected"], key=f"pp_m_{row['key']}")

    # ------------------------------------------------------------ the rail
    agents = suggest_similar_agents(
        f"{st.session_state.get('pp_title', '')} {st.session_state.get('pp_text', '')}")
    opportunity = compute_opportunity(pain, chosen, reusable_agents=agents)

    with rail:
        st.markdown(pain_summary_rail(pain, st.session_state["pp_type_label"], who),
                    unsafe_allow_html=True)
        st.selectbox("Who is affected?", list(WHO_AFFECTED.keys()), index=1,
                     key="pp_who", label_visibility="collapsed")
        st.markdown(next_after_submission(), unsafe_allow_html=True)

    # -------------------------------------------------- already reported?
    # Checked here, before the submit button, rather than after saving. This is
    # the moment where knowing somebody already reported it changes what you do:
    # it turns a duplicate submission into a second voice on an existing one.
    draft = {
        "title": st.session_state.get("pp_title", ""),
        "description": st.session_state.get("pp_text", ""),
        "pain_type": st.session_state.get("pp_type", ""),
        "twin_context": twin_context,
        "outcomes": chosen,
        "current_workflow": st.session_state.get("pp_workflow") or [],
    }
    already = similarity.similar_painpoints(draft, submissions, limit=3)
    if already:
        with st.container(border=True):
            st.markdown(
                f"#### 🔎 {len(already)} "
                f"{'team has' if len(already) == 1 else 'teams have'} "
                "described something like this")
            st.caption(
                "Matched on the shape of the work — what arrives, what is done to it "
                "and where it goes — not on wording. Submit anyway if yours is "
                "genuinely different; the overlap is worth knowing either way."
            )
            for row in already:
                marker = "🟥" if row["band"] == "duplicate" else (
                    "🟦" if row["band"] == "pattern" else "⬜")
                st.markdown(
                    f"{marker} **{row['score']:.0f}** · {row['title']} — "
                    f"*{row['unit'] or 'unassigned'}*"
                    f"{f' · {row['submitter']}' if row['submitter'] else ''}")
                st.caption(" · ".join(row["reasons"]) or row["band_label"])
                if row["reusable"]:
                    st.caption("↳ One agent could serve both.")

    # ---------------------------------------------------------- AI preview
    with st.container(border=True):
        st.markdown(
            "<div class='pc-prev-h'><h2>AI Preview</h2>"
            "<span class='muted'>(based on your input)</span>"
            "<span class='pc-badge'>Preview only</span></div>", unsafe_allow_html=True)
        p1, p2, p3, p4 = st.columns(4, gap="medium")
        workflow = st.session_state["pp_workflow"]
        with p1:
            with st.container(border=True):
                st.markdown(
                    current_workflow_card(workflow, len(workflow) or int(steps_count)),
                    unsafe_allow_html=True)
                with st.popover("View all steps", use_container_width=True):
                    edited = st.text_area(
                        "One step per line", value="\n".join(workflow),
                        height=300, key="pp_workflow_edit")
                    if st.button("Save steps", use_container_width=True):
                        # Through _fill_step_cells so the numbered cells in step 2
                        # show the edit too, rather than the two views disagreeing.
                        _fill_step_cells([
                            line.strip() for line in edited.splitlines() if line.strip()])
                        st.session_state["pp_workflow_source"] = "edited"
                        rerun_app()
        with p2:
            with st.container(border=True):
                st.markdown(improvement_card(estimated_improvement(pain)), unsafe_allow_html=True)
        with p3:
            with st.container(border=True):
                st.markdown(ai_opportunity_card(opportunity), unsafe_allow_html=True)
        with p4:
            with st.container(border=True):
                st.markdown(
                    next_action_card([
                        ("🔎", "Find similar solutions"),
                        ("🤖", "See existing AI agents"),
                        ("👤", "Connect with SME"),
                        ("🚀", "Start a POC"),
                    ]), unsafe_allow_html=True)
                with st.popover("Who is submitting? (optional)", use_container_width=True):
                    st.text_input("Name", key="pp_name")
                    st.text_input("Department / BU", key="pp_dept")
                    st.text_input("Region", key="pp_region")
                    st.text_input("Role", key="pp_role")
                    st.selectbox("Confidentiality", ["Public", "Internal", "Private-to-Team"],
                                 index=1, key="pp_conf")
                    st.file_uploader("Attachments",
                                     type=["csv", "pdf", "png", "jpg", "jpeg", "txt", "json"],
                                     accept_multiple_files=True, key="pp_files")
                if st.button("Submit Pain Point", type="primary", use_container_width=True,
                             key="pp_submit"):
                    if not str(st.session_state["pp_text"]).strip():
                        st.error("Describe the pain point in step 1 before submitting.")
                    else:
                        if not st.session_state["pp_analyzed"]:
                            _pp_analyze(st.session_state["pp_text"])
                        _pp_save(submissions, pain, opportunity, metrics, chosen, agents,
                                 st.session_state.get("pp_name", ""),
                                 st.session_state.get("pp_dept", ""),
                                 st.session_state.get("pp_region", ""),
                                 st.session_state.get("pp_role", ""),
                                 st.session_state.get("pp_conf", "Internal"),
                                 st.session_state.get("pp_files"),
                                 twin_context)

    st.markdown(feature_strip(), unsafe_allow_html=True)


# Kept so any older link into the wizard entry point still works.
render_pain_point_wizard = render_pain_point_capture


def _pp_save(submissions, pain, opp, metrics, outcomes, agents,
             name, department, region, role, confidentiality, attachments,
             twin_context: dict | None = None) -> None:
    """Persist a wizard submission in the shape the rest of the app expects."""
    token = f"{int(datetime.utcnow().timestamp())}"
    stored_files = store_attachments(attachments, token)
    title = st.session_state["pp_title"]
    description = st.session_state["pp_text"]
    type_label = st.session_state["pp_type_label"]

    # Map the new scoring onto the fields the feed, matrix and tables read.
    impact_score = round(opp["impact"] / 10.0, 1)
    urgency = {"LOW": 3.0, "MODERATE": 5.5, "HIGH": 7.5, "SEVERE": 9.0}.get(pain["level"], 5.5)
    difficulty = ("Easy" if opp["complexity"] <= 30 else
                  "Medium" if opp["complexity"] <= 55 else
                  "Hard" if opp["complexity"] <= 75 else "Critical")

    skills = [type_label] + [row["label"] for row in metrics if row["selected"]][:3]
    entry = {
        "id": f"challenge_{token}",
        "title": title,
        "description": description,
        "submitter": {"name": name or "Anonymous", "department": department,
                      "region": region, "role": role},
        "attachments": stored_files,
        "category": type_label,
        "pain_type": st.session_state["pp_type"],
        "difficulty": difficulty,
        "confidentiality": confidentiality,
        "upvotes": 0,
        "comments": 0,
        "urgency": urgency,
        "impact_score": impact_score,
        "similar_agents": agents,
        "similar_rackers": [p.get("name") for p in HUMAN_STACK.search_people(" ".join(skills))],
        "similar_projects": [p.get("title") for p in HUMAN_STACK.search_projects(" ".join(skills))],
        "created_at": datetime.utcnow().isoformat(),
        # --- where it sits in the digital twin ----------------------------
        "twin_context": dict(twin_context or {}),
        # --- the quick-capture payload -----------------------------------
        "baseline": pain,
        "opportunity": opp,
        "outcomes": outcomes,
        "current_workflow": st.session_state["pp_workflow"],
        "workflow_source": st.session_state["pp_workflow_source"],
        "metrics": [
            {k: row[k] for k in ("key", "label", "icon", "unit", "group", "better",
                                 "before", "target", "actual")}
            for row in metrics if row["selected"]
        ],
    }
    entry["ai_baseline"] = generate_ai_baseline(title, description, type_label, difficulty)
    if not entry["similar_agents"]:
        entry["similar_agents"] = entry["ai_baseline"].get("similar_agents", [])

    submissions.insert(0, entry)
    save_submissions(submissions)
    st.success(
        f"Submitted — **{title}**. Pain today: {pain['level']} "
        f"({pain['annual_hours']:,.0f} human hours a year). "
        f"AI opportunity: {opp['score']}/100 — {opp['classification']}."
    )
    _pp_reset()
    rerun_app()


# Everything below is this page's own bootstrap. app.py imports this module to
# reuse render_pain_point_capture for the home page, and none of it should run
# in that case -- see services/ui/utils/embed_flags.py.
if not embed_flags.CAPTURE_EMBEDDED:
    st.set_page_config(page_title="How Can AI Help? — YESAICAN LAB", page_icon="🔥", layout="wide")

    # This page reads and writes submitted pain points, so it carries the same gate
    # as the home page. No-op unless YESAICAN_AUTH_MODE is configured.
    require_auth()

    submissions = load_submissions()
    solutions = load_solutions()

    # The capture panel is the whole top of the page — the old hero, page title and
    # Slack-channel panel used to push it below the fold. They now live further
    # down, under the feed, where they do not compete with the primary task.
    render_pain_point_capture(submissions)

    # Nothing below the form. The leaderboard, the AI auto-blueprint and the
    # solution ideas live on Propose a Cure; the challenge feed and its
    # Before/Target/Actual tables live on Current Submitted PainPoints. This
    # page is for describing your own painpoint and nothing else.
