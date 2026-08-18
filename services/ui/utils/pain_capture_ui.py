"""Presentation layer for the pain-point capture page.

Pure HTML/CSS builders — no Streamlit calls and no state. Keeping the markup
here means the page module stays about flow and persistence, and these pieces
can be rendered into a static file for design review without booting the app.
"""

from __future__ import annotations

import html
from typing import Any, Iterable, Mapping

__all__ = [
    "CAPTURE_CSS",
    "business_flow_section",
    "ai_opportunity_card",
    "current_workflow_card",
    "feature_strip",
    "how_it_works",
    "improvement_card",
    "intro_section",
    "next_action_card",
    "next_after_submission",
    "numbered_cell",
    "page_header",
    "pain_summary_rail",
    "section_heading",
    "section_title",
    "step_heading",
    "twin_chain",
]


CAPTURE_CSS = """
<style>
:root {
  --pc-indigo:      #5b3fd6;
  --pc-indigo-dark: #4930b0;
  --pc-indigo-wash: #efeafe;
  --pc-ink:         #1a1a2e;
  --pc-ink-soft:    #5a5a75;
  --pc-ink-faint:   #8b8ba7;
  --pc-surface:     #ffffff;
  --pc-page:        #f7f7fb;
  --pc-rule:        #e6e6f0;
  --pc-green:       #16a34a;
  --pc-green-wash:  #eafaf0;
  --pc-amber:       #d97706;
  --pc-red:         #dc2626;
}

/* Page ground + typography */
.stApp, [data-testid="stAppViewContainer"] { background: var(--pc-page); }
/* Clear the shell's fixed top bar. A flat 1.6rem here slid the page title and
   the "How it works" pill underneath it. */
.block-container { padding-top: calc(var(--tb-h, 72px) + 1.2rem) !important;
                   max-width: 1600px !important; }
html, body, [class*="css"] { font-family: "Inter", "Segoe UI", system-ui, -apple-system, sans-serif; }
/* The design is drawn on a 15px base. At Streamlit's 16px default every tile
   label and card subtitle picks up an extra wrapped line. */
html, body, [class*="st-"] { font-size: 15px; }

/* ---------- header ---------- */
.pc-head { display:flex; align-items:flex-start; justify-content:space-between; gap:1rem;
           margin-bottom:1.4rem; flex-wrap:wrap; }
.pc-head h1 { font-size:1.75rem; font-weight:750; color:var(--pc-ink); margin:0 0 .3rem;
              letter-spacing:-.02em; }
.pc-head p  { color:var(--pc-ink-soft); margin:0; font-size:.98rem; }
.pc-howto { border:1px solid var(--pc-rule); background:var(--pc-surface); border-radius:10px;
            padding:.55rem 1rem; color:var(--pc-ink-soft); font-size:.9rem; font-weight:600;
            white-space:nowrap; }

/* ---------- cards ---------- */
.pc-card { background:var(--pc-surface); border:1px solid var(--pc-rule); border-radius:16px;
           padding:1.15rem 1.25rem; margin-bottom:1rem; }
.pc-card-tight { padding:1rem 1.1rem; }
.pc-step { display:flex; align-items:center; gap:.6rem; margin-bottom:.15rem; }
.pc-num { width:26px; height:26px; border-radius:50%; background:var(--pc-indigo); color:#fff;
          font-size:.82rem; font-weight:700; display:inline-flex; align-items:center;
          justify-content:center; flex:0 0 26px; }
.pc-num.amber { background:#f59e0b; }
.pc-step h3 { font-size:1.05rem; font-weight:700; color:var(--pc-ink); margin:0; }
.pc-sub { color:var(--pc-ink-soft); font-size:.88rem; margin:.15rem 0 .8rem 2.1rem; }
.pc-tip { color:var(--pc-ink-faint); font-size:.83rem; margin:0 0 .7rem; }

.pc-h4 { font-size:.95rem; font-weight:700; color:var(--pc-ink); margin:0 0 .55rem; }
.pc-note { font-size:.82rem; color:var(--pc-ink-faint); margin:.5rem 0 0; }

/* examples panel */
.pc-eg { background:var(--pc-indigo-wash); border-radius:12px; padding:.8rem .9rem; }
.pc-eg-t { font-size:.8rem; font-weight:700; color:var(--pc-indigo-dark); margin:0 0 .45rem; }
.pc-eg ul { margin:0; padding-left:1rem; }
.pc-eg li { font-size:.82rem; color:var(--pc-ink-soft); margin-bottom:.35rem; line-height:1.4; }

/* baseline hint */
.pc-hint { background:#eef4ff; border-radius:10px; padding:.7rem .85rem; font-size:.87rem;
           color:var(--pc-ink-soft); margin-top:.6rem; }
.pc-hint b { color:var(--pc-indigo-dark); }

/* ---------- right rail ---------- */
.pc-rail-t { font-size:1.02rem; font-weight:700; color:var(--pc-ink); margin:0 0 .8rem; }
.pc-gauge-wrap { text-align:center; }
.pc-gauge-cap { font-size:.78rem; color:var(--pc-ink-faint); margin:.2rem 0 0; }
.pc-stat { border:1px solid var(--pc-rule); border-radius:12px; padding:.7rem .85rem;
           margin-bottom:.6rem; }
/* Sentence case, not uppercase: "HUMAN HOURS PER MONTH" wrapped to three lines
   in the rail and swamped the number it labels. */
.pc-stat-l { font-size:.76rem; color:var(--pc-ink-faint); letter-spacing:0;
             margin:0 0 .25rem; line-height:1.3; }
.pc-stat-v { font-size:1.5rem; font-weight:700; color:var(--pc-ink); line-height:1;
             font-variant-numeric:tabular-nums; }
.pc-stat-v.sm { font-size:1.15rem; }

.pc-chip { display:inline-flex; align-items:center; gap:.35rem; border:1px solid var(--pc-rule);
           border-radius:9px; padding:.4rem .6rem; font-size:.85rem; color:var(--pc-ink-soft);
           margin:0 .35rem .4rem 0; }
.pc-chip.on { border-color:var(--pc-indigo); background:var(--pc-indigo-wash);
              color:var(--pc-indigo-dark); font-weight:650; }

/* ---------- preview ---------- */
.pc-prev { background:var(--pc-surface); border:1px solid var(--pc-rule); border-radius:18px;
           padding:1.2rem 1.35rem; margin-top:.4rem; }
.pc-prev-h { display:flex; align-items:center; gap:.6rem; margin-bottom:1rem; }
.pc-prev-h h2 { font-size:1.1rem; font-weight:750; color:var(--pc-ink); margin:0; }
.pc-prev-h .muted { color:var(--pc-ink-faint); font-weight:500; font-size:.9rem; }
.pc-badge { background:var(--pc-indigo-wash); color:var(--pc-indigo-dark); font-size:.74rem;
            font-weight:700; padding:.22rem .6rem; border-radius:999px; }

.pc-flow { list-style:none; margin:0; padding:0; }
.pc-flow li { display:grid; grid-template-columns:1.5rem 1fr; gap:.5rem; padding:.3rem 0;
              font-size:.86rem; color:var(--pc-ink-soft); border-bottom:1px solid #f2f2f7; }
.pc-flow li:last-child { border-bottom:none; }
.pc-flow .n { color:var(--pc-ink-faint); font-variant-numeric:tabular-nums; }
.pc-more { font-size:.83rem; color:var(--pc-indigo); font-weight:600; margin:.5rem 0 0; }

.pc-imp { width:100%; border-collapse:collapse; font-size:.85rem; }
.pc-imp td { padding:.38rem 0; border-bottom:1px solid #f2f2f7; color:var(--pc-ink-soft); }
.pc-imp td:last-child { text-align:right; }
.pc-imp tr:last-child td { border-bottom:none; }
.pc-arrow { color:var(--pc-ink-faint); }
.pc-to { color:var(--pc-ink); font-weight:650; }
.pc-pct { background:var(--pc-green-wash); color:var(--pc-green); font-weight:700;
          font-size:.78rem; padding:.15rem .45rem; border-radius:6px; }
.pc-assumed { color:var(--pc-ink-faint); font-size:.72rem; }

.pc-score { font-size:2.6rem; font-weight:750; color:var(--pc-green); line-height:1;
            font-variant-numeric:tabular-nums; }
.pc-score-word { font-size:1.05rem; font-weight:700; color:var(--pc-green); margin-left:.4rem; }
.pc-bar { height:7px; border-radius:99px; background:#eceCf4; overflow:hidden; margin:.7rem 0 .9rem; }
.pc-bar span { display:block; height:100%; background:var(--pc-green); border-radius:99px; }
.pc-kv { display:flex; justify-content:space-between; font-size:.85rem; padding:.3rem 0;
         color:var(--pc-ink-soft); border-bottom:1px solid #f2f2f7; }
.pc-kv:last-child { border-bottom:none; }
.pc-kv b { color:var(--pc-ink); font-weight:650; }

.pc-action { display:flex; align-items:center; gap:.6rem; padding:.5rem 0; font-size:.88rem;
             color:var(--pc-ink-soft); }
.pc-action .ic { width:26px; height:26px; border-radius:8px; background:var(--pc-indigo-wash);
                 display:inline-flex; align-items:center; justify-content:center; flex:0 0 26px; }

/* ---------- checklist / strip ---------- */
.pc-check { background:var(--pc-green-wash); border:1px solid #cdeddb; border-radius:14px;
            padding:.9rem 1rem; }
.pc-check h4 { font-size:.92rem; font-weight:700; color:var(--pc-ink); margin:0 0 .5rem; }
.pc-check .row { display:grid; grid-template-columns:1fr 1fr; gap:.2rem .8rem; }
.pc-check div.i { font-size:.82rem; color:var(--pc-ink-soft); }
.pc-check .tick { color:var(--pc-green); font-weight:700; margin-right:.3rem; }
.pc-lock { font-size:.78rem; color:var(--pc-ink-faint); margin-top:.6rem; }

.pc-strip { display:grid; grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); gap:1rem;
            margin-top:1.1rem; }
.pc-feat { display:flex; align-items:center; gap:.75rem; }
.pc-feat .ic { width:42px; height:42px; border-radius:50%; background:var(--pc-indigo-wash);
               display:inline-flex; align-items:center; justify-content:center; font-size:1.15rem;
               flex:0 0 42px; }
.pc-feat b { display:block; font-size:.92rem; color:var(--pc-ink); }
.pc-feat span { font-size:.82rem; color:var(--pc-ink-faint); }

/* ---------- Streamlit widget restyle ---------- */
div[data-testid="stTextArea"] textarea,
div[data-testid="stNumberInput"] input,
div[data-testid="stTextInput"] input {
  border-radius:10px !important; border:1px solid var(--pc-rule) !important;
  background:var(--pc-surface) !important; color:var(--pc-ink) !important; font-size:.9rem !important;
}
div[data-testid="stTextArea"] textarea:focus,
div[data-testid="stNumberInput"] input:focus { border-color:var(--pc-indigo) !important;
  box-shadow:0 0 0 3px rgba(91,63,214,.14) !important; }
div[data-testid="stWidgetLabel"] p { font-size:.82rem !important; color:var(--pc-ink-soft) !important;
  font-weight:600 !important; }

.stButton > button {
  border-radius:10px; border:1px solid var(--pc-rule); background:var(--pc-surface);
  color:var(--pc-ink); font-weight:600; font-size:.88rem; padding:.5rem .9rem;
}
.stButton > button:hover { border-color:var(--pc-indigo); color:var(--pc-indigo-dark); }
.stButton > button[kind="primary"] {
  background:var(--pc-indigo); border-color:var(--pc-indigo); color:#fff;
}
.stButton > button[kind="primary"]:hover { background:var(--pc-indigo-dark); color:#fff; }
/* ---------- outcome tiles (step 3) ---------- */
/* Streamlit checkboxes restyled as the tiles in bestui.png: bordered card,
   indigo wash when ticked. :has() gives us the checked state without JS. */
.st-key-pp_outcomes [data-testid="stCheckbox"] { margin-bottom:.4rem; }
.st-key-pp_outcomes [data-testid="stCheckbox"] > label {
  border:1px solid var(--pc-rule); border-radius:10px; padding:.45rem .55rem;
  width:100%; background:var(--pc-surface); align-items:flex-start;
  transition:border-color .12s ease, background .12s ease; min-height:52px;
}
.st-key-pp_outcomes [data-testid="stCheckbox"]:has(input:checked) > label {
  border-color:var(--pc-indigo); background:var(--pc-indigo-wash);
}
.st-key-pp_outcomes [data-testid="stCheckbox"] label p { font-size:.74rem !important; line-height:1.25 !important; }
.st-key-pp_outcomes [data-testid="stCheckbox"] label p strong { font-size:.77rem; color:var(--pc-ink); }
.st-key-pp_outcomes [data-testid="stCheckbox"]:has(input:checked) label p strong { color:var(--pc-indigo-dark); }

/* ---------- baseline tiles (step 2) ---------- */
.pc-b-lab { display:flex; align-items:center; gap:.3rem; font-size:.79rem; white-space:nowrap;
            color:var(--pc-ink-soft); font-weight:650; margin:0 0 .25rem; line-height:1.2; }
.pc-b-cap { font-size:.72rem; color:var(--pc-ink-faint); margin:.3rem 0 0; line-height:1.2;
            min-height:1.9em; }
div[data-testid="stNumberInput"] input { font-size:1.3rem !important; font-weight:700 !important;
  color:var(--pc-ink) !important; text-align:left; padding:.25rem .5rem !important; }
div[data-testid="stNumberInput"] button { display:none !important; }

/* ---------- amber recommends panel ---------- */
.pc-rec { background:#fffbeb; border:1px solid #fde68a; border-radius:12px; padding:.75rem .8rem; }
.pc-rec h5 { font-size:.8rem; font-weight:700; color:#92400e; margin:0 0 .5rem; line-height:1.3; }
.pc-rec div { font-size:.76rem; color:var(--pc-ink-soft); padding:.14rem 0; }
.pc-rec .tk { color:var(--pc-green); font-weight:700; margin-right:.3rem; }
[data-testid="stCheckbox"] label p { font-size:.84rem !important; }

/* ---------- how it works ---------- */
.pc-hiw { background:var(--pc-surface); border:1px solid var(--pc-rule); border-radius:16px;
          padding:1.1rem 1.25rem; margin:0 0 1.1rem; }
.pc-hiw-h { display:flex; align-items:baseline; gap:.55rem; margin:0 0 .9rem; }
.pc-hiw-h b { font-size:1.02rem; font-weight:700; color:var(--pc-ink); }
.pc-hiw-h span { font-size:.86rem; color:var(--pc-ink-faint); }
.pc-hiw-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:.9rem; }
.pc-hiw-step { display:flex; gap:.65rem; align-items:flex-start; }
.pc-hiw-step .n { width:24px; height:24px; border-radius:50%; background:var(--pc-indigo-wash);
                  color:var(--pc-indigo-dark); font-size:.78rem; font-weight:700; flex:0 0 24px;
                  display:inline-flex; align-items:center; justify-content:center; margin-top:.1rem; }
.pc-hiw-step b { display:block; font-size:.89rem; font-weight:650; color:var(--pc-ink);
                 margin-bottom:.15rem; }
.pc-hiw-step p { font-size:.83rem; color:var(--pc-ink-soft); margin:0; line-height:1.5; }
.pc-hiw-foot { margin:.95rem 0 0; padding-top:.75rem; border-top:1px solid var(--pc-rule);
               font-size:.84rem; color:var(--pc-ink-soft); }
.pc-hiw-foot b { color:var(--pc-indigo-dark); font-weight:650; }

/* ---------- twin context chain ---------- */
.pc-chain { display:flex; align-items:stretch; gap:.4rem; flex-wrap:wrap; margin:.2rem 0 0; }
.pc-link { flex:1 1 150px; min-width:140px; border:1px solid var(--pc-rule); border-radius:11px;
           padding:.5rem .65rem; background:var(--pc-surface); position:relative; }
.pc-link.me { border-color:var(--pc-indigo); background:var(--pc-indigo-wash); }
.pc-link .k { font-size:.66rem; font-weight:700; letter-spacing:.04em; text-transform:uppercase;
              color:var(--pc-ink-faint); margin:0 0 .15rem; }
.pc-link.me .k { color:var(--pc-indigo-dark); }
.pc-link .v { font-size:.8rem; font-weight:650; color:var(--pc-ink); line-height:1.3;
              word-break:break-word; }
.pc-link .s { display:block; font-size:.71rem; color:var(--pc-ink-faint); margin-top:.15rem;
              line-height:1.35; }
.pc-link.empty .v { color:var(--pc-ink-faint); font-weight:500; font-style:italic; }
.pc-arrow-x { align-self:center; color:var(--pc-ink-faint); font-size:1rem; flex:0 0 auto; }

/* ---------- section heading (peer of the page title) ---------- */
.pc-sect { margin:0 0 .9rem; }
.pc-sect h2 { font-size:1.45rem; font-weight:750; color:var(--pc-ink); margin:0 0 .25rem;
              letter-spacing:-.02em; }
.pc-sect p { font-size:.94rem; color:var(--pc-ink-soft); margin:0; }

/* ---------- business flow ontology ---------- */
/* No card of its own: the section and the flow builder share one bordered
   Streamlit container, so the builder reads as the foot of the table rather
   than as a second panel floating under it. */
.pc-bfo { background:transparent; border:none; padding:0; margin:0; }
.pc-bfo-h { display:flex; align-items:baseline; gap:.55rem; flex-wrap:wrap; margin:0 0 .7rem; }
.pc-bfo-h b { font-size:1.02rem; font-weight:700; color:var(--pc-ink); }
.pc-bfo-h span { font-size:.84rem; color:var(--pc-ink-faint); }
.pc-rule-line { background:var(--pc-indigo-wash); border-radius:10px; padding:.55rem .75rem;
                font-size:.82rem; color:var(--pc-indigo-dark); font-weight:600; margin:0 0 .9rem;
                overflow-x:auto; white-space:nowrap; }
.pc-layers { display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:.55rem;
             margin:0 0 1rem; }
.pc-layer { border:1px solid var(--pc-rule); border-radius:10px; padding:.55rem .65rem; }
.pc-layer .n { font-size:.65rem; font-weight:700; letter-spacing:.06em; text-transform:uppercase;
               color:var(--pc-indigo); }
.pc-layer b { display:block; font-size:.84rem; color:var(--pc-ink); margin:.1rem 0 .1rem; }
.pc-layer span { font-size:.72rem; color:var(--pc-ink-faint); line-height:1.4; }

.pc-chain-t { font-size:.72rem; font-weight:700; letter-spacing:.05em; text-transform:uppercase;
              color:var(--pc-ink-faint); margin:0 0 .5rem; }
.pc-edges { display:flex; flex-direction:column; gap:.3rem; }
.pc-edge { display:grid; grid-template-columns:1fr auto 1fr auto; gap:.5rem; align-items:center;
           border:1px solid var(--pc-rule); border-radius:10px; padding:.45rem .6rem;
           background:var(--pc-surface); }
.pc-edge.hot { border-color:var(--pc-amber); background:#fffdf5; }
.pc-edge .who { font-size:.8rem; font-weight:650; color:var(--pc-ink); }
.pc-edge .act { display:block; font-size:.71rem; color:var(--pc-ink-faint); font-weight:500; }
.pc-edge .obj { font-size:.72rem; font-weight:650; color:var(--pc-indigo-dark);
                background:var(--pc-indigo-wash); border-radius:7px; padding:.15rem .45rem;
                white-space:nowrap; }
.pc-edge .load { font-size:.7rem; font-weight:700; border-radius:999px; padding:.1rem .45rem;
                 white-space:nowrap; }
.pc-edge .load.none { color:var(--pc-ink-faint); background:transparent; font-weight:500; }
.pc-edge .load.some { color:#92400e; background:#fef3c7; }
.pc-edge.proposed { border-style:dashed; }
.pc-edge .prop { font-size:.62rem; font-weight:700; letter-spacing:.05em; text-transform:uppercase;
                 color:var(--pc-ink-faint); border:1px solid var(--pc-rule); border-radius:5px;
                 padding:.02rem .28rem; margin-left:.35rem; white-space:nowrap; }

/* ---------- intro ---------- */
.pc-intro { background:var(--pc-surface); border:1px solid var(--pc-rule); border-radius:18px;
            padding:1.5rem 1.6rem; margin:0 0 1.2rem; }
.pc-intro-eye { font-size:.7rem; font-weight:700; letter-spacing:.14em; text-transform:uppercase;
                color:var(--pc-indigo); margin:0 0 .5rem; }
.pc-intro h2 { font-size:1.5rem; font-weight:750; color:var(--pc-ink); margin:0 0 .55rem;
               letter-spacing:-.02em; line-height:1.2; }
.pc-intro-lede { font-size:.95rem; color:var(--pc-ink-soft); line-height:1.6; margin:0;
                 max-width:78ch; }
.pc-intro-mission { background:var(--pc-indigo-wash); border-radius:12px; padding:.8rem 1rem;
                    margin:.9rem 0 0; font-size:.92rem; color:var(--pc-indigo-dark);
                    line-height:1.55; }
.pc-intro-mission b { font-weight:700; }
.pc-intro-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(290px,1fr));
                 gap:1rem; margin-top:1.2rem; padding-top:1.2rem;
                 border-top:1px solid var(--pc-rule); }
.pc-intro-col h3 { font-size:.98rem; font-weight:700; color:var(--pc-ink); margin:0 0 .1rem; }
.pc-intro-col .sub { font-size:.8rem; color:var(--pc-ink-faint); margin:0 0 .65rem; }
.pc-intro-list { list-style:none; margin:0; padding:0; }
.pc-intro-list li { display:grid; grid-template-columns:1.25rem 1fr; gap:.5rem; align-items:start;
                    font-size:.85rem; color:var(--pc-ink-soft); line-height:1.5;
                    padding:.22rem 0; }
.pc-intro-list li b { color:var(--pc-ink); font-weight:650; }
.pc-role { border:1px solid var(--pc-rule); border-radius:11px; padding:.6rem .75rem;
           margin-bottom:.5rem; }
.pc-role .who { font-size:.72rem; font-weight:700; letter-spacing:.04em; text-transform:uppercase;
                color:var(--pc-indigo-dark); margin:0 0 .3rem; }
.pc-role p { font-size:.83rem; color:var(--pc-ink-soft); margin:.12rem 0; line-height:1.45; }
/* How it works now lives inside the intro, so it drops its own card chrome and
   becomes the closing row of that one rather than a second panel under it. */
.pc-intro .pc-hiw { background:transparent; border:none; border-radius:0; padding:0;
                    margin:1.2rem 0 0; padding-top:1.2rem;
                    border-top:1px solid var(--pc-rule); }

/* ---------- numbered list inputs (painpoints, steps) ---------- */
.pc-cell-n { font-size:.68rem; font-weight:700; color:var(--pc-indigo-dark);
             background:var(--pc-indigo-wash); border-radius:5px; width:1.15rem;
             height:1.15rem; display:flex; align-items:center; justify-content:center;
             margin:.35rem 0 .1rem; font-variant-numeric:tabular-nums; }

/* ---------- flow builder ---------- */
.pc-fb { border-top:1px solid var(--pc-rule); margin-top:1rem; padding-top:.9rem; }
.pc-fb-t { font-size:.72rem; font-weight:700; letter-spacing:.05em; text-transform:uppercase;
           color:var(--pc-ink-faint); margin:0 0 .1rem; }
.pc-fb-s { font-size:.78rem; color:var(--pc-ink-faint); margin:0 0 .6rem; line-height:1.45; }
</style>
"""


