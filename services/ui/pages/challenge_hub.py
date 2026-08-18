"""Current Challenges — every submitted painpoint, and who is on it.

One table, not two. The old split — a "challenges" table and a separate
"proposed cures" table — meant you could not answer the only question that
matters at a glance: which painpoints still need somebody. Here an unclaimed
painpoint and one already being worked are rows in the same list, told apart
by their status and by whether the action is "I can help" or "View idea".

Reads the same two files the capture page writes, so a painpoint submitted on
the home page appears here immediately — no API, no import step.
"""

from __future__ import annotations

import html
import re
from datetime import datetime, timezone
from urllib.parse import quote
from typing import Any

import streamlit as st

from services.shared import similarity
from services.ui.utils.auth_gate import require_auth
from services.ui.utils.challenge_link import (
    backfill_challenge_ids,
    challenge_id_of,
    solutions_by_challenge,
)
from services.ui.utils.meta_store import load_json, save_json
from services.ui.utils.page_template import empty_state, page_chrome

SUBMISSIONS_FILE = "how_ai_help_submissions.json"
SOLUTIONS_FILE = "how_ai_help_solutions.json"

DIFFICULTIES = ["Easy", "Medium", "Hard", "Critical"]
SOLUTION_STATUSES = ["Draft", "Prototype", "MVP", "In production"]


# --------------------------------------------------------------------------
# storage
# --------------------------------------------------------------------------

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


# --------------------------------------------------------------------------
# presentation
# --------------------------------------------------------------------------

HUB_CSS = """
<style>
.ch-head { display:grid; gap:.5rem; padding:.6rem .8rem; background:var(--pc-surface-alt);
           border:1px solid var(--pc-rule); border-radius:11px; margin-bottom:.4rem; }
.ch-head span { font-size:.72rem; font-weight:650; letter-spacing:.03em; text-transform:uppercase;
                color:var(--pc-ink-faint); }
.ch-cell { font-size:.86rem; color:var(--pc-ink-soft); line-height:1.45; }
.ch-cell b { color:var(--pc-ink); font-weight:650; }
.ch-cell .sub { display:block; font-size:.74rem; color:var(--pc-ink-faint); margin-top:.1rem; }
.ch-st { display:inline-block; border-radius:999px; padding:.14rem .55rem; font-size:.71rem;
         font-weight:700; white-space:nowrap; }
.ch-st.open { background:#fff7ed; color:#b45309; }
.ch-st.taken { background:var(--pc-indigo-wash); color:var(--pc-indigo-dark); }
.ch-st.done { background:var(--pc-green-wash); color:var(--pc-green); }
.ch-sig { font-size:.74rem; color:var(--pc-ink-faint); white-space:nowrap; }
.ch-row-rule { border-bottom:1px solid var(--pc-rule); margin:.15rem 0 .55rem; }
.ch-sim { display:inline-block; border-radius:999px; padding:.14rem .55rem; font-size:.71rem;
          font-weight:700; white-space:nowrap; }
.ch-sim.duplicate { background:#fef2f2; color:#b91c1c; }
.ch-sim.pattern   { background:var(--pc-indigo-wash); color:var(--pc-indigo-dark); }
.ch-sim.look      { background:var(--pc-surface-alt); color:var(--pc-ink-faint); }
.ch-none { font-size:.78rem; color:var(--pc-ink-faint); }
.ch-jump { display:block; font-size:.74rem; color:var(--pc-indigo-dark); text-decoration:none;
           margin-top:.16rem; line-height:1.3; }
.ch-jump:hover { text-decoration:underline; }
/* Matches Streamlit's secondary button, so the row's three actions read as one
   set even though this one is an anchor. */
.ch-btn { display:block; width:100%; box-sizing:border-box; text-align:center;
          padding:.36rem .6rem; margin:.18rem 0; border:1px solid var(--pc-rule);
          border-radius:8px; background:var(--pc-surface); color:var(--pc-ink);
          font-size:.875rem; font-weight:500; text-decoration:none;
          transition:border-color .12s ease,color .12s ease; }
.ch-btn:hover { border-color:var(--pc-indigo); color:var(--pc-indigo-dark); }
/* The row anchors sit under the sticky top bar, so an unadjusted jump lands
   with the target row hidden behind it. */
.ch-anchor { display:block; position:relative; top:calc(-1 * (var(--tb-h,72px) + 12px));
             visibility:hidden; }
</style>
"""

COLUMNS = [2.1, 1.0, 0.95, 1.15, 2.0, 1.15, 1.15, 1.2]
HEADERS = ["Challenge", "Submitter", "Signals", "Similar",
           "Proposed AI approach", "Helper", "Status", "Action"]


def _e(value: Any) -> str:
    return html.escape(str(value if value is not None else ""))


