# Admin & REX 2.0 Integration — YES AI CAN
# Admin views and metadata exports for REX 2.0

import streamlit as st
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import pandas as pd

from collections import Counter

from services.shared import insights, similarity
from services.shared.pain_metrics import IMPROVEMENT_TARGETS
from services.shared.pipeline import stage_of
from services.ui.utils.meta_store import load_json
from services.ui.utils.page_template import page_chrome

st.set_page_config(
    page_title="Admin & REX 2.0 — YES AI CAN",
    layout="wide"
)

# Metadata storage
META_DIR = Path(__file__).parent.parent.parent.parent / ".sandbox_meta"
HUMANS_FILE = META_DIR / "humans.json"
PROJECTS_FILE = META_DIR / "projects.json"
AGENTS_FILE = META_DIR / "agents.json"
PATTERNS_FILE = META_DIR / "patterns.json"
STATS_FILE = META_DIR / "stats.json"
META_DIR.mkdir(exist_ok=True)

def load_humans() -> List[Dict]:
    if HUMANS_FILE.exists():
        try:
            with open(HUMANS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def load_projects() -> List[Dict]:
    if PROJECTS_FILE.exists():
        try:
            with open(PROJECTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def load_agents() -> List[Dict]:
    if AGENTS_FILE.exists():
        try:
            with open(AGENTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def load_patterns() -> List[Dict]:
    if PATTERNS_FILE.exists():
        try:
            with open(PATTERNS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def load_stats() -> Dict:
    if STATS_FILE.exists():
        try:
            with open(STATS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_stats(stats: Dict):
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)


def load_library_agents() -> List[Dict]:
    """The production library — the file the pipeline publishes proven POCs to.

    Not the same store as load_agents() above, which reads the admin metadata
    copy. Counting "cures in production" from that one reported zero however
    many had shipped.
    """
    path = Path(__file__).resolve().parents[1] / "data" / "agents.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return [row for row in data if isinstance(row, dict)] if isinstance(data, list) else []
    except Exception:
        return []


# Page header
page_chrome("admin_rex", "PainPoints Metrics Dashboard",
            "What our Community has submitted, solved and shipped.")
st.markdown("---")

# The admin password gate is gone. It compared against "admin123" hard-coded in
# this file, so it kept nobody out and told anyone who read the source the
# shared secret. Access belongs at the reverse proxy — see auth_gate's docstring.

submissions = load_json("how_ai_help_submissions.json", [])
solutions = load_json("how_ai_help_solutions.json", [])
library = load_library_agents()

humans = load_humans()
projects = load_projects()
agents = load_agents()
patterns = load_patterns()
stats = load_stats()

stats['total_humans'] = len(humans)
stats['total_projects'] = len(projects)
stats['total_agents'] = len(agents)
stats['total_patterns'] = len(patterns)
stats['last_updated'] = datetime.now().isoformat()
save_stats(stats)

summary = insights.overview(submissions, solutions, library)

# High enough to mean "every unit". The per-unit views are read as a complete
# picture — their hours are expected to add up to the headline total — so a
# silent top-10 cut makes them lie by omission rather than merely abbreviate.
ALL_UNITS = 1000

# ---------------------------------------------------------------- live stats
st.subheader("Current projects")
row_a = st.columns(4, gap="small")
row_a[0].metric("Painpoints on the board", summary["painpoints_total"])
row_a[1].metric(f"New (last {insights.NEW_WINDOW_DAYS}d)", summary["painpoints_new"])
row_a[2].metric("Solved", summary["painpoints_solved"])
row_a[3].metric("Still open", summary["painpoints_open"])

row_b = st.columns(4, gap="small")
row_b[0].metric("Cures proposed", summary["cures_proposed"])
row_b[1].metric("Current POCs", summary["pocs_current"])
row_b[2].metric("POCs proven", summary["pocs_proven"])
row_b[3].metric("In production library", summary["in_production_library"])

row_c = st.columns(3, gap="small")
row_c[0].metric("Hours/year on the board", f"{summary['hours_on_the_board']:,.0f}")
row_c[1].metric("Hours being addressed", f"{summary['hours_addressed']:,.0f}")
row_c[2].metric("Agents in library", summary["agents_total"])

st.divider()

# ------------------------------------------------------------------- charts
st.subheader("Where the pain is")

chart_left, chart_right = st.columns(2, gap="medium")

with chart_left:
    st.markdown("**Hours a year, by business unit**")
    # by_business_unit defaults to the top 10. There are more units than that,
    # and a chart that silently drops five of them while the total above it
    # counts all fifteen is worse than no chart.
    units = insights.by_business_unit(submissions, limit=ALL_UNITS)
    if units:
        # Hours rather than a count of painpoints: one unit with a 2,000-hour
        # problem matters more than another with three small ones, and a bar
        # chart of counts would say the opposite.
        frame = (pd.DataFrame(units)
                 .sort_values("annual_hours", ascending=False)
                 .set_index("unit")[["annual_hours"]])
        st.bar_chart(frame.rename(columns={"annual_hours": "Hours / year"}),
                     color="#6d5bd0", height=300)
    else:
        st.info("No unit recorded on any painpoint yet.")

with chart_right:
    st.markdown("**Where everything sits in the pipeline**")
    stage_counts = Counter(stage_of(record) for record in submissions)
    # Numbered labels because st.bar_chart sorts its index alphabetically, which
    # rendered the funnel as Captured / In library / POC drafted / Proven — the
    # stages in an order the work never actually travels in.
    ordered = [(label, stage_counts.get(key, 0)) for key, label in (
        ("captured", "1 Captured"), ("poc", "2 POC drafted"),
        ("proven", "3 Proven"), ("published", "4 In library"))]
    st.bar_chart(pd.DataFrame(ordered, columns=["Stage", "Painpoints"]).set_index("Stage"),
                 color="#2fa37a", height=300)

st.markdown("**Painpoints submitted over time**")
dated = []
for record in submissions:
    raw = str(record.get("created_at") or "").strip()
    if not raw:
        continue
    try:
        moment = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        continue
    dated.append(moment.date())
if dated:
    # Cumulative, not per-day: with a handful of submissions a daily bar chart
    # is mostly zeros and reads as though nothing is happening.
    series = pd.Series(1, index=pd.to_datetime(sorted(dated)))
    st.area_chart(series.resample("D").sum().cumsum().rename("Painpoints on the board"),
                  color="#6d5bd0", height=240)
else:
    st.caption("No submission dates recorded yet.")

st.divider()

# ------------------------------------------------- painpoint / cure register
st.subheader("Painpoints and the cures found for them")
st.caption(
    "One row per painpoint: what it costs today, who is curing it, and what a fix "
    "would return. **Time** and **Steps** show today's baseline and the target a fix "
    "aims at. **Est. gain** is the conservative half-target figure — hours a year "
    "returned if a fix only ever achieves half of what it targets — and it is shown "
    "only where somebody has actually proposed a cure. These are targets derived from "
    "the submitter's own baseline, not measurements."
)

cures_by_challenge: Dict[str, List[Dict]] = {}
for cure in solutions:
    key = str(cure.get("challenge_id") or "")
    if key:
        cures_by_challenge.setdefault(key, []).append(cure)


def _unit_of(record: Dict) -> str:
    context = record.get("twin_context") or {}
    submitter = record.get("submitter")
    submitter = submitter if isinstance(submitter, dict) else {}
    return str(context.get("business_unit") or submitter.get("department") or "—")


register_rows = []
for record in submissions:
    baseline = record.get("baseline") or {}
    minutes = float(baseline.get("minutes_per_task") or 0)
    steps = int(baseline.get("steps") or 0)
    hours = float(baseline.get("annual_hours") or 0)
    attached = cures_by_challenge.get(str(record.get("id") or ""), [])

    # The same target multipliers the submitter was shown in the AI preview, so
    # the dashboard cannot quote a different number to the same person.
    time_cell = "—"
    if minutes:
        target_minutes = max(1, round(minutes * IMPROVEMENT_TARGETS["time_per_task"]))
        time_cell = f"{minutes:g} → {target_minutes:g} min"
    steps_cell = "—"
    if steps:
        steps_cell = f"{steps} → {max(1, round(steps * IMPROVEMENT_TARGETS['steps_per_task']))}"

    lead = attached[0] if attached else {}
    register_rows.append({
        "Painpoint": str(record.get("title") or "Untitled")[:60],
        "Business unit": _unit_of(record),
        "Cure found": (str(lead.get("what_features") or lead.get("challenge") or "—")[:55]
                       if attached else "— none yet"),
        "Helper": (lead.get("helper") or lead.get("author") or "—") if attached else "—",
        "Cures": len(attached),
        "Status": (lead.get("status") or "Draft") if attached else "Open",
        "Time / task": time_cell,
        "Steps / task": steps_cell,
        "Hours / year": f"{hours:,.0f}" if hours else "—",
        # Only claimed where a cure exists: an unclaimed painpoint returns
        # nothing, and showing a gain against it would be counting a saving
        # nobody is working on.
        "Est. gain h/yr": (f"{float(baseline.get('annual_hours_at_half') or 0):,.0f}"
                           if attached and hours else "—"),
    })

if register_rows:
    register_rows.sort(key=lambda row: -float(str(row["Hours / year"]).replace(",", "") or 0)
                       if row["Hours / year"] != "—" else 0)
    st.dataframe(pd.DataFrame(register_rows), hide_index=True, use_container_width=True,
                 height=min(60 + 35 * len(register_rows), 620))

    claimed = [r for r in register_rows if r["Est. gain h/yr"] != "—"]
    total_gain = sum(float(r["Est. gain h/yr"].replace(",", "")) for r in claimed)
    foot = st.columns(3, gap="small")
    foot[0].metric("Painpoints with a cure", f"{len(claimed)} of {len(register_rows)}")
    foot[1].metric("Est. gain, cured only", f"{total_gain:,.0f} h/yr")
    foot[2].metric("Still unclaimed", len(register_rows) - len(claimed))
else:
    st.info("No painpoints on the board yet.")

st.divider()

# --------------------------------------------------------------- AI analysis
st.subheader("🤖 AI Analysis")
st.caption(
    "Reads every submission, cure and published agent, and cross-references them "
    "against the business-flow ontology to find where the same pain is felt twice."
)

# Runs on load rather than waiting for a click. It is a few milliseconds of set
# arithmetic over a board this size, and a dashboard that shows nothing until
# you press a button is a dashboard most people never see the interesting half
# of. The button stays, to recompute after somebody submits.
if "rex_analysis" not in st.session_state:
    st.session_state["rex_analysis"] = insights.analyse(submissions, solutions, library)

if st.button("🔄  Refresh analysis", type="primary"):
    st.session_state["rex_analysis"] = insights.analyse(submissions, solutions, library)

analysis = st.session_state.get("rex_analysis")
if analysis:
    st.markdown("#### Headline")
    st.dataframe(
        pd.DataFrame([
            {"Metric": "New painpoints", "Value": analysis["overview"]["painpoints_new"]},
            {"Metric": "Painpoints solved", "Value": analysis["overview"]["painpoints_solved"]},
            {"Metric": "Current POCs", "Value": analysis["overview"]["pocs_current"]},
            {"Metric": "Cures in production library",
             "Value": analysis["overview"]["in_production_library"]},
        ]),
        hide_index=True, use_container_width=True)

    left, right = st.columns(2, gap="medium")

    with left:
        st.markdown("#### Most active people")
        people = analysis["people"]
        if people:
            st.dataframe(
                pd.DataFrame(people).rename(columns={
                    "name": "Person", "submitted": "Painpoints",
                    "cures": "Cures", "total": "Total"}),
                hide_index=True, use_container_width=True)
        else:
            st.info("Nobody has put their name to a submission or a cure yet.")

    with right:
        st.markdown("#### Business units with the most pain")
        # Not analysis["units"], which takes the default top 10 and would hide
        # units while the headline hours above still counted them.
        units = insights.by_business_unit(submissions, limit=ALL_UNITS)
        st.caption(f"All {len(units)} units. Ranked by painpoint count, then hours.")
        if units:
            frame = pd.DataFrame(units)
            frame["annual_hours"] = frame["annual_hours"].map(lambda v: f"{v:,.0f}")
            st.dataframe(
                frame.rename(columns={
                    "unit": "Business unit", "painpoints": "Painpoints",
                    "annual_hours": "Hours / year"}),
                hide_index=True, use_container_width=True)
        else:
            st.info("No unit recorded on any painpoint yet.")

    st.markdown("#### Top 10 painpoints by cross-unit reach")
    st.caption(
        "Ranked by how many business units feel it, using the ontology map — the flow "
        "edge it sits on, where its output goes, and any other unit reporting the same "
        "kind of pain. A problem five teams share is worth fixing before a bigger one "
        "that bothers a single team."
    )
    reach = analysis["top_reach"]
    if reach:
        frame = pd.DataFrame(reach)
        frame["unit_names"] = frame["unit_names"].map(lambda names: ", ".join(names))
        frame["annual_hours"] = frame["annual_hours"].map(lambda v: f"{v:,.0f}")
        frame["reach_hours"] = frame["reach_hours"].map(lambda v: f"{v:,.0f}")
        st.dataframe(
            frame[["title", "unit", "pain_type", "units", "unit_names",
                   "annual_hours", "reach_hours", "score"]].rename(columns={
                "title": "Painpoint", "unit": "Owned by", "pain_type": "Type",
                "units": "Units reached", "unit_names": "Which units",
                "annual_hours": "Hours / year", "reach_hours": "Reach-weighted hours",
                "score": "Opportunity"}),
            hide_index=True, use_container_width=True)
    else:
        st.info("Nothing to rank yet.")

    st.markdown("#### Painpoints felt across departments")
    cross = analysis["cross_department"]
    if cross:
        frame = pd.DataFrame(cross)
        frame["unit_names"] = frame["unit_names"].map(lambda names: ", ".join(names))
        st.dataframe(
            frame[["title", "units", "unit_names", "pain_type"]].rename(columns={
                "title": "Painpoint", "units": "Units", "unit_names": "Which units",
                "pain_type": "Type"}),
            hide_index=True, use_container_width=True)
    else:
        st.info("No painpoint currently reaches more than one unit.")

    st.markdown("#### Most similar painpoints")
    st.caption(
        "Scored on the shape of the work — what arrives, what is done to it, where it "
        "goes — rather than on wording, because two teams rarely describe the same job "
        "in the same words. **Reusable** means one agent could serve both."
    )
    pairs = similarity.painpoint_pairs(submissions, limit=15)
    if pairs:
        frame = pd.DataFrame(pairs)
        frame["reasons"] = frame["reasons"].map(lambda items: " · ".join(items))
        st.dataframe(
            frame[["score", "band_label", "a", "a_unit", "b", "b_unit",
                   "reusable", "cross_unit", "reasons"]].rename(columns={
                "score": "Similarity", "band_label": "What it means",
                "a": "Painpoint A", "a_unit": "A unit",
                "b": "Painpoint B", "b_unit": "B unit",
                "reusable": "One agent could serve both",
                "cross_unit": "Different units", "reasons": "Why"}),
            hide_index=True, use_container_width=True)
    else:
        st.info("No two painpoints look alike yet.")

st.divider()