BASELINE_ICONS = {"steps": "👣", "time": "⏱", "freq": "🔁"}


def baseline_label(icon: str, question: str) -> str:
    return f"<p class='pc-b-lab'><span>{icon}</span><span>{_e(question)}</span></p>"


def baseline_caption(text: str) -> str:
    return f"<p class='pc-b-cap'>{_e(text)}</p>"


def recommends_panel(rows: Iterable[Mapping[str, Any]]) -> str:
    items = "".join(
        f"<div><span class='tk'>✓</span>{_e(row['label'])}</div>" for row in rows
    )
    return f"<div class='pc-rec'><h5>AI recommends measuring:</h5>{items}</div>"


def _e(value: Any) -> str:
    return html.escape(str(value if value is not None else ""))


def _c(markup: str) -> str:
    """Strip leading indentation from every line of an HTML block.

    Streamlit renders markdown before HTML, and markdown treats a line indented
    by four spaces as a code block — so a nicely-indented f-string of HTML gets
    partly printed as literal tags on the page. Collapsing the indentation is
    what stops that.
    """
    return "".join(line.strip() for line in str(markup).splitlines())


def page_header() -> str:
    return (
        "<div class='pc-head'><div>"
        "<h1>Submit a Pain Point in 3 Simple Steps 🚀</h1>"
        "<p>Tell us what hurts, how it's done today, and what better looks like.</p>"
        "</div><div class='pc-howto'>ⓘ How it works</div></div>"
    )