def _anchor(identifier: str) -> str:
    """A DOM-safe id for a challenge, so rows can link to each other."""
    return "pp-" + re.sub(r"[^a-zA-Z0-9_-]+", "-", str(identifier or "x")).strip("-").lower()


def _stage(solutions: list[dict]) -> tuple[str, str]:
    """(css class, label) for a challenge, from the solutions attached to it."""
    if not solutions:
        return "open", "Open — needs a helper"
    statuses = [str(s.get("status") or "Draft") for s in solutions]
    if any(s == "In production" for s in statuses):
        return "done", "In production"
    return "taken", f"Being worked · {statuses[0]}"


def render_row(challenge: dict, solutions: list[dict],
               alike: list[dict] | None = None) -> None:
    """One painpoint, plus whoever is on it and whoever else has it too."""
    identifier = challenge_id_of(challenge)
    alike = alike or []
    cells = st.columns(COLUMNS, gap="small")

    submitter = (challenge.get("submitter") or {}).get("name") or "Anonymous"
    department = (challenge.get("submitter") or {}).get("department") or ""
    baseline = challenge.get("baseline") or {}
    hours = float(baseline.get("annual_hours") or 0.0)

    cells[0].markdown(
        f"<span class='ch-anchor' id='{_anchor(identifier)}'></span>"
        f"<div class='ch-cell'><b>{_e(challenge.get('title') or 'Untitled')}</b>"
        f"<span class='sub'>{_e(challenge.get('category') or challenge.get('pain_type') or '')}</span></div>",
        unsafe_allow_html=True)
    cells[1].markdown(
        f"<div class='ch-cell'>{_e(submitter)}"
        f"<span class='sub'>{_e(department)}</span></div>", unsafe_allow_html=True)
    cells[2].markdown(
        f"<div class='ch-cell'><span class='ch-sig'>⚡ {float(challenge.get('urgency') or 0):.1f}"
        f" · 🎯 {float(challenge.get('impact_score') or 0):.1f}</span>"
        f"<span class='sub'>{f'{hours:,.0f} h/yr' if hours else 'not sized'}</span></div>",
        unsafe_allow_html=True)

    # How many other teams are living with the same thing. The top score drives
    # the colour, because "somebody already reported this" and "there is a loose
    # family resemblance" deserve very different amounts of attention.
    if alike:
        top = alike[0]
        # Each match is a link straight to that painpoint's row, so "who else
        # has this" is one click rather than a scan back through the table.
        links = "".join(
            f"<a class='ch-jump' href='#{_anchor(row['id'])}'>"
            f"→ {_e(row['title'][:44])}{'…' if len(row['title']) > 44 else ''}"
            f" <span style='opacity:.7'>({row['score']:.0f})</span></a>"
            for row in alike[:3]
        )
        cells[3].markdown(
            f"<div class='ch-cell'><span class='ch-sim {_e(top['band'])}'>"
            f"{top['score']:.0f} · {len(alike)} alike</span>{links}</div>",
            unsafe_allow_html=True)
    else:
        cells[3].markdown("<div class='ch-cell'><span class='ch-none'>—</span></div>",
                          unsafe_allow_html=True)

    if solutions:
        lead = solutions[0]
        approach = str(lead.get("approach") or lead.get("what_features") or "").strip()
        approach = approach.replace("\n", " · ")
        cells[4].markdown(
            f"<div class='ch-cell'>{_e(approach[:150])}{'…' if len(approach) > 150 else ''}</div>",
            unsafe_allow_html=True)

        # The helper gets a column of their own. Buried as a sub-line under the
        # approach, the one thing a reader scans for — who is on this, and are
        # they from my team — was the least visible thing in the row.
        helper = lead.get("helper") or lead.get("author") or "A helper"
        department = lead.get("helper_department") or ""
        extra = f"<span class='sub'>+{len(solutions) - 1} more helping</span>" \
            if len(solutions) > 1 else ""
        cells[5].markdown(
            f"<div class='ch-cell'>🤝 <b>{_e(helper)}</b>"
            f"<span class='sub'>{_e(department)}</span>{extra}</div>",
            unsafe_allow_html=True)
    else:
        cells[4].markdown(
            "<div class='ch-cell' style='color:var(--pc-ink-faint)'>No proposal yet — "
            "this one is up for grabs.</div>", unsafe_allow_html=True)
        cells[5].markdown("<div class='ch-cell'><span class='ch-none'>Nobody yet</span></div>",
                          unsafe_allow_html=True)

    css_class, label = _stage(solutions)
    cells[6].markdown(f"<span class='ch-st {css_class}'>{_e(label)}</span>",
                      unsafe_allow_html=True)

    with cells[7]:
        # Only one panel opens at a time, so a second click replaces the first
        # rather than leaving an invisible one latched behind it.
        def _open(slot: str) -> None:
            for key in ("ch_helping", "ch_similar"):
                st.session_state.pop(key, None)
            st.session_state[slot] = identifier
            rerun()

        if st.button("🤝 I can help", key=f"help_{identifier}", type="primary",
                     use_container_width=True):
            _open("ch_helping")

        # A link, not a button: the cure is written up in full on Propose a
        # Cure, so this jumps straight to that entry rather than rendering a
        # second, thinner copy of it here.
        #
        # Hand-rolled anchor rather than st.link_button, which hard-codes
        # target="_blank" — that opened the cure in a new tab and left the board
        # sitting where it was, which is not "jump to it".
        if solutions:
            cure_id = str(solutions[0].get("id") or "")
            st.markdown(
                f"<a class='ch-btn' target='_self' "
                f"href='/cures_list?cure_id={quote(cure_id)}'>"
                f"View Cure</a>", unsafe_allow_html=True)

        if alike and st.button(f"Similar ({len(alike)})", key=f"sim_{identifier}",
                               use_container_width=True):
            _open("ch_similar")

    st.markdown("<div class='ch-row-rule'></div>", unsafe_allow_html=True)


