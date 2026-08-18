"""Template skin for the home page.

The home page markup predates the design in ``app_shell``/``pain_capture_ui``
and carries its own neon class names (``feature-card``, ``neon-table``,
``quick-access-card`` …). Rather than rewrite five thousand lines of markup,
this module re-skins those class names onto the same tokens the rest of the
template uses, and is injected *after* ``BASE_CSS`` so it wins.

Two token sets are defined so the existing dark-mode toggle keeps working: the
light set is the template as designed, the dark set keeps the same shapes on a
dark ground. Everything below the token block is written once, against the
tokens — no colour is repeated per theme.
"""

from __future__ import annotations

__all__ = ["TOKENS", "home_template_css"]


# The light values are the template's own palette, shared verbatim with
# services/ui/utils/app_shell.py and pain_capture_ui.py.
TOKENS: dict[str, dict[str, str]] = {
    "light": {
        "page":        "#f7f7fb",
        "surface":     "#ffffff",
        "surface_alt": "#fcfcfe",
        "ink":         "#1a1a2e",
        "ink_soft":    "#5a5a75",
        "ink_faint":   "#8b8ba7",
        "rule":        "#e6e6f0",
        "indigo":      "#5b3fd6",
        "indigo_dark": "#4930b0",
        "indigo_wash": "#efeafe",
        "green":       "#16a34a",
        "green_wash":  "#eafaf0",
        "amber":       "#d97706",
        "amber_wash":  "#fffbeb",
        "shadow":      "0 1px 2px rgba(26,26,46,.04)",
        "shadow_lift": "0 6px 18px rgba(26,26,46,.08)",
    },
    "dark": {
        "page":        "#131024",
        "surface":     "#1c1834",
        "surface_alt": "#221d3d",
        "ink":         "#f3f1fb",
        "ink_soft":    "#bab5d6",
        "ink_faint":   "#8b86ab",
        "rule":        "#2f2952",
        "indigo":      "#7c5cff",
        "indigo_dark": "#9b77ff",
        "indigo_wash": "#2a2350",
        "green":       "#4ade80",
        "green_wash":  "#16301f",
        "amber":       "#fbbf24",
        "amber_wash":  "#2e2410",
        "shadow":      "0 1px 2px rgba(0,0,0,.35)",
        "shadow_lift": "0 6px 18px rgba(0,0,0,.45)",
    },
}