def intro_section() -> str:
    """Why, what and who YES AI CAN is — the page's opening statement.

    Sits above the capture form because a first-time visitor needs to know what
    they have landed on before being asked what hurts. The three parts answer
    three separate questions, so they are laid out as three, not run together
    as prose.
    """
    what = [
        ("🧠", "Mine our global superpowers", "map every skill, SME, and domain expert"),
        ("🔍", "Collect real business pain points", "Kaggle-style challenge submissions"),
        ("🚀", "Turn problems into agents", "Customer ZERO → Customer ONE blueprints"),
        ("🪄", "Give zero-code tools", "create explainable AI agents instantly"),
        ("🤝", "Connect Ambassadors, SMEs", "engineers, and innovators"),
        ("♻️", "Accelerate reuse", "through a shared, governed agent library"),
        ("🏗️", "Power the next generation", "of OpenStack + private AI solutions"),
        ("🌏", "Unite Rackers globally", "into one open innovation community"),
    ]
    what_rows = "".join(
        f"<li><span>{icon}</span><span><b>{_e(title)}</b> — {_e(detail)}</span></li>"
        for icon, title, detail in what
    )

    roles = [
        ("As User / Live Improver", [
            "Submit any pain point or workflow — “How Can AI Help?”",
            "Report improvement needs or new ideas to the community",
        ]),
        ("As Solution Finder / Builder", [
            "Help Rackers solve real-life problems",
            "Build AI tools that improve tasks, workflows, and happiness",
        ]),
    ]
    role_cards = "".join(
        f"<div class='pc-role'><p class='who'>{_e(who)}</p>"
        + "".join(f"<p>· {_e(line)}</p>" for line in lines)
        + "</div>"
        for who, lines in roles
    )

    who_for = [
        ("🙋", "Anyone with a task that hurts",
         "No AI knowledge needed. One sentence is enough to start."),
        ("🛠", "Solution finders and builders",
         "Zero-code tools, or bring your own stack."),
        ("🎓", "Ambassadors and SMEs",
         "Get matched to the challenges your expertise actually fits."),
        ("📊", "Business unit leads",
         "See which handoffs between units cost the most hours."),
    ]
    who_rows = "".join(
        f"<li><span>{icon}</span><span><b>{_e(title)}</b><br>{_e(detail)}</span></li>"
        for icon, title, detail in who_for
    )

    return _c(f"""
    <div class="pc-intro">
      <p class="pc-intro-eye">Why · What · How · Who — YES AI CAN FabLab</p>
      <h2>💡 Why We Exist</h2>
      <p class="pc-intro-lede">Our Community has 5,000+ hidden superpowers — unique skills,
      ideas, and lived experiences waiting to be unlocked. YES AI CAN is the place where
      those superpowers become visible: in profiles, in projects, in prototypes, in agents,
      in solutions, and in community.</p>
      <p class="pc-intro-mission">Our mission: give everyone — regardless of background —
      the confidence, tools, and platform to say
      <b>“YES, AI CAN BE HELPED, or HELP each other.”</b><br>
      That is what YES AI CAN is all about: people helping people, teams helping other
      teams as one team, for a common powerful success — and building transversal
      skills sharing.</p>

      <div class="pc-intro-grid">
        <div class="pc-intro-col">
          <h3>🌌 What YES AI CAN Is</h3>
          <p class="sub">Our Community's AI Foundry + Community Agent Factory, built to:</p>
          <ul class="pc-intro-list">{what_rows}</ul>
        </div>
        <div class="pc-intro-col">
          <h3>🧩 Challenge &amp; Solution Flow</h3>
          <p class="sub">Two ways in. Most people end up doing both.</p>
          {role_cards}
        </div>
        <div class="pc-intro-col">
          <h3>👥 Who it is for</h3>
          <p class="sub">If your work has a slow, manual or broken bit — you.</p>
          <ul class="pc-intro-list">{who_rows}</ul>
        </div>
      </div>
      {how_it_works()}
    </div>
    """)


