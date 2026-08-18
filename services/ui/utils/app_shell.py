"""The YES AI CAN application shell: fixed left sidebar + top bar.

Streamlit's own chrome (auto page list, header, deploy toolbar) is hidden and
replaced with this, so every page sits inside the designed frame. Navigation
uses real anchors to Streamlit's multipage URLs rather than widgets, which
keeps the markup identical to the design and survives reruns.
"""

from __future__ import annotations

import base64
import html
from functools import lru_cache
from pathlib import Path
from typing import Iterable

__all__ = ["NAV_ITEMS", "render_shell", "SHELL_CSS"]

# (label, slug, icon). slug "" means the app root.
# Ordered as the work actually flows: get the lay of the land, see what is
# already open, then add to it, then follow it down the pipeline. "My Space" is
# parked rather than deleted — the page still exists and its route still
# resolves, it just is not in the rail.
NAV_ITEMS: list[tuple[str, str, str]] = [
    ("Home",                     "",                "home"),
    ("Getting Started",   "documentation_learning", "cap"),
    # The ontology sits above the dashboard because it is what the dashboard's
    # numbers are computed over — reach, cross-unit spread and similarity all
    # read these handoffs.
    ("My Company Workflows Ontology", "company_workflows", "org"),
    ("PainPoints Metrics Dashboard", "admin_rex", "chart"),
    # Reading the board comes before adding to it: seeing that somebody already
    # reported your problem is the point at which a submission becomes a
    # co-sponsor instead of a duplicate.
    # The board, then adding to it, then curing something on it.
    ("Current PainPoints", "challenge_hub", "flag"),
    ("Submit My PainPoints",     "how_can_ai_help", "pin"),
    ("Propose a Cure",    "solution_submit",      "bulb"),
    ("Current Cures and Remedies", "cures_list",   "pill"),
    ("Current Challenge Pipeline", "pipeline",      "flow"),
    ("Current POC",       "poc_hub",              "flask"),
    ("Community Agent Library", "agent_library",    "robot"),
    # People & Skills folded into Community — the page still exists and its
    # route still resolves, it is just not a second rail entry for the same
    # errand: find a person, read about the community.
    ("Community",         "community_ambassadors", "people"),
    # Feedback about the LAB itself, kept out of the painpoint queue — that
    # queue is the product, and "this page confused me" is not the same kind of
    # thing as "billing takes 45 minutes".
    ("Improvements Feedback", "improvements",     "megaphone"),
    # Learning Center moved to the top as "Getting Started" — it is what a new
    # arrival needs first, not a footnote after everything else.
    #
    # Settings (admin_agents) is parked rather than deleted, like My Space: the
    # page still exists and its route still resolves, it just is not in the rail.
]

# Inline stroke icons keep the sidebar self-contained — no font or CDN.
_ICONS = {
    "home":  "M3 10.5 12 3l9 7.5M5 9.5V21h14V9.5",
    "space": "M4 5h16v14H4zM4 9h16",
    "pin":   "M12 21s7-6.2 7-11a7 7 0 1 0-14 0c0 4.8 7 11 7 11z M12 10.5v.01",
    "flag":  "M5 21V4h13l-2.5 4L18 12H5",
    "flow":  "M4 6h5v4H4zM15 14h5v4h-5zM9 8h3a2 2 0 0 1 2 2v4M14 16l-2-2 2-2",
    "flask": "M10 3h4M10 3v6l-5 9a2 2 0 0 0 1.8 3h10.4a2 2 0 0 0 1.8-3l-5-9V3M7.5 15h9",
    "bulb":  "M9 18h6M10 21h4M12 3a6 6 0 0 1 4 10.5V16H8v-2.5A6 6 0 0 1 12 3z",
    "robot": "M7 9h10v8H7zM12 5v4M9 13h.01M15 13h.01M4 12h3M17 12h3",
    "user":  "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4 21c0-4 3.6-6 8-6s8 2 8 6",
    "people": "M9 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7zM2 20c0-3.4 3.1-5 7-5s7 1.6 7 5M17 8a3 3 0 1 0 0-6M18 20c0-2.6-.9-4.2-2.5-5",
    "book":  "M4 5.5A2.5 2.5 0 0 1 6.5 3H20v15H6.5A2.5 2.5 0 0 0 4 20.5zM4 5.5V20.5",
    "cap":   "M2 9l10-5 10 5-10 5zM6 11.5V17c0 1.5 3 3 6 3s6-1.5 6-3v-5.5",
    "pill":  "M10.5 3.5a5 5 0 0 1 7 7l-7 7a5 5 0 0 1-7-7zM7 7l7 7",
    "org":   "M9 4h6v4H9zM3 16h6v4H3zM15 16h6v4h-6zM12 8v4M6 16v-2h12v2",
    "megaphone": "M3 11v2a1 1 0 0 0 1 1h2l4 4V6L6 10H4a1 1 0 0 0-1 1zM14 8.5a4 4 0 0 1 0 7M17 5.5a8 8 0 0 1 0 13",
    "chart": "M4 4v16h16M8 16v-5M12 16V8M16 16v-3",
    "gear":  "M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7zM19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-2.9 1.2 2 2 0 1 1-4 0 1.7 1.7 0 0 0-2.9-1.2l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1A1.7 1.7 0 0 0 4.6 15a2 2 0 1 1 0-4 1.7 1.7 0 0 0 1.2-2.9l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 2.9-1.2 2 2 0 1 1 4 0 1.7 1.7 0 0 0 2.9 1.2l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0 1.2 2.9 2 2 0 1 1 0 4z",
}


