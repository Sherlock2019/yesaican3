"""Current POC — every proof of concept being built, and where it runs.

The pipeline page answers "how far has this got". This one answers the build
questions instead: whose repo, what platform, is it up, who owns it. Same POC
records, different question — so the details live on the POC rather than being
scattered across notes nobody can aggregate.
"""

from __future__ import annotations

import html
from typing import Any

import streamlit as st

import json
from pathlib import Path

from services.shared.pipeline import (
    POC_PLATFORMS,
    POC_STATUSES,
    STAGES,
    blueprint_for,
    draft_poc,
    pipeline_rows,
    poc_progress,
    promote_to_agent,
    stage_of,
)
from services.ui.utils.auth_gate import require_auth
from services.ui.utils.meta_store import load_json, save_json
from services.ui.utils.page_template import empty_state, page_chrome

SUBMISSIONS_FILE = "how_ai_help_submissions.json"
AGENTS_PATH = Path(__file__).resolve().parents[1] / "data" / "agents.json"
STAGE_LABELS = {key: (label, icon) for key, label, _hint, icon in STAGES}


def load_submissions() -> list[dict]:
    data = load_json(SUBMISSIONS_FILE, [])
    return data if isinstance(data, list) else []


def save_submissions(records: list[dict]) -> None:
    save_json(SUBMISSIONS_FILE, records)


def load_agents() -> list[dict]:
    if not AGENTS_PATH.exists():
        return []
    try:
        data = json.loads(AGENTS_PATH.read_text(encoding="utf-8"))
        return [row for row in data if isinstance(row, dict)] if isinstance(data, list) else []
    except Exception:
        return []


def save_agents(records: list[dict]) -> None:
    AGENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    AGENTS_PATH.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


def rerun() -> None:
    getattr(st, "rerun", getattr(st, "experimental_rerun", lambda: None))()


def _e(value: Any) -> str:
    return html.escape(str(value if value is not None else ""))


def _c(markup: str) -> str:
    return "".join(line.strip() for line in str(markup).splitlines())


POC_CSS = """
<style>
.pk-wrap { background:var(--pc-surface); border:1px solid var(--pc-rule); border-radius:16px;
           box-shadow:var(--pc-shadow); overflow-x:auto; margin:0 0 1.2rem; }
.pk-tbl { width:100%; border-collapse:collapse; font-size:.84rem; min-width:1120px; }
.pk-tbl thead th { background:var(--pc-surface-alt); color:var(--pc-ink-faint); font-size:.72rem;
                   font-weight:650; letter-spacing:.03em; text-transform:uppercase; text-align:left;
                   padding:.62rem .75rem; border-bottom:1px solid var(--pc-rule); white-space:nowrap; }
.pk-tbl td { padding:.7rem .75rem; border-bottom:1px solid var(--pc-rule);
             color:var(--pc-ink-soft); vertical-align:top; }
.pk-tbl tr:last-child td { border-bottom:none; }
.pk-tbl .nm { font-weight:650; color:var(--pc-ink); }
.pk-tbl .sub { display:block; font-size:.73rem; color:var(--pc-ink-faint); margin-top:.12rem; }
.pk-mono { font-family:ui-monospace,"SF Mono",Consolas,monospace; font-size:.76rem;
           color:var(--pc-indigo-dark); word-break:break-all; }
.pk-none { color:var(--pc-ink-faint); font-style:italic; }
.pk-st { display:inline-block; border-radius:999px; padding:.12rem .5rem; font-size:.71rem;
         font-weight:700; white-space:nowrap; }
.pk-st.notstarted { background:var(--pc-surface-alt); color:var(--pc-ink-faint); }
.pk-st.building   { background:#fffbeb; color:#92400e; }
.pk-st.testing    { background:var(--pc-indigo-wash); color:var(--pc-indigo-dark); }
.pk-st.live       { background:var(--pc-green-wash); color:var(--pc-green); }
.pk-st.parked     { background:#fef2f2; color:#b91c1c; }
.pk-plat { display:inline-block; border:1px solid var(--pc-rule); border-radius:6px;
           padding:.08rem .4rem; font-size:.73rem; }

/* ---- ontology blueprint (moved from the pipeline page) ---- */
.pk-bp { background:var(--pc-surface); border:1px solid var(--pc-rule); border-radius:16px;
         padding:1.1rem 1.2rem; box-shadow:var(--pc-shadow); margin:0 0 1rem; }
.pk-bp h3 { font-size:1.05rem; font-weight:700; color:var(--pc-ink); margin:0 0 .15rem; }
.pk-bp .pat { display:inline-block; background:var(--pc-indigo); color:#fff; font-size:.76rem;
              font-weight:650; border-radius:8px; padding:.2rem .6rem; margin:.3rem 0 .8rem; }
.pk-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); gap:.9rem; }
.pk-box { border:1px solid var(--pc-rule); border-radius:11px; padding:.65rem .75rem; }
.pk-box .t { font-size:.72rem; font-weight:700; color:var(--pc-ink-faint); letter-spacing:.03em;
             text-transform:uppercase; margin:0 0 .35rem; }
.pk-box ul { margin:0; padding-left:1rem; }
.pk-box li { font-size:.79rem; color:var(--pc-ink-soft); line-height:1.45; margin-bottom:.2rem; }
.pk-obj { display:inline-block; border:1px solid var(--pc-rule); border-radius:7px; font-size:.72rem;
          color:var(--pc-ink-soft); padding:.12rem .4rem; margin:0 .25rem .25rem 0;
          background:var(--pc-surface-alt); }
.pk-guard { background:#fffbeb; border:1px solid #fde68a; border-radius:11px; padding:.6rem .75rem;
            font-size:.79rem; color:#92400e; margin-top:.85rem; }
.pk-steps { counter-reset:s; list-style:none; margin:0; padding:0; }
.pk-steps li { counter-increment:s; position:relative; padding-left:1.7rem; font-size:.82rem;
               color:var(--pc-ink-soft); line-height:1.5; margin-bottom:.35rem; }
.pk-steps li::before { content:counter(s); position:absolute; left:0; top:.05rem; width:1.15rem;
  height:1.15rem; border-radius:50%; background:var(--pc-indigo-wash); color:var(--pc-indigo-dark);
  font-size:.68rem; font-weight:700; display:flex; align-items:center; justify-content:center; }
</style>
"""