def how_it_works() -> str:
    """The three-step explainer that used to sit on the old home page.

    Same promise as the old neon block — submit a pain point, find the people
    who will build it with you, ship the good ones to the library — rewritten
    to the template's card, badge and type scale.
    """
    steps = [
        ("Submit your pain point",
         "Tell us what is slow, manual, repetitive or error-prone. One sentence is enough."),
        ("Find the people who build it with you",
         "Great Rackers and teams propose a solution that will put a smile on your face."),
        ("Ship it to the Production Library",
         "The best solutions are shared for us and for our customers, ready to reuse."),
    ]
    cells = "".join(
        f"<div class='pc-hiw-step'><span class='n'>{index}</span>"
        f"<span><b>{_e(title)}</b><p>{_e(body)}</p></span></div>"
        for index, (title, body) in enumerate(steps, start=1)
    )
    return _c(f"""
    <div class="pc-hiw">
      <div class="pc-hiw-h"><b>🏠 How it works</b>
        <span>Share real customer or team pain points, let Ambassadors propose AI cures,
        and convert the best submissions into Customer ONE projects.</span></div>
      <div class="pc-hiw-grid">{cells}</div>
      <p class="pc-hiw-foot">By putting all our ideas and talents together we build
      <b>better services, a better culture, happier customers — and a better world.</b></p>
    </div>
    """)