SHELL_CSS = """
<style>
:root{
  --sb-w:240px; --tb-h:72px;
  /* Sidebar on Apple's iOS dark palette. The deep purple ground was the real
     problem: a saturated hue leaves very little room between "readable label"
     and "the background", so every inactive item read as disabled. iOS solves
     this by desaturating the ground to near-black elevated greys and putting
     the colour in the selection instead.
       systemGray6 dark #1C1C1E / systemGray5 dark #2C2C2E — the ground
       label dark #FFFFFF, secondaryLabel rgba(235,235,245,.60)
       systemIndigo dark #5E5CE6, systemBlue dark #0A84FF — the tint
       systemPurple dark #BF5AF2 — the brand mark
       fill rgba(120,120,128,.36) — the hover state */
  --nav-bg:#1C1C1E; --nav-bg2:#242426;
  --nav-ink:#EBEBF5; --nav-ink-on:#FFFFFF;
  --nav-tint:#5E5CE6; --nav-tint-2:#0A84FF; --nav-purple:#BF5AF2;
  --nav-fill:rgba(120,120,128,.36); --nav-sep:rgba(84,84,88,.55);
  --pc-indigo:#5b3fd6; --pc-indigo-dark:#4930b0; --pc-indigo-wash:#efeafe;
  --pc-ink:#1a1a2e; --pc-ink-soft:#5a5a75; --pc-ink-faint:#8b8ba7;
  --pc-surface:#ffffff; --pc-page:#f7f7fb; --pc-rule:#e6e6f0;
  --pc-green:#16a34a; --pc-green-wash:#eafaf0;
}

/* ---- hide Streamlit's own chrome ---- */
[data-testid="stSidebar"], [data-testid="stSidebarNav"],
[data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"],
header[data-testid="stHeader"], #MainMenu, footer, [data-testid="stToolbar"],
[data-testid="stDecoration"], [data-testid="stStatusWidget"] { display:none !important; }

.stApp, [data-testid="stAppViewContainer"]{ background:var(--pc-page); }
[data-testid="stAppViewContainer"] > .main{ padding-top:0 !important; }
.block-container{
  padding:calc(var(--tb-h) + 1.2rem) 1.1rem 3rem calc(var(--sb-w) + 1.2rem) !important;
  max-width:100% !important;
}
/* Streamlit's default column gap is generous; at four columns across it costs
   more than it gives, and the labels start wrapping mid-word. */
[data-testid="stHorizontalBlock"]{ gap:.7rem !important; }
html,body,[class*="css"]{ font-family:Inter,"Segoe UI",system-ui,-apple-system,sans-serif; }

/* ---- sidebar ---- */
.yz-sb{
  position:fixed; left:0; top:0; width:var(--sb-w); height:100vh; z-index:1000;
  background:linear-gradient(180deg,var(--nav-bg) 0%,var(--nav-bg2) 100%);
  padding:1.05rem .8rem 1rem; overflow-y:auto; display:flex; flex-direction:column;
}
.yz-sb::-webkit-scrollbar{ width:6px; }
.yz-sb::-webkit-scrollbar-thumb{ background:rgba(255,255,255,.16); border-radius:9px; }
/* Stacked, not side by side: at this size the mark is wider than the room left
   beside it in a 240px rail, so the wordmark sits underneath it instead. */
.yz-brand{
  display:flex; flex-direction:column; align-items:center; text-align:center;
  gap:.55rem; padding:.35rem .4rem 1.25rem;
}
.yz-mark{
  /* iOS app-icon geometry: a superellipse-ish 22% radius, not a rounded square. */
  width:138px; height:138px; border-radius:22%; flex:0 0 138px; overflow:hidden;
  display:flex; align-items:center; justify-content:center;
  box-shadow:0 8px 26px rgba(94,92,230,.40);
}
/* No gradient behind the artwork: the emblem carries its own near-black ground,
   and a tint underneath it would show as a rim wherever the PNG is transparent. */
.yz-mark.img{ background:#07070f; }
.yz-mark img{ width:100%; height:100%; object-fit:cover; display:block; }
/* Fallback mark only — used when the logo file is missing. */
.yz-mark.glyph{ background:linear-gradient(135deg,var(--nav-tint),var(--nav-purple)); }
.yz-brand b{ display:block; color:#fff; font-size:1.32rem; font-weight:800;
  letter-spacing:-.015em; line-height:1.12; }
.yz-brand b i{ font-style:normal; color:var(--nav-purple); }
/* iOS secondaryLabel, the one place a muted tone is correct — it is a caption,
   not a control. */
.yz-brand span{ display:block; color:rgba(235,235,245,.60); font-size:.71rem; letter-spacing:.02em; }

.yz-nav{ display:flex; flex-direction:column; gap:.14rem; }
.yz-nav a{
  position:relative;
  display:flex; align-items:center; gap:.7rem; padding:.6rem .7rem;
  /* iOS continuous-corner sidebar row */
  border-radius:10px;
  color:var(--nav-ink); font-size:.92rem; font-weight:500; text-decoration:none;
  letter-spacing:-.01em;
  transition:background .15s ease,color .15s ease;
}
.yz-nav a:hover{ background:var(--nav-fill); color:var(--nav-ink-on); }
/* The iPadOS sidebar selection: a filled row in the tint colour with white
   text, rather than a faint wash plus a rule. On a desaturated ground the fill
   carries the state on its own, so the accent bar is no longer needed. */
.yz-nav a.on{
  background:linear-gradient(135deg,var(--nav-tint),var(--nav-tint-2));
  color:var(--nav-ink-on); font-weight:600;
  box-shadow:0 1px 6px rgba(10,132,255,.34);
}
.yz-nav a.on:hover{ color:var(--nav-ink-on); }
.yz-nav svg{ width:19px; height:19px; flex:0 0 19px; stroke:currentColor; fill:none;
  stroke-width:1.8; stroke-linecap:round; stroke-linejoin:round; opacity:1; }
/* Inactive glyphs sit at iOS secondaryLabel weight so the label leads and the
   icon supports it, instead of the two competing. */
.yz-nav a:not(.on) svg{ opacity:.72; }
.yz-nav a:hover svg{ opacity:1; }

.yz-promo{
  margin-top:auto; background:var(--nav-bg2); border:1px solid var(--nav-sep);
  border-radius:14px; padding:1rem .95rem; color:#fff; position:relative; overflow:hidden;
}
.yz-promo h4{ font-size:.93rem; font-weight:650; margin:0 0 .4rem; line-height:1.25;
  letter-spacing:-.01em; }
.yz-promo p{ font-size:.77rem; color:rgba(235,235,245,.60); margin:0 0 .7rem; line-height:1.45; }
.yz-promo .rocket{ font-size:1.5rem; display:block; text-align:right; margin:-.2rem 0 .2rem; }
.yz-promo a{
  display:block; text-align:center; background:var(--nav-tint-2); color:#fff;
  text-decoration:none; font-size:.83rem; font-weight:600; padding:.55rem; border-radius:10px;
  letter-spacing:-.01em;
}
.yz-promo a:hover{ background:#409CFF; }

/* ---- top bar ---- */
.yz-tb{
  position:fixed; top:0; left:var(--sb-w); right:0; height:var(--tb-h); z-index:999;
  background:#fff; border-bottom:1px solid var(--pc-rule);
  display:flex; align-items:center; gap:1rem; padding:0 1.6rem;
}
.yz-search{
  flex:1; max-width:690px; display:flex; align-items:center; gap:.6rem;
  border:1px solid var(--pc-rule); border-radius:11px; padding:.55rem .85rem;
  background:#fcfcfe; color:var(--pc-ink-faint); font-size:.89rem;
}
.yz-search .kbd{
  margin-left:auto; border:1px solid var(--pc-rule); border-radius:6px; padding:.05rem .35rem;
  font-size:.72rem; color:var(--pc-ink-faint); background:#fff;
}
.yz-cta{
  display:inline-flex; align-items:center; gap:.45rem; background:var(--pc-indigo); color:#fff;
  text-decoration:none; font-size:.89rem; font-weight:650; padding:.62rem 1.15rem;
  border-radius:11px; white-space:nowrap; box-shadow:0 4px 12px rgba(91,63,214,.28);
}
.yz-cta:hover{ background:var(--pc-indigo-dark); color:#fff; }
.yz-bell{ color:var(--pc-ink-faint); display:flex; }
/* The signed-in chip is gone. It showed a hard-coded "Avery Chen / Racker" to
   everybody: not the viewer's name, not anyone's, and a leftover of the
   Rackspace wording besides. A fake identity is worse than none, and the app
   has no session to read a real one from. */

@media (max-width:1100px){
  :root{ --sb-w:0px; }
  .yz-sb{ display:none; }
  .yz-tb{ left:0; }
  .block-container{ padding-left:1.1rem !important; padding-right:1.1rem !important; }
}
</style>
"""