def render_similar(challenge: dict, alike: list[dict]) -> None:
    """Who else has this same problem, and why the app thinks so.

    The reasons are shown rather than just the score: "same job, same input,
    felt in two units" is something a person can act on or disagree with, while
    a bare percentage is something they can only take on faith.
    """
    st.subheader(f"Others with the same problem as “{challenge.get('title', '')}”")
    st.caption(
        "Matched on the shape of the work — what arrives, what is done to it and "
        "where it goes — not on wording. Two teams rarely describe the same job "
        "in the same words."
    )
    for row in alike:
        head = f"{row['score']:.0f} · {row['title']}"
        with st.expander(head, expanded=row is alike[0]):
            top = st.columns([3, 1], gap="small")
            top[0].markdown(f"**{row['band_label'] or 'Possible overlap'}**")
            top[1].markdown(f"**{row['unit'] or 'Unassigned'}**")
            for reason in row["reasons"]:
                st.markdown(f"- {reason}")
            if row["reusable"]:
                st.success("One agent could serve both — same job, and the same "
                           "thing read or the same place written.")
            if row["cross_unit"]:
                st.info("Different business units. Worth building once and "
                        "shipping to both rather than solving twice.")
            else:
                st.warning("Same business unit — these may be one painpoint "
                           "reported twice. Worth merging.")
            st.caption(str(row["record"].get("description") or "")[:400])
    if st.button("Close", key="sim_close"):
        st.session_state.pop("ch_similar", None)
        rerun()


