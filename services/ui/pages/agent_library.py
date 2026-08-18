"""Community Agent Library — every solution in production, for internal use.

The same shape as the public "AI for the People" library: Industry, Agent Name,
Role / Description, Users, Comments, Rating, Action — but the internal catalog,
so it lists what our Community actually runs rather than what is on show.

Reads through ``agent_catalog``, which is the one loader that knows about both
the built-in catalog and ``services/ui/data/agents.json`` — the file the
pipeline writes when a proven POC is published. Anything promoted from a
painpoint therefore appears here without a second import step.
"""

from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import streamlit as st

from services.ui.utils.agent_catalog import _load_raw_catalog
from services.ui.utils.meta_store import load_json, save_json
from services.ui.utils.page_template import empty_state, page_chrome

AGENTS_PATH = Path(__file__).resolve().parents[1] / "data" / "agents.json"
FEEDBACK_FILE = "agent_feedback.json"

STATUS_STYLE = {
    "new":          ("🆕 NEW", "new"),
    "available":    ("✅ Available", "ok"),
    "coming soon":  ("⏳ Coming Soon", "warn"),
    "being built":  ("🛠️ Being Built", "warn"),
    "wip":          ("🧪 WIP", "wip"),
}
LAUNCHABLE = {"available", "new", "being built"}

# Agents whose page is not simply /<slugified name>.
ROUTE_OVERRIDES = {
    "HF Agent Wrapper": "hf_inspector",
    "Agent Manager": "hf_inspector",
    "Agent Builder": "agent_builder",
    "CEO driver DASHBOARD": "ceo_driver_dashboard",
    "Real Estate Evaluator": "real_estate_evaluator",
    "Anti-Fraud & KYC Agent": "anti_fraud_kyc",
    "Credit Score Agent": "credit_score",
    "Credit Appraisal Agent": "credit_appraisal",
    "Asset Appraisal Agent": "asset_appraisal",
    "Legal Compliance Agent": "legal_compliance",
    "IT Troubleshooter": "troubleshooter_agent",
    "Unified Risk Orchestration": "unified_risk",
    "Chatbot Assistant": "chatbot_assistant",
}


def load_feedback() -> dict[str, dict]:
    data = load_json(FEEDBACK_FILE, {})
    return data if isinstance(data, dict) else {}


def save_feedback(data: dict) -> None:
    save_json(FEEDBACK_FILE, data)


def load_agents() -> list[dict]:
    return _load_raw_catalog()


def save_agents(records: list[dict]) -> None:
    AGENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    AGENTS_PATH.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


def rerun() -> None:
    getattr(st, "rerun", getattr(st, "experimental_rerun", lambda: None))()


def _e(value: Any) -> str:
    return html.escape(str(value if value is not None else ""))


def _c(markup: str) -> str:
    return "".join(line.strip() for line in str(markup).splitlines())


def _plain(name: str) -> str:
    """Agent name without its leading emoji, for routing and matching."""
    import re
    return re.sub(r"^[^\w]+", "", str(name or "")).strip()


def _route(name: str) -> str:
    plain = _plain(name)
    if plain in ROUTE_OVERRIDES:
        return ROUTE_OVERRIDES[plain]
    import re
    return re.sub(r"[^a-z0-9]+", "_", plain.lower()).strip("_")


def _stars(rating: float) -> str:
    full = int(round(max(0.0, min(5.0, rating))))
    return "★" * full + "☆" * (5 - full) if full else "—"