def section_title(title: str, subtitle: str = "") -> str:
    """A heading that sits at the same level as the page title."""
    sub = f"<p>{_e(subtitle)}</p>" if subtitle else ""
    return f"<div class='pc-sect'><h2>{_e(title)}</h2>{sub}</div>"


def business_flow_section(
    layers: Iterable[tuple[str, str, str]],
    core_rule: str,
    edges: Iterable[Mapping[str, Any]],
    load: Mapping[str, Mapping[str, Any]] | None = None,
) -> str:
    """The Business Flow Ontology: the rule, its four layers, and the chain.

    Each edge carries how much submitted pain is attached to it, which is the
    whole reason for modelling flow rather than org structure — a hot edge is a
    broken handoff, and it is visible here without opening anything.
    """
    load = load or {}

    layer_cells = "".join(
        f"<div class='pc-layer'><span class='n'>{index} · {_e(name)}</span>"
        f"<b>{_e(purpose)}</b><span>{_e(shape)}</span></div>"
        for index, (name, purpose, shape) in enumerate(layers, start=1)
    )

    rows = []
    for record in edges:
        identifier = str(record.get("id") or "")
        entry = load.get(identifier) or {}
        count = int(entry.get("count") or 0)
        hours = float(entry.get("annual_hours") or 0.0)
        if count:
            badge = (f"<span class='load some'>{count} pain · "
                     f"{hours:,.0f} h/yr</span>")
        else:
            badge = "<span class='load none'>—</span>"
        state = str(record.get("state") or "")
        tag = f"<span class='prop'>{_e(state)}</span>" if state else ""
        classes = "pc-edge" + (" hot" if count else "") + (" proposed" if state else "")
        rows.append(
            f"<div class='{classes}'>"
            f"<span><span class='who'>{_e(record.get('producer_name'))}{tag}</span>"
            f"<span class='act'>{_e(record.get('activity'))}</span></span>"
            f"<span class='obj'>{_e(record.get('object_name'))} →</span>"
            f"<span><span class='who'>{_e(record.get('consumer_name'))}</span>"
            f"<span class='act'>triggers {_e(record.get('triggers'))}</span></span>"
            f"{badge}</div>"
        )

    return _c(f"""
    <div class="pc-bfo">
      <div class="pc-bfo-h"><b>🏢 Business Flow Ontology</b>
        <span>Not an org chart. Units own activities, activities produce objects,
        and an object landing in another unit's inbox starts their next activity.</span></div>
      <div class="pc-rule-line">{_e(core_rule)}</div>
      <div class="pc-layers">{layer_cells}</div>
      <p class="pc-chain-t">Business value chain — pain attached to each handoff</p>
      <div class="pc-edges">{''.join(rows)}</div>
    </div>
    """)


