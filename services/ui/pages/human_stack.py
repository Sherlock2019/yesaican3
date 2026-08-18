# Human Stack Directory — YES AI CAN
# Directory of all Rackers participating in AI innovation

import streamlit as st
import hashlib
import html
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

from services.ui.utils.meta_store import load_json, save_json, META_DIR
from services.ui.utils import embed_flags
from services.ui.utils.page_template import page_chrome

st.set_page_config(
    page_title="Human Stack Directory — YES AI CAN",
    layout="wide"
)

STAR_CSS = """
<style>
.hs-star {
    display:inline-block;
    font-size:18px;
    margin-right:2px;
    transition:all 0.3s ease;
}

.hs-star-on {
    color:#FFD447;
    text-shadow:0 0 6px #ffea8a, 0 0 12px #ffd447;
    animation:pulseStar 1.8s infinite ease-in-out;
}

.hs-star-off {
    color:#3c3c3c;
}

@keyframes pulseStar {
    0%   { text-shadow:0 0 4px #ffea8a; transform:scale(1);}
    50%  { text-shadow:0 0 10px #ffd447, 0 0 20px #ffea8a; transform:scale(1.15); }
    100% { text-shadow:0 0 4px #ffea8a; transform:scale(1);}
}

.feedback-block {
    display:flex;
    flex-direction:column;
    justify-content:flex-start;
    align-items:flex-start;
    gap:4px;
    padding-top:4px;
}

.feedback-stars {
    color:#ffd700;
    font-size:18px;
    text-shadow:0 0 6px #ffdd55, 0 0 12px #ffaa00;
    animation:starPulse 1.8s infinite ease-in-out;
}

.feedback-comment {
    font-size:13px;
    color:#cbd5e1;
    max-width:260px;
    line-height:1.2;
    word-wrap:break-word;
}
</style>
"""