LIB_CSS = """
<style>
.lb-wrap { background:var(--pc-surface); border:1px solid var(--pc-rule); border-radius:16px;
           box-shadow:var(--pc-shadow); overflow-x:auto; margin:0 0 1.2rem; }
.lb-tbl { width:100%; border-collapse:collapse; font-size:.85rem; min-width:1120px; }
.lb-tbl thead th { background:var(--pc-indigo); color:#fff; font-size:.74rem; font-weight:700;
                   letter-spacing:.03em; text-align:left; padding:.7rem .8rem; white-space:nowrap; }
.lb-tbl thead th:first-child { border-top-left-radius:0; }
.lb-tbl td { padding:.75rem .8rem; border-bottom:1px solid var(--pc-rule);
             color:var(--pc-ink-soft); vertical-align:top; }
.lb-tbl tr:last-child td { border-bottom:none; }
.lb-tbl tr:hover td { background:var(--pc-surface-alt); }
.lb-ind { font-size:.8rem; color:var(--pc-ink-faint); }
.lb-nm { font-weight:700; color:var(--pc-ink); }
.lb-nm .origin { display:block; font-size:.72rem; color:var(--pc-indigo-dark); font-weight:600;
                 margin-top:.15rem; }
.lb-desc { max-width:38ch; line-height:1.5; }
.lb-st { display:inline-block; border-radius:999px; padding:.14rem .55rem; font-size:.72rem;
         font-weight:700; white-space:nowrap; }
.lb-st.new  { background:#eff6ff; color:#1d4ed8; }
.lb-st.ok   { background:var(--pc-green-wash); color:var(--pc-green); }
.lb-st.warn { background:#fffbeb; color:#92400e; }
.lb-st.wip  { background:#fdf2f8; color:#be185d; }
.lb-num { text-align:center; white-space:nowrap; font-variant-numeric:tabular-nums; }
.lb-latest { display:block; font-size:.72rem; color:var(--pc-ink-faint); font-style:italic;
             max-width:22ch; margin-top:.25rem; line-height:1.35; }
.lb-stars { color:#f59e0b; font-size:.95rem; letter-spacing:.06em; white-space:nowrap; }
.lb-rate { display:block; font-size:.74rem; color:var(--pc-ink-faint); }
.lb-btn { display:inline-block; background:var(--pc-indigo); color:#fff !important;
          text-decoration:none !important; font-size:.8rem; font-weight:650; border-radius:9px;
          padding:.38rem .8rem; white-space:nowrap; }
.lb-btn:hover { background:var(--pc-indigo-dark); }
.lb-btn.off { background:var(--pc-surface-alt); color:var(--pc-ink-faint) !important;
              border:1px solid var(--pc-rule); }
</style>
"""


def library_table(agents: list[dict], feedback: dict) -> str:
    rows = []
    for record in agents:
        name = str(record.get("agent") or record.get("name") or "").strip()
        if not name:
            continue
        status = str(record.get("status") or "Available")
        label, css = STATUS_STYLE.get(status.strip().lower(), (status, "warn"))

        fb = feedback.get(_plain(name), {})
        users = int(fb.get("users") or 0)
        comments = [str(c) for c in (fb.get("comments") or [])]
        rating = float(fb.get("rating") or 0)
        latest = comments[-1] if comments else "No feedback yet."

        launchable = status.strip().lower() in LAUNCHABLE
        route = _route(name)
        action = (
            f"<a class='lb-btn' href='/{route}' target='_self'>🚀 Launch</a>"
            if launchable else "<span class='lb-btn off'>🔒 Coming Soon</span>"
        )

        # Agents promoted from a painpoint say so — that provenance is the
        # reason to trust one over an idea somebody added by hand.
        origin = record.get("origin_title")
        origin_html = (f"<span class='origin'>↳ from “{_e(origin)}”</span>" if origin else "")

        rows.append(_c(f"""
        <tr>
          <td class='lb-ind'>{_e(record.get('industry') or record.get('sector') or '—')}</td>
          <td class='lb-nm'>{_e(name)}{origin_html}</td>
          <td class='lb-desc'>{_e(record.get('description') or '—')}</td>
          <td><span class='lb-st {css}'>{_e(label)}</span></td>
          <td class='lb-num'>👥 {users}</td>
          <td class='lb-num'>💬 {len(comments)}
              <span class='lb-latest'>“{_e(latest[:70])}{'…' if len(latest) > 70 else ''}”</span></td>
          <td class='lb-num'><span class='lb-stars'>{_stars(rating)}</span>
              <span class='lb-rate'>{f'{rating:.1f}/5' if rating else '—'}</span></td>
          <td class='lb-num'>{action}</td>
        </tr>
        """))

    return _c(f"""
    <div class="lb-wrap">
      <table class="lb-tbl">
        <thead><tr>
          <th>Industry</th><th>Agent Name</th><th>Role / Description</th><th>Status</th>
          <th>Users</th><th>Comments</th><th>Rating</th><th>Action</th>
        </tr></thead>
        <tbody>{''.join(rows)}</tbody>
      </table>
    </div>
    """)