def _icon(name: str) -> str:
    path = _ICONS.get(name, _ICONS["home"])
    return f"<svg viewBox='0 0 24 24' aria-hidden='true'><path d='{path}'/></svg>"


def _nav(active: str) -> str:
    rows = []
    # Library and Learning Center both point at documentation_learning, so match
    # only the first item for a slug — otherwise two entries light up at once.
    matched = False
    for label, slug, icon in NAV_ITEMS:
        href = f"/{slug}" if slug else "/"
        is_active = not matched and slug == active
        if is_active:
            matched = True
        cls = " class='on'" if is_active else ""
        rows.append(
            f"<a href='{href}' target='_self'{cls}>{_icon(icon)}"
            f"<span>{html.escape(label)}</span></a>"
        )
    return "".join(rows)


def _c(markup: str) -> str:
    """Strip per-line indentation.

    Streamlit runs markdown before HTML, and markdown turns any four-space
    indented line into a code block — which prints raw tags on the page.
    """
    return "".join(line.strip() for line in str(markup).splitlines())


_LOGO_FILE = Path(__file__).resolve().parents[1] / "assets" / "yesaican_mark.png"


@lru_cache(maxsize=1)
def _brand_mark() -> str:
    """The sidebar mark: the YES AI CAN emblem, inlined as a data URI.

    Inlined rather than served: the sidebar is injected as raw HTML through
    st.markdown, and Streamlit only serves files from a static directory that
    has to be enabled in config. A 30 KB data URI always resolves, on any host
    and behind any reverse proxy, with no extra request.

    Falls back to the old star glyph if the file is missing, so a checkout that
    somehow lacks the asset still renders a sidebar rather than a broken image.
    """
    try:
        encoded = base64.b64encode(_LOGO_FILE.read_bytes()).decode("ascii")
    except OSError:
        return (
            "<span class='yz-mark glyph'>"
            "<svg viewBox='0 0 24 24' width='22' height='22' fill='#fff'>"
            "<path d='M12 2.6l2.6 6.1 6.6.5-5 4.3 1.5 6.4-5.7-3.4-5.7 3.4 "
            "1.5-6.4-5-4.3 6.6-.5z'/></svg></span>"
        )
    return (
        f"<span class='yz-mark img'>"
        f"<img src='data:image/png;base64,{encoded}' alt='YES AI CAN'></span>"
    )