# ============================================
# AI-Augmented Services / Products Catalog
# Used to enrich the Human Stack search bar
# ============================================
AI_SERVICE_CATALOG: List[Dict[str, Any]] = [
    {
        "name": "AI Billing Reconciliation & Formatter",
        "department": "Finance / Billing",
        "product_tag": "billing-formatter",
        "description": (
            "Auto-match ERP exports vs invoices, normalize customer formats "
            "to RAX schema, and flag mismatches."
        ),
        "skills": [
            "LLM Guardrails",
            "Workflow Automation",
            "Data Engineering",
            "Reliability Engineering",
            "Cloud",
        ],
        "search_tags": ["billing", "reconciliation", "invoice", "finance-ai"],
    },
    {
        "name": "AI Renewal Risk Radar",
        "department": "Sales Ops / GTM",
        "product_tag": "renewal-risk-radar",
        "description": (
            "Score renewal risk, summarize notes, and surface save-motions & playbooks."
        ),
        "skills": [
            "Generative AI",
            "Analytics",
            "Recommendation",
            "Prompt Artistry",
        ],
        "search_tags": ["renewal", "churn", "sales-ai", "account-health"],
    },
    {
        "name": "AI Ticket Triage & Escalation Predictor",
        "department": "Customer Support / NOC",
        "product_tag": "ticket-triage",
        "description": (
            "Classify tickets, predict escalation risk, and suggest next actions / runbooks."
        ),
        "skills": [
            "Monitoring AI",
            "Reinforcement Learning",
            "Autonomy",
            "Agent Orchestration",
            "IT Troubleshooter",
        ],
        "search_tags": ["ticket", "support-ai", "escalation", "triage"],
    },
    {
        "name": "Infra Readiness & Capacity Copilot",
        "department": "Cloud / Infra / OpenStack",
        "product_tag": "infra-capacity-copilot",
        "description": (
            "Parse logs, run pre-change checks, and forecast CPU/storage exhaustion."
        ),
        "skills": [
            "Cloud",
            "Reliability Engineering",
            "Simulation",
            "Workflow Automation",
            "Self-Supervised",
        ],
        "search_tags": ["openstack", "capacity", "deploy-check", "infra-ai"],
    },
    {
        "name": "AI SOC Incident Reporter",
        "department": "Security / SOC",
        "product_tag": "soc-incident-reporter",
        "description": (
            "Group events, generate timelines & compliance-ready narratives, and highlight gaps."
        ),
        "skills": [
            "AI Safety",
            "LLM Guardrails",
            "Monitoring AI",
            "Security Analytics",
        ],
        "search_tags": ["soc", "incident-report", "security-ai", "siem"],
    },
    {
        "name": "HR Onboarding Router & FAQ Copilot",
        "department": "HR / People Ops",
        "product_tag": "hr-onboarding-router",
        "description": (
            "Auto-classify HR tickets, suggest answers, and collect missing information."
        ),
        "skills": [
            "Human–AI Interaction",
            "Multimodal ML",
            "Workflow Automation",
        ],
        "search_tags": ["hr", "onboarding", "people-ai", "faq-bot"],
    },
    {
        "name": "Contract Clause Extractor & Risk Annotator",
        "department": "Legal / Compliance",
        "product_tag": "contract-clause-extractor",
        "description": (
            "OCR + parse PDFs, label clauses, and explain risks in simple language."
        ),
        "skills": [
            "Multimodal ML",
            "Vision AI",
            "LLM Guardrails",
            "Prompt Artistry",
        ],
        "search_tags": ["contract", "legal-ai", "clause", "doc-ai"],
    },
    {
        "name": "Engineering Health & Repo Insights",
        "department": "Product / Engineering",
        "product_tag": "engineering-health-dashboard",
        "description": (
            "Track commits, PR velocity, churn, flaky tests, and agent usage."
        ),
        "skills": [
            "Agent Orchestration",
            "Monitoring AI",
            "DevOps",
            "Analytics",
        ],
        "search_tags": ["repo-health", "engineering-ai", "devops"],
    },
    {
        "name": "Analytics Question-Answering Copilot",
        "department": "Data & Analytics",
        "product_tag": "analytics-qa-copilot",
        "description": (
            "Turn natural-language questions into SQL, charts, and narrative insights."
        ),
        "skills": [
            "Generative AI",
            "Reinforcement Learning",
            "Data Engineering",
            "LLM Guardrails",
        ],
        "search_tags": ["bi", "analytics-ai", "data-copilot"],
    },
    {
        "name": "AI Strategy & Portfolio Cockpit",
        "department": "Exec / Strategy / CFO / CIO",
        "product_tag": "ai-portfolio-cockpit",
        "description": (
            "Aggregate agents, usage, value, risk posture, and OKR impact."
        ),
        "skills": [
            "AI Safety",
            "Monitoring AI",
            "Model Alignment",
            "Analytics",
        ],
        "search_tags": ["portfolio", "strategy-ai", "ai-roi", "exec-dashboard"],
    },
    {
        "name": "Vendor & SLA Comparison Assistant",
        "department": "Procurement / Vendor Mgmt",
        "product_tag": "vendor-sla-assistant",
        "description": (
            "Extract obligations from contracts, compare vendors, and highlight gaps."
        ),
        "skills": [
            "Vision AI",
            "LLM Guardrails",
            "Prompt Artistry",
        ],
        "search_tags": ["vendor", "sla", "procurement-ai"],
    },
    {
        "name": "Learning Path & Skill Gap Copilot",
        "department": "Training / L&D",
        "product_tag": "learning-path-copilot",
        "description": (
            "Map skills to gaps and learning paths, and recommend training content."
        ),
        "skills": [
            "Human–AI Interaction",
            "Recommendation",
            "Generative AI",
        ],
        "search_tags": ["learning", "skills", "training-ai"],
    },
]

def load_humans() -> List[Dict]:
    """
    Load humans.json from the meta store (.sandbox_meta directory).
    This uses the centralized meta_store utility for consistent file access.
    """
    try:
        data = load_json("humans.json", [])
        if not isinstance(data, list):
            return []
        return data
    except Exception as e:
        st.error(f"Failed to load humans.json: {e}")
        return []

# def load_humans() -> List[Dict]:
#     base_records = load_json("humans.json", [])
#     if not isinstance(base_records, list):
#         base_records = []
#     data_path = Path(__file__).resolve().parents[2] / "data" / "humans.json"
#     data_records: List[Dict] = []
#     if data_path.exists():
#         try:
#             with open(data_path, "r", encoding="utf-8") as handle:
#                 raw = json.load(handle)
#                 if isinstance(raw, list):
#                     data_records = raw
#         except Exception:
#             data_records = []
#     combined = list(base_records)
#     seen: set[str] = {
#         str(item.get("id") or item.get("email") or item.get("name", "")).lower()
#         for item in combined
#         if item
#     }
#     for record in data_records:
#         key = str(record.get("id") or record.get("email") or record.get("name", "")).lower()
#         if not key or key in seen:
#             continue
#         combined.append(record)
#         seen.add(key)
#     return combined


def save_humans(humans: List[Dict]):
    """
    Save humans list to the meta store (.sandbox_meta directory).
    This uses the centralized meta_store utility for consistent file access.
    """
    try:
        save_json("humans.json", humans)
    except Exception as e:
        st.error(f"Failed to save profile: {e}")

def generate_id() -> str:
    """Generate a unique ID for a profile."""
    return f"human_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(load_humans())}"


