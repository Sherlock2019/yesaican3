import streamlit as st
from datetime import datetime
from typing import List, Dict

from services.ui.utils.meta_store import load_json, save_json
from services.ui.utils.page_template import page_chrome


st.set_page_config(
    page_title="Login & My Space — YES AI CAN",
    layout="wide"
)


def hash_password(raw: str) -> str:
    import hashlib
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_humans() -> List[Dict]:
    return load_json("humans.json", [])


def save_humans(humans: List[Dict]) -> None:
    save_json("humans.json", humans)


def load_projects() -> List[Dict]:
    return load_json("projects.json", [])


def save_projects(projects: List[Dict]) -> None:
    save_json("projects.json", projects)


def update_human_projects(email: str, project_id: str, action: str) -> None:
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
        save_humans(humans)


page_chrome("login_portal", "My Space", "Your profile, submissions and saved work.")
st.markdown("Manage your profile, projects, and contributions in one place.")
st.markdown("---")

humans = load_humans()
projects = load_projects()
auth_user = st.session_state.get("auth_user")


def authenticate(email: str, password: str) -> Dict | None:
    target = next((h for h in humans if h.get("email") == email.strip()), None)
    if not target:
        return None
    stored_hash = target.get("password_hash")
    if not stored_hash:
        return None
    if stored_hash == hash_password(password.strip()):
        return {
            "id": target.get("id"),
            "name": target.get("name"),
            "email": target.get("email"),
        }
    return None


if auth_user:
    st.success(f"Welcome back, **{auth_user.get('name', auth_user.get('email'))}**!")
    logout_col, edit_col = st.columns([1, 1])
    with logout_col:
        if st.button("🚪 Logout"):
            st.session_state.pop("auth_user", None)
            st.rerun()
    with edit_col:
        if st.button("✏️ Edit Profile"):
            st.session_state['edit_profile'] = auth_user.get("id")
            st.switch_page("pages/human_stack.py")

    st.markdown("---")

    # Profile summary
    profile = next((h for h in humans if h.get("id") == auth_user.get("id")), {})
    with st.expander("👤 Profile Summary", expanded=True):
        st.write(f"**Name:** {profile.get('name', 'N/A')}")
        st.write(f"**Email:** {profile.get('email', 'N/A')}")
        st.write(f"**Role:** {profile.get('role', 'N/A')}")
        st.write(f"**Department:** {profile.get('department', 'N/A')}")
        st.write(f"**Region:** {profile.get('region', 'N/A')}")
        if profile.get("skills"):
            st.write(f"**Skills:** {', '.join(profile.get('skills', []))}")
        if profile.get("ambassador"):
            st.success("🌟 You are an AI Ambassador!")

    st.markdown("---")

    # Personal projects dashboard
    st.subheader("🧱 My Projects")
    user_email = auth_user.get("email")
    my_projects = [
        p for p in projects
        if p.get("owner_email") == user_email or user_email in p.get("author_emails", [])
    ]

    with st.expander("➕ Add New Project", expanded=False):
        with st.form("personal_project_form"):
            title = st.text_input("Project Title *")
            description = st.text_area("Project Description *")
            phase = st.selectbox("Phase", ["Incubation", "MVP", "Ready for Production"])
            tags_input = st.text_input("Tags (comma-separated)")
            repo_link = st.text_input("Repository Link")
            demo_link = st.text_input("Demo Link")
            submitted = st.form_submit_button("Create Project")

            if submitted:
                if not title or not description:
                    st.error("⚠️ Title and Description are required.")
                else:
                    project_id = f"project_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(projects)}"
                    project = {
                        "id": project_id,
                        "title": title,
                        "description": description,
                        "phase": phase,
                        "tags": [t.strip() for t in tags_input.split(",") if t.strip()],
                        "repo_link": repo_link,
                        "demo_link": demo_link,
                        "authors": [auth_user.get("name") or user_email],
                        "author_emails": [user_email],
                        "owner_email": user_email,
                        "owner_name": auth_user.get("name"),
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat(),
                        "comments": [],
                        "suggestions": [],
                        "tested_feedback": [],
                        "stars": 0,
                    }
                    projects.append(project)
                    save_projects(projects)
                    update_human_projects(user_email, project_id, "add")
                    st.success("✅ Project created!")
                    st.rerun()

    if not my_projects:
        st.info("You haven't added any projects yet. Use the form above to get started!")
    else:
        for project in my_projects:
            expander = st.expander(f"🧱 {project.get('title', 'Untitled')} — {project.get('phase', 'N/A')}")
            project_id = project.get("id")
            title_key = f"title_{project_id}"
            desc_key = f"description_{project_id}"
            phase_key = f"phase_{project_id}"
            tags_key = f"tags_{project_id}"
            repo_key = f"repo_{project_id}"
            demo_key = f"demo_{project_id}"

            new_title = expander.text_input("Title", value=project.get("title", ""), key=title_key)
            new_description = expander.text_area("Description", value=project.get("description", ""), key=desc_key)
            new_phase = expander.selectbox(
                "Phase", ["Incubation", "MVP", "Ready for Production"],
                index=["Incubation", "MVP", "Ready for Production"].index(project.get("phase", "Incubation")),
                key=phase_key
            )
            new_tags = expander.text_input("Tags (comma-separated)", value=", ".join(project.get("tags", [])), key=tags_key)
            new_repo = expander.text_input("Repository Link", value=project.get("repo_link", ""), key=repo_key)
            new_demo = expander.text_input("Demo Link", value=project.get("demo_link", ""), key=demo_key)

            col_save, col_delete = expander.columns([3, 1])
            with col_save:
                if st.button("💾 Save Changes", key=f"save_{project_id}"):
                    project["title"] = st.session_state[title_key]
                    project["description"] = st.session_state[desc_key]
                    project["phase"] = st.session_state[phase_key]
                    project["tags"] = [t.strip() for t in st.session_state[tags_key].split(",") if t.strip()]
                    project["repo_link"] = st.session_state[repo_key]
                    project["demo_link"] = st.session_state[demo_key]
                    project["updated_at"] = datetime.now().isoformat()
                    save_projects(projects)
                    st.success("✅ Project updated.")
                    st.rerun()
            with col_delete:
                if st.button("🗑️ Delete", key=f"delete_{project_id}"):
                    projects = [p for p in projects if p.get("id") != project_id]
                    save_projects(projects)
                    update_human_projects(user_email, project_id, "remove")
                    st.warning("Project deleted.")
                    st.rerun()

else:
    st.subheader("Login to continue")
    with st.form("login_form"):
        email = st.text_input("Email *")
        password = st.text_input("Password *", type="password")
        submitted = st.form_submit_button("🔐 Login")

        if submitted:
            if not email or not password:
                st.error("⚠️ Email and password are required.")
            else:
                user = authenticate(email, password)
                if user:
                    st.session_state["auth_user"] = user
                    st.success("✅ Login successful!")
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials. Please check your email/password.")

    st.info("Don't have an account? Create your profile in the 👤 Human Stack Directory first.")
