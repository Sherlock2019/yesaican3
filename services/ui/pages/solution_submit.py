"""Propose a Cure — pick a submitted painpoint and say how you would fix it.

Reads the same two files the capture page and the challenges board use, so the
dropdown always lists the painpoints that actually exist and a proposal written
here shows up on the board immediately. No API in the path: this page has to
work with the backend stopped, because that is when people are drafting ideas.
"""

from __future__ import annotations

import html
from datetime import datetime, timezone
from typing import Any

import pandas as pd
import streamlit as st

from services.shared import similarity
from services.ui.utils import embed_flags
from services.ui.utils.auth_gate import require_auth
from services.ui.utils.challenge_link import (
    backfill_challenge_ids,
    challenge_id_of,
    solutions_by_challenge,
)
from services.ui.utils.meta_store import load_json, save_json
from services.ui.utils.page_template import empty_state, page_chrome

# The challenge feed, the leaderboard, the auto-blueprint and the solution
# detail cards all already existed on the pain-point page. They are imported
# rather than reimplemented so this is a move, not a second version that drifts
# — the Before/Target/Actual tables and the AI Baseline in particular are a lot
# of behaviour to get subtly wrong. The flag stops that module running its own
# page bootstrap on import; see services/ui/utils/embed_flags.py.
embed_flags.CAPTURE_EMBEDDED = True
try:
    from services.ui.pages import how_can_ai_help as capture
finally:
    embed_flags.CAPTURE_EMBEDDED = False

SUBMISSIONS_FILE = "how_ai_help_submissions.json"
SOLUTIONS_FILE = "how_ai_help_solutions.json"

DIFFICULTIES = ["Easy", "Medium", "Hard", "Critical"]


def load_submissions() -> list[dict]:
    data = load_json(SUBMISSIONS_FILE, [])
    return data if isinstance(data, list) else []


def load_solutions() -> list[dict]:
    data = load_json(SOLUTIONS_FILE, [])
    return data if isinstance(data, list) else []


def save_solutions(records: list[dict]) -> None:
    save_json(SOLUTIONS_FILE, records)


def rerun() -> None:
    getattr(st, "rerun", getattr(st, "experimental_rerun", lambda: None))()


def _e(value: Any) -> str:
    return html.escape(str(value if value is not None else ""))


CURE_CSS = """
<style>
.cu-strip { display:grid; grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); gap:1rem;
            margin:0 0 1.3rem; }
.cu-feat { display:flex; align-items:center; gap:.75rem; }
.cu-feat .ic { width:42px; height:42px; border-radius:50%; background:var(--pc-indigo-wash);
               display:inline-flex; align-items:center; justify-content:center; font-size:1.15rem;
               flex:0 0 42px; }
.cu-feat b { display:block; font-size:.92rem; color:var(--pc-ink); }
.cu-feat span { font-size:.82rem; color:var(--pc-ink-faint); }

.cu-board { background:var(--pc-surface); border:1px solid var(--pc-rule); border-radius:14px;
            padding:1rem 1.15rem; }
.cu-rank { display:grid; grid-template-columns:1.4rem 1fr auto; gap:.6rem; align-items:center;
           padding:.42rem 0; border-bottom:1px solid var(--pc-rule); font-size:.86rem; }
.cu-rank:last-child { border-bottom:none; }
.cu-rank .n { font-size:.78rem; font-weight:700; color:var(--pc-ink-faint);
              font-variant-numeric:tabular-nums; }
.cu-rank .t { color:var(--pc-ink); font-weight:600; }
.cu-rank .s { font-size:.78rem; color:var(--pc-ink-soft); white-space:nowrap;
              font-variant-numeric:tabular-nums; }
.cu-note { font-size:.8rem; color:var(--pc-ink-faint); margin:.7rem 0 0; }

.cu-bp { background:var(--pc-indigo-wash); border-radius:14px; padding:1rem 1.15rem; }
.cu-bp b { display:block; font-size:.96rem; color:var(--pc-ink); margin-bottom:.3rem; }
.cu-bp p { font-size:.86rem; color:var(--pc-ink-soft); margin:0 0 .55rem; line-height:1.55; }
.cu-bp li { font-size:.84rem; color:var(--pc-ink-soft); margin-bottom:.22rem; }

.cu-idea { border:1px solid var(--pc-rule); border-radius:12px; padding:.75rem .9rem;
           margin-bottom:.6rem; background:var(--pc-surface); }
.cu-idea .h { display:flex; justify-content:space-between; gap:.6rem; align-items:baseline;
              margin-bottom:.3rem; flex-wrap:wrap; }
.cu-idea .who { font-size:.88rem; font-weight:650; color:var(--pc-ink); }
.cu-idea .for { font-size:.76rem; color:var(--pc-ink-faint); }
.cu-idea .diff { font-size:.7rem; font-weight:700; border-radius:999px; padding:.1rem .5rem;
                 background:var(--pc-indigo-wash); color:var(--pc-indigo-dark); white-space:nowrap; }
.cu-idea p { font-size:.84rem; color:var(--pc-ink-soft); margin:0; line-height:1.55; }
</style>
"""

