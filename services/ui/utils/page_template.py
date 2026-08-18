"""The one design system every page in the app renders through.

The home page and the pain-point capture panel set the look: a fixed indigo
sidebar and white top bar from ``app_shell``, light cards on a #f7f7fb ground,
Inter type, indigo accents. Everything in here exists so the rest of the pages
match that without each one hand-rolling its own markup.

Most pages are plain Streamlit — st.title, st.columns, st.dataframe, st.form —
so this styles Streamlit's own widgets rather than asking pages to be rewritten
in HTML. A page joins the design system with one call::

    page_chrome("challenge_hub", "Challenges", "Open problems waiting for a
                solution finder.")

Tokens live in ``app_shell.SHELL_CSS``'s :root, which ``page_chrome`` renders
first; only the handful this sheet adds are defined here.
"""

from __future__ import annotations

import html

import streamlit as st

from services.ui.utils.app_shell import render_shell

__all__ = [
    "PAGE_CSS", "page_chrome", "page_header", "section", "stat_row", "empty_state", "secret",
]


def secret(key: str, default: str = "") -> str:
    """Read a Streamlit secret without exploding when there is no secrets.toml.

    ``st.secrets.get`` is not a safe dict-style get: with no secrets file on
    disk it raises StreamlitSecretNotFoundError. Read at module scope, that
    killed a page before it rendered a single element.
    """
    try:
        return str(st.secrets.get(key, default) or default)
    except Exception:
        return default


