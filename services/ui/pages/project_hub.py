# Project Hub — What AI Knows / What AI Built
# Database of all AI projects by Rackers

import hashlib
import re
from datetime import datetime
from typing import Any, Dict, List

import streamlit as st

from services.shared.records import carry_opportunity_fields
from services.ui.utils.meta_store import META_DIR, load_json, save_json
from services.ui.utils.page_template import page_chrome

st.set_page_config(
    page_title="Project Hub — YES AI CAN",
    layout="wide"
)

SUBMISSIONS_FILE = "how_ai_help_submissions.json"

SAMPLE_PROJECTS: List[Dict[str, Any]] = [
    {
        "id": "renewable_finance_copilot",
        "title": "Renewable Finance Copilot",
        "summary": "Forecast capital flows & compliance across global farms for rapid financing decisions.",
        "description": "Forecast capital flows & compliance across global farms for rapid financing decisions.",
        "business_area": "Green Energy",
        "phase": "MVP",
        "status": "MVP",
        "authors": ["Avery Chen", "Mia Patel"],
        "owner_name": "Avery Chen",
        "owner_department": "Rackers Lab",
        "owner_region": "GLOBAL",
        "tags": ["Finance", "Renewable", "Copilot"],
        "stars": 24,
        "comments": [],
        "upvotes": 18,
        "created_at": "2024-09-02T00:00:00",
        "updated_at": "2024-10-10T00:00:00",
        "business_value": "Compliance + capital orchestration",
    },
    {
        "id": "cx_sentiment_heatmap",
        "title": "CX Sentiment Heatmap",
        "summary": "Streaming sentiment insights for our Community customer boards.",
        "description": "Streaming sentiment insights for our Community customer boards.",
        "business_area": "Customer Success",
        "phase": "Incubation",
        "status": "Incubation",
        "authors": ["Lila Moreno"],
        "owner_name": "Lila Moreno",
        "owner_department": "Customer Success",
        "owner_region": "AMER",
        "tags": ["Customer Experience", "Analytics"],
        "stars": 15,
        "comments": [],
        "upvotes": 11,
        "created_at": "2024-07-25T00:00:00",
        "updated_at": "2024-08-15T00:00:00",
        "business_value": "Executive-ready heatmaps for CX reviews",
    },
]


def _coerce_project_collection(raw: Any) -> List[Dict[str, Any]]:
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        for key in ("items", "records", "data", "projects"):
            value = raw.get(key)
            if isinstance(value, list):
                return value
        return [raw]
    return []


def load_projects() -> List[Dict]:
    raw = load_json("projects.json", [])
    records = _coerce_project_collection(raw)
    if not records:
        records = [dict(project) for project in SAMPLE_PROJECTS]
    normalized: List[Dict[str, Any]] = []
    for project in records:
        normalized.append(_normalize_project_record(dict(project)))
    return normalized


def save_projects(projects: List[Dict]):
    save_json("projects.json", projects)


def load_humans() -> List[Dict]:
    return load_json("humans.json", [])


def load_help_submissions() -> List[Dict]:
    data = load_json(SUBMISSIONS_FILE, [])
    if isinstance(data, dict):
        for key in ("items", "records", "data"):
            if key in data and isinstance(data[key], list):
                data = data[key]
                break
        else:
            data = [data]
    return data or []


def ensure_submission_id_local(submission: Dict[str, Any]) -> str:
    if submission.get("id"):
        return str(submission["id"])
    submitter = submission.get("submitter", {}) or {}
    raw = (
        f"{submission.get('title', '')}|"
        f"{submitter.get('name', '')}|"
        f"{submitter.get('department', '')}|"
        f"{(submission.get('description') or '')[:80]}"
    )
    digest = hashlib.sha1(raw.encode("utf-8", "ignore")).hexdigest()[:10]
    anchor = f"challenge_{digest}"
    submission["id"] = anchor
    return anchor


