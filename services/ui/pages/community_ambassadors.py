# Community & Ambassadors — YES AI CAN
# Showcase Ambassador cohorts and community engagement

import streamlit as st
import html
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
from services.ui.utils.page_template import page_chrome

st.set_page_config(
    page_title="Community & Ambassadors — YES AI CAN",
    layout="wide"
)

# Storage goes through meta_store, which resolves the one .sandbox_meta the
# rest of the app writes to. The previous parent.parent.parent.parent hop
# landed on an empty directory at the repo root, so this page always showed
# zero profiles however many were saved.
from services.ui.utils.meta_store import load_json


def load_humans() -> List[Dict]:
    data = load_json("humans.json", [])
    return data if isinstance(data, list) else []


def load_projects() -> List[Dict]:
    data = load_json("projects.json", [])
    return data if isinstance(data, list) else []

# Page header
page_chrome("community_ambassadors", "Community", "Ambassadors, cohorts and contributors.")
st.markdown("**YES AI CAN — Rackers Lab & Community**")
st.markdown("---")

humans = load_humans()
projects = load_projects()

def render_directory(profiles: List[Dict]) -> None:
    """The Human Stack directory — who is in our Community and what they bring.

    A table rather than cards: the question people arrive with is "who knows
    X", and scanning a skills column answers it far faster than reading down a
    grid of profile tiles.
    """
    if not profiles:
        st.info("No profiles yet. Add yours from People & Skills.")
        return

    st.markdown("""
    <style>
    .hs-tbl-wrap { background:var(--pc-surface); border:1px solid var(--pc-rule);
                   border-radius:14px; overflow-x:auto; box-shadow:var(--pc-shadow); }
    .hs-tbl { width:100%; border-collapse:collapse; font-size:.85rem; min-width:940px; }
    .hs-tbl thead th { background:var(--pc-surface-alt); color:var(--pc-ink-faint);
                       font-size:.72rem; font-weight:650; letter-spacing:.03em;
                       text-transform:uppercase; text-align:left; padding:.6rem .75rem;
                       border-bottom:1px solid var(--pc-rule); white-space:nowrap; }
    .hs-tbl td { padding:.65rem .75rem; border-bottom:1px solid var(--pc-rule);
                 color:var(--pc-ink-soft); vertical-align:top; }
    .hs-tbl tr:last-child td { border-bottom:none; }
    .hs-tbl .nm { font-weight:650; color:var(--pc-ink); }
    .hs-chip { display:inline-block; background:var(--pc-indigo-wash);
               color:var(--pc-indigo-dark); border-radius:6px; padding:.1rem .4rem;
               font-size:.72rem; margin:0 .25rem .25rem 0; white-space:nowrap; }
    .hs-chip.built { background:var(--pc-green-wash); color:var(--pc-green); }
    .hs-stars { color:#f59e0b; white-space:nowrap; }
    </style>
    """, unsafe_allow_html=True)

    def chips(values, extra: str = "") -> str:
        items = values if isinstance(values, list) else [values]
        cleaned = [str(v).strip() for v in items if str(v or "").strip()]
        if not cleaned:
            return "<span style='color:var(--pc-ink-faint)'>—</span>"
        return "".join(
            f"<span class='hs-chip {extra}'>{html.escape(v)}</span>" for v in cleaned[:6])

    rows = []
    for person in profiles:
        rating = person.get("rating") or person.get("badge_rating") or 0
        try:
            stars = "★" * int(round(float(rating))) or "—"
        except (TypeError, ValueError):
            stars = "—"
        feedback = str(person.get("feedback") or person.get("badge") or "").strip()
        rows.append(
            "<tr>"
            f"<td class='nm'>{html.escape(str(person.get('name') or '—'))}</td>"
            f"<td>{html.escape(str(person.get('department') or '—'))}</td>"
            f"<td>{html.escape(str(person.get('region') or '—'))}</td>"
            f"<td>{chips(person.get('skills') or person.get('expertise') or [])}</td>"
            f"<td>{chips(person.get('projects_built') or person.get('products_built') or [], 'built')}</td>"
            f"<td><span class='hs-stars'>{stars}</span>"
            f"<div style='font-size:.74rem;color:var(--pc-ink-faint)'>"
            f"{html.escape(feedback[:70]) or 'No feedback yet'}</div></td>"
            "</tr>"
        )

    st.markdown(
        "<div class='hs-tbl-wrap'><table class='hs-tbl'><thead><tr>"
        "<th>Name</th><th>Department</th><th>Region</th><th>Skills / Expertise</th>"
        "<th>Products Built</th><th>Badge of Honor &amp; Feedback</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>",
        unsafe_allow_html=True)


