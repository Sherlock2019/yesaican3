"""My Company Workflows Ontology — how work moves between business units.

Its own page rather than a preamble on the submission form. The ontology is
reference material the whole app is built on: the pipeline counts pain onto its
handoffs, similarity uses its business objects, and the dashboard ranks reach
across it. Anyone should be able to read it, or fix a handoff that is modelled
wrong, without first opening a form that asks them what hurts.

The section itself is imported from the capture page rather than reimplemented,
so this is a move and not a second copy that drifts. The flag stops that module
running its own page bootstrap on import; see services/ui/utils/embed_flags.py.
"""

from __future__ import annotations

import streamlit as st

from services.shared import business_flow as bf
from services.ui.utils import embed_flags
from services.ui.utils.auth_gate import require_auth
from services.ui.utils.meta_store import load_json
from services.ui.utils.page_template import page_chrome
from services.ui.utils.pain_capture_ui import CAPTURE_CSS

embed_flags.CAPTURE_EMBEDDED = True
try:
    from services.ui.pages import how_can_ai_help as capture
finally:
    embed_flags.CAPTURE_EMBEDDED = False

SUBMISSIONS_FILE = "how_ai_help_submissions.json"


def load_submissions() -> list[dict]:
    data = load_json(SUBMISSIONS_FILE, [])
    return [r for r in data if isinstance(r, dict)] if isinstance(data, list) else []


st.set_page_config(page_title="My Company Workflows Ontology — YES AI CAN",
                   page_icon="🏢", layout="wide")
require_auth()

page_chrome(
    "company_workflows",
    "My Company Workflows Ontology",
    "How work moves between business units — and where the pain sits on it.",
)

# The section is built from the capture page's own markup, so it needs that
# page's stylesheet. Without it the value chain renders as unstyled text.
st.markdown(CAPTURE_CSS, unsafe_allow_html=True)
st.markdown("---")

submissions = load_submissions()

# Draws the four ontology layers, the value chain with pain counted onto each
# handoff, and the interactive flow builder underneath it.
capture.render_business_flow(submissions)

st.divider()

# A little orientation, since this page is now reachable without having gone
# through the form that used to explain it.
left, right = st.columns(2, gap="medium")
with left:
    st.markdown("#### What this is for")
    st.markdown(
        "- **Submitting a painpoint** asks which handoff your task feeds. That is what "
        "lets the app tell you who else is affected.\n"
        "- **The dashboard** ranks painpoints by how many units they reach, using these "
        "edges.\n"
        "- **Similarity** treats two painpoints sitting on the same business object as a "
        "stronger match than two that merely read alike."
    )
with right:
    st.markdown("#### If a handoff is wrong")
    st.markdown(
        "Change it in the flow builder above. Edits are kept separately from the "
        "modelled chain and marked **edited** or **proposed**, so a handoff somebody "
        "changed this morning is never mistaken for the original model."
    )
    st.caption(
        f"{len(bf.all_edges())} handoffs · {len(bf.BUSINESS_UNITS)} business units · "
        f"{len(bf.BUSINESS_OBJECTS)} business objects"
    )