# --------------------------------------------------------------------------
# page
# --------------------------------------------------------------------------

st.set_page_config(page_title="Community Agent Library — YES AI CAN",
                   page_icon="🤖", layout="wide")

page_chrome(
    "agent_library",
    "Community Agent Library",
    "Every solution our Community runs in production — internal use.",
)
st.markdown(LIB_CSS, unsafe_allow_html=True)

flash = st.session_state.pop("lib_flash", None)
if flash:
    st.success(flash)

agents = load_agents()
feedback = load_feedback()

if not agents:
    st.markdown(
        empty_state("🤖", "No agents in the library yet",
                    "Prove a POC on Current POC and publish it — it lands here "
                    "and re-enters the reuse pool."),
        unsafe_allow_html=True)
    st.stop()

published = [a for a in agents if a.get("origin_challenge")]
available = [a for a in agents if str(a.get("status", "")).strip().lower() in LAUNCHABLE]

metric_cols = st.columns(4, gap="small")
metric_cols[0].metric("Agents", len(agents))
metric_cols[1].metric("Launchable", len(available))
metric_cols[2].metric("From a painpoint", len(published))
metric_cols[3].metric("Industries", len({a.get("industry") or a.get("sector") for a in agents}))

filter_col, search_col = st.columns([1, 2], gap="small")
industries = sorted({str(a.get("industry") or a.get("sector") or "—") for a in agents})
chosen_industry = filter_col.selectbox("Industry", ["All"] + industries, key="lib_industry")
query = search_col.text_input("Search", key="lib_query",
                              placeholder="Name, description, industry…")

shown = agents
if chosen_industry != "All":
    shown = [a for a in shown if str(a.get("industry") or a.get("sector") or "—") == chosen_industry]
if query.strip():
    needle = query.strip().lower()
    shown = [
        a for a in shown
        if needle in f"{a.get('agent', '')} {a.get('description', '')} "
                     f"{a.get('industry', '')} {a.get('sector', '')}".lower()
    ]

st.caption(f"Showing {len(shown)} of {len(agents)}.")
if shown:
    st.markdown(library_table(shown, feedback), unsafe_allow_html=True)
else:
    st.info("Nothing matches that filter.")

st.divider()

# ------------------------------------------------------------------ feedback
st.markdown("### 💬 Rate an agent")
st.caption("Ratings and comments show in the table above.")

names = [_plain(str(a.get("agent") or a.get("name") or "")) for a in shown or agents]
names = [n for n in names if n]

with st.form("agent_feedback"):
    pick_col, rate_col = st.columns([2, 1], gap="small")
    target = pick_col.selectbox("Agent", names)
    score = rate_col.slider("Rating", 1, 5, 5)
    note = st.text_input("Comment", placeholder="What worked, what did not")
    sent = st.form_submit_button("Submit feedback", type="primary", use_container_width=True)

if sent:
    entry = feedback.setdefault(target, {"rating": 0, "users": 0, "comments": []})
    existing = list(entry.get("comments") or [])
    if note.strip():
        existing.append(note.strip())
    # Running mean over the ratings received, so one late review cannot
    # overwrite everything before it.
    count = int(entry.get("count") or 0) + 1
    mean = ((float(entry.get("rating") or 0) * (count - 1)) + score) / count
    entry.update({
        "rating": round(mean, 2),
        "count": count,
        "users": int(entry.get("users") or 0) + 1,
        "comments": existing,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })
    save_feedback(feedback)
    st.session_state["lib_flash"] = f"Thanks — feedback recorded for **{target}**."
    rerun()