# People & Skills is folded in here rather than living in its own rail entry:
# finding someone and reading about the community are the same errand. Its three
# tabs are imported, not rebuilt — the profile form alone is 140 lines of state
# handling that would drift the moment there were two of it.
from services.ui.utils import embed_flags

embed_flags.PROFILES_EMBEDDED = True
try:
    from services.ui.pages import human_stack as profiles
finally:
    embed_flags.PROFILES_EMBEDDED = False

st.markdown(profiles.STAR_CSS, unsafe_allow_html=True)

tab0, tab_new, tab_find, tab1, tab2, tab3, tab4 = st.tabs([
    "👥 Directory", "➕ Create/Edit Profile", "🔍 Search & Filter",
    "🌟 Ambassadors", "🏆 Leaderboard", "⭐ Top Projects", "📅 Events",
])

with tab0:
    st.subheader(f"Human Stack Directory — {len(humans)} Profiles")
    st.caption("Who is in our Community, what they know, and what they have built.")
    render_directory(humans)
    st.divider()
    st.caption("Full profile cards, with view / edit / delete:")
    profiles.render_directory()

with tab_new:
    profiles.render_profile_form()

with tab_find:
    profiles.render_search()

with tab1:
    st.subheader("AI Ambassador Cohorts")
    
    ambassadors = [h for h in humans if h.get('ambassador', False)]
    
    if not ambassadors:
        st.info("🌟 No ambassadors yet. Apply to become an AI Ambassador!")
    else:
        st.write(f"**Total Ambassadors: {len(ambassadors)}**")
        
        # Group by region
        regions = {}
        for amb in ambassadors:
            region = amb.get('region', 'Unknown')
            if region not in regions:
                regions[region] = []
            regions[region].append(amb)
        
        for region, amb_list in regions.items():
            st.markdown(f"### {region} ({len(amb_list)} Ambassadors)")
            cols = st.columns(3)
            for idx, amb in enumerate(amb_list):
                with cols[idx % 3]:
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
                                border: 2px solid #ff0066; border-radius: 12px; padding: 1rem; margin-bottom: 1rem;
                                box-shadow: 0 4px 12px rgba(255,0,102,0.1);">
                        <h4 style="color: #ff0066; margin-bottom: 0.5rem;">🌟 {amb.get('name', 'Unknown')}</h4>
                        <p style="color: #334155; margin: 0.2rem 0;"><strong>Role:</strong> {amb.get('role', 'N/A')}</p>
                        <p style="color: #334155; margin: 0.2rem 0;"><strong>Skills:</strong> {', '.join(amb.get('skills', [])[:3])}</p>
                    </div>
                    """, unsafe_allow_html=True)
        
        st.markdown("---")
        if st.button("📝 Apply to Ambassador Program", use_container_width=True):
            st.info("📝 Ambassador application form coming soon!")

with tab2:
    st.subheader("Contribution Leaderboard")
    
    # Calculate contributions
    contributions = {}
    for human in humans:
        human_id = human.get('id')
        contributions[human_id] = {
            'name': human.get('name', 'Unknown'),
            'projects': len([p for p in projects if human.get('name') in p.get('authors', [])]),
            'skills': len(human.get('skills', [])),
            'ambassador': human.get('ambassador', False),
            'total_score': 0
        }
        # Score: projects * 10 + skills * 2 + ambassador bonus 50
        contributions[human_id]['total_score'] = (
            contributions[human_id]['projects'] * 10 +
            contributions[human_id]['skills'] * 2 +
            (50 if contributions[human_id]['ambassador'] else 0)
        )
    
    # Sort by score
    sorted_contributors = sorted(contributions.values(), key=lambda x: x['total_score'], reverse=True)
    
    st.write(f"**Top {min(10, len(sorted_contributors))} Contributors**")
    
    for idx, contrib in enumerate(sorted_contributors[:10], 1):
        medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"#{idx}"
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
                    border: 2px solid #00d4ff; border-radius: 12px; padding: 1rem; margin-bottom: 0.5rem;
                    box-shadow: 0 4px 12px rgba(0,212,255,0.1);">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h4 style="color: #00d4ff; margin: 0;">{medal} {contrib['name']}</h4>
                    <p style="color: #334155; margin: 0.3rem 0;">Projects: {contrib['projects']} | Skills: {contrib['skills']}</p>
                </div>
                <div style="font-size: 1.5rem; font-weight: 700; color: #ff0066;">
                    {contrib['total_score']} pts
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

with tab3:
    st.subheader("Top Projects by Stars")

    # Sort projects by stars
    sorted_projects = sorted(projects, key=lambda x: x.get('stars', 0), reverse=True)

    if not sorted_projects:
        st.info("⭐ No projects yet. Submit your first project!")
    else:
        for idx, project in enumerate(sorted_projects[:10], 1):
            medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"#{idx}"
            units = [u for u in project.get('business_units', []) if u]
            # A project spanning units is the interesting case, so say so in the
            # header — that is what someone is scanning this list for.
            span = f" · needs {len(units)} business units" if len(units) > 1 else ""
            title = project.get('title', 'Untitled')
            with st.expander(f"{medal} {title} — ⭐ {project.get('stars', 0)} stars{span}"):
                st.write(f"**Description:** {project.get('description', 'N/A')}")
                st.write(f"**Authors:** {', '.join(project.get('authors', []))}")
                st.write(f"**Phase:** {project.get('phase', 'N/A')}")

                if units:
                    st.write(f"**Business units involved:** {', '.join(units)}")

                expertise = [e for e in project.get('expertise_needed', []) if e]
                if expertise:
                    st.markdown("**Expertise needed**")
                    for item in expertise:
                        st.markdown(f"- {item}")

                closes = [t for t in project.get('closes_titles', []) if t]
                if closes:
                    st.markdown(f"**Painpoints this would close ({len(closes)})**")
                    for item in closes:
                        st.markdown(f"- {item}")

                if project.get('blocked_on'):
                    st.warning(f"**Blocked on:** {project['blocked_on']}")
                if project.get('ask'):
                    st.info(f"**The ask:** {project['ask']}")

                if project.get('tags'):
                    st.caption("Tags: " + ", ".join(project['tags']))

with tab4:
    st.subheader("Upcoming Events & Activities")
    
    st.info("📅 Event calendar coming soon! Check back for AI Ambassador meetups, workshops, and community events.")
    
    # Placeholder for events
    st.markdown("""
    ### 🎯 Upcoming Events
    
    - **AI Ambassador Monthly Meetup** — First Tuesday of each month
    - **YES AI CAN Workshop Series** — Every other Thursday
    - **Customer ZERO → Customer ONE Showcase** — Quarterly
    
    ### 📢 Announcements
    
    - New AI Ambassador cohort applications open!
    - Project Hub now supports collaborative feedback
    - Agent Library updated with latest Customer ZERO agents
    """)