def find_submission_record(submission_id: str, fallback_title: str | None = None) -> Dict[str, Any] | None:
    submissions = load_help_submissions()
    target = (submission_id or "").strip()
    fallback = (fallback_title or "").strip().lower()
    for submission in submissions:
        current_id = ensure_submission_id_local(submission)
        if target and current_id == target:
            return submission
        title = submission.get("title", "").strip().lower()
        if fallback and title == fallback:
            return submission
    return None


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def convert_submission_to_project(submission_id: str, fallback: Dict[str, Any]) -> tuple[bool, str, Dict[str, Any] | None]:
    submission = find_submission_record(submission_id, fallback.get("title"))
    if not submission and not fallback.get("title"):
        return False, "Unable to locate the original challenge details.", None
    projects = load_projects()
    for existing in projects:
        if existing.get("source_submission_id") == submission_id and submission_id:
            return False, "Project already exists for this challenge.", existing
    source = submission or {
        "title": fallback.get("title"),
        "description": fallback.get("description"),
        "category": fallback.get("category"),
        "difficulty": fallback.get("difficulty", "Medium"),
        "submitter": {
            "name": fallback.get("submitter"),
            "department": fallback.get("department"),
            "region": fallback.get("region"),
        },
        "upvotes": _to_int(fallback.get("upvotes"), 0),
        "comments": _to_int(fallback.get("comments"), 0),
        "urgency": fallback.get("urgency"),
        "impact_score": fallback.get("impact"),
    }
    submitter = source.get("submitter", {}) or {}
    project_entry: Dict[str, Any] = {
        "title": source.get("title", "New Project"),
        "summary": source.get("description", "")[:280],
        "business_area": source.get("category", "General"),
        "status": "Incubation",
        "phase": "Incubation",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "upvotes": source.get("upvotes", 0),
        "comments": source.get("comments", 0),
        "source_submission_id": submission_id,
        "authors": [submitter.get("name")] if submitter.get("name") else [],
        "owner_name": submitter.get("name"),
        "owner_department": submitter.get("department"),
        "owner_region": submitter.get("region"),
        "difficulty": source.get("difficulty", fallback.get("difficulty", "Medium")),
        "urgent_score": source.get("urgency"),
        "impact_score": source.get("impact_score") or fallback.get("impact"),
    }
    # Carry the whole opportunity block, not just the AI baseline — the intake
    # wizard's pain sizing, scoring and metric plan travel with the project.
    carry_opportunity_fields(source, project_entry)
    ensure_project_id(project_entry)
    projects.insert(0, project_entry)
    save_projects(projects)
    return True, f"Project '{project_entry['title']}' created in Project Hub.", project_entry


def update_human_project_link(email: str, project_id: str, action: str) -> None:
    humans = load_humans()
    updated = False
    for human in humans:
        if human.get("email") == email:
            project_ids = human.get("projects_authored", [])
            if action == "add" and project_id not in project_ids:
                project_ids.append(project_id)
                updated = True
            elif action == "remove" and project_id in project_ids:
                project_ids.remove(project_id)
                updated = True
            human["projects_authored"] = project_ids
            human["updated_at"] = datetime.now().isoformat()
            break
    if updated:
        save_json("humans.json", humans)


def slugify_label(value: str | None) -> str:
    if not value:
        return "project"
    cleaned = re.sub(r"[^0-9a-zA-Z]+", " ", value).strip().lower()
    return "_".join(cleaned.split()) or "project"


def ensure_project_id(project: Dict[str, Any]) -> str:
    if project.get("id"):
        return str(project["id"])
    slug = slugify_label(project.get("title") or project.get("summary"))
    project["id"] = slug or f"project_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    return project["id"]


def get_project_identifier(project: Dict[str, Any]) -> str:
    return str(project.get("id") or ensure_project_id(project))


def find_project_by_identifier(projects: List[Dict[str, Any]], identifier: str | None, fallback_name: str | None = None) -> Dict[str, Any] | None:
    target = (identifier or "").strip()
    fallback = slugify_label(fallback_name) if fallback_name else ""
    for project in projects:
        project_id = ensure_project_id(project)
        if target and project_id == target:
            return project
        title_slug = slugify_label(project.get("title"))
        if target and title_slug == target:
            return project
        if fallback and title_slug == fallback:
            return project
    return None


def _normalize_project_record(project: Dict[str, Any]) -> Dict[str, Any]:
    description = project.get("description")
    summary = project.get("summary")
    if not description and summary:
        project["description"] = summary
    if not summary and description:
        project["summary"] = description
    ensure_project_id(project)
    return project


def get_project_description(project: Dict[str, Any]) -> str:
    return project.get("description") or project.get("summary") or "N/A"


def _get_query_params() -> dict[str, list[str]]:
    raw = st.query_params
    params: dict[str, list[str]] = {}
    try:
        items = raw.items()
    except AttributeError:
        items = raw.to_dict().items()
    for key, value in items:
        if isinstance(value, (list, tuple)):
            params[key] = list(value)
        else:
            params[key] = [value]
    return params


def _set_query_params(params: dict[str, list[str] | str]) -> None:
    st.query_params = params


def _get_last(params: dict[str, list[str]], key: str) -> str | None:
    values = params.get(key, [])
    if not values:
        return None
    return values[-1]