def twin_chain(context: Mapping[str, Any]) -> str:
    """Where this task sits in the digital twin, as a left-to-right chain.

    Reading it back as a chain is what makes a wrong answer obvious: an input
    that nobody upstream produces, or an output going somewhere the twin says
    the unit does not hand work to, shows up immediately.
    """
    def link(kind: str, value: Any, sub: str = "", me: bool = False) -> str:
        filled = str(value or "").strip()
        classes = "pc-link" + (" me" if me else "") + ("" if filled else " empty")
        shown = _e(filled) if filled else "—"
        sub_html = f"<span class='s'>{_e(sub)}</span>" if sub and filled else ""
        return f"<div class='{classes}'><p class='k'>{_e(kind)}</p>" \
               f"<div class='v'>{shown}{sub_html}</div></div>"

    arrow = "<span class='pc-arrow-x'>→</span>"
    return _c(f"""
    <div class="pc-chain">
      {link("My input", context.get("input"), context.get("input_from", ""))}
      {arrow}
      {link("My task", context.get("task"), context.get("business_unit", ""), me=True)}
      {arrow}
      {link("My output goes to", context.get("output_to"), context.get("output_flow", ""))}
    </div>
    """)


def numbered_cell(number: int) -> str:
    """The row number that sits above a list input.

    Above rather than beside: Streamlit lays a column out as a block, so a
    number in its own narrow column would drift out of line with the field the
    moment one of them wrapped.
    """
    return f"<p class='pc-cell-n'>{int(number)}</p>"