def blueprint_card(challenge: dict, poc: dict | None) -> str:
    """The ontology blueprint behind a POC — moved here whole from the pipeline.

    Shown before a POC exists as well as after: it is what the draft will be
    built from, so seeing it is how somebody decides whether to draft at all.
    """
    blueprint = blueprint_for(challenge.get("pain_type"))
    source = poc or blueprint
    objects = "".join(f"<span class='pk-obj'>{_e(o)}</span>" for o in source.get("objects", []))
    caps = "".join(f"<li>{_e(c)}</li>" for c in source.get("capabilities", []))
    tools = "".join(f"<li>{_e(t)}</li>" for t in source.get("tools", []))
    steps = "".join(f"<li>{_e(s)}</li>" for s in (poc or {}).get("build_steps", []))
    steps_box = (
        f"<div class='pk-box' style='margin-top:.9rem'><p class='t'>Build plan</p>"
        f"<ol class='pk-steps'>{steps}</ol></div>" if steps else ""
    )
    name = (poc or {}).get("name") or "Ontology blueprint"
    return _c(f"""
    <div class="pk-bp">
      <h3>{_e(name)}</h3>
      <span class="pat">{_e(source.get('pattern', ''))}</span>
      <div class="pk-grid">
        <div class="pk-box"><p class="t">Ontology objects</p>{objects}</div>
        <div class="pk-box"><p class="t">Capabilities</p><ul>{caps}</ul></div>
        <div class="pk-box"><p class="t">Tools to wire up</p><ul>{tools}</ul></div>
      </div>
      {steps_box}
      <div class="pk-guard">🛡 {_e(source.get('guardrail', ''))}</div>
    </div>
    """)


def _status_class(status: str) -> str:
    return str(status or "Not started").lower().replace(" ", "")