def handle_conversion_from_params() -> bool:
    params = _get_query_params()
    convert_id = _get_last(params, "convert_submission_id") or _get_last(params, "source_submission_id")
    if not convert_id:
        return False
    fallback = {
        "title": _get_last(params, "convert_submission_title") or _get_last(params, "challenge_title"),
        "description": _get_last(params, "convert_submission_description"),
        "category": _get_last(params, "convert_submission_category"),
        "difficulty": _get_last(params, "convert_submission_difficulty"),
        "submitter": _get_last(params, "convert_submission_submitter"),
        "department": _get_last(params, "convert_submission_department"),
        "region": _get_last(params, "convert_submission_region"),
        "upvotes": _get_last(params, "convert_submission_upvotes"),
        "comments": _get_last(params, "convert_submission_comments"),
        "urgency": _get_last(params, "convert_submission_urgency"),
        "impact": _get_last(params, "convert_submission_impact"),
    }
    success, message, project = convert_submission_to_project(convert_id, fallback)
    params.pop("convert_submission_id", None)
    params.pop("source_submission_id", None)
    params.pop("convert_submission_title", None)
    params.pop("convert_submission_description", None)
    params.pop("convert_submission_category", None)
    params.pop("convert_submission_difficulty", None)
    params.pop("convert_submission_submitter", None)
    params.pop("convert_submission_department", None)
    params.pop("convert_submission_region", None)
    params.pop("convert_submission_upvotes", None)
    params.pop("convert_submission_comments", None)
    params.pop("convert_submission_urgency", None)
    params.pop("convert_submission_impact", None)
    params.pop("challenge_title", None)
    if success and project:
        target_id = get_project_identifier(project)
        params["project_id"] = target_id
        params["project_name"] = project.get("title")
        st.success(message)
        st.session_state["view_project"] = target_id
        _set_query_params(params)
        st.rerun()
        return True
    st.warning(message)
    _set_query_params(params)
    return False


def reset_project_selection() -> None:
    st.session_state.pop("view_project", None)
    params = _get_query_params()
    params.pop("project_id", None)
    params.pop("project_name", None)
    _set_query_params(params)
    st.rerun()


def render_project_detail(project: Dict[str, Any]) -> None:
    st.markdown(f"#### 🧩 {project.get('title', 'Untitled')} — {project.get('phase', project.get('status', 'N/A'))}")
    col1, col2 = st.columns([2, 1])
    with col1:
        description = get_project_description(project)
        st.write(f"**Description:** {description}")
        if project.get('what'):
            st.write(f"**What:** {project.get('what')}")
        if project.get('so_what'):
            st.write(f"**So What:** {project.get('so_what')}")
        if project.get('for_who'):
            st.write(f"**For Who:** {project.get('for_who')}")
        if project.get('how'):
            st.write(f"**How:** {project.get('how')}")
        if project.get('tags'):
            st.write(f"**Tags:** {', '.join(project.get('tags', []))}")
    with col2:
        st.write(f"**Phase:** {project.get('phase', project.get('status', 'N/A'))}")
        st.write(f"**Created:** {project.get('created_at', 'N/A')[:10]}")
        st.write(f"**Updated:** {project.get('updated_at', project.get('created_at', 'N/A'))[:10]}")
        owner_label = project.get('owner_name') or project.get('owner_email')
        if owner_label:
            st.write(f"**Owner:** {owner_label}")
        st.write(f"**Stars:** {project.get('stars', 0)}")
        if project.get('repo_link'):
            st.markdown(f"[🔗 Repository]({project.get('repo_link')})")
        if project.get('demo_link'):
            st.markdown(f"[🔗 Demo]({project.get('demo_link')})")
    if project.get("ai_baseline"):
        with st.expander("🤖 AI Baseline Blueprint"):
            st.json(project["ai_baseline"])


def activate_project_view(identifier: str, title: str | None = None) -> None:
    st.session_state["view_project"] = identifier
    params = _get_query_params()
    params["project_id"] = identifier
    if title:
        params["project_name"] = title
    _set_query_params(params)
    st.rerun()

def generate_id() -> str:
    """Generate a unique ID for a project."""
    return f"project_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(load_projects())}"

# Page header
page_chrome("", "Projects", "Prototypes, MVPs and production launches.")
st.markdown("**YES AI CAN — Rackers Lab & Community**")
st.markdown("---")

# Tabs: List View, Submit Project, Detail View
tab1, tab2, tab3 = st.tabs(["📊 All Projects", "➕ Submit Project", "🔍 Search & Filter"])

handle_conversion_from_params()
projects = load_projects()
humans = load_humans()
auth_user = st.session_state.get("auth_user")