def hash_password(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_profile_feedback() -> Dict[str, List[Dict[str, Any]]]:
    raw = load_json("human_feedback.json", {})
    normalized: Dict[str, List[Dict[str, Any]]] = {}
    if isinstance(raw, dict):
        for key, value in raw.items():
            if isinstance(value, list):
                normalized[key] = value
            elif isinstance(value, dict):
                normalized[key] = [value]
    return normalized


def save_profile_feedback(record: Dict[str, List[Dict[str, Any]]]) -> None:
    save_json("human_feedback.json", record)


def render_rating_stars(score: int | None) -> str:
    if score is None or score < 0:
        score = 0
    bounded = min(5, max(0, score))
    return "★" * bounded + "☆" * (5 - bounded)


def render_stars(rating: int) -> str:
    stars = []
    for idx in range(1, 6):
        cls = "hs-star-on" if idx <= rating else "hs-star-off"
        stars.append(f"<span class='hs-star {cls}'>★</span>")
    return "".join(stars)


def format_review_timestamp(value: str | None) -> str:
    if not value:
        return "Unknown time"
    try:
        parsed = datetime.fromisoformat(value)
        return parsed.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(value)



# This page's own chrome. Community imports the three render functions below
# and calls them inside its own tabs, so none of this may run on import.
if not embed_flags.PROFILES_EMBEDDED:
    page_chrome('human_stack', 'People & Skills',
                'Who knows what — skills, SMEs and portfolios.')
    st.markdown(STAR_CSS, unsafe_allow_html=True)


# humans = load_humans()
# query_params = st.experimental_get_query_params()
# profile_param = (query_params.get("profile_id") or [None])[0]
# if profile_param:
#     st.session_state["view_profile"] = profile_param

# # ─────────────────────────────
# # TAB 1 — Card Directory
# # ─────────────────────────────
# with tab1:
#     st.subheader("All Rackers in AI Innovation")

#     # Focused profile view (when launched from any View button)
#     view_id = st.session_state.get("view_profile")
#     if view_id:
#         target = next((h for h in humans if str(h.get("id")) == str(view_id)), None)
#         if target:
#             st.markdown(f"### 👤 {target.get('name','Unknown')}")
#             col_a, col_b = st.columns(2)
#             with col_a:
#                 st.write(f"**Department:** {target.get('department','N/A')}")
#                 st.write(f"**Region:** {target.get('region','N/A')}")
#                 st.write(f"**Role:** {target.get('role','N/A')}")
#                 st.write(f"**Skills:** {', '.join(target.get('skills', [])) or '—'}")
#                 st.write(f"**Products Built:** {', '.join(target.get('ai_services', [])) or '—'}")
#             with col_b:
#                 if target.get("bio"):
#                     st.write(f"**Bio:** {target.get('bio')}")
#                 if target.get("domain_expertise"):
#                     st.write(f"**Domain Expertise:** {target.get('domain_expertise')}")
#                 if target.get("linkedin"):
#                     st.markdown(f"[🔗 LinkedIn]({target.get('linkedin')})")
#                 if target.get("github"):
#                     st.markdown(f"[🔗 GitHub]({target.get('github')})")
#                 if target.get("portfolio"):
#                     st.markdown(f"[🔗 Portfolio]({target.get('portfolio')})")

#             actions = st.columns(3)
#             if actions[0].button("← Back to list", key="view_back"):
#                 st.session_state.pop("view_profile", None)
#                 st.rerun()
#             if actions[1].button("Edit", key="view_edit"):
#                 st.session_state["edit_profile"] = view_id
#                 st.rerun()
#             if actions[2].button("Delete", key="view_delete"):
#                 humans = [h for h in humans if str(h.get("id")) != str(view_id)]
#                 save_humans(humans)
#                 st.session_state.pop("view_profile", None)
#                 st.success("Profile deleted.")
#                 st.rerun()
#             st.markdown("---")
#         else:
#             st.warning("Selected profile not found. It may have been removed.")
#             st.session_state.pop("view_profile", None)

#     if not humans:
#         st.info("👋 No profiles yet. Be the first to create your profile!")
#     else:
#         # Display as cards
#         cols = st.columns(3)
#         for idx, human in enumerate(humans):
#             with cols[idx % 3]:
#                 with st.container():
#                     st.markdown(
#                         f"""
#                         <div style="background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
#                                     border: 2px solid #ff0066; border-radius: 12px; padding: 1.5rem; margin-bottom: 1rem;
#                                     box-shadow: 0 4px 12px rgba(255,0,102,0.1);">
#                             <h3 style="color: #ff0066; margin-bottom: 0.5rem;">{human.get('name', 'Unknown')}</h3>
#                             <p style="color: #334155; margin: 0.3rem 0;"><strong>Role:</strong> {human.get('role', 'N/A')}</p>
#                             <p style="color: #334155; margin: 0.3rem 0;"><strong>Department:</strong> {human.get('department', 'N/A')}</p>
#                             <p style="color: #334155; margin: 0.3rem 0;"><strong>Region:</strong> {human.get('region', 'N/A')}</p>
#                             <p style="color: #334155; margin: 0.3rem 0;"><strong>Skills:</strong> {', '.join(human.get('skills', [])[:3])}</p>
#                         </div>
#                         """,
#                         unsafe_allow_html=True,
#                     )

#                     cta_col1, cta_col2, cta_col3 = st.columns(3)
#                     with cta_col1:
#                         if st.button("View", key=f"view_{human.get('id')}"):
#                             st.session_state["view_profile"] = human.get("id")
#                             st.rerun()
#                     with cta_col2:
#                         if st.button("Edit", key=f"t1_edit_{human.get('id')}"):
#                             st.session_state["edit_profile"] = human.get("id")
#                             st.session_state["view_profile"] = human.get("id")
#                             st.rerun()
#                     with cta_col3:
#                         if st.button("Delete", key=f"delete_{human.get('id')}"):
#                             humans = [h for h in humans if h.get("id") != human.get("id")]
#                             save_humans(humans)
#                             st.success(f"Deleted profile: {human.get('name', 'Unknown')}")
#                             st.rerun()
# ─────────────────────────────
# TAB 1 — Card Directory
# ─────────────────────────────
def render_directory():
    # Loaded per call: this renders inside Community too, and a module-level
    # read would go stale after the first run of that page.
    humans = load_humans()
    profile_feedback = load_profile_feedback()

    url_profile_id = st.query_params.get('profile_id')
    if url_profile_id and 'view_profile' not in st.session_state:
        st.session_state['view_profile'] = url_profile_id

    st.subheader("All Rackers in AI Innovation")

    view_id = st.session_state.get("view_profile")

    if view_id:
        target = next((h for h in humans if str(h.get("id")) == str(view_id)), None)

        if target:
            if st.button("← Back to Directory", key="view_back_top"):
                st.session_state.pop("view_profile", None)
                st.rerun()

            st.markdown("---")

            profile_key = str(target.get("id"))
            reviews = profile_feedback.get(profile_key, [])
            latest_review = reviews[-1] if reviews else None
            average_score = (
                round(
                    sum((review.get("rating", 0) for review in reviews)) / len(reviews),
                    1,
                )
                if reviews
                else 0
            )

            col_header, col_badge, col_actions = st.columns([3, 1, 1])
            with col_header:
                st.markdown(f"## 👤 {target.get('name', 'Unknown')}")
                st.markdown(f"**{target.get('role', 'N/A')}** | {target.get('department', 'N/A')}")
            with col_badge:
                if reviews:
                    badge_stars = render_rating_stars(int(round(average_score)))
                    st.markdown(
                        f"""
                        <div style="background: linear-gradient(135deg, #ffd700 0%, #ffed4e 100%);
                                    border: 2px solid #ff0066; border-radius: 12px; padding: 1rem;
                                    text-align: center; box-shadow: 0 4px 12px rgba(255,0,102,0.2);">
                            <div style="font-size: 2em; margin-bottom: 0.25rem;">{badge_stars}</div>
                            <div style="font-weight: bold; color: #1e293b; font-size: 1.2em;">{average_score:.1f}/5</div>
                            <div style="font-size: 0.75em; color: #475569; margin-top: 0.25rem;">Badge of Honor</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        """
                        <div style="background: #f1f5f9; border: 2px dashed #94a3b8; border-radius: 12px; 
                                    padding: 1rem; text-align: center;">
                            <div style="font-size: 1.5em; margin-bottom: 0.25rem;">⭐</div>
                            <div style="font-size: 0.85em; color: #64748b;">Not rated yet</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            with col_actions:
                if st.button("✏️ Edit Profile", key="view_edit_large", use_container_width=True):
                    st.session_state["edit_profile"] = view_id
                    st.info("Go to the 'Create/Edit Profile' tab to make changes.")

            if latest_review and latest_review.get("comment"):
                author_label = html.escape(latest_review.get("commenter", "Community"))
                st.markdown(
                    f"""
                    <div style="background: #f0f9ff; border-left: 4px solid #0ea5e9; 
                                padding: 1rem; margin: 1rem 0; border-radius: 8px;">
                        <strong style="color: #0c4a6e;">💬 Community Feedback:</strong>
                        <p style="margin: 0.5rem 0 0 0; color: #334155; font-style: italic;">"{html.escape(latest_review.get('comment'))}"</p>
                        <small style="color:#475569;">— {author_label}</small>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            st.markdown("---")

            c1, c2 = st.columns([1, 2])

            with c1:
                st.markdown("#### 📌 Contact & Info")
                st.write(f"**Region:** {target.get('region', 'N/A')}")
                st.write(f"**Team:** {target.get('team', 'N/A')}")
                st.write(f"**Email:** {target.get('email', 'N/A')}")

                st.markdown("#### 🔗 Links")
                links = []
                if target.get('linkedin'): links.append(f"[LinkedIn]({target.get('linkedin')})")
                if target.get('github'): links.append(f"[GitHub]({target.get('github')})")
                if target.get('portfolio'): links.append(f"[Portfolio]({target.get('portfolio')})")

                if links:
                    for link in links:
                        st.markdown(f"- {link}")
                else:
                    st.caption("No links provided.")

                st.markdown("#### 📫 Contact this profile")
                contact_options = ["Teams", "Slack", "Email"]
                selected_channel = st.selectbox(
                    "Choose a channel",
                    options=contact_options,
                    key=f"contact_channel_{target.get('id')}",
                )
                email_addr = target.get("email") or ""
                contact_links = {
                    "Teams": target.get("teams_link") or f"https://teams.microsoft.com/l/chat/0/0?users={email_addr}",
                    "Slack": target.get("slack_link") or f"https://slack.com/app_redirect?channel={email_addr}",
                    "Email": f"mailto:{email_addr}" if email_addr else "",
                }
                contact_url = contact_links.get(selected_channel, "")
                if contact_url:
                    st.markdown(
                        f"""
                        <a href="{contact_url}" target="_blank">
                            <div style="display:inline-flex; align-items:center; justify-content:center;
                                        padding:0.45rem 0.9rem; border-radius:12px; background:#0ea5e9;
                                        color:#fff; font-weight:700;">Contact via {selected_channel}</div>
                        </a>
                        """,
                        unsafe_allow_html=True,
                    )
                else:
                    st.caption("Contact link is not configured for this channel.")

            with c2:
                st.markdown("#### 🛠 Skills")
                if target.get('skills'):
                    skills_html = "".join([
                        f"<span style='background-color:#f0f2f6; color:#31333F; padding:4px 8px; margin:0 4px 4px 0; border-radius:4px; display:inline-block; font-size:0.9em; border:1px solid #dce0e6'>{s}</span>" 
                        for s in target.get('skills', [])
                    ])
                    st.markdown(skills_html, unsafe_allow_html=True)
                else:
                    st.write("—")

                st.markdown("#### 📖 Bio")
                st.info(target.get('bio', 'No bio provided.'))

                st.markdown("#### 🧠 Domain Expertise")
                st.write(target.get('domain_expertise', 'N/A'))

            st.markdown("---")

            if reviews:
                col_stat1, col_stat2 = st.columns(2)
                with col_stat1:
                    stars_stat = render_rating_stars(int(round(average_score)))
                    col_stat1.metric("Average Rating", f"{average_score:.1f}/5 {stars_stat}")
                with col_stat2:
                    last_updated = format_review_timestamp(latest_review.get("updated_at") if latest_review else None)
                    col_stat2.metric("Last Review", last_updated)

            st.markdown("#### ⭐ Rate this profile")
            rating_default = latest_review.get("rating") if latest_review else 4
            comment_default = latest_review.get("comment", "") if latest_review else ""
            comment_author = (
                latest_review.get("commenter", "")
                if latest_review
                else ""
            )
            with st.form(f"rating_form_{target.get('id')}"):
                rating_choice = st.select_slider(
                    "Score (3-5 stars):",
                    options=[3, 4, 5],
                    value=rating_default if isinstance(rating_default, int) else 4,
                    format_func=lambda val: f"{render_rating_stars(val)} {val}/5",
                )
                commenter_name = st.text_input(
                    "Commenter name (optional)",
                    value=comment_author,
                    key=f"commenter_name_{profile_key}",
                    placeholder="e.g. Cassie, Product Ops",
                )
                comment_txt = st.text_area(
                    "Tell us why you scored them (optional):",
                    value=comment_default,
                    placeholder="Great communicator, built <XYZ>, 0.1s..."
                )
                submitted_rating = st.form_submit_button("Submit rating", use_container_width=True)
                if submitted_rating:
                    feedback_payload = {
                        "rating": rating_choice,
                        "comment": comment_txt.strip(),
                        "commenter": commenter_name.strip() or None,
                        "updated_at": datetime.now().isoformat(),
                    }
                    profile_feedback.setdefault(profile_key, [])
                    profile_feedback[profile_key].append(feedback_payload)
                    save_profile_feedback(profile_feedback)
                    st.success("Thanks! Your rating is now part of the badge.")
                    st.balloons()
                    st.rerun()

            st.markdown("---")

            with st.expander(f"Community Reviews ({len(reviews)})", expanded=bool(reviews)):
                if not reviews:
                    st.caption("No reviews yet. Be the first to share your experience!")
                else:
                    for review in reversed(reviews):
                        comment_content = review.get("comment", "").strip()
                        stars_display = render_rating_stars(review.get("rating", 0))
                        timestamp = format_review_timestamp(review.get("updated_at"))
                        author_line = html.escape(review.get("commenter", "Community"))
                        st.markdown(
                            f"""
                            <div style="border:1px solid rgba(15,23,42,0.08); padding:0.85rem; border-radius:10px; margin-bottom:0.75rem; background:#ffffff;">
                                <div style="display:flex; justify-content:space-between; align-items:center;">
                                    <div style="font-weight:600; font-size:1rem;">{stars_display} {review.get('rating', 0)}/5</div>
                                    <div style="font-size:0.75rem; color:#64748b;">{timestamp}</div>
                                </div>
                                <div style="font-size:0.75rem; color:#475569; margin-top:0.15rem;">— {author_line}</div>
                                <p style="margin:0.5rem 0 0 0; color:#334155;">{html.escape(comment_content) if comment_content else '<em>No comment provided.</em>'}</p>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

            col_del1, col_del2 = st.columns([3, 1])
            with col_del2:
                if st.button("🗑️ Delete Profile", key="view_delete_large", type="secondary"):
                    humans = [h for h in humans if str(h.get("id")) != str(view_id)]
                    save_humans(humans)
                    st.session_state.pop("view_profile", None)
                    st.success("Profile deleted.")
                    st.rerun()

        else:
            st.warning(f"Profile with ID '{view_id}' not found. It may have been deleted.")
            if st.button("Back to List"):
                st.session_state.pop("view_profile", None)
                if "profile_id" in st.query_params:
                    del st.query_params["profile_id"]
                st.rerun()

    else:
        if not humans:
            st.info("👋 No profiles yet. Be the first to create your profile!")
        else:
            cols = st.columns(3)
            for idx, human in enumerate(humans):
                profile_key = str(human.get("id"))
                reviews = profile_feedback.get(profile_key, [])
                latest_review = reviews[-1] if reviews else None
                average_score = (
                    round(
                        sum((review.get("rating", 0) for review in reviews)) / len(reviews),
                        1,
                    )
                    if reviews
                    else None
                )
                with cols[idx % 3]:
                    with st.container():
                        st.markdown(
                            f"""
                            <div style="background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
                                        border: 1px solid #e2e8f0; border-radius: 12px; padding: 1.5rem; margin-bottom: 1rem;
                                        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
                                <h3 style="color: #ff0066; margin-bottom: 0.5rem;">{human.get('name', 'Unknown')}</h3>
                                <div style="font-size: 0.9em; color: #64748b; margin-bottom: 0.5rem;">
                                    {human.get('role', 'N/A')} <br>
                                    {human.get('department', 'N/A')}
                                </div>
                                <p style="color: #334155; font-size: 0.85em;">
                                    <strong>Skills:</strong> {', '.join(human.get('skills', [])[:3])}{'...' if len(human.get('skills', [])) > 3 else ''}
                                </p>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                        if st.button("View Profile", key=f"view_{human.get('id')}", use_container_width=True):
                            st.session_state["view_profile"] = human.get("id")
                            st.rerun()
                if reviews:
                    stars_html = render_stars(int(round(average_score)))
                    comment_excerpt = (latest_review.get("comment", "") if latest_review else "").strip()
                    comment_text = html.escape(comment_excerpt.replace("\n", " ").strip() or "No feedback yet.")
                    if len(comment_text) > 220:
                        comment_text = comment_text[:220].rstrip() + "…"
                    html_feedback = f"""
                    <div class="feedback-block">
                        <div class="feedback-stars">{stars_html}</div>
                        <div class="feedback-comment">{comment_text}</div>
                    </div>
                    """
                    st.markdown(html_feedback, unsafe_allow_html=True)
# ─────────────────────────────
# TAB 2 — Create / Edit Profile
# ─────────────────────────────
def render_profile_form():
    # Loaded per call: this renders inside Community too, and a module-level
    # read would go stale after the first run of that page.
    humans = load_humans()
    profile_feedback = load_profile_feedback()

    st.subheader("Create or Edit Your Profile")

    # Check if editing
    edit_id = st.session_state.get("edit_profile")
    editing = None
    if edit_id:
        for h in humans:
            if h.get("id") == edit_id:
                editing = h
                break

    with st.form("profile_form"):
        name = st.text_input("Full Name *", value=editing.get("name", "") if editing else "")
        email = st.text_input("Email *", value=editing.get("email", "") if editing else "")
        department = st.text_input("Department / BU", value=editing.get("department", "") if editing else "")
        team = st.text_input("Team", value=editing.get("team", "") if editing else "")
        role = st.text_input("Role", value=editing.get("role", "") if editing else "")
        region_choices = ["Americas", "EMEA", "APAC", "Global"]
        region_default = 0
        if editing:
            try:
                region_default = region_choices.index(editing.get("region", "Americas"))
            except ValueError:
                region_default = 0
        region = st.selectbox(
            "Region / Time zone",
            region_choices,
            index=region_default,
        )

        skills_input = st.text_input(
            "Skills (comma-separated)",
            value=", ".join(editing.get("skills", [])) if editing else "",
        )
        skills = [s.strip() for s in skills_input.split(",") if s.strip()]

        domain_expertise = st.text_area(
            "Domain Expertise", value=editing.get("domain_expertise", "") if editing else ""
        )
        bio = st.text_area("Bio / Introduction", value=editing.get("bio", "") if editing else "")

        linkedin = st.text_input("LinkedIn URL", value=editing.get("linkedin", "") if editing else "")
        github = st.text_input("GitHub URL", value=editing.get("github", "") if editing else "")
        portfolio = st.text_input("Portfolio URL", value=editing.get("portfolio", "") if editing else "")

        password_label = (
            "Password * (used for login)" if not editing else "Password (leave blank to keep current)"
        )
        password_input = st.text_input(
            password_label, type="password", placeholder="Enter a secure password"
        )
        confirm_password = st.text_input(
            "Confirm Password", type="password", placeholder="Re-enter password"
        )

        resume_file = st.file_uploader(
            "Resume (PDF)", type=["pdf"], help="Upload your resume in PDF format"
        )

        ambassadorship = st.checkbox(
            "AI Ambassador", value=editing.get("ambassador", False) if editing else False
        )

        submitted = st.form_submit_button("💾 Save Profile", use_container_width=True)

        if submitted:
            if not name or not email:
                st.error("⚠️ Name and Email are required!")
            else:
                password_hash = editing.get("password_hash") if editing else None
                if (not editing) or password_input.strip():
                    if not password_input.strip():
                        st.error("⚠️ Please enter a password.")
                        submitted = False
                    elif password_input != confirm_password:
                        st.error("⚠️ Passwords do not match.")
                        submitted = False
                    else:
                        password_hash = hash_password(password_input.strip())

                if submitted:
                    profile = {
                        "id": editing.get("id") if editing else generate_id(),
                        "name": name,
                        "email": email,
                        "department": department,
                        "team": team,
                        "role": role,
                        "region": region,
                        "skills": skills,
                        "domain_expertise": domain_expertise,
                        "bio": bio,
                        "linkedin": linkedin,
                        "github": github,
                        "portfolio": portfolio,
                        "ambassador": ambassadorship,
                        "projects_authored": editing.get("projects_authored", [])
                        if editing
                        else [],
                        "created_at": editing.get("created_at", datetime.now().isoformat())
                        if editing
                        else datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat(),
                        "password_hash": password_hash,
                    }

                # Save resume if uploaded
                if submitted and resume_file:
                    resume_dir = META_DIR / "resumes"
                    resume_dir.mkdir(exist_ok=True)
                    resume_path = resume_dir / f"{profile['id']}_resume.pdf"
                    with open(resume_path, "wb") as f:
                        f.write(resume_file.getvalue())
                    profile["resume_path"] = str(resume_path)

                if editing:
                    # Update existing
                    for i, h in enumerate(humans):
                        if h.get("id") == edit_id:
                            humans[i] = profile
                            break
                    st.success("✅ Profile updated!")
                else:
                    # Add new
                    humans.append(profile)
                    st.success("✅ Profile created!")

                save_humans(humans)
                if "edit_profile" in st.session_state:
                    del st.session_state["edit_profile"]
                st.rerun()

# ─────────────────────────────
# TAB 3 — Search & Filter (with product needs)
# ─────────────────────────────
def render_search():
    # Loaded per call: this renders inside Community too, and a module-level
    # read would go stale after the first run of that page.
    humans = load_humans()
    profile_feedback = load_profile_feedback()

    st.subheader("Search & Filter Rackers")

    # Build search options from humans + AI service catalog
    all_skills = set()
    all_departments = set()

    for h in humans:
        for s in h.get("skills", []) or []:
            if s:
                all_skills.add(str(s))
        dept = h.get("department")
        if dept:
            all_departments.add(str(dept))

    # Enrich with AI product catalog: names, product tags, search tags
    ai_product_terms = set()
    for svc in AI_SERVICE_CATALOG:
        name = svc.get("name")
        if name:
            ai_product_terms.add(str(name))
        tag = svc.get("product_tag")
        if tag:
            ai_product_terms.add(str(tag))
        for t in svc.get("search_tags", []) or []:
            if t:
                ai_product_terms.add(str(t))

    search_options = sorted(all_skills | all_departments | ai_product_terms)

    col_filters, col_region, col_amb = st.columns([3, 1, 1])

    with col_filters:
        selected_filters = st.multiselect(
            "Search by skills, AI products, or department:",
            options=search_options,
            default=[],
            placeholder="e.g. billing, contract, openstack, repo-health, training-ai …",
        )

    with col_region:
        filter_region = st.selectbox("Region", ["All", "Americas", "EMEA", "APAC", "Global"])

    with col_amb:
        filter_ambassador = st.checkbox("Only Ambassadors")

    # Optional free-text keyword search
    keyword = st.text_input(
        "Optional keyword search (name, bio, domain expertise…)",
        value="",
        placeholder="Type any word: GenAI, OpenStack, SOC, VR, etc.",
    )

    # Start with all humans
    filtered = humans

    # Apply tag-based filters (skills / products / departments)
    if selected_filters:
        selected_lower = {f.lower() for f in selected_filters}
        new_filtered: List[Dict[str, Any]] = []
        for h in filtered:
            # Build a simple "tag haystack" from profile fields
            skill_text = " ".join(h.get("skills", []))
            haystack_parts = [
                h.get("name", ""),
                h.get("department", ""),
                h.get("team", ""),
                h.get("role", ""),
                h.get("region", ""),
                skill_text,
                h.get("domain_expertise", ""),
                h.get("bio", ""),
            ]
            haystack = " ".join(p for p in haystack_parts if p).lower()
            if any(tag in haystack for tag in selected_lower):
                new_filtered.append(h)
        filtered = new_filtered

    # Apply region filter
    if filter_region != "All":
        filtered = [h for h in filtered if h.get("region") == filter_region]

    # Apply ambassador filter
    if filter_ambassador:
        filtered = [h for h in filtered if h.get("ambassador", False)]

    # Apply keyword search
    if keyword.strip():
        kw = keyword.lower().strip()
        filtered = [
            h
            for h in filtered
            if kw in (h.get("name", "").lower())
            or kw in " ".join(h.get("skills", [])).lower()
            or kw in h.get("domain_expertise", "").lower()
            or kw in h.get("bio", "").lower()
        ]

    st.write(f"**Found {len(filtered)} Racker(s)**")

    # Small helper: show what the AI product catalog looks like for users
    with st.expander("💡 Browse AI product needs you can search for"):
        st.markdown(
            """
            You can search by **product needs** as well as skills, for example:
            - `billing`, `billing-formatter`, `finance-ai`
            - `renewal`, `churn`, `account-health`
            - `ticket`, `support-ai`, `triage`
            - `openstack`, `infra-ai`, `capacity`
            - `soc`, `incident-report`, `security-ai`
            - `contract`, `legal-ai`, `doc-ai`
            - `repo-health`, `engineering-ai`, `devops`
            - `analytics-ai`, `data-copilot`
            - `strategy-ai`, `ai-roi`, `exec-dashboard`
            - `vendor`, `sla`, `procurement-ai`
            - `learning`, `training-ai`
            """
        )

    for human in filtered:
        with st.expander(f"👤 {human.get('name')} — {human.get('role', 'N/A')}"):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Department:** {human.get('department', 'N/A')}")
                st.write(f"**Team:** {human.get('team', 'N/A')}")
                st.write(f"**Region:** {human.get('region', 'N/A')}")
                st.write(f"**Skills:** {', '.join(human.get('skills', []))}")
            with col2:
                if human.get("linkedin"):
                    st.markdown(f"[🔗 LinkedIn]({human.get('linkedin')})")
                if human.get("github"):
                    st.markdown(f"[🔗 GitHub]({human.get('github')})")
                if human.get("portfolio"):
                    st.markdown(f"[🔗 Portfolio]({human.get('portfolio')})")
                if human.get("ambassador"):
                    st.markdown("**🌟 AI Ambassador**")

            if human.get("bio"):
                st.write(f"**Bio:** {human.get('bio')}")

            if st.button("Edit Profile", key=f"t3_edit_{human.get('id')}"):
                st.session_state["edit_profile"] = human.get("id")
                st.rerun()


if not embed_flags.PROFILES_EMBEDDED:
    _t1, _t2, _t3 = st.tabs(
        ['📋 Directory', '➕ Create/Edit Profile', '🔍 Search & Filter'])
    with _t1:
        render_directory()
    with _t2:
        render_profile_form()
    with _t3:
        render_search()