def poc_table(rows: list[dict]) -> str:
    body = []
    for row in rows:
        repo = row.get("github") or ""
        demo = row.get("demo_url") or ""
        platform = row.get("platform") or ""
        owner = row.get("owner") or ""
        status = row.get("poc_status") or "Not started"
        stage_label, stage_icon = STAGE_LABELS[row["stage"]]
        criteria = f"{row['met']}/{row['total']}" if row["total"] else "—"

        body.append(_c(f"""
        <tr>
          <td><span class='nm'>{_e(row['poc_name'] or row['title'])}</span>
              <span class='sub'>from “{_e(row['title'])}”</span></td>
          <td><span class='pk-st {_status_class(status)}'>{_e(status)}</span></td>
          <td>{f"<span class='pk-mono'>{_e(repo)}</span>" if repo
               else "<span class='pk-none'>no repo</span>"}</td>
          <td>{f"<span class='pk-plat'>{_e(platform)}</span>" if platform
               else "<span class='pk-none'>not deployed</span>"}</td>
          <td>{f"<span class='pk-mono'>{_e(demo)}</span>" if demo
               else "<span class='pk-none'>—</span>"}</td>
          <td>{_e(owner) if owner else "<span class='pk-none'>unassigned</span>"}</td>
          <td>{_e(row.get('effort_days') or '—')} d</td>
          <td>{criteria}</td>
          <td>{stage_icon} {_e(stage_label)}</td>
        </tr>
        """))

    return _c(f"""
    <div class="pk-wrap">
      <table class="pk-tbl">
        <thead><tr>
          <th>POC</th><th>Status</th><th>GitHub</th><th>Platform</th><th>Demo URL</th>
          <th>Owner</th><th>Build</th><th>Criteria</th><th>Pipeline stage</th>
        </tr></thead>
        <tbody>{''.join(body)}</tbody>
      </table>
    </div>
    """)


# --------------------------------------------------------------------------
# page
# --------------------------------------------------------------------------

st.set_page_config(page_title="Current POC — YES AI CAN", page_icon="🧪", layout="wide")
require_auth()

page_chrome(
    "poc_hub",
    "Current POC",
    "Every proof of concept being built — repo, platform, owner and whether it is up.",
)
st.markdown(POC_CSS, unsafe_allow_html=True)

flash = st.session_state.pop("poc_flash", None)
if flash:
    st.success(flash)


submissions = load_submissions()
if not submissions:
    st.markdown(
        empty_state("🧪", "No painpoints yet",
                    "Submit one first — a POC is drafted from its ontology blueprint, "
                    "so there has to be a painpoint to draft from."),
        unsafe_allow_html=True)
    st.stop()

# The table lists only records that actually have a POC: a painpoint with no
# blueprint is not a proof of concept, and listing it would bury the ones
# being built. The picker below covers everything, because drafting a new POC
# is exactly the case where one does not exist yet.
with_poc = [record for record in submissions if record.get("poc")]
rows = pipeline_rows(with_poc) if with_poc else []

live = sum(1 for r in rows if r.get("poc_status") == "Live")
deployed = sum(1 for r in rows if r.get("platform"))
with_repo = sum(1 for r in rows if r.get("github"))

metric_cols = st.columns(4, gap="small")
metric_cols[0].metric("POCs", len(rows))
metric_cols[1].metric("With a repo", with_repo)
metric_cols[2].metric("Deployed somewhere", deployed)
metric_cols[3].metric("Live", live)

if rows:
    st.markdown(poc_table(rows), unsafe_allow_html=True)
else:
    st.markdown(
        empty_state("🧪", "No POCs drafted yet",
                    "Pick a painpoint below and press “Draft POC from blueprint”. "
                    "It appears in this table straight away."),
        unsafe_allow_html=True)

st.divider()

# ------------------------------------------------------- pick what to work on
order = [record.get("id") for record in submissions]
labels = {
    record.get("id"): (
        f"{STAGE_LABELS[stage_of(record)][1]}  "
        f"{(record.get('poc') or {}).get('name') or record.get('title') or 'Untitled'}"
    )
    for record in submissions
}
if st.session_state.get("poc_selected") not in order:
    st.session_state["poc_selected"] = order[0]

picker_col, _spacer = st.columns([2, 3])
selected_id = picker_col.selectbox(
    "Work on", order, format_func=lambda i: labels.get(i, str(i)), key="poc_selected")
record = next((r for r in submissions if r.get("id") == selected_id), submissions[0])
poc = record.get("poc")
stage = stage_of(record)

st.markdown(f"### {record.get('title', 'Untitled')}")
met, total = poc_progress(poc or {})
st.caption(
    f"{record.get('category') or '—'} · stage: **{STAGE_LABELS[stage][0]}**"
    + (f" · {met}/{total} acceptance criteria met" if total else "")
)

st.markdown(blueprint_card(record, poc), unsafe_allow_html=True)

action_col, detail_col = st.columns([1, 2], gap="medium")