projects_changed = False
for project in projects:
    previous = project.get("id")
    ensure_project_id(project)
    if project.get("id") != previous:
        projects_changed = True
if projects_changed:
    save_projects(projects)

query_params = _get_query_params()
project_param = query_params.get("project_id", [None])[-1]
project_name_param = query_params.get("project_name", [None])[-1]
selected_project = None
session_project = st.session_state.get("view_project")
if session_project:
    selected_project = find_project_by_identifier(projects, session_project)
if not selected_project:
    selected_project = find_project_by_identifier(projects, project_param, project_name_param)

if selected_project:
    st.markdown("### 🔍 Project Spotlight")
    back_cols = st.columns([1, 4])
    if back_cols[0].button("← Back to Project Hub", key="back_project_selection"):
        reset_project_selection()
    render_project_detail(selected_project)
    st.divider()

with tab1:
    st.subheader("All AI Projects")
    st.caption("Tip: manage your own submissions from the 🔐 Login / My Space dashboard.")
    
    if not projects:
        st.info("🚀 No projects yet. Be the first to submit your AI project!")
    else:
        # Filter by phase
        phase_filter = st.selectbox("Filter by Phase", ["All", "Incubation", "MVP", "Ready for Production"])
        filtered = projects
        if phase_filter != "All":
            filtered = [p for p in projects if p.get('phase') == phase_filter]
        
        # Display as cards
        for project in filtered:
            identifier = get_project_identifier(project)
            with st.expander(f"🧱 {project.get('title', 'Untitled')} — {project.get('phase', project.get('status', 'N/A'))}"):
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.write(f"**Description:** {get_project_description(project)}")
                    st.write(f"**Authors:** {', '.join(project.get('authors', []))}")
                    st.write(f"**Tags:** {', '.join(project.get('tags', []))}")
                    if project.get('repo_link'):
                        st.markdown(f"[🔗 Repository]({project.get('repo_link')})")
                    if project.get('demo_link'):
                        st.markdown(f"[🔗 Demo]({project.get('demo_link')})")
                with col2:
                    st.write(f"**Phase:** {project.get('phase', project.get('status', 'N/A'))}")
                    st.write(f"**Created:** {project.get('created_at', 'N/A')[:10]}")
                    owner_label = project.get('owner_name') or project.get('owner_email')
                    if owner_label:
                        st.write(f"**Owner:** {owner_label}")
                    stars = project.get('stars', 0)
                    st.write(f"⭐ {stars} stars")
                    
                    if st.button("View Details", key=f"view_{identifier}"):
                        activate_project_view(identifier, project.get('title'))

with tab2:
    st.subheader("Submit a New Project")
    
    if not auth_user:
        st.info("🔐 Please log in via **Login / My Space** to submit and manage projects.")
    else:
        owner_name = auth_user.get("name") or auth_user.get("email")
        st.success(f"Submitting as **{owner_name}** ({auth_user.get('email')})")
        with st.form("project_form"):
            title = st.text_input("Project Title *")
            description = st.text_area("Project Description *")
            
            # What / So What / For Who / How / Where / What Now / What Next
            st.markdown("### Project Details")
            what = st.text_area("What (What is this project?)")
            so_what = st.text_area("So What (Why does it matter?)")
            for_who = st.text_area("For Who (Who is this for?)")
            how = st.text_area("How (How does it work?)")
            where = st.text_area("Where (Where is it deployed/used?)")
            what_now = st.text_area("What Now (Current status)")
            what_next = st.text_area("What Next (Future plans)")
            
            extra_authors = st.text_input("Additional Contributors (comma-separated)")
            extra_author_list = [a.strip() for a in extra_authors.split(',') if a.strip()]
            all_authors = [owner_name] + extra_author_list
            
            phase = st.selectbox("Project Phase *", 
                               ["Incubation", "MVP", "Ready for Production"])
            
            tags_input = st.text_input("Tags (comma-separated) - Industry, use case, tech stack")
            tags = [t.strip() for t in tags_input.split(',') if t.strip()]
            
            repo_link = st.text_input("Repository Link (GitHub, GitLab, etc.)")
            demo_link = st.text_input("Demo Link")
            
            artifacts = st.file_uploader("Artifacts (screenshots, PDFs, datasets)", 
                                         type=['png', 'jpg', 'jpeg', 'pdf', 'csv', 'json'],
                                         accept_multiple_files=True)
            
            submitted = st.form_submit_button("🚀 Submit Project", use_container_width=True)
            
            if submitted:
                if not title or not description:
                    st.error("⚠️ Title and Description are required!")
                else:
                    project = {
                        "id": generate_id(),
                        "title": title,
                        "description": description,
                        "what": what,
                        "so_what": so_what,
                        "for_who": for_who,
                        "how": how,
                        "where": where,
                        "what_now": what_now,
                        "what_next": what_next,
                        "authors": all_authors,
                        "author_emails": [auth_user.get("email")],
                        "owner_email": auth_user.get("email"),
                        "owner_name": owner_name,
                        "phase": phase,
                        "tags": tags,
                        "repo_link": repo_link,
                        "demo_link": demo_link,
                        "stars": 0,
                        "comments": [],
                        "suggestions": [],
                        "tested_feedback": [],
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat()
                    }
                    
                    # Save artifacts
                    if artifacts:
                        artifacts_dir = META_DIR / "project_artifacts" / project['id']
                        artifacts_dir.mkdir(parents=True, exist_ok=True)
                        artifact_paths = []
                        for artifact in artifacts:
                            artifact_path = artifacts_dir / artifact.name
                            with open(artifact_path, "wb") as f:
                                f.write(artifact.getvalue())
                            artifact_paths.append(str(artifact_path))
                        project['artifacts'] = artifact_paths
                    
                    projects.append(project)
                    save_projects(projects)
                    update_human_project_link(auth_user.get("email"), project["id"], "add")
                    st.success("✅ Project submitted!")
                    st.rerun()

