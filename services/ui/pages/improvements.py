"""Improvements Feedback — tell us what to fix about the LAB itself.

Deliberately separate from a painpoint. A painpoint is a problem in someone's
job that the community might build an agent for; this is a problem with *this
app*. Filing the second as the first would put "the similarity column is
confusing" into the same queue as "billing takes 45 minutes", and the queue is
the product, so it has to stay clean.

Its own store too: human_feedback.json holds peer reviews of people and
agent_feedback.json holds agent ratings. Neither means the same thing, and
overloading either would make both harder to read.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd
import streamlit as st

from services.ui.utils.app_shell import NAV_ITEMS
from services.ui.utils.auth_gate import require_auth
from services.ui.utils.meta_store import load_json, save_json
from services.ui.utils.page_template import empty_state, page_chrome

FEEDBACK_FILE = "improvement_feedback.json"

KINDS = [
    "💡 Idea",
    "🧩 Missing feature",
    "😕 Confusing — I could not work out how to do it",
    "🐛 Something is broken",
    "🐢 Too slow",
]
PRIORITIES = ["Nice to have", "Would help a lot", "Blocking me"]

# The areas are the rail itself, so a suggestion always lands on a real page
# rather than a free-text guess at what it is called.
AREAS = ["The app as a whole"] + [label for label, _slug, _icon in NAV_ITEMS] + ["Something else"]


def load_feedback() -> list[dict]:
    data = load_json(FEEDBACK_FILE, [])
    return [r for r in data if isinstance(r, dict)] if isinstance(data, list) else []


def save_feedback(records: list[dict]) -> None:
    save_json(FEEDBACK_FILE, records)


def rerun() -> None:
    getattr(st, "rerun", getattr(st, "experimental_rerun", lambda: None))()


st.set_page_config(page_title="Improvements Feedback — YES AI CAN",
                   page_icon="📣", layout="wide")
require_auth()

page_chrome(
    "improvements",
    "Improvements Feedback",
    "Anything about this LAB that could be better — say so here.",
)
st.markdown("---")

records = load_feedback()

flash = st.session_state.pop("fb_flash", None)
if flash:
    st.success(flash)

# ------------------------------------------------------------------- form
st.subheader("Suggest an improvement")
st.caption(
    "This is for the LAB itself — the pages, the wording, anything that got in your way. "
    "A problem in **your own job** belongs in Submit My PainPoints instead, so the two "
    "queues stay separate."
)

with st.form("improvement_form", clear_on_submit=True):
    top = st.columns([1.2, 1.2, 1.6], gap="small")
    name = top[0].text_input("Your name", placeholder="Optional — leave blank to stay anonymous")
    department = top[1].text_input("Your team", placeholder="Optional")
    area = top[2].selectbox("Which part of the LAB?", AREAS, index=0)

    mid = st.columns([1.6, 1.2], gap="small")
    kind = mid[0].selectbox("What kind of feedback is it?", KINDS, index=0)
    priority = mid[1].selectbox("How much does it matter?", PRIORITIES, index=0)

    suggestion = st.text_area(
        "What would you improve?", height=110,
        placeholder="The similarity column shows a score but I cannot tell what it is "
                    "comparing until I open the panel.")
    why = st.text_area(
        "Why does it matter — what would it let you do?", height=90,
        placeholder="I would know whether to read the matches before writing a duplicate.")

    submitted = st.form_submit_button("📣  Send my feedback", type="primary",
                                      use_container_width=True)

if submitted:
    if not suggestion.strip():
        st.error("Tell us what you would improve — the rest is optional.")
    else:
        token = int(datetime.now(timezone.utc).timestamp())
        records.insert(0, {
            "id": f"feedback_{token}",
            "name": name.strip() or "Anonymous",
            "department": department.strip(),
            "area": area,
            "kind": kind,
            "priority": priority,
            "suggestion": suggestion.strip(),
            "why": why.strip(),
            "votes": 0,
            "status": "New",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        save_feedback(records)
        st.session_state["fb_flash"] = (
            f"Thank you{' ' + name.strip() if name.strip() else ''} — "
            "your feedback is on the list below."
        )
        rerun()

st.divider()

# ------------------------------------------------------------------- list
st.subheader("What people have asked for")

if not records:
    st.markdown(
        empty_state("📣", "No feedback yet",
                    "Be the first — the form above takes about thirty seconds."),
        unsafe_allow_html=True)
    st.stop()

blocking = sum(1 for r in records if r.get("priority") == "Blocking me")
stat = st.columns(4, gap="small")
stat[0].metric("Suggestions", len(records))
stat[1].metric("Blocking someone", blocking)
stat[2].metric("Areas touched", len({str(r.get("area") or "") for r in records}))
stat[3].metric("Total “me too”", sum(int(r.get("votes") or 0) for r in records))

filters = st.columns([1.4, 1.4, 1.2], gap="small")
area_filter = filters[0].selectbox(
    "Area", ["All"] + sorted({str(r.get("area") or "—") for r in records}), key="fb_area")
kind_filter = filters[1].selectbox(
    "Kind", ["All"] + sorted({str(r.get("kind") or "—") for r in records}), key="fb_kind")
sort_by = filters[2].selectbox("Sort by", ["Most “me too”", "Newest", "Priority"], key="fb_sort")

shown = [
    r for r in records
    if (area_filter == "All" or str(r.get("area") or "—") == area_filter)
    and (kind_filter == "All" or str(r.get("kind") or "—") == kind_filter)
]

_PRIORITY_RANK = {p: index for index, p in enumerate(reversed(PRIORITIES))}
if sort_by == "Most “me too”":
    shown.sort(key=lambda r: -int(r.get("votes") or 0))
elif sort_by == "Priority":
    shown.sort(key=lambda r: -_PRIORITY_RANK.get(str(r.get("priority")), 0))
else:
    shown.sort(key=lambda r: str(r.get("created_at") or ""), reverse=True)

st.dataframe(
    pd.DataFrame([{
        "Suggestion": str(r.get("suggestion") or "")[:90],
        "Area": r.get("area") or "—",
        "Kind": r.get("kind") or "—",
        "Priority": r.get("priority") or "—",
        "Me too": int(r.get("votes") or 0),
        "From": r.get("name") or "Anonymous",
        "Team": r.get("department") or "—",
        "When": str(r.get("created_at") or "")[:10],
    } for r in shown]),
    hide_index=True, use_container_width=True,
    height=min(60 + 35 * len(shown), 420))

st.markdown("**Read one in full, or add your voice to it**")
st.caption("“Me too” is the only prioritisation signal here — five people asking for the "
           "same thing is worth more than one person asking loudly.")

# One vote per suggestion per session. Not real identity, and not meant to be:
# it stops an accidental double-click from counting twice without pretending to
# be an authentication system this app does not have.
voted: set[str] = st.session_state.setdefault("fb_voted", set())

for record in shown[:25]:
    identifier = str(record.get("id") or "")
    header = (f"{record.get('kind', '')} · {str(record.get('suggestion') or '')[:70]} "
              f"— 👍 {int(record.get('votes') or 0)}")
    with st.expander(header):
        meta = st.columns(4, gap="small")
        meta[0].markdown(f"**Area**  \n{record.get('area') or '—'}")
        meta[1].markdown(f"**Priority**  \n{record.get('priority') or '—'}")
        meta[2].markdown(f"**From**  \n{record.get('name') or 'Anonymous'}"
                         f"{' · ' + record['department'] if record.get('department') else ''}")
        meta[3].markdown(f"**When**  \n{str(record.get('created_at') or '')[:10]}")

        st.markdown("**What they would improve**")
        st.write(record.get("suggestion") or "—")
        if record.get("why"):
            st.markdown("**Why it matters**")
            st.write(record["why"])

        if identifier in voted:
            st.caption("✅ You have already added your voice to this one.")
        elif st.button("👍  Me too", key=f"vote_{identifier}"):
            for row in records:
                if str(row.get("id") or "") == identifier:
                    row["votes"] = int(row.get("votes") or 0) + 1
                    break
            save_feedback(records)
            voted.add(identifier)
            st.session_state["fb_flash"] = "Counted — thanks."
            rerun()