def step_heading(number: int, title: str, subtitle: str, amber: bool = False) -> str:
    cls = "pc-num amber" if amber else "pc-num"
    return (
        f"<div class='pc-step'><span class='{cls}'>{number}</span><h3>{_e(title)}</h3></div>"
        f"<p class='pc-sub'>{_e(subtitle)}</p>"
    )


def section_heading(text: str) -> str:
    return f"<div class='pc-h4'>{_e(text)}</div>"


def _gauge_svg(score: int, band: str) -> str:
    """Semi-circular gauge. The arc length encodes the score directly."""
    colour = {"LOW": "#16a34a", "MODERATE": "#f59e0b", "HIGH": "#dc2626", "SEVERE": "#b91c1c"}.get(band, "#dc2626")
    radius, cx, cy = 70.0, 90.0, 90.0
    circumference = 3.14159 * radius            # half circle
    filled = circumference * max(0, min(100, score)) / 100.0
    return _c(f"""
    <svg viewBox="0 0 180 108" width="100%" style="max-width:210px" role="img"
         aria-label="Pain score {score} out of 100, {_e(band.title())}">
      <path d="M {cx - radius} {cy} A {radius} {radius} 0 0 1 {cx + radius} {cy}"
            fill="none" stroke="#ececf4" stroke-width="13" stroke-linecap="round"/>
      <path d="M {cx - radius} {cy} A {radius} {radius} 0 0 1 {cx + radius} {cy}"
            fill="none" stroke="{colour}" stroke-width="13" stroke-linecap="round"
            stroke-dasharray="{filled:.1f} {circumference:.1f}"/>
      <text x="{cx}" y="{cy - 12}" text-anchor="middle" font-size="34" font-weight="700"
            fill="#1a1a2e" font-family="Inter,Segoe UI,system-ui,sans-serif">{score}</text>
      <text x="{cx}" y="{cy + 8}" text-anchor="middle" font-size="14" font-weight="700"
            fill="{colour}" font-family="Inter,Segoe UI,system-ui,sans-serif">{_e(band.title())}</text>
    </svg>
    """)


def pain_summary_rail(pain: Mapping[str, Any], pain_type_label: str, who: str) -> str:
    """The live 'Your Pain Summary' rail. Recomputes on every input change."""
    score = int(pain.get("pain_score") or 0)
    band = str(pain.get("level") or "LOW")
    monthly = float(pain.get("monthly_hours") or 0)
    annual = float(pain.get("annual_hours") or 0)
    half = float(pain.get("annual_hours_at_half") or 0)

    icons = {"Just me": "👤", "My team": "👥", "My department": "🏢", "Our customers": "🤝"}
    who_chips = "".join(
        f"<div class='pc-chip{' on' if option == who else ''}' "
        f"style='display:flex;width:100%;margin:0 0 .3rem'>"
        f"<span>{icons[option]}</span><span>{_e(option)}</span></div>"
        for option in ("Just me", "My team", "My department", "Our customers")
    )

    return _c(f"""
    <div class="pc-card">
      <div class="pc-rail-t">Your Pain Summary</div>
      <div style="display:grid;grid-template-columns:1.1fr .9fr;gap:.8rem;align-items:center">
        <div class="pc-gauge-wrap">
          <div class="pc-stat-l" style="text-align:center">Pain Score</div>
          {_gauge_svg(score, band)}
          <p class="pc-gauge-cap">{_e(band.title())} impact opportunity</p>
        </div>
        <div>
          <div class="pc-stat">
            <p class="pc-stat-l">Human hours<br>per month</p>
            <div class="pc-stat-v">{monthly:,.1f}</div>
          </div>
          <div class="pc-stat" style="margin-bottom:0">
            <p class="pc-stat-l">Human hours<br>per year</p>
            <div class="pc-stat-v">{annual:,.0f}</div>
          </div>
        </div>
      </div>
      <div class="pc-stat" style="margin-top:.8rem;margin-bottom:0">
        <p class="pc-stat-l">Annual impact <span style="text-transform:none">(if 50% improvement)</span></p>
        <div class="pc-stat-v">{half:,.0f} hrs</div>
      </div>
    </div>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:.7rem">
      <div class="pc-card pc-card-tight" style="margin-bottom:0">
        <p class="pc-stat-l">Pain Type <span style="text-transform:none">(detected)</span></p>
        <div style="display:flex;gap:.4rem;align-items:flex-start;margin-top:.35rem">
          <span style="font-size:1rem">📄</span>
          <div>
            <b style="color:var(--pc-indigo-dark);font-size:.85rem">{_e(pain_type_label)}</b>
            <p class="pc-note" style="margin-top:.15rem">Tasks done over and over with manual steps.</p>
          </div>
        </div>
      </div>
      <div class="pc-card pc-card-tight" style="margin-bottom:0">
        <p class="pc-stat-l">Who is affected?</p>
        <div style="margin-top:.4rem">{who_chips}</div>
      </div>
    </div>
    """)