with tab3:
    st.subheader("Search & Filter Projects")
    
    search_term = st.text_input("🔍 Search by title, description, or tags")
    filter_phase = st.selectbox("Filter by Phase", ["All", "Incubation", "MVP", "Ready for Production"])
    filter_tags = st.text_input("Filter by Tags (comma-separated)")
    
    filtered = projects
    if search_term:
        search_lower = search_term.lower()
        filtered = [p for p in filtered if 
                   search_lower in p.get('title', '').lower() or
                   search_lower in p.get('description', '').lower() or
                   search_lower in ' '.join(p.get('tags', [])).lower()]
    
    if filter_phase != "All":
        filtered = [p for p in filtered if p.get('phase') == filter_phase]
    
    if filter_tags:
        filter_tag_list = [t.strip().lower() for t in filter_tags.split(',')]
        filtered = [p for p in filtered if 
                   any(tag.lower() in [t.lower() for t in p.get('tags', [])] 
                       for tag in filter_tag_list)]
    
    st.write(f"**Found {len(filtered)} project(s)**")
    
    # Sort by stars (most popular first)
    filtered.sort(key=lambda x: x.get('stars', 0), reverse=True)
    
    for project in filtered:
        identifier = get_project_identifier(project)
        with st.expander(f"⭐ {project.get('stars', 0)} | 🧱 {project.get('title', 'Untitled')} — {project.get('phase', project.get('status', 'N/A'))}"):
            col1, col2 = st.columns([2, 1])
            with col1:
                st.write(f"**Description:** {get_project_description(project)}")
                if project.get('what'):
                    st.write(f"**What:** {project.get('what')}")
                if project.get('so_what'):
                    st.write(f"**So What:** {project.get('so_what')}")
                if project.get('for_who'):
                    st.write(f"**For Who:** {project.get('for_who')}")
                st.write(f"**Authors:** {', '.join(project.get('authors', []))}")
                st.write(f"**Tags:** {', '.join(project.get('tags', []))}")
            with col2:
                if project.get('repo_link'):
                    st.markdown(f"[🔗 Repository]({project.get('repo_link')})")
                if project.get('demo_link'):
                    st.markdown(f"[🔗 Demo]({project.get('demo_link')})")
                st.write(f"**Phase:** {project.get('phase', project.get('status', 'N/A'))}")
                st.write(f"**Created:** {project.get('created_at', 'N/A')[:10]}")
            
            # Social features
            col1, col2, col3 = st.columns(3)
            with col1:
                    if st.button(f"⭐ Star ({project.get('stars', 0)})", key=f"star_{identifier}"):
                        for i, p in enumerate(projects):
                            if p.get('id') == project.get('id'):
                                projects[i]['stars'] = projects[i].get('stars', 0) + 1
                                save_projects(projects)
                                st.rerun()
            with col2:
                if st.button("💬 Comment", key=f"comment_{identifier}"):
                    st.session_state['comment_project'] = identifier
            with col3:
                if st.button("💡 Suggest", key=f"suggest_{identifier}"):
                    st.session_state['suggest_project'] = identifier
            
            # Show comments if any
            if project.get('comments'):
                st.markdown("**Comments:**")
                for comment in project.get('comments', [])[-5:]:  # Show last 5
                    st.write(f"- {comment}")
