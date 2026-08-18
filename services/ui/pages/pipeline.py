"""The pipeline board: ontology + pain point → POC → proven → agent.

One page for the whole lifecycle, so nobody has to hold the workflow in their
head. Every action here writes back to the same files the rest of the app reads
— a POC drafted on this page shows up on the pain point, and an agent published
here is immediately offered as reuse against the next similar submission.
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

import streamlit as st

from services.shared.pipeline import (
    STAGES,
    STAGE_KEYS,
    blueprint_for,
    draft_poc,
    pipeline_counts,
    pipeline_rows,
    poc_progress,
    promote_to_agent,
    stage_of,
)
from services.ui.utils.auth_gate import require_auth
from services.ui.utils.meta_store import load_json, save_json
from services.ui.utils.page_template import page_chrome

SUBMISSIONS_FILE = "how_ai_help_submissions.json"
AGENTS_PATH = Path(__file__).resolve().parents[1] / "data" / "agents.json"


# --------------------------------------------------------------------------
# storage
# --------------------------------------------------------------------------

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
    AGENTS_PATH.write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def rerun() -> None:
    getattr(st, "rerun", getattr(st, "experimental_rerun", lambda: None))()


# --------------------------------------------------------------------------
# presentation
# --------------------------------------------------------------------------

PIPELINE_CSS = """
<style>
/* ---- the flow ribbon ---- */
.pl-flow { display:grid; grid-template-columns:auto repeat(4, 1fr); gap:.55rem; align-items:stretch;
           margin:0 0 1.4rem; }
