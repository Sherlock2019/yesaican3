"""AI Human Trainers — who owns each agent, who is teaching it, is it ready.

The rows are derived, not registered: every POC on a painpoint and every agent
in the library already exists elsewhere, so this page joins them rather than
keeping a second list that would drift. The only thing stored here is the part
that is genuinely new — ownership, who signed up to train, and what each
training round measured.

Readiness is computed in services/shared/training.py from five facts, and the
unmet ones are shown by name. "62%" tells nobody what to do next; "no owner,
accuracy 71% against a 90% bar" does.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from services.shared import training
from services.shared.pipeline import stage_of
from services.ui.utils.auth_gate import require_auth
from services.ui.utils.challenge_link import challenge_id_of
from services.ui.utils.meta_store import load_json, save_json
from services.ui.utils.page_template import empty_state, page_chrome

SUBMISSIONS_FILE = "how_ai_help_submissions.json"
HUMANS_FILE = "humans.json"
TRAINERS_FILE = "agent_trainers.json"
LIBRARY_PATH = Path(__file__).resolve().parents[1] / "data" / "agents.json"

STAGE_LABEL = {"captured": "Captured", "poc": "POC", "proven": "Proven",
               "published": "In library"}


def _list(name: str) -> list[dict]:
    data = load_json(name, [])
    return [r for r in data if isinstance(r, dict)] if isinstance(data, list) else []


def load_library() -> list[dict]:
    if not LIBRARY_PATH.exists():
        return []
    try:
        data = json.loads(LIBRARY_PATH.read_text(encoding="utf-8"))
        return [r for r in data if isinstance(r, dict)] if isinstance(data, list) else []
    except Exception:
        return []


def load_trainers() -> dict[str, dict]:
    data = load_json(TRAINERS_FILE, {})
    return data if isinstance(data, dict) else {}


def save_trainers(store: dict[str, dict]) -> None:
    save_json(TRAINERS_FILE, store)


def rerun() -> None:
    getattr(st, "rerun", getattr(st, "experimental_rerun", lambda: None))()


def buildable(submissions: list[dict], library: list[dict]) -> list[dict]:
    """Everything a human could train: every POC, plus published agents.

    POCs are included deliberately — that is when training input is worth most,
    and waiting until an agent ships is too late to shape it.
    """
    rows: list[dict] = []
    published = {str(a.get("origin_challenge") or ""): a for a in library}

    for record in submissions:
        poc = record.get("poc")
        if not isinstance(poc, dict):
            continue
        identifier = str(poc.get("id") or challenge_id_of(record))
        context = record.get("twin_context") or {}
        submitter = record.get("submitter")
        submitter = submitter if isinstance(submitter, dict) else {}
        agent = published.get(str(record.get("id") or ""))
        rows.append({
            "id": identifier,
            "name": str((agent or {}).get("agent") or poc.get("name")
                        or record.get("title") or "Untitled"),
            "stage": STAGE_LABEL.get(stage_of(record), "POC"),
            "unit": str(context.get("business_unit")
                        or submitter.get("department") or "Unassigned"),
            "submitter": str(submitter.get("name") or ""),
            "painpoint": str(record.get("title") or ""),
            "poc": poc,
            "github": str(poc.get("github") or ""),
            "status": str(poc.get("status") or ""),
        })
    return rows


st.set_page_config(page_title="AI Human Trainers — YES AI CAN", page_icon="🧑‍🏫",
                   layout="wide")
require_auth()

page_chrome(
    "ai_human_trainers",
    "AI Human Trainers",
    "Who owns each agent, who is teaching it, and whether it is ready for production.",
)
st.markdown("---")

submissions = _list(SUBMISSIONS_FILE)
humans = _list(HUMANS_FILE)
library = load_library()
store = load_trainers()
agents = buildable(submissions, library)

flash = st.session_state.pop("tr_flash", None)
if flash:
    st.success(flash)

if not agents:
    st.markdown(
        empty_state("🧑‍🏫", "Nothing to train yet",
                    "An agent appears here as soon as a painpoint gets a POC."),
        unsafe_allow_html=True)
    st.stop()

# --------------------------------------------------------------- the table
scored = []
for agent in agents:
    record = store.get(agent["id"], {})
    result = training.readiness(record, agent["poc"])
    scored.append({**agent, "record": record, "readiness": result})

ready = sum(1 for a in scored if a["readiness"]["band"] == "ready")
untrained = sum(1 for a in scored if not a["readiness"]["trainers"])
unowned = sum(1 for a in scored if not str(a["record"].get("owner") or "").strip())

top = st.columns(4, gap="small")
top[0].metric("Agents in training", len(scored))
top[1].metric("Ready for production", ready)
top[2].metric("Nobody training them", untrained)
top[3].metric("No owner", unowned)

st.dataframe(
    pd.DataFrame([{
        "Agent / POC": a["name"][:52],
        "Stage": a["stage"],
        "Serves": a["unit"],
        "Owner": str(a["record"].get("owner") or "— unowned"),
        "Trainers": len(a["readiness"]["trainers"]),
        "Rounds": a["readiness"]["rounds"],
        "Accuracy": (f"{a['readiness']['accuracy']:.0f}%"
                     if a["readiness"]["accuracy"] is not None else "—"),
        "Readiness": f"{a['readiness']['score']:.0f}%",
        "Status": a["readiness"]["band_label"],
        "Blocked on": ", ".join(a["readiness"]["blockers"]) or "nothing",
    } for a in sorted(scored, key=lambda a: -a["readiness"]["score"])]),
    hide_index=True, use_container_width=True,
    height=min(60 + 35 * len(scored), 460))

st.divider()

# ------------------------------------------------------------- one agent
st.subheader("Take one on")

labels = [f"{a['name'][:60]} — {a['stage']} · {a['readiness']['score']:.0f}% ready"
          for a in scored]
picked = scored[labels.index(st.selectbox("Which agent?", labels, key="tr_pick"))]
record = picked["record"]
result = picked["readiness"]

head = st.columns(4, gap="small")
head[0].metric("Stage", picked["stage"])
head[1].metric("Serves", picked["unit"])
head[2].metric("Readiness", f"{result['score']:.0f}%")
head[3].metric("Status", result["band_label"])

left, right = st.columns([1.15, 1], gap="medium")

with left:
    st.markdown("**Production readiness**")
    for gate in result["gates"]:
        st.markdown(f"{'✅' if gate['met'] else '⬜'} **{gate['label']}** — {gate['detail']}")
    if result["band"] == "ready":
        st.success("All five gates pass. This one can go to production.")
    else:
        st.info("Blocked on: " + ", ".join(result["blockers"]))

    st.markdown("**Ownership**")
    with st.form("owner_form", clear_on_submit=False):
        owner = st.text_input("Who owns this agent?",
                              value=str(record.get("owner") or ""),
                              placeholder="The person accountable for it in production")
        if st.form_submit_button("Save owner", use_container_width=True):
            entry = store.setdefault(picked["id"], {})
            entry["owner"] = owner.strip()
            entry["updated_at"] = datetime.now(timezone.utc).isoformat()
            save_trainers(store)
            st.session_state["tr_flash"] = (
                f"{owner.strip()} now owns {picked['name']}." if owner.strip()
                else "Owner cleared.")
            rerun()

with right:
    st.markdown("**Trainers**")
    current = result["trainers"]
    st.write(", ".join(current) if current else "Nobody yet.")

    # Suggestions rather than a blank field: the person who reported the
    # painpoint is the domain expert for the agent that fixes it.
    suggestions = training.suggest_trainers(picked["unit"], picked["submitter"], humans)
    fresh = [s for s in suggestions if s["name"] not in current]
    if fresh:
        st.caption("Worth asking:")
        for person in fresh:
            cols = st.columns([2.4, 1], gap="small")
            cols[0].markdown(f"**{person['name']}** — {person['why']}")
            if cols[1].button("Add", key=f"add_{picked['id']}_{person['name']}",
                              use_container_width=True):
                entry = store.setdefault(picked["id"], {})
                entry.setdefault("trainers", []).append(person["name"])
                save_trainers(store)
                st.session_state["tr_flash"] = f"{person['name']} added as a trainer."
                rerun()

    with st.form("volunteer_form", clear_on_submit=True):
        volunteer = st.text_input("Or sign yourself up", placeholder="Your name")
        if st.form_submit_button("✋  I'll train this", type="primary",
                                 use_container_width=True):
            if not volunteer.strip():
                st.error("Put your name in first.")
            else:
                entry = store.setdefault(picked["id"], {})
                names = entry.setdefault("trainers", [])
                if volunteer.strip() in names:
                    st.warning("You are already on this one.")
                else:
                    names.append(volunteer.strip())
                    save_trainers(store)
                    st.session_state["tr_flash"] = (
                        f"Thanks {volunteer.strip()} — you are training {picked['name']}.")
                    rerun()

st.divider()

# --------------------------------------------------------- training rounds
st.markdown("**Training results**")
rounds = record.get("rounds") if isinstance(record.get("rounds"), list) else []
if rounds:
    st.dataframe(
        pd.DataFrame([{
            "Date": str(r.get("date") or "")[:10],
            "Trainer": r.get("trainer") or "—",
            "What was given": r.get("kind") or "—",
            "Items": r.get("items") or 0,
            "Accuracy after": (f"{float(r['accuracy']):.0f}%"
                               if str(r.get("accuracy") or "").strip() not in ("", "None")
                               else "not measured"),
            "Notes": str(r.get("notes") or "")[:70],
        } for r in sorted(rounds, key=lambda r: str(r.get("date") or ""), reverse=True)]),
        hide_index=True, use_container_width=True)
else:
    st.caption("No training logged yet. The first round is the one that moves readiness.")

with st.form("round_form", clear_on_submit=True):
    st.markdown("**Log a training round**")
    row = st.columns([1, 1.1, 1.7], gap="small")
    when = row[0].date_input("When", value=date.today())
    trainer = row[1].text_input("Trainer", placeholder="Your name")
    kind = row[2].selectbox("What did you give it?", training.TRAINING_KINDS)

    row2 = st.columns([1, 1.2, 2.4], gap="small")
    items = row2[0].number_input("How many items?", min_value=0, step=5, value=0)
    # Optional on purpose: a round that supplied examples without re-measuring
    # is still worth recording, and readiness skips unmeasured rounds rather
    # than treating them as a score of zero.
    measured = row2[1].number_input("Accuracy after (%) — leave 0 if not measured",
                                    min_value=0.0, max_value=100.0, step=1.0, value=0.0)
    notes = row2[2].text_input("Notes", placeholder="What it still gets wrong")

    if st.form_submit_button("📈  Log this round", type="primary", use_container_width=True):
        if not trainer.strip():
            st.error("Put the trainer's name in.")
        else:
            entry = store.setdefault(picked["id"], {})
            entry.setdefault("rounds", []).append({
                "date": when.isoformat(),
                "trainer": trainer.strip(),
                "kind": kind,
                "items": int(items),
                "accuracy": float(measured) if measured > 0 else None,
                "notes": notes.strip(),
            })
            if trainer.strip() not in entry.setdefault("trainers", []):
                entry["trainers"].append(trainer.strip())
            entry["updated_at"] = datetime.now(timezone.utc).isoformat()
            save_trainers(store)
            st.session_state["tr_flash"] = "Round logged — readiness updated."
            rerun()