FEATURES = [
    ("⏱", "Fast", "Propose in under 60 seconds"),
    ("💡", "AI-Powered", "We do the heavy analysis"),
    ("📈", "High Impact", "Focus on what creates real value"),
    ("🤝", "Human-Centered", "Built by our Community, for our Community"),
]


def feature_strip() -> str:
    cells = "".join(
        f"<div class='cu-feat'><span class='ic'>{icon}</span>"
        f"<span><b>{_e(title)}</b><span>{_e(sub)}</span></span></div>"
        for icon, title, sub in FEATURES
    )
    return f"<div class='cu-strip'>{cells}</div>"


def _score(record: dict, proposals: int) -> float:
    """Blend used to rank the board.

    Upvotes, urgency and impact, plus discussion velocity — a painpoint people
    are actively proposing against is a live one, so proposals count too.
    """
    return (
        float(record.get("upvotes") or 0) * 2.0
        + float(record.get("urgency") or 0)
        + float(record.get("impact_score") or 0)
        + proposals * 1.5
    )


def leaderboard(submissions: list[dict], grouped: dict[str, list[dict]]) -> str:
    ranked = sorted(
        submissions,
        key=lambda r: -_score(r, len(grouped.get(challenge_id_of(r), []))),
    )
    rows = "".join(
        f"<div class='cu-rank'><span class='n'>{index}</span>"
        f"<span class='t'>{_e(record.get('title') or 'Untitled')}</span>"
        f"<span class='s'>👍 {int(record.get('upvotes') or 0)} · "
        f"⚡ {float(record.get('urgency') or 0):.1f} · "
        f"🎯 {float(record.get('impact_score') or 0):.1f}</span></div>"
        for index, record in enumerate(ranked[:8], start=1)
    )
    return (
        f"<div class='cu-board'>{rows}"
        f"<p class='cu-note'>Total painpoints: {len(submissions)} · ranking blends upvotes, "
        f"urgency, impact and how many cures have been proposed.</p></div>"
    )


AUTO_BLUEPRINT = """
<div class="cu-bp">
  <b>🤖 AI Auto-Blueprint</b>
  <p>Every submission triggers a baseline that drafts the agent workflow, the datasets it
  needs, the risk notes, a suggested UI/API surface, and a timeline estimate — so a cure
  starts from a draft rather than a blank page.</p>
  <ul>
    <li>🔍 Auto-detects similar agents and reusable patterns.</li>
    <li>🪄 Generates a “Convert to Project” payload with owners and version 0.1.</li>
    <li>👥 Tags suggested Ambassadors and SMEs straight from the Human Stack.</li>
  </ul>
</div>
"""


# --------------------------------------------------------------------------
# page
# --------------------------------------------------------------------------

st.set_page_config(page_title="Propose a Cure — YES AI CAN", page_icon="💡", layout="wide")
require_auth()

page_chrome(
    "solution_submit",
    "Propose a Cure",
    "Pick a painpoint our Community has submitted and say how you would fix it.",
)
st.markdown(CURE_CSS, unsafe_allow_html=True)
st.markdown(feature_strip(), unsafe_allow_html=True)

flash = st.session_state.pop("cure_flash", None)
if flash:
    st.success(flash)