def home_template_css(theme: str = "light", content_max_width: str = "100%") -> str:
    """Return the override stylesheet for the home page.

    ``content_max_width`` is the device-preview width the page already computed,
    re-asserted here because the shell's own ``.block-container`` rule uses
    ``!important`` and would otherwise pin the page to full width.
    """
    t = TOKENS.get(str(theme).lower(), TOKENS["light"])
    return f"""
<style>
:root {{
  --yz-page:{t['page']}; --yz-surface:{t['surface']}; --yz-surface-alt:{t['surface_alt']};
  --yz-ink:{t['ink']}; --yz-ink-soft:{t['ink_soft']}; --yz-ink-faint:{t['ink_faint']};
  --yz-rule:{t['rule']};
  --yz-indigo:{t['indigo']}; --yz-indigo-dark:{t['indigo_dark']}; --yz-indigo-wash:{t['indigo_wash']};
  --yz-green:{t['green']}; --yz-green-wash:{t['green_wash']};
  --yz-amber:{t['amber']}; --yz-amber-wash:{t['amber_wash']};
  --yz-shadow:{t['shadow']}; --yz-shadow-lift:{t['shadow_lift']};
}}

/* ---------------------------------------------------------------- ground */
html, body, .stApp, [data-testid="stAppViewContainer"] {{
  background: var(--yz-page) !important;
  color: var(--yz-ink) !important;
}}
html, body, [class*="css"] {{
  font-family: Inter, "Segoe UI", system-ui, -apple-system, sans-serif !important;
}}
/* The legacy sheet pins everything to 18px, which is a full step above the
   template and pushes every card off its intended rhythm. */
html, body, [class*="st-"] {{ font-size: 16px !important; }}

/* Content clears the fixed shell. Padding lives on the view container rather
   than .block-container so the device-preview width keeps working inside it. */
[data-testid="stMain"], [data-testid="stAppViewContainer"] > .main {{
  padding-left: var(--sb-w, 240px) !important;
  padding-top: var(--tb-h, 72px) !important;
}}
.block-container {{
  max-width: {content_max_width} !important;
  width: 100% !important;
  margin-left: auto !important;
  margin-right: auto !important;
  padding: 1.6rem 1.6rem 3rem !important;
}}
@media (max-width: 1100px) {{
  [data-testid="stMain"], [data-testid="stAppViewContainer"] > .main {{
    padding-left: 0 !important;
  }}
}}

h1, h2, h3, h4, h5, h6 {{ color: var(--yz-ink) !important; letter-spacing: -.01em; }}
p, li, span, label, .stMarkdown {{ color: var(--yz-ink-soft); }}
a {{ color: var(--yz-indigo-dark); }}
hr {{ border: none !important; border-top: 1px solid var(--yz-rule) !important; }}

/* The shell hides `footer` to kill Streamlit's own chrome, which also catches
   the page's sign-off. Put that one back. */
.stApp footer {{ display: block !important; visibility: visible !important; }}

/* Streamlit styles links inside its markdown containers, and that beats the
   shell's own rules — the top-bar CTA and the sidebar nav came out as blue
   underlined links. Restate them at a specificity Streamlit cannot outrank. */
.yz-tb a.yz-cta, .yz-tb a.yz-cta:hover, .yz-tb a.yz-cta:visited {{
  color: #fff !important; text-decoration: none !important;
}}
.yz-sb .yz-nav a, .yz-sb .yz-nav a:visited {{
  color: var(--nav-ink) !important; text-decoration: none !important;
}}
.yz-sb .yz-nav a:hover, .yz-sb .yz-nav a.on {{ color: #fff !important; }}
.yz-promo a, .yz-promo a:visited, .yz-promo a:hover {{
  color: #fff !important; text-decoration: none !important;
}}

/* Empty containers still claim a 16px flex gap each, and the top of the page
   stacks half a dozen style-only st.markdown calls — 100px of dead space above
   the hero. Collapse the ones that carry nothing but a stylesheet. The shell's
   own markdown pairs a <style> with the sidebar markup, so :only-child spares
   it, as it does every other block that renders something. */
[data-testid="stElementContainer"]:has(
  > [data-testid="stMarkdown"] > [data-testid="stMarkdownContainer"] > style:only-child
) {{ display: none !important; }}

/* The device-preview picker is pinned to the corner, below the top bar. The
   legacy sheet pinned it by "any column holding a selectbox", which now also
   catches real dropdowns further down the page — undo that. */
div[data-testid="column"]:has(div[data-baseweb="select"]) {{
  position: static !important; top: auto !important; right: auto !important;
  width: auto !important; z-index: auto !important;
}}
.st-key-device_view_pin {{
  position: fixed !important;
  top: calc(var(--tb-h, 72px) + 12px) !important;
  right: 18px !important;
  width: 200px !important;
  z-index: 900 !important;
}}
.st-key-device_view_pin label,
.stSelectbox label {{
  font-size: .72rem !important; font-weight: 650 !important;
  color: var(--yz-ink-faint) !important; text-shadow: none !important;
  letter-spacing: .02em !important; text-transform: none !important;
  margin-bottom: 3px !important;
}}
div[data-baseweb="select"] {{
  background: var(--yz-surface) !important;
  border: 1px solid var(--yz-rule) !important;
  border-radius: 10px !important;
  box-shadow: var(--yz-shadow) !important;
  backdrop-filter: none !important;
  min-height: 38px !important;
}}
/* The legacy sheet gave the control 6px of padding on top of Streamlit's own,
   which clipped the selected label to half a line. */
div[data-baseweb="select"] > div {{
  padding: 0 .6rem !important; min-height: 36px !important; display: flex !important;
  align-items: center !important;
}}
div[data-baseweb="select"] > div,
div[data-baseweb="select"] > div > div,
div[data-baseweb="select"] span,
div[data-baseweb="select"] p {{ color: var(--yz-ink) !important; font-weight: 550 !important; }}
div[data-baseweb="select"] svg, div[data-baseweb="select"] svg path {{
  fill: var(--yz-ink-faint) !important; color: var(--yz-ink-faint) !important;
}}
ul[role="listbox"] {{
  background: var(--yz-surface) !important; border: 1px solid var(--yz-rule) !important;
  border-radius: 10px !important; box-shadow: var(--yz-shadow-lift) !important;
}}
li[role="option"], li[role="option"] span, li[role="option"] div {{
  color: var(--yz-ink) !important; background: transparent !important;
}}
li[role="option"]:hover {{
  background: var(--yz-indigo-wash) !important; color: var(--yz-indigo-dark) !important;
  box-shadow: none !important;
}}

/* ----------------------------------------------------------- panel boxes */
.left-box, .right-box {{
  background: transparent !important;
  border: none !important;
  border-radius: 0 !important;
  box-shadow: none !important;
  padding: 0 !important;
  color: var(--yz-ink) !important;
}}

/* ---------------------------------------------------------------- cards */
.feature-card {{
  background: var(--yz-surface) !important;
  border: 1px solid var(--yz-rule) !important;
  border-radius: 16px !important;
  padding: 1.15rem 1.25rem !important;
  margin: 0 0 1rem !important;
  box-shadow: var(--yz-shadow) !important;
}}
.feature-card:hover {{
  transform: none !important;
  border-color: var(--yz-indigo) !important;
  box-shadow: var(--yz-shadow-lift) !important;
}}
.feature-card-blue {{
  background: var(--yz-indigo-wash) !important;
  border-color: var(--yz-indigo) !important;
}}
.feature-title {{
  font-size: 1.05rem !important;
  font-weight: 700 !important;
  color: var(--yz-ink) !important;
  margin-bottom: .55rem !important;
}}
.feature-title-blue {{ color: var(--yz-indigo-dark) !important; }}
.feature-text, .feature-card p {{
  font-size: .92rem !important;
  line-height: 1.6 !important;
  color: var(--yz-ink-soft) !important;
}}
.feature-text-white {{ color: var(--yz-ink-soft) !important; }}
.feature-card h4 {{
  font-size: .95rem !important; font-weight: 700 !important;
  color: var(--yz-ink) !important; margin: 1rem 0 .4rem !important;
}}
.feature-card strong {{ color: var(--yz-ink) !important; }}
ul.feature-list {{ list-style: none !important; padding-left: 0 !important; margin: .3rem 0 !important; }}
ul.feature-list li {{
  padding: .3rem 0 !important; font-size: .9rem !important; line-height: 1.5 !important;
  color: var(--yz-ink-soft) !important;
}}
ul.feature-list li:before {{ content: "✓ "; color: var(--yz-indigo) !important; font-weight: 700; margin-right: .4rem; }}
ul.feature-list-white li {{ color: var(--yz-ink-soft) !important; }}
ul.feature-list-white li:before {{ color: var(--yz-indigo) !important; }}

/* ------------------------------------------------------------- buttons */
.stButton > button {{
  border: 1px solid var(--yz-rule) !important;
  background: var(--yz-surface) !important;
  color: var(--yz-ink) !important;
  border-radius: 10px !important;
  font-weight: 600 !important;
  font-size: .88rem !important;
  padding: .55rem .95rem !important;
  box-shadow: none !important;
  transition: border-color .13s ease, background .13s ease !important;
}}
.stButton > button:hover {{
  border-color: var(--yz-indigo) !important;
  color: var(--yz-indigo-dark) !important;
  background: var(--yz-indigo-wash) !important;
  transform: none !important;
  filter: none !important;
  box-shadow: none !important;
}}
.stButton > button[kind="primary"],
.stButton > button[data-testid="stBaseButton-primary"] {{
  background: var(--yz-indigo) !important;
  border-color: var(--yz-indigo) !important;
}}
/* Streamlit puts the label in a nested <p>, which the page-wide body colour
   above would otherwise paint dark-on-indigo. */
.stButton > button[kind="primary"],
.stButton > button[kind="primary"] p,
.stButton > button[kind="primary"] span,
.stButton > button[kind="primary"] div,
.stButton > button[data-testid="stBaseButton-primary"],
.stButton > button[data-testid="stBaseButton-primary"] p {{ color: #fff !important; }}
.stButton > button[kind="primary"]:hover,
.stButton > button[data-testid="stBaseButton-primary"]:hover {{
  background: var(--yz-indigo-dark) !important; color: #fff !important;
}}

/* --------------------------------------------------------- quick access */
.quick-access-card, .quick-access-card.light {{
  background: var(--yz-surface) !important;
  border: 1px solid var(--yz-rule) !important;
  border-radius: 16px !important;
  padding: 1.15rem 1.25rem !important;
  box-shadow: var(--yz-shadow) !important;
}}
.quick-access-card h3 {{
  font-size: 1.05rem !important; font-weight: 700 !important;
  color: var(--yz-ink) !important; margin-bottom: .25rem !important;
}}
.quick-access-card p {{ color: var(--yz-ink-soft) !important; font-size: .88rem !important; }}
.quick-access-card .stButton > button {{
  background: var(--yz-surface) !important;
  border: 1px solid var(--yz-rule) !important;
  color: var(--yz-ink) !important;
  box-shadow: none !important;
}}
.quick-access-card .stButton > button:hover {{
  background: var(--yz-indigo-wash) !important;
  border-color: var(--yz-indigo) !important;
  color: var(--yz-indigo-dark) !important;
  transform: none !important;
}}
.neon-divider {{
  height: 1px !important; background: var(--yz-rule) !important;
  box-shadow: none !important; margin: 1.5rem 0 !important;
}}

/* ------------------------------------------------------- nav / commands */
.nav-center-wrapper, .nav-center-wrapper.light {{
  background: var(--yz-surface) !important;
  border: 1px solid var(--yz-rule) !important;
  border-radius: 16px !important;
  padding: 1.15rem 1.25rem !important;
  box-shadow: var(--yz-shadow) !important;
}}
.nav-center-header h2,
.nav-center-wrapper.light .nav-center-header h2 {{
  font-size: 1.35rem !important; font-weight: 750 !important;
  color: var(--yz-ink) !important; letter-spacing: -.02em !important;
}}
.nav-center-header p,
.nav-center-wrapper.light .nav-center-header p {{ color: var(--yz-ink-soft) !important; }}
.nav-mini-block {{
  background: var(--yz-surface-alt) !important;
  border: 1px solid var(--yz-rule) !important;
  border-radius: 14px !important;
  box-shadow: none !important;
}}
.nav-mini-block .stButton > button {{
  background: var(--yz-surface) !important;
  border: 1px solid var(--yz-rule) !important;
  color: var(--yz-ink) !important;
  box-shadow: none !important;
}}
.nav-mini-block .stButton > button:hover {{
  background: var(--yz-indigo-wash) !important;
  border-color: var(--yz-indigo) !important;
  color: var(--yz-indigo-dark) !important;
  transform: none !important;
}}
.nav-mini-desc,
.nav-center-wrapper.light .nav-mini-desc {{
  color: var(--yz-ink-faint) !important; font-size: .82rem !important;
}}
.nav-section-description {{ color: var(--yz-ink-soft) !important; font-size: .88rem !important; }}
.nav-bottom-card {{
  background: var(--yz-surface) !important;
  border: 1px solid var(--yz-rule) !important;
  border-radius: 14px !important;
  color: var(--yz-ink-soft) !important;
  box-shadow: var(--yz-shadow) !important;
}}
.nav-bottom-card h4 {{ color: var(--yz-ink) !important; }}
.nav-bottom-card .project-entry {{ border-top: 1px solid var(--yz-rule) !important; }}
.nav-bottom-card .project-entry strong {{ color: var(--yz-indigo-dark) !important; }}
.nav-bottom-card .project-meta,
.nav-bottom-card .project-scores,
.nav-bottom-card .builder-list,
.nav-bottom-card .search-footer {{ color: var(--yz-ink-soft) !important; }}
.nav-bottom-card .project-score {{ color: var(--yz-green) !important; }}
.nav-bottom-card .search-chip {{
  background: var(--yz-indigo-wash) !important; color: var(--yz-indigo-dark) !important;
}}

/* ------------------------------------------------------ challenge cards */
.challenge-form-card, .challenge-form-card.light {{
  background: var(--yz-surface) !important;
  border: 1px solid var(--yz-rule) !important;
  border-radius: 14px !important;
  box-shadow: var(--yz-shadow) !important;
}}
.challenge-form-card h4 {{ color: var(--yz-ink) !important; }}
.challenge-form-meta,
.challenge-form-card.light .challenge-form-meta,
.challenge-attachment-list li,
.challenge-form-card.light .challenge-attachment-list li {{ color: var(--yz-ink-soft) !important; }}
.challenge-form-actions .primary {{
  background: var(--yz-indigo) !important; color: #fff !important;
}}
.challenge-form-actions .secondary,
.challenge-form-card.light .challenge-form-actions .secondary {{
  background: var(--yz-indigo-wash) !important; color: var(--yz-indigo-dark) !important;
}}

/* --------------------------------------------------------------- tables */
.neon-table, .neon-table.light {{
  background: var(--yz-surface) !important;
  border: 1px solid var(--yz-rule) !important;
  border-radius: 16px !important;
  padding: 1.15rem 1.25rem !important;
  box-shadow: var(--yz-shadow) !important;
  animation: none !important;
}}
.neon-table-title,
.neon-table.light .neon-table-title {{
  font-size: 1.02rem !important; font-weight: 700 !important;
  color: var(--yz-ink) !important; letter-spacing: 0 !important;
  margin-bottom: .8rem !important;
}}
.neon-table-header {{
  background: var(--yz-surface-alt) !important;
  border: 1px solid var(--yz-rule) !important;
  border-radius: 10px !important;
  box-shadow: none !important;
  margin-bottom: .35rem !important;
}}
.neon-table-header .neon-table-cell {{
  color: var(--yz-ink-faint) !important;
  font-size: .78rem !important;
  font-weight: 650 !important;
  letter-spacing: .02em !important;
  min-height: 40px !important;
}}
.neon-table-cell,
.neon-table.light .neon-table-cell {{
  color: var(--yz-ink-soft) !important;
  border-right: none !important;
  font-size: .86rem !important;
  min-height: 46px !important;
}}
.neon-table-cell strong {{ color: var(--yz-ink) !important; font-weight: 650 !important; }}
.neon-table-row, .neon-table.light .neon-table-row {{
  background: transparent !important;
  border: none !important;
  border-bottom: 1px solid var(--yz-rule) !important;
  border-radius: 0 !important;
  margin-bottom: 0 !important;
  box-shadow: none !important;
}}
.neon-table-row:hover {{
  background: var(--yz-surface-alt) !important;
  transform: none !important;
  box-shadow: none !important;
  border-color: var(--yz-rule) !important;
}}
.neon-table-action {{
  background: var(--yz-indigo) !important;
  color: #fff !important;
  border-radius: 9px !important;
  padding: .38rem .85rem !important;
  font-size: .8rem !important;
  font-weight: 650 !important;
  box-shadow: none !important;
}}
.neon-table-action:hover {{ background: var(--yz-indigo-dark) !important; color: #fff !important; }}
.neon-action-secondary,
.neon-table.light .neon-action-secondary {{
  color: var(--yz-indigo-dark) !important; font-size: .78rem !important; font-weight: 600 !important;
}}
.table-tag, .neon-table.light .table-tag {{
  background: var(--yz-indigo-wash) !important; color: var(--yz-indigo-dark) !important;
  font-size: .74rem !important;
}}
.om-sample-tag {{ color: var(--yz-ink-faint) !important; border-color: var(--yz-rule) !important; }}
.status-badge {{
  background: var(--yz-indigo-wash) !important; border: 1px solid var(--yz-indigo) !important;
  color: var(--yz-indigo-dark) !important; font-size: .74rem !important;
}}
.status-badge.success {{
  background: var(--yz-green-wash) !important; border-color: var(--yz-green) !important;
  color: var(--yz-green) !important;
}}
.status-badge.warning {{
  background: var(--yz-amber-wash) !important; border-color: var(--yz-amber) !important;
  color: var(--yz-amber) !important;
}}
.status-badge.danger {{
  background: #fef2f2 !important; border-color: #dc2626 !important; color: #dc2626 !important;
}}
.status-badge.info {{
  background: var(--yz-indigo-wash) !important; border-color: var(--yz-indigo) !important;
  color: var(--yz-indigo-dark) !important;
}}
.neon-table-empty, .neon-table.light .neon-table-empty {{
  color: var(--yz-ink-faint) !important; font-style: normal !important;
}}

/* ------------------------------------------------------------- feedback */
.feedback-stars {{ animation: none !important; text-shadow: none !important; color: var(--yz-amber) !important; }}
.feedback-text {{ color: var(--yz-ink-faint) !important; }}

/* ---------------------------------------------------- Streamlit widgets */
div[data-testid="stTextArea"] textarea,
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input {{
  background: var(--yz-surface) !important;
  color: var(--yz-ink) !important;
  border: 1px solid var(--yz-rule) !important;
  border-radius: 10px !important;
}}
div[data-testid="stExpander"] {{
  background: var(--yz-surface) !important;
  border: 1px solid var(--yz-rule) !important;
  border-radius: 14px !important;
}}
[data-testid="stAlert"] {{ border-radius: 12px !important; }}
[data-testid="stCaptionContainer"], .stCaption {{ color: var(--yz-ink-faint) !important; }}

footer {{
  text-align: center; padding: 2rem 0 1rem; margin-top: 2.5rem;
  border-top: 1px solid var(--yz-rule) !important;
  color: var(--yz-ink-faint) !important;
  font-size: .85rem !important; font-weight: 500 !important;
}}
</style>
"""