with action_col:
    if stage == "captured":
        st.markdown("**Step 1 — draft the POC**")
        st.caption(
            "Joins the ontology blueprint for this pain type with the baseline and "
            "outcomes captured at intake. Instant and repeatable — no model call."
        )
        if st.button("🧪  Draft POC from blueprint", type="primary", use_container_width=True):
            record["poc"] = draft_poc(record)
            save_submissions(submissions)
            st.session_state["poc_flash"] = (
                f"POC drafted — **{record['poc']['name']}** "
                f"({record['poc']['pattern']}), about {record['poc']['effort_days']} days to build."
            )
            rerun()

    elif stage in ("poc", "proven") and poc:
        st.markdown(f"**Step 2 — prove it** ({met}/{total})")
        st.caption(f"Estimated build: **{poc.get('effort_days', '—')} days**."
                   + (f" Reuses {', '.join(poc['reuse'])}." if poc.get("reuse") else ""))

        changed = False
        for index, criterion in enumerate(poc.get("acceptance", [])):
            before = criterion.get("before")
            target = criterion.get("target")
            hint = ""
            if before not in (None, "") and target not in (None, ""):
                hint = f" ({before} → {target} {criterion.get('unit', '')})".rstrip()
            new_value = st.checkbox(
                f"{criterion['label']}{hint}",
                value=bool(criterion.get("met")),
                key=f"poc_ac_{selected_id}_{criterion['key']}_{index}",
            )
            if new_value != bool(criterion.get("met")):
                criterion["met"] = new_value
                changed = True
        if changed:
            save_submissions(submissions)
            rerun()

        if stage == "proven":
            st.success("Acceptance met — ready to publish.")
            if st.button("🚀  Publish to Community Agent Library", type="primary",
                         use_container_width=True):
                agent = promote_to_agent(record, poc)
                agents = load_agents()
                agents.insert(0, agent)
                save_agents(agents)
                record["published_agent"] = agent["agent"]
                save_submissions(submissions)
                st.session_state["poc_flash"] = (
                    f"🚀 Published **{agent['agent']}** to the Community Agent Library "
                    f"({agent['sector']} / {agent['industry']}). It is now in the reuse pool."
                )
                rerun()

    elif stage == "published":
        st.markdown("**Live in the library**")
        st.success(f"🚀 {record.get('published_agent')}")
        st.caption(
            "It is now in the reuse pool, so the next matching painpoint is scored "
            "as cheaper to build — which is the point of the loop."
        )

with detail_col:
    baseline = record.get("baseline") or {}
    opportunity = record.get("opportunity") or {}
    m = st.columns(4)
    m[0].metric("Pain score", baseline.get("pain_score", "—"))
    m[1].metric("Hours / year", f"{float(baseline.get('annual_hours') or 0):,.0f}")
    m[2].metric("Opportunity", opportunity.get("score", "—"))
    m[3].metric("Build days", (poc or {}).get("effort_days", "—"))
    if record.get("description"):
        st.markdown(f"> {record['description']}")

# ---------------------------------------------------------------- the editor
if poc:
    st.divider()
    st.markdown("### ✎ POC details")

    with st.form("poc_details"):
        row_a = st.columns(2, gap="small")
        status = row_a[0].selectbox(
            "Status", list(POC_STATUSES),
            index=list(POC_STATUSES).index(poc.get("status"))
            if poc.get("status") in POC_STATUSES else 0)
        owner = row_a[1].text_input("Owner", value=str(poc.get("owner") or ""),
                                    placeholder="Who is building it")

        row_b = st.columns(2, gap="small")
        github = row_b[0].text_input("GitHub repo", value=str(poc.get("github") or ""),
                                     placeholder="owner/repo")
        platform_options = list(POC_PLATFORMS)
        current_platform = str(poc.get("platform") or "")
        if current_platform and current_platform not in platform_options:
            platform_options.append(current_platform)
        platform = row_b[1].selectbox(
            "Platform deployed", [""] + platform_options,
            index=(platform_options.index(current_platform) + 1) if current_platform else 0,
            format_func=lambda name: name or "Not deployed")

        demo_url = st.text_input("Demo URL", value=str(poc.get("demo_url") or ""),
                                 placeholder="https://…")
        notes = st.text_area("Notes", value=str(poc.get("notes") or ""), height=90,
                             placeholder="What is left, what is blocked, what to watch")

        saved = st.form_submit_button("Save POC details", type="primary",
                                      use_container_width=True)

    if saved:
        poc.update({
            "status": status,
            "owner": owner.strip(),
            "github": github.strip(),
            "platform": platform,
            "demo_url": demo_url.strip(),
            "notes": notes.strip(),
        })
        record["poc"] = poc
        save_submissions(submissions)
        st.session_state["poc_flash"] = (
            f"Saved — **{poc.get('name', 'POC')}** is {status.lower()}"
            + (f" on {platform}." if platform else ".")
        )
        rerun()