def current_workflow_card(steps: Iterable[str], total: int) -> str:
    steps = list(steps)
    shown = steps[:5]
    rows = "".join(
        f"<li><span class='n'>{i}</span><span>{_e(step)}</span></li>"
        for i, step in enumerate(shown, start=1)
    )
    remaining = max(0, total - len(shown))
    more = f"<p class='pc-more'>+ {remaining} more steps</p>" if remaining else ""
    if not steps:
        rows = ("<li><span class='n'>–</span><span>Describe the pain point, then "
                "generate the steps.</span></li>")
    return (
        f"{section_heading(f'Current Workflow ({total} detections)')}"
        f"<ul class='pc-flow'>{rows}</ul>{more}"
    )


def improvement_card(rows: Iterable[Mapping[str, Any]]) -> str:
    body = "".join(
        "<tr>"
        f"<td>{_e(row['label'])}"
        + ("<br><span class='pc-assumed'>typical target</span>" if row.get("assumed") else "")
        + "</td>"
        f"<td>{_e(row['before'])} <span class='pc-arrow'>→</span> "
        f"<span class='pc-to'>{_e(row['after'])}</span></td>"
        f"<td><span class='pc-pct'>{int(row['pct'])}%</span></td>"
        "</tr>"
        for row in rows
    )
    return (
        f"{section_heading('Estimated Improvement (target)')}"
        f"<table class='pc-imp'><tbody>{body}</tbody></table>"
    )


def ai_opportunity_card(opportunity: Mapping[str, Any]) -> str:
    score = int(opportunity.get("score") or 0)
    word = "Excellent" if score >= 80 else "Strong" if score >= 65 else "Moderate" if score >= 45 else "Low"
    complexity = int(opportunity.get("complexity") or 0)
    complexity_word = ("Low" if complexity <= 30 else "Low-Medium" if complexity <= 45
                       else "Medium" if complexity <= 60 else "High")
    readiness = int(opportunity.get("readiness") or 0)
    readiness_word = "High" if readiness >= 70 else "Medium" if readiness >= 50 else "Low"
    return _c(f"""
    {section_heading('AI Opportunity')}
    <p class="pc-stat-l">Opportunity Score</p>
    <div><span class="pc-score">{score}</span><span class="pc-score-word">{word}</span></div>
    <div class="pc-bar"><span style="width:{max(0, min(100, score))}%"></span></div>
    <div class="pc-kv"><span>Complexity</span><b>{complexity_word}</b></div>
    <div class="pc-kv"><span>Time to first value</span><b>~ {_e(opportunity.get('time_to_first_value', '—'))}</b></div>
    <div class="pc-kv"><span>Readiness</span><b>{readiness_word}</b></div>
    """)


def next_action_card(actions: Iterable[tuple[str, str]]) -> str:
    rows = "".join(
        f"<div class='pc-action'><span class='ic'>{icon}</span><span>{_e(label)}</span></div>"
        for icon, label in actions
    )
    return f"{section_heading('Recommended Next Action')}{rows}"


def next_after_submission() -> str:
    left = ["AI will analyze your pain point", "Identify similar challenges",
            "Recommend solutions & agents"]
    right = ["Estimate impact & complexity", "Connect you with the right people"]
    cells = "".join(f"<div class='i'><span class='tick'>✓</span>{_e(t)}</div>" for t in left)
    cells += "".join(f"<div class='i'><span class='tick'>✓</span>{_e(t)}</div>" for t in right)
    return (
        "<div class='pc-check'><h4>Next after submission</h4>"
        f"<div class='row'>{cells}</div>"
        "<p class='pc-lock'>🔒 Your data is private and secure.</p></div>"
    )


def feature_strip() -> str:
    items = [
        ("⏱", "Fast", "Submit in under 60 seconds"),
        ("💡", "AI-Powered", "We do the heavy analysis"),
        ("📈", "High Impact", "Focus on what creates real value"),
        ("🤝", "Human-Centered", "Built by Rackers, for Rackers"),
    ]
    cells = "".join(
        f"<div class='pc-feat'><span class='ic'>{icon}</span>"
        f"<span><b>{_e(title)}</b><span>{_e(sub)}</span></span></div>"
        for icon, title, sub in items
    )
    return f"<div class='pc-strip'>{cells}</div>"