def render_helper_form(challenge: dict, solutions: list[dict], all_solutions: list[dict]) -> None:
    """What the helper fills in when they take a painpoint on."""
    title = challenge.get("title") or "Untitled"
    st.markdown(f"### 🤝 Helping with — {title}")
    if challenge.get("description"):
        st.caption(challenge["description"][:400])

    with st.form(f"helper_form_{challenge_id_of(challenge)}"):
        name_col, diff_col = st.columns(2, gap="small")
        helper = name_col.text_input("Your name *", placeholder="Who is taking this on")
        difficulty = diff_col.selectbox("How hard is it to build?", DIFFICULTIES, index=1)

        what = st.text_area(
            "What will your solution do? *", height=90,
            placeholder="Convert any customer billing layout to the internal schema automatically.")
        how = st.text_area(
            "How — components and workflow", height=90,
            placeholder="Schema detector → field mapper → validator → writer, with a review queue.")
        tools_col, new_col = st.columns(2, gap="small")
        reused = tools_col.text_input(
            "AI tools reused", placeholder="Document parser, HF agent wrapper")
        created = new_col.text_input(
            "New AI tools created", placeholder="Billing schema mapper")
        benefits = st.text_area(
            "So what — the benefit", height=70,
            placeholder="Cuts 45 minutes per invoice to under 8, and removes the re-keying step.")
        status = st.selectbox("Where is it now?", SOLUTION_STATUSES, index=0)

        submitted = st.form_submit_button("Submit my proposal", type="primary",
                                          use_container_width=True)

    if submitted:
        if not helper.strip() or not what.strip():
            st.error("Your name and what the solution does are both needed.")
            return
        parts = [
            f"• What: {what.strip()}",
            f"• How: {how.strip()}" if how.strip() else "",
            f"• AI tools reused: {reused.strip()}" if reused.strip() else "",
            f"• New AI tools: {created.strip()}" if created.strip() else "",
            f"• So what: {benefits.strip()}" if benefits.strip() else "",
        ]
        token = int(datetime.now(timezone.utc).timestamp())
        all_solutions.insert(0, {
            "id": f"solution_{token}",
            "challenge_id": challenge_id_of(challenge),
            "challenge": challenge.get("title", ""),
            "submitter": (challenge.get("submitter") or {}).get("name", ""),
            "author": helper.strip(),
            "helper": helper.strip(),
            "approach": "\n".join(p for p in parts if p),
            "what_features": what.strip(),
            "how_components": how.strip(),
            "ai_tools_used": reused.strip(),
            "ai_tools_created": created.strip(),
            "so_what_benefits": benefits.strip(),
            "difficulty": difficulty,
            "status": status,
            "upvotes": 0,
            "comments": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        save_solutions(all_solutions)
        st.session_state.pop("ch_helping", None)
        st.session_state["ch_flash"] = (
            f"Thanks {helper.strip()} — your proposal for **{title}** is on the board."
        )
        rerun()

    if st.button("Cancel", key="ch_cancel_help"):
        st.session_state.pop("ch_helping", None)
        rerun()


# render_idea() used to draw the proposals inline here. "View Cure" now links to
# the Current Cures List on Propose a Cure, which shows the same cure with its
# painpoint, its reuse candidates and the full write-up — so keeping a second,
# thinner rendering of the same record would only be a place for the two to
# disagree.


# --------------------------------------------------------------------------
# page
# --------------------------------------------------------------------------

st.set_page_config(page_title="Current Challenges — YES AI CAN", page_icon="🧩", layout="wide")
require_auth()

page_chrome(
    "challenge_hub",
    "Current PainPoints",
    "Everything our Community has submitted — the ones still open, the ones being worked, "
    "and who is curing them.",
)
st.markdown(HUB_CSS, unsafe_allow_html=True)

flash = st.session_state.pop("ch_flash", None)
if flash:
    st.success(flash)

submissions = load_submissions()
solutions = load_solutions()

# Older solutions matched their challenge by title alone; give them the id so
# the join below cannot silently miss them.
if backfill_challenge_ids(submissions, solutions):
    save_solutions(solutions)

if not submissions:
    st.markdown(
        empty_state("🧩", "No painpoints yet",
                    "Submit one from Submit My PainPoints and it appears here straight away, "
                    "ready for a helper to pick up."),
        unsafe_allow_html=True)
    st.stop()

grouped = solutions_by_challenge(submissions, solutions)
open_count = sum(1 for s in submissions if not grouped.get(challenge_id_of(s)))

# Scored once for the whole table rather than per row: the board is small, but
# this is O(n^2) and rerunning it inside the render loop would make it O(n^3).
similar_map = {
    challenge_id_of(record): similarity.similar_painpoints(record, submissions, limit=5)
    for record in submissions
}
shared_count = sum(1 for rows in similar_map.values() if rows)

stat_a, stat_b, stat_c, stat_d = st.columns(4, gap="small")
stat_a.metric("Painpoints on the board", len(submissions))
stat_b.metric("Still need a helper", open_count)
stat_c.metric("Being worked", len(submissions) - open_count)
stat_d.metric("Shared with another team", shared_count,
              help="Painpoints where at least one other submission looks like the "
                   "same job — a candidate for one agent serving both.")

only_open = st.toggle("Show only the ones needing a helper", key="ch_only_open")

st.markdown(
    "<div class='ch-head' style='grid-template-columns:"
    + " ".join(f"{w}fr" for w in COLUMNS) + "'>"
    + "".join(f"<span>{_e(header)}</span>" for header in HEADERS)
    + "</div>",
    unsafe_allow_html=True)

# Unclaimed first: the whole point of fusing the two tables is that the work
# needing somebody is what you see without scrolling.
ordered = sorted(
    submissions,
    key=lambda record: (bool(grouped.get(challenge_id_of(record))),
                        -float(record.get("impact_score") or 0)),
)
helping = st.session_state.get("ch_helping")
comparing = st.session_state.get("ch_similar")

shown = 0
for challenge in ordered:
    identifier = challenge_id_of(challenge)
    attached = grouped.get(identifier, [])
    if only_open and attached:
        continue
    alike = similar_map.get(identifier, [])
    render_row(challenge, attached, alike)
    shown += 1

    # Panels open directly under the row that was clicked. They used to render
    # after the whole table, which on a board this long put them well below the
    # fold — the click worked, but nothing visibly happened, so the buttons
    # read as broken.
    if helping == identifier:
        render_helper_form(challenge, attached, solutions)
    elif comparing == identifier and alike:
        render_similar(challenge, alike)

if not shown:
    st.info("Every painpoint has a helper. Untick the filter to see them all.")