submissions = load_submissions()
solutions = load_solutions()

if not submissions:
    st.markdown(
        empty_state("💡", "No painpoints to cure yet",
                    "Once someone submits one it appears in the dropdown here, "
                    "ready for a proposal."),
        unsafe_allow_html=True)
    st.stop()

if backfill_challenge_ids(submissions, solutions):
    save_solutions(solutions)

grouped = solutions_by_challenge(submissions, solutions)

form_col, side_col = st.columns([1.7, 1], gap="medium")

with form_col:
    st.markdown("### 💡 Propose a Cure")

    # Outside the form so the caption below reacts to the choice — inside, it
    # would only update after submitting, which is too late to be useful.
    titles = {challenge_id_of(r): (r.get("title") or "Untitled") for r in submissions}
    chosen_id = st.selectbox(
        "Select a painpoint to solve", list(titles),
        format_func=lambda i: titles.get(i, i), key="cure_challenge")
    chosen = next((r for r in submissions if challenge_id_of(r) == chosen_id), submissions[0])

    existing = grouped.get(chosen_id, [])
    baseline = chosen.get("baseline") or {}
    hours = float(baseline.get("annual_hours") or 0.0)
    st.caption(
        (chosen.get("description") or "No description.")[:220]
        + (f" · ~{hours:,.0f} h/yr" if hours else "")
        + (f" · {len(existing)} cure(s) already proposed" if existing else " · no cures yet")
    )

    with st.form("cure_form"):
        name_col, diff_col = st.columns(2, gap="small")
        author = name_col.text_input("Your Name *", placeholder="Who is proposing this")
        difficulty = diff_col.selectbox("Solution Difficulty", DIFFICULTIES, index=0)

        what = st.text_area(
            "What (features) *", height=90,
            placeholder="Custom billing format conversion and timeline delivery")
        how = st.text_area(
            "How (components / workflow)", height=90,
            placeholder="Schema detector → mapping engine → validator → writer, with review queue")
        tools = st.text_area(
            "AI tools used", height=70,
            placeholder="LLM (Gemma, Mistral), document parser, regression")
        benefits = st.text_area(
            "So what (benefits / impact)", height=70,
            placeholder="Efficiency, cost, risk, UX — what actually changes for the team")

        submitted = st.form_submit_button("Submit Solution Proposal", type="primary",
                                          use_container_width=True)

    if submitted:
        if not author.strip() or not what.strip():
            st.error("Your name and the What are both needed.")
        else:
            parts = [
                f"• What: {what.strip()}",
                f"• How: {how.strip()}" if how.strip() else "",
                f"• AI tools: {tools.strip()}" if tools.strip() else "",
                f"• So what: {benefits.strip()}" if benefits.strip() else "",
            ]
            token = int(datetime.now(timezone.utc).timestamp())
            solutions.insert(0, {
                "id": f"solution_{token}",
                "challenge_id": chosen_id,
                "challenge": chosen.get("title", ""),
                "submitter": (chosen.get("submitter") or {}).get("name", ""),
                "author": author.strip(),
                "helper": author.strip(),
                "approach": "\n".join(p for p in parts if p),
                "what_features": what.strip(),
                "how_components": how.strip(),
                "ai_tools_used": tools.strip(),
                "so_what_benefits": benefits.strip(),
                "difficulty": difficulty,
                "status": "Draft",
                "upvotes": 0,
                "comments": 0,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            save_solutions(solutions)
            st.session_state["cure_flash"] = (
                f"Thanks {author.strip()} — your cure for **{chosen.get('title')}** is on the board."
            )
            rerun()

with side_col:
    # The originals, moved here whole — not a rewrite.
    capture.render_leaderboard_and_blueprint(submissions)

st.divider()

# The cures list used to sit here. It now has its own page — Current Cures and
# Remedies — because browsing what already exists and writing something new are
# two different errands, and the first is what you do before the second. That
# page is also where "View Cure" on the board lands.
st.divider()
st.markdown(
    "Looking for what has already been proposed? "
    "[**Current Cures and Remedies**](/cures_list) lists every cure, the painpoint "
    "it treats, and who is building it."
)
