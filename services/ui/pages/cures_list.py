"""Current Cures and Remedies — every proposed cure and the painpoint it treats.

Its own page rather than a section inside Propose a Cure: proposing a cure and
browsing what already exists are two different errands, and the second one is
what you do *before* the first. It is also the landing point for "View Cure" on
the Current PainPoints board, which deep-links here with ?cure_id=…

Reads the same two files the capture page and the board use, so a cure written
anywhere in the app appears here immediately — no API, no import step.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from services.shared import similarity
from services.ui.utils.auth_gate import require_auth
from services.ui.utils.challenge_link import backfill_challenge_ids, challenge_id_of
from services.ui.utils.meta_store import load_json, save_json
from services.ui.utils.page_template import empty_state, page_chrome

SUBMISSIONS_FILE = "how_ai_help_submissions.json"
SOLUTIONS_FILE = "how_ai_help_solutions.json"


def load_submissions() -> list[dict]:
    data = load_json(SUBMISSIONS_FILE, [])
    return [r for r in data if isinstance(r, dict)] if isinstance(data, list) else []


def load_solutions() -> list[dict]:
    data = load_json(SOLUTIONS_FILE, [])
    return [r for r in data if isinstance(r, dict)] if isinstance(data, list) else []


def _unit_of(painpoint: dict | None) -> str:
    if not painpoint:
        return ""
    context = painpoint.get("twin_context") or {}
    submitter = painpoint.get("submitter")
    submitter = submitter if isinstance(submitter, dict) else {}
    return str(context.get("business_unit") or submitter.get("department") or "")


def cure_label(cure: dict, index: int) -> str:
    what = str(cure.get("what_features") or "").strip()
    if not what:
        # Older cures kept everything in one free-text blob, so fall back to its
        # first line rather than showing a blank row.
        blob = str(cure.get("approach") or "").strip()
        what = blob.splitlines()[0] if blob else "Untitled cure"
    helper = cure.get("helper") or cure.get("author") or "someone"
    return f"{index + 1}. {what[:70]} — {helper}"


# --------------------------------------------------------------------------
# page
# --------------------------------------------------------------------------

st.set_page_config(page_title="Current Cures and Remedies — YES AI CAN",
                   page_icon="💊", layout="wide")
require_auth()

page_chrome(
    "cures_list",
    "Current Cures and Remedies",
    "Every cure our Community has proposed, and the painpoint it treats.",
)
st.markdown("---")

submissions = load_submissions()
solutions = load_solutions()
if backfill_challenge_ids(submissions, solutions):
    save_json(SOLUTIONS_FILE, solutions)

if not solutions:
    st.markdown(
        empty_state("💊", "No cures yet",
                    "Propose one from Propose a Cure and it appears here straight away."),
        unsafe_allow_html=True)
    st.stop()

by_id = {challenge_id_of(record): record for record in submissions}

# Resolve the deep link before the filter widget is drawn: a status filter left
# on "In production" would otherwise hide the very cure the link points at, and
# the page would land on somebody else's. Session keys may only be assigned
# before their widget exists, hence the two-stage handling.
requested = str((st.query_params.get("cure_id") if hasattr(st, "query_params")
                 else None) or "").strip()
deeplink_new = bool(requested) and st.session_state.get("_cure_deeplink") != requested
if deeplink_new:
    st.session_state["_cure_deeplink"] = requested
    st.session_state["cure_list_status"] = "All"

statuses = sorted({str(s.get("status") or "Draft") for s in solutions})
in_production = sum(1 for s in solutions if str(s.get("status") or "") == "In production")

top = st.columns(4, gap="small")
top[0].metric("Cures on the board", len(solutions))
top[1].metric("Painpoints treated", len({str(s.get("challenge_id") or "") for s in solutions
                                         if s.get("challenge_id")}))
top[2].metric("In production", in_production)
top[3].metric("Helpers involved", len({str(s.get("helper") or s.get("author") or "").strip()
                                       for s in solutions
                                       if str(s.get("helper") or s.get("author") or "").strip()}))

filter_col, count_col = st.columns([2, 1], gap="small")
chosen = filter_col.selectbox("Show", ["All"] + statuses, index=0, key="cure_list_status")
listed = [s for s in solutions
          if chosen == "All" or str(s.get("status") or "Draft") == chosen]
count_col.metric("Cures listed", len(listed))

if not listed:
    st.info(f"No cures at status “{chosen}”. Switch the filter to All to see them.")
    st.stop()

rows = []
for index, cure in enumerate(listed):
    painpoint = by_id.get(str(cure.get("challenge_id") or ""))
    rows.append({
        "#": index + 1,
        "Cure": str(cure.get("what_features") or "—")[:80],
        "Treats painpoint": str(cure.get("challenge") or "—")[:65],
        "Painpoint's unit": _unit_of(painpoint) or "—",
        "Helper": cure.get("helper") or cure.get("author") or "—",
        "Helper's department": cure.get("helper_department") or "—",
        "AI tools": str(cure.get("ai_tools_used") or "—")[:45],
        "Effort": cure.get("difficulty") or "—",
        "Status": cure.get("status") or "Draft",
    })
st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True,
             height=min(60 + 35 * len(rows), 560))

# ----------------------------------------------------------------- details
st.divider()
st.subheader("Cure details")

labels = [cure_label(cure, index) for index, cure in enumerate(listed)]

# Second stage of the deep link: point the picker at the requested cure. Applied
# once per distinct id, so you can still choose a different one afterwards
# without the link dragging you back.
if deeplink_new:
    matched = next((i for i, cure in enumerate(listed)
                    if str(cure.get("id") or "") == requested), None)
    if matched is not None:
        st.session_state["cure_detail_pick"] = labels[matched]
    else:
        st.warning("That cure is no longer on the board — showing the list instead.")

picked_label = st.selectbox("Pick a cure to read in full", labels, key="cure_detail_pick")
picked = listed[labels.index(picked_label)]
painpoint = by_id.get(str(picked.get("challenge_id") or ""))

with st.container(border=True):
    st.markdown(f"### {picked.get('what_features') or 'Untitled cure'}")
    head = st.columns(4, gap="small")
    head[0].metric("Helper", str(picked.get("helper") or picked.get("author") or "—"))
    head[1].metric("Department", str(picked.get("helper_department") or "—"))
    head[2].metric("Effort", str(picked.get("difficulty") or "—"))
    head[3].metric("Status", str(picked.get("status") or "Draft"))

    left, right = st.columns(2, gap="medium")
    with left:
        st.markdown("**What it builds**")
        st.write(picked.get("what_features") or "—")
        st.markdown("**How it works**")
        st.write(picked.get("how_components") or "—")
        st.markdown("**AI tools**")
        st.write(picked.get("ai_tools_used") or "—")
        if picked.get("ai_tools_created"):
            st.markdown("**New tools built**")
            st.write(picked["ai_tools_created"])
    with right:
        st.markdown("**So what — the benefit**")
        st.write(picked.get("so_what_benefits") or "—")
        if picked.get("why_me"):
            st.markdown("**Why this helper**")
            st.write(picked["why_me"])
        st.markdown("**Proposed**")
        st.write(str(picked.get("created_at") or "—")[:10])
        if picked.get("approach") and not picked.get("what_features"):
            st.markdown("**Full proposal**")
            st.write(picked["approach"])

    st.markdown("**The painpoint it treats**")
    if painpoint:
        context = painpoint.get("twin_context") or {}
        baseline = painpoint.get("baseline") or {}
        st.markdown(f"*{painpoint.get('title') or 'Untitled'}* — "
                    f"{context.get('business_unit') or 'unassigned'} · "
                    f"{float(baseline.get('annual_hours') or 0):,.0f} h/yr")
        st.caption(str(painpoint.get("description") or "")[:600])
    else:
        # A cure whose challenge_id points nowhere — say so rather than
        # rendering an empty block that looks like a loading failure.
        st.caption(f"Recorded against “{picked.get('challenge') or 'unknown'}”, "
                   "which is no longer on the board.")

    alike = similarity.similar_cures(picked, solutions, by_id, limit=3)
    if alike:
        st.markdown("**Reuse before you rebuild**")
        st.caption("Closest existing cures, weighted by how far along they are — a "
                   "shipped one beats an identical draft.")
        for row in alike:
            st.markdown(
                f"- **{row['score']:.0f}** · {row['title'][:80]} — "
                f"{row['helper']} ({row['helper_department'] or 'unknown team'}) · "
                f"*{row['status'] or 'no status'}* — "
                f"{' · '.join(row['reasons']) or 'similar build'}")