PAGE_CSS = """
<style>
:root {
  --pc-surface-alt:#fcfcfe;
  --pc-amber:#d97706; --pc-amber-wash:#fffbeb;
  --pc-red:#dc2626;   --pc-red-wash:#fef2f2;
  --pc-shadow:0 1px 2px rgba(26,26,46,.04);
  --pc-shadow-lift:0 6px 18px rgba(26,26,46,.08);
}

/* ---------------------------------------------------------------- ground */
html, body, .stApp, [data-testid="stAppViewContainer"] {
  background: var(--pc-page) !important;
  color: var(--pc-ink) !important;
}
html, body, [class*="css"] {
  font-family: Inter, "Segoe UI", system-ui, -apple-system, sans-serif !important;
}
html, body, [class*="st-"] { font-size: 15px; }

/* Content clears the fixed shell. */
[data-testid="stMain"], [data-testid="stAppViewContainer"] > .main {
  padding-left: var(--sb-w, 240px) !important;
}
.block-container {
  padding: calc(var(--tb-h, 72px) + 1.2rem) 1.6rem 3.5rem !important;
  max-width: 1600px !important;
}
@media (max-width: 1100px) {
  [data-testid="stMain"], [data-testid="stAppViewContainer"] > .main { padding-left: 0 !important; }
}

/* ------------------------------------------------------------ typography */
h1, [data-testid="stHeading"] h1 {
  font-size: 1.75rem !important; font-weight: 750 !important;
  color: var(--pc-ink) !important; letter-spacing: -.02em !important;
  padding: 0 !important; margin: 0 0 .3rem !important;
}
h2 { font-size: 1.25rem !important; font-weight: 700 !important; color: var(--pc-ink) !important;
     margin: 1.6rem 0 .6rem !important; padding: 0 !important; letter-spacing: -.01em !important; }
h3 { font-size: 1.05rem !important; font-weight: 700 !important; color: var(--pc-ink) !important;
     margin: 1.2rem 0 .5rem !important; padding: 0 !important; }
h4, h5, h6 { font-size: .95rem !important; font-weight: 700 !important;
             color: var(--pc-ink) !important; margin: .9rem 0 .4rem !important; padding: 0 !important; }
p, li, .stMarkdown { color: var(--pc-ink-soft); font-size: .92rem; line-height: 1.6; }
strong, b { color: var(--pc-ink); }
a, a:visited { color: var(--pc-indigo-dark); }
small, [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {
  color: var(--pc-ink-faint) !important; font-size: .82rem !important;
}
hr, [data-testid="stDivider"] {
  border: none !important; border-top: 1px solid var(--pc-rule) !important; margin: 1.4rem 0 !important;
}
code, pre, [data-testid="stCodeBlock"] {
  background: var(--pc-surface-alt) !important; color: var(--pc-ink) !important;
  border: 1px solid var(--pc-rule) !important; border-radius: 8px !important;
  font-size: .85rem !important;
}

/* ---------------------------------------------------------------- cards */
[data-testid="stVerticalBlockBorderWrapper"] {
  background: var(--pc-surface) !important;
  border: 1px solid var(--pc-rule) !important;
  border-radius: 16px !important;
  box-shadow: var(--pc-shadow) !important;
}
[data-testid="stVerticalBlockBorderWrapper"] > div { padding: 0 !important; }
[data-testid="stForm"] {
  background: var(--pc-surface) !important;
  border: 1px solid var(--pc-rule) !important;
  border-radius: 16px !important;
  padding: 1.15rem 1.25rem !important;
  box-shadow: var(--pc-shadow) !important;
}
[data-testid="stExpander"] {
  background: var(--pc-surface) !important;
  border: 1px solid var(--pc-rule) !important;
  border-radius: 14px !important;
  box-shadow: none !important;
}
[data-testid="stExpander"] summary,
[data-testid="stExpander"] details > summary {
  font-size: .9rem !important; font-weight: 650 !important; color: var(--pc-ink) !important;
}
[data-testid="stExpander"] summary:hover { color: var(--pc-indigo-dark) !important; }

/* -------------------------------------------------------------- buttons */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {
  border: 1px solid var(--pc-rule) !important;
  background: var(--pc-surface) !important;
  color: var(--pc-ink) !important;
  border-radius: 10px !important;
  font-weight: 600 !important;
  font-size: .88rem !important;
  padding: .5rem .95rem !important;
  box-shadow: none !important;
  transition: border-color .13s ease, background .13s ease !important;
}
.stButton > button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover {
  border-color: var(--pc-indigo) !important;
  background: var(--pc-indigo-wash) !important;
  color: var(--pc-indigo-dark) !important;
  transform: none !important; box-shadow: none !important;
}
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"],
.stButton > button[data-testid="stBaseButton-primary"],
.stFormSubmitButton > button[data-testid="stBaseButton-primaryFormSubmit"] {
  background: var(--pc-indigo) !important; border-color: var(--pc-indigo) !important;
}
.stButton > button[kind="primary"], .stButton > button[kind="primary"] p,
.stFormSubmitButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] p,
.stButton > button[data-testid="stBaseButton-primary"],
.stButton > button[data-testid="stBaseButton-primary"] p,
.stFormSubmitButton > button[data-testid="stBaseButton-primaryFormSubmit"],
.stFormSubmitButton > button[data-testid="stBaseButton-primaryFormSubmit"] p { color: #fff !important; }
.stButton > button[kind="primary"]:hover,
.stFormSubmitButton > button[kind="primary"]:hover { background: var(--pc-indigo-dark) !important; }

/* --------------------------------------------------------------- inputs */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stDateInput"] input,
[data-baseweb="select"] > div {
  background: var(--pc-surface) !important;
  color: var(--pc-ink) !important;
  border: 1px solid var(--pc-rule) !important;
  border-radius: 10px !important;
  font-size: .9rem !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
  border-color: var(--pc-indigo) !important;
  box-shadow: 0 0 0 3px rgba(91,63,214,.14) !important;
}
[data-testid="stWidgetLabel"] p, [data-testid="stWidgetLabel"] label {
  font-size: .83rem !important; font-weight: 600 !important; color: var(--pc-ink-soft) !important;
}
[data-baseweb="select"] span, [data-baseweb="select"] div { color: var(--pc-ink) !important; }
[data-baseweb="popover"], ul[role="listbox"] {
  background: var(--pc-surface) !important; border: 1px solid var(--pc-rule) !important;
  border-radius: 10px !important; box-shadow: var(--pc-shadow-lift) !important;
}
li[role="option"], li[role="option"] span { color: var(--pc-ink) !important; }
li[role="option"]:hover { background: var(--pc-indigo-wash) !important; color: var(--pc-indigo-dark) !important; }
[data-testid="stFileUploader"] section {
  background: var(--pc-surface-alt) !important; border: 1px dashed var(--pc-rule) !important;
  border-radius: 12px !important;
}
[data-testid="stSlider"] [role="slider"] { background: var(--pc-indigo) !important; }

/* ----------------------------------------------------------------- tabs */
.stTabs [data-baseweb="tab-list"] {
  gap: .25rem !important; border-bottom: 1px solid var(--pc-rule) !important;
}
.stTabs [data-baseweb="tab"] {
  background: transparent !important; border: none !important;
  color: var(--pc-ink-faint) !important; font-size: .9rem !important; font-weight: 600 !important;
  padding: .55rem .9rem !important;
}
.stTabs [data-baseweb="tab"][aria-selected="true"] {
  color: var(--pc-indigo-dark) !important;
  border-bottom: 2px solid var(--pc-indigo) !important;
}
.stTabs [data-baseweb="tab-highlight"] { background: var(--pc-indigo) !important; }

/* --------------------------------------------------------------- tables */
[data-testid="stDataFrame"], [data-testid="stTable"] {
  border: 1px solid var(--pc-rule) !important; border-radius: 12px !important;
  overflow: hidden !important; background: var(--pc-surface) !important;
  box-shadow: none !important;
}
[data-testid="stTable"] thead th, [data-testid="stDataFrame"] thead th {
  background: var(--pc-surface-alt) !important; color: var(--pc-ink-faint) !important;
  font-size: .78rem !important; font-weight: 650 !important;
  border-bottom: 1px solid var(--pc-rule) !important;
}
[data-testid="stTable"] tbody td {
  color: var(--pc-ink-soft) !important; font-size: .86rem !important;
  border-bottom: 1px solid var(--pc-rule) !important;
}

/* -------------------------------------------------------------- metrics */
[data-testid="stMetric"] {
  background: var(--pc-surface) !important; border: 1px solid var(--pc-rule) !important;
  border-radius: 12px !important; padding: .8rem .95rem !important;
}
[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] p {
  color: var(--pc-ink-faint) !important; font-size: .78rem !important; font-weight: 600 !important;
}
[data-testid="stMetricValue"] {
  color: var(--pc-ink) !important; font-size: 1.6rem !important; font-weight: 700 !important;
  font-variant-numeric: tabular-nums;
}

/* --------------------------------------------------------------- alerts */
[data-testid="stAlert"] {
  border-radius: 12px !important; border: 1px solid var(--pc-rule) !important;
  box-shadow: none !important; font-size: .88rem !important;
}
[data-testid="stAlert"] p { font-size: .88rem !important; }

/* --------------------------------------------------- page header + bits */
.pg-head { margin: 0 0 1.4rem; }
.pg-head h1 { font-size: 1.75rem; font-weight: 750; color: var(--pc-ink);
              letter-spacing: -.02em; margin: 0 0 .3rem; }
.pg-head p { color: var(--pc-ink-soft); font-size: .95rem; margin: 0; }

.pg-sec { background: var(--pc-surface); border: 1px solid var(--pc-rule); border-radius: 16px;
          padding: 1.15rem 1.25rem; margin: 0 0 1rem; box-shadow: var(--pc-shadow); }
.pg-sec h3 { font-size: 1.02rem; font-weight: 700; color: var(--pc-ink); margin: 0 0 .5rem; }
.pg-sec p { color: var(--pc-ink-soft); font-size: .9rem; margin: 0; }

.pg-stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
            gap: .8rem; margin: 0 0 1.2rem; }
.pg-stat { background: var(--pc-surface); border: 1px solid var(--pc-rule); border-radius: 14px;
           padding: .85rem 1rem; }
.pg-stat .l { font-size: .76rem; color: var(--pc-ink-faint); margin: 0 0 .25rem; }
.pg-stat .v { font-size: 1.55rem; font-weight: 700; color: var(--pc-ink); line-height: 1;
              font-variant-numeric: tabular-nums; }
.pg-stat .v.accent { color: var(--pc-indigo); }

.pg-empty { background: var(--pc-surface); border: 1px dashed var(--pc-rule); border-radius: 16px;
            padding: 2.2rem 1.25rem; text-align: center; }
.pg-empty .i { font-size: 1.7rem; display: block; margin-bottom: .5rem; }
.pg-empty b { display: block; font-size: .98rem; color: var(--pc-ink); margin-bottom: .25rem; }
.pg-empty span { font-size: .87rem; color: var(--pc-ink-faint); }
</style>
"""