.pl-src { background:linear-gradient(160deg,#3a2a8c,#241a5e); border-radius:14px; padding:.85rem .9rem;
          color:#fff; min-width:150px; display:flex; flex-direction:column; justify-content:center; }
.pl-src b { display:block; font-size:.84rem; font-weight:700; margin-bottom:.2rem; }
.pl-src span { font-size:.73rem; color:#c3bce6; line-height:1.35; }
.pl-node { position:relative; background:var(--pc-surface); border:1px solid var(--pc-rule);
           border-radius:14px; padding:.85rem .95rem; box-shadow:var(--pc-shadow); }
.pl-node.on { border-color:var(--pc-indigo); box-shadow:0 0 0 3px rgba(91,63,214,.10); }
.pl-node .ic { font-size:1.05rem; }
.pl-node .lb { font-size:.82rem; font-weight:700; color:var(--pc-ink); margin:.2rem 0 .05rem; }
.pl-node .ct { font-size:1.6rem; font-weight:750; color:var(--pc-indigo); line-height:1.1;
               font-variant-numeric:tabular-nums; }
.pl-node .hint { font-size:.72rem; color:var(--pc-ink-faint); line-height:1.35; margin-top:.15rem; }
.pl-node::after { content:"›"; position:absolute; right:-.52rem; top:50%; transform:translateY(-50%);
                  font-size:1.2rem; color:var(--pc-ink-faint); z-index:2; }
.pl-node:last-child::after { content:none; }

/* ---- workflow table ---- */
.pl-tbl-wrap { background:var(--pc-surface); border:1px solid var(--pc-rule); border-radius:16px;
               box-shadow:var(--pc-shadow); overflow-x:auto; margin:0 0 1.2rem; }
.pl-tbl { width:100%; border-collapse:collapse; font-size:.84rem; min-width:1040px; }
.pl-tbl thead th { background:var(--pc-surface-alt); color:var(--pc-ink-faint); font-size:.73rem;
                   font-weight:650; letter-spacing:.03em; text-transform:uppercase; text-align:left;
                   padding:.65rem .75rem; border-bottom:1px solid var(--pc-rule); white-space:nowrap; }
.pl-tbl tbody td { padding:.7rem .75rem; border-bottom:1px solid var(--pc-rule);
                   color:var(--pc-ink-soft); vertical-align:middle; }
.pl-tbl tbody tr:last-child td { border-bottom:none; }
.pl-tbl tbody tr.sel { background:var(--pc-indigo-wash); }
.pl-tbl tbody tr.sel td { color:var(--pc-ink); }
.pl-tbl .ttl { font-weight:650; color:var(--pc-ink); }
.pl-tbl .sub { display:block; font-size:.73rem; color:var(--pc-ink-faint); margin-top:.1rem; }
.pl-tbl .num { text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }
.pl-tbl .pat { font-size:.76rem; color:var(--pc-indigo-dark); font-weight:600; }

/* stage badge — the one column people scan first */
.pl-st { display:inline-flex; align-items:center; gap:.3rem; border-radius:999px; padding:.15rem .55rem;
         font-size:.72rem; font-weight:700; white-space:nowrap; }
.pl-st.captured  { background:#eef2ff; color:#4338ca; }
.pl-st.poc       { background:#fffbeb; color:#92400e; }
.pl-st.proven    { background:var(--pc-green-wash); color:var(--pc-green); }
.pl-st.published { background:var(--pc-indigo); color:#fff; }

.pl-mini { width:74px; height:5px; border-radius:99px; background:#ececf4; overflow:hidden;
           display:inline-block; vertical-align:middle; margin-right:.4rem; }
.pl-mini span { display:block; height:100%; background:var(--pc-green); border-radius:99px; }
.pl-tag { display:inline-block; background:var(--pc-indigo-wash); color:var(--pc-indigo-dark);
          font-size:.68rem; font-weight:650; border-radius:6px; padding:.1rem .38rem; margin-right:.25rem; }

/* ---- POC table ---- */
.pl-poc-h { display:flex; align-items:baseline; gap:.6rem; margin:1.6rem 0 .2rem; }
.pl-poc-h b { font-size:1.05rem; font-weight:700; color:var(--pc-ink); }
.pl-poc-h span { font-size:.84rem; color:var(--pc-ink-faint); }
.pl-poc { width:100%; border-collapse:collapse; font-size:.84rem; min-width:1000px; }
.pl-poc thead th { background:var(--pc-surface-alt); color:var(--pc-ink-faint); font-size:.72rem;
                   font-weight:650; letter-spacing:.03em; text-transform:uppercase; text-align:left;
                   padding:.6rem .75rem; border-bottom:1px solid var(--pc-rule); white-space:nowrap; }
.pl-poc td { padding:.7rem .75rem; border-bottom:1px solid var(--pc-rule);
             color:var(--pc-ink-soft); vertical-align:top; }
.pl-poc tr:last-child td { border-bottom:none; }
.pl-poc .nm { font-weight:650; color:var(--pc-ink); }
.pl-poc .sub { display:block; font-size:.73rem; color:var(--pc-ink-faint); margin-top:.12rem; }
.pl-feat { display:inline-block; background:var(--pc-surface-alt); border:1px solid var(--pc-rule);
           border-radius:6px; padding:.08rem .38rem; font-size:.72rem; margin:0 .22rem .22rem 0; }
.pl-repo { font-family:ui-monospace,"SF Mono",Consolas,monospace; font-size:.76rem;
           color:var(--pc-indigo-dark); word-break:break-all; }
.pl-repo.none { color:var(--pc-ink-faint); font-style:italic; font-family:inherit; }

/* ---- blueprint detail ---- */
.pl-bp { background:var(--pc-surface); border:1px solid var(--pc-rule); border-radius:16px;
         padding:1.1rem 1.2rem; box-shadow:var(--pc-shadow); margin:0 0 1rem; }
.pl-bp h3 { font-size:1.05rem; font-weight:700; color:var(--pc-ink); margin:0 0 .15rem; }
.pl-bp .pat { display:inline-block; background:var(--pc-indigo); color:#fff; font-size:.76rem;
              font-weight:650; border-radius:8px; padding:.2rem .6rem; margin:.3rem 0 .8rem; }
.pl-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); gap:.9rem; }
.pl-box { border:1px solid var(--pc-rule); border-radius:11px; padding:.65rem .75rem; }
.pl-box .t { font-size:.72rem; font-weight:700; color:var(--pc-ink-faint); letter-spacing:.03em;
             text-transform:uppercase; margin:0 0 .35rem; }
.pl-box ul { margin:0; padding-left:1rem; }
.pl-box li { font-size:.79rem; color:var(--pc-ink-soft); line-height:1.45; margin-bottom:.2rem; }
.pl-obj { display:inline-block; border:1px solid var(--pc-rule); border-radius:7px; font-size:.72rem;
          color:var(--pc-ink-soft); padding:.12rem .4rem; margin:0 .25rem .25rem 0; background:var(--pc-surface-alt); }
.pl-guard { background:#fffbeb; border:1px solid #fde68a; border-radius:11px; padding:.6rem .75rem;
            font-size:.79rem; color:#92400e; margin-top:.85rem; }
.pl-steps { counter-reset:s; list-style:none; margin:0; padding:0; }
.pl-steps li { counter-increment:s; position:relative; padding-left:1.7rem; font-size:.82rem;
               color:var(--pc-ink-soft); line-height:1.5; margin-bottom:.35rem; }
.pl-steps li::before { content:counter(s); position:absolute; left:0; top:.05rem; width:1.15rem;
  height:1.15rem; border-radius:50%; background:var(--pc-indigo-wash); color:var(--pc-indigo-dark);
  font-size:.68rem; font-weight:700; display:flex; align-items:center; justify-content:center; }
</style>
"""


def _e(value: Any) -> str:
    return html.escape(str(value if value is not None else ""))


def _c(markup: str) -> str:
    """Strip indentation — markdown treats 4-space-indented lines as code."""
    return "".join(line.strip() for line in str(markup).splitlines())


def flow_ribbon(counts: dict[str, int], active: str | None) -> str:
    nodes = []
    for key, label, hint, icon in STAGES:
        cls = "pl-node on" if key == active else "pl-node"
        nodes.append(
            f"<div class='{cls}'><span class='ic'>{icon}</span>"
            f"<div class='lb'>{_e(label)}</div>"
            f"<div class='ct'>{counts.get(key, 0)}</div>"
            f"<div class='hint'>{_e(hint)}</div></div>"
        )
    return _c(f"""
    <div class="pl-flow">
      <div class="pl-src"><b>🧬 Ontology</b>
        <span>12 blueprints. Objects, pattern, tools and guardrail per pain type.</span></div>
      {''.join(nodes)}
    </div>
    """)


def blueprint_card(challenge: dict, poc: dict | None) -> str:
    blueprint = blueprint_for(challenge.get("pain_type"))
    source = poc or blueprint
    objects = "".join(f"<span class='pl-obj'>{_e(o)}</span>" for o in source.get("objects", []))
    caps = "".join(f"<li>{_e(c)}</li>" for c in source.get("capabilities", []))
    tools = "".join(f"<li>{_e(t)}</li>" for t in source.get("tools", []))
    steps = "".join(f"<li>{_e(s)}</li>" for s in (poc or {}).get("build_steps", []))
    steps_box = (
        f"<div class='pl-box' style='margin-top:.9rem'><p class='t'>Build plan</p>"
        f"<ol class='pl-steps'>{steps}</ol></div>" if steps else ""
    )
    name = (poc or {}).get("name") or "Ontology blueprint"
    return _c(f"""
    <div class="pl-bp">
      <h3>{_e(name)}</h3>
      <span class="pat">{_e(source.get('pattern', ''))}</span>
      <div class="pl-grid">
        <div class="pl-box"><p class="t">Ontology objects</p>{objects}</div>
        <div class="pl-box"><p class="t">Capabilities</p><ul>{caps}</ul></div>
        <div class="pl-box"><p class="t">Tools to wire up</p><ul>{tools}</ul></div>
      </div>
      {steps_box}
      <div class="pl-guard">🛡 {_e(source.get('guardrail', ''))}</div>
    </div>
    """)


STAGE_LABELS = {key: (label, icon) for key, label, _hint, icon in STAGES}


def poc_table(rows: list[dict]) -> str:
    """Every POC that exists, with where it lives and what it does.

    Only records that have reached POC appear: the table answers "what is
    actually being built", and listing painpoints with no blueprint would bury
    that under things nobody has started.
    """
    built = [row for row in rows if row["stage"] in ("poc", "proven", "published")]
    if not built:
        return _c("""
        <div class='pl-poc-h'><b>🧪 POC table</b>
          <span>Nothing drafted yet — draft a POC below and it appears here.</span></div>
        """)

    body = []
    for row in built:
        repo = str(row.get("github") or "").strip()
        repo_cell = (f"<span class='pl-repo'>{_e(repo)}</span>" if repo
                     else "<span class='pl-repo none'>no repo yet</span>")
        features = "".join(
            f"<span class='pl-feat'>{_e(capability)}</span>"
            for capability in (row.get("capabilities") or [])[:4]
        ) or "<span style='color:var(--pc-ink-faint)'>—</span>"
        criteria = f"{row['met']}/{row['total']}" if row["total"] else "—"
        label, icon = STAGE_LABELS[row["stage"]]
        body.append(_c(f"""
        <tr>
          <td><span class='nm'>{_e(row['poc_name'] or row['title'])}</span>
              <span class='sub'>from “{_e(row['title'])}”</span></td>
          <td><span class='pat'>{_e(row['pattern'])}</span></td>
          <td>{repo_cell}</td>
          <td>{features}</td>
          <td class='num'>{_e(row.get('effort_days') or '—')} d</td>
          <td class='num'>{criteria}</td>
          <td><span class='pl-st {row['stage']}'>{icon} {_e(label)}</span></td>
        </tr>
        """))

    return _c(f"""
    <div class="pl-poc-h"><b>🧪 POC table</b>
      <span>{len(built)} in flight — what is being built, where it lives, how far it has got.</span></div>
    <div class="pl-tbl-wrap">
      <table class="pl-poc">
        <thead><tr>
          <th>POC</th><th>Pattern</th><th>GitHub</th><th>Features</th>
          <th>Build</th><th>Criteria</th><th>Status</th>
        </tr></thead>
        <tbody>{''.join(body)}</tbody>
      </table>
    </div>
    """)


def workflow_table(rows: list[dict], selected_id: Any) -> str:
    """The whole workflow as one table — every record, every stage, one scan.

    Ordered by stage so the table reads left-to-right as the pipeline reads:
    what is waiting, what is being built, what is proven, what shipped.
    """
    body = []
    for row in rows:
        label, icon = STAGE_LABELS[row["stage"]]
        hours = f"{row['annual_hours']:,.0f}" if row["annual_hours"] else "—"
        tag = f"<span class='pl-tag'>{_e(row['classification'])}</span>" if row["classification"] else ""

        if row["total"]:
            pct = int(100 * row["met"] / row["total"])
            criteria = (f"<span class='pl-mini'><span style='width:{pct}%'></span></span>"
                        f"{row['met']}/{row['total']}")
        else:
            criteria = "<span style='color:var(--pc-ink-faint)'>—</span>"

        poc_cell = (
            f"<span class='pat'>{_e(row['pattern'])}</span>"
            f"<span class='sub'>{_e(row['poc_name'])}</span>"
            if row["pattern"] else "<span style='color:var(--pc-ink-faint)'>not drafted</span>"
        )
        build = f"{row['effort_days']} d" if row.get("effort_days") else "—"

        body.append(_c(f"""
        <tr class="{'sel' if row['id'] == selected_id else ''}">
          <td><span class="ttl">{_e(row['title'])}</span>
              <span class="sub">{tag}{_e(row['category'] or row['pain_type'] or '')}</span></td>
          <td><span class="pl-st {row['stage']}">{icon} {_e(label)}</span></td>
          <td class="num">{hours}</td>
          <td class="num">{row['score']}</td>
          <td>{poc_cell}</td>
          <td class="num">{build}</td>
          <td class="num">{criteria}</td>
          <td>{_e(row['next'])}</td>
        </tr>
        """))

    return _c(f"""
    <div class="pl-tbl-wrap">
      <table class="pl-tbl">
        <thead><tr>
          <th>Pain point</th><th>Stage</th><th>Hours / yr</th><th>Score</th>
          <th>POC blueprint</th><th>Build</th><th>Criteria</th><th>Next action</th>
        </tr></thead>
        <tbody>{''.join(body)}</tbody>
      </table>
    </div>
    """)


# --------------------------------------------------------------------------
# page
# --------------------------------------------------------------------------

st.set_page_config(page_title="Pipeline — YES AI CAN", page_icon="🧬", layout="wide")
require_auth()

page_chrome(
    "pipeline",
    "Current Challenge Pipeline",
    "Where every submitted painpoint has got to: matched, drafted as a POC, "
    "proven, then published to the Community Agent Library.",
)
st.markdown(PIPELINE_CSS, unsafe_allow_html=True)

submissions = load_submissions()

if not submissions:
    from services.ui.utils.page_template import empty_state
    st.markdown(
        empty_state("🎯", "Nothing in the pipeline yet",
                    "Submit a pain point on the home page and it appears here, "
                    "already matched to its ontology blueprint."),
        unsafe_allow_html=True)
    st.stop()

# Confirmations survive the rerun that follows the action that caused them.
# st.success() straight before rerun() paints a message the rerun immediately
# throws away, so the person never sees what they just did.
flash = st.session_state.pop("pl_flash", None)
if flash:
    st.success(flash)

rows = pipeline_rows(submissions)
counts = pipeline_counts(submissions)

# Pin the selection in session state rather than defaulting to rows[0] each run:
# the board re-sorts by stage, so a record that has just moved forward would
# otherwise drop out from under the person who moved it.
if "pl_selected" not in st.session_state:
    st.session_state["pl_selected"] = rows[0]["id"]
selected = next(
    (s for s in submissions if s.get("id") == st.session_state["pl_selected"]),
    submissions[0],
)
selected_id = selected.get("id")
st.session_state["pl_selected"] = selected_id

st.markdown(flow_ribbon(counts, stage_of(selected)), unsafe_allow_html=True)

# ---------------------------------------------------------- the workflow table
st.markdown(workflow_table(rows, selected_id), unsafe_allow_html=True)

st.caption(
    "Drafting a POC, ticking its acceptance criteria and publishing it to the "
    "Community Agent Library all happen on **Current POC**."
)


# Drafting, proving and publishing a POC all live on the Current POC page now.
# This page answers one question — how far has each painpoint got — and a
# second set of controls here only made people wonder which was authoritative.