def render_shell(active: str = "") -> str:
    """HTML for the whole frame. Render once per page, before any content."""
    return SHELL_CSS + _c(f"""
<div class="yz-sb">
  <div class="yz-brand">
    {_brand_mark()}
    <span><b>YES <i>AI</i> CAN</b><span>Community LAB</span></span>
  </div>
  <nav class="yz-nav">{_nav(active)}</nav>
  <div class="yz-promo">
    <h4>Build AI. Solve Problems.<br>Make Impact.</h4>
    <p>Together we build better services, happier customers, and a better world.</p>
    <span class="rocket">🚀</span>
    <a href="/documentation_learning" target="_self">Learn More</a>
  </div>
</div>

<div class="yz-tb">
  <div class="yz-search">
    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor"
         stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.2-3.2"/></svg>
    <span>Search challenges, people, skills, solutions...</span>
    <span class="kbd">⌘ K</span>
  </div>
  <a class="yz-cta" href="/how_can_ai_help" target="_self">
    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor"
         stroke-width="2.4" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>
    Submit Pain Point
  </a>
  <span class="yz-bell">
    <svg viewBox="0 0 24 24" width="21" height="21" fill="none" stroke="currentColor"
         stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
      <path d="M18 8a6 6 0 1 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10.5 21a2 2 0 0 0 3 0"/></svg>
  </span>
</div>
""")