def _e(value: object) -> str:
    return html.escape(str(value if value is not None else ""))


def _c(markup: str) -> str:
    """Strip per-line indentation before handing HTML to st.markdown.

    Streamlit runs markdown first, and markdown turns any four-space indented
    line into a code block — which prints raw tags on the page.
    """
    return "".join(line.strip() for line in str(markup).splitlines())


def page_header(title: str, subtitle: str = "") -> str:
    sub = f"<p>{_e(subtitle)}</p>" if subtitle else ""
    return f"<div class='pg-head'><h1>{_e(title)}</h1>{sub}</div>"


def page_chrome(active: str = "", title: str = "", subtitle: str = "") -> None:
    """Render the shell, the design system, and (optionally) the page header.

    Call once, at the top of a page, straight after ``st.set_page_config``.
    ``active`` is the sidebar slug to highlight — see ``app_shell.NAV_ITEMS``.
    """
    st.markdown(render_shell(active=active), unsafe_allow_html=True)
    st.markdown(PAGE_CSS, unsafe_allow_html=True)
    if title:
        st.markdown(page_header(title, subtitle), unsafe_allow_html=True)


def section(title: str, body: str = "") -> str:
    """A plain template card, for a short block of prose."""
    text = f"<p>{_e(body)}</p>" if body else ""
    return f"<div class='pg-sec'><h3>{_e(title)}</h3>{text}</div>"


def stat_row(stats: list[tuple[str, object]], accent_first: bool = False) -> str:
    """A row of KPI tiles, as on the home page's summary rail."""
    cells = []
    for index, (label, value) in enumerate(stats):
        cls = "v accent" if accent_first and index == 0 else "v"
        cells.append(
            f"<div class='pg-stat'><p class='l'>{_e(label)}</p>"
            f"<div class='{cls}'>{_e(value)}</div></div>"
        )
    return f"<div class='pg-stats'>{''.join(cells)}</div>"


def empty_state(icon: str, title: str, hint: str = "") -> str:
    """What a page shows before it has any data — a card, not a bare st.info."""
    return _c(f"""
    <div class="pg-empty">
      <span class="i">{icon}</span>
      <b>{_e(title)}</b>
      <span>{_e(hint)}</span>
    </div>
    """)
