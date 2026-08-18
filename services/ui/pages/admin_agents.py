#!/usr/bin/env python3
"""🔧 Admin Page for Managing Landing Page Agents"""
from __future__ import annotations

import json
import os
import traceback
from pathlib import Path
from typing import List, Dict, Any

import streamlit as st
from services.ui.utils.page_template import page_chrome

# Import error logger
try:
    import sys
    from pathlib import Path
    error_logger_path = Path(__file__).parent / "error_logger.py"
    if error_logger_path.exists():
        import importlib.util
        spec = importlib.util.spec_from_file_location("error_logger", error_logger_path)
        error_logger = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(error_logger)
        log_error = error_logger.log_error
        log_form_data = error_logger.log_form_data
        get_recent_errors = error_logger.get_recent_errors
        clear_error_log = error_logger.clear_error_log
    else:
        raise ImportError("error_logger.py not found")
except Exception as e:
    # Fallback if import fails
    print(f"Warning: Error logger not available: {e}")
    def log_error(*args, **kwargs):
        print(f"Error (logger not available): {args}, {kwargs}")
    def log_form_data(*args, **kwargs):
        pass
    def get_recent_errors(*args, **kwargs):
        return []
    def clear_error_log():
        return True

# Set page config
st.set_page_config(
    page_title="🔧 Agent Manager Admin",
    page_icon="🔧",
    layout="wide",
)

# Add custom styling - matching app.py theme
st.markdown(
    """
    <style>
    html, body, .block-container { 
        background-color:#0f172a !important; 
        color:#e2e8f0 !important; 
    }
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
    }
    h1 {
        color: #60a5fa;
        text-align: center;
        margin-bottom: 1.5rem;
        font-size: 2.5rem !important;
        font-weight: 800 !important;
    }
    h2, h3 {
        color: #7dd3fc !important;
        font-weight: 700 !important;
    }
    .stButton > button {
        background: linear-gradient(180deg, #4ea3ff 0%, #2f86ff 60%, #0f6fff 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 14px !important;
        padding: 14px 28px !important;
        font-size: 18px !important;
        font-weight: 700 !important;
        box-shadow: 0 8px 24px rgba(15,111,255,0.35) !important;
        cursor: pointer;
    }
    .stButton > button:hover {
        filter: brightness(1.06);
        transform: translateY(-1px);
        box-shadow: 0 10px 28px rgba(15,111,255,0.45) !important;
    }
    .stButton > button:active {
        transform: translateY(0);
        box-shadow: 0 4px 12px rgba(15,111,255,0.35) !important;
    }
    
    /* Agent card styling - bigger and more prominent */
    .agent-card-container {
        background: linear-gradient(180deg, rgba(15,25,35,0.95), rgba(30,41,59,0.95));
        border: 2px solid rgba(0,200,255,0.4);
        border-radius: 16px;
        padding: 2rem 2.5rem;
        margin: 1.5rem 0;
        box-shadow: 0 8px 32px rgba(0,200,255,0.2);
        transition: all 0.3s ease-in-out;
    }
    .agent-card-container:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 40px rgba(0,240,255,0.35);
        border-color: rgba(0,240,255,0.6);
    }
    
    /* Larger agent name */
    .agent-name {
        font-size: 1.8rem !important;
        font-weight: 800 !important;
        color: #e2e8f0 !important;
        margin-bottom: 0.5rem !important;
    }
    
    /* Larger sector/industry */
    .agent-meta {
        font-size: 1.2rem !important;
        color: #94a3b8 !important;
        margin-bottom: 1rem !important;
    }
    
    /* Larger description */
    .agent-description {
        font-size: 1.15rem !important;
        color: #cbd5e1 !important;
        line-height: 1.7 !important;
        margin: 1rem 0 !important;
    }
    
    /* Status badges - bigger */
    .status-badge {
        font-size: 1.1rem !important;
        font-weight: 700 !important;
        padding: 0.5rem 1rem !important;
        border-radius: 8px !important;
    }
    
    /* Input fields styling */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div {
        background-color: rgba(15,23,42,0.8) !important;
        color: #e2e8f0 !important;
        border: 1px solid rgba(0,200,255,0.3) !important;
        border-radius: 8px !important;
        font-size: 1.1rem !important;
        padding: 0.75rem !important;
    }
    
    /* Tabs styling - matching app.py */
    [data-testid="stTabs"] [data-baseweb="tab"] {
        font-size: 24px !important;
        font-weight: 700 !important;
        padding: 16px 32px !important;
        border-radius: 12px !important;
        background-color: #1e293b !important;
        color: #f8fafc !important;
    }
    [data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] {
        background: linear-gradient(90deg, #2563eb, #1d4ed8) !important;
        color: white !important;
        border-bottom: 4px solid #60a5fa !important;
        box-shadow: 0 4px 14px rgba(37,99,235,0.5);
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e293b, #0f172a) !important;
    }
    
    /* Caption styling */
    .stCaption {
        font-size: 1.1rem !important;
        color: #94a3b8 !important;
    }
    
    /* Markdown text */
    .stMarkdown {
        font-size: 1.1rem !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Path to agents data file
AGENTS_DATA_FILE = Path(__file__).parent.parent / "data" / "agents.json"
LAYOUTS_DIR = Path(__file__).parent.parent / "data" / "layouts"
LAYOUTS_DIR.mkdir(parents=True, exist_ok=True)

# Status options
STATUS_OPTIONS = ["Available", "NEW", "Coming Soon", "WIP", "Being Built"]
ACTION_OPTIONS = ["Auto", "Launch", "Preview", "Coming Soon", "Disabled"]

def load_agents() -> List[Dict[str, Any]]:
    """Load agents from JSON file."""
    if AGENTS_DATA_FILE.exists():
        try:
            with open(AGENTS_DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Error loading agents: {e}")
            return []
    return []

def save_agents(agents: List[Dict[str, Any]], save_to_history: bool = True) -> bool:
    """Save agents to JSON file."""
    try:
        AGENTS_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(AGENTS_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(agents, f, indent=4, ensure_ascii=False)
        
        # Save to history for undo (only if not already in history from undo operation)
        if save_to_history:
            save_to_undo_history(agents)
        
        return True
    except Exception as e:
        st.error(f"Error saving agents: {e}")
        return False

def save_to_undo_history(agents: List[Dict[str, Any]]):
    """Save current state to undo history (max 3 steps)."""
    # Initialize if not exists
    if "agent_history" not in st.session_state:
        st.session_state.agent_history = []
    if "history_index" not in st.session_state:
        st.session_state.history_index = -1
    
    # Deep copy the agents list
    agents_copy = json.loads(json.dumps(agents))
    
    # If we're in the middle of history (not at the end), truncate future history
    if st.session_state.history_index < len(st.session_state.agent_history) - 1:
        st.session_state.agent_history = st.session_state.agent_history[:st.session_state.history_index + 1]
    
    # Add new state
    st.session_state.agent_history.append(agents_copy)
    
    # Keep only last 3 states
    if len(st.session_state.agent_history) > 3:
        st.session_state.agent_history.pop(0)
        # Keep history_index at the end
        st.session_state.history_index = len(st.session_state.agent_history) - 1
    else:
        st.session_state.history_index = len(st.session_state.agent_history) - 1

def undo_agents() -> bool:
    """Undo to previous state. Returns True if undo was successful."""
    # Initialize if not exists
    if "agent_history" not in st.session_state:
        return False
    if "history_index" not in st.session_state:
        return False
    
    if st.session_state.history_index > 0:
        st.session_state.history_index -= 1
        previous_state = st.session_state.agent_history[st.session_state.history_index]
        # Deep copy to avoid reference issues
        st.session_state.agents = json.loads(json.dumps(previous_state))
        # Save without adding to history (to avoid infinite loop)
        try:
            AGENTS_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(AGENTS_DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(st.session_state.agents, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            st.error(f"Error saving undo: {e}")
            return False
    return False

def can_undo() -> bool:
    """Check if undo is possible."""
    if "agent_history" not in st.session_state or "history_index" not in st.session_state:
        return False
    return st.session_state.history_index > 0 and len(st.session_state.agent_history) > 1

def save_layout(layout_name: str, agents: List[Dict[str, Any]]) -> bool:
    """Save a library layout with a given name."""
    try:
        layout_file = LAYOUTS_DIR / f"{layout_name}.json"
        with open(layout_file, "w", encoding="utf-8") as f:
            json.dump(agents, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"Error saving layout: {e}")
        return False

def load_layout(layout_name: str) -> List[Dict[str, Any]]:
    """Load a library layout by name."""
    try:
        layout_file = LAYOUTS_DIR / f"{layout_name}.json"
        if layout_file.exists():
            with open(layout_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return []
    except Exception as e:
        st.error(f"Error loading layout: {e}")
        return []

def list_saved_layouts() -> List[str]:
    """List all saved layout names."""
    try:
        layouts = []
        for layout_file in LAYOUTS_DIR.glob("*.json"):
            layouts.append(layout_file.stem)
        return sorted(layouts)
    except Exception:
        return []

def get_unique_values_from_agents(agents: List[Dict[str, Any]], field: str) -> List[str]:
    """Get unique values from agents for a given field."""
    values = set()
    for agent in agents:
        value = agent.get(field, "").strip()
        if value:
            values.add(value)
    return sorted(list(values))

def get_all_emojis_from_agents(agents: List[Dict[str, Any]]) -> List[str]:
    """Get all unique emojis from agents."""
    emojis = set()
    for agent in agents:
        emoji = agent.get("emoji", "").strip()
        if emoji:
            emojis.add(emoji)
    # Add some common emojis if not present
    common_emojis = ["🤖", "💳", "🏦", "🛡️", "⚖️", "🧩", "💬", "🧠", "🩺", "⚡", "☀️", "🚗", "🔋", "🛻", "🔐", "🏛️", "📈", "🎬", "🎰"]
    for emoji in common_emojis:
        emojis.add(emoji)
    return sorted(list(emojis))

def setup_copied_agent_backend(original_route_name: str, copied_route_name: str, agent_name: str) -> Dict[str, Any]:
    """
    Automatically update all necessary files for a copied agent to have independent backend.
    
    Returns:
        Dict with 'success' (bool) and 'messages' (list of strings) describing what was updated.
    """
    import re
    import shutil
    
    results = {
        "success": True,
        "messages": [],
        "errors": []
    }
    
    base_dir = Path(__file__).parent.parent
    pages_dir = base_dir / "pages"
    app_py = base_dir / "app.py"
    agents_py = base_dir.parent / "api" / "routers" / "agents.py"
    
    # 1. Create backend page file
    original_page = pages_dir / f"{original_route_name}.py"
    copied_page = pages_dir / f"{copied_route_name}.py"
    
    if original_page.exists() and not copied_page.exists():
        try:
            shutil.copy2(original_page, copied_page)
            # Update page title and route references in copied file
            with open(copied_page, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Replace page title references
            content = content.replace(f'page_title="{original_route_name}"', f'page_title="{agent_name}"', 1)
            content = content.replace(f'page_title="', f'page_title="{agent_name} (Copy) — ', 1)
            
            # Replace any route references in comments
            content = re.sub(
                rf'({re.escape(original_route_name)})',
                copied_route_name,
                content,
                count=1  # Only replace first occurrence in comments
            )
            
            with open(copied_page, "w", encoding="utf-8") as f:
                f.write(content)
            
            results["messages"].append(f"✅ Created backend page: pages/{copied_route_name}.py")
        except Exception as e:
            results["errors"].append(f"❌ Failed to create backend page: {e}")
            results["success"] = False
    elif copied_page.exists():
        results["messages"].append(f"ℹ️ Backend page already exists: pages/{copied_route_name}.py")
    elif not original_page.exists():
        results["messages"].append(f"⚠️ Original page not found: pages/{original_route_name}.py (skipping page creation)")
    
    # 2. Update app.py - launch_path_overrides
    if app_py.exists():
        try:
            with open(app_py, "r", encoding="utf-8") as f:
                app_content = f.read()
            
            # Check if already added
            if f'"{copied_route_name}":' not in app_content:
                # Add to launch_path_overrides
                pattern = rf'("{re.escape(original_route_name)}":\s*"/{re.escape(original_route_name)}",?\s*\n)'
                replacement = f'\\1            "{copied_route_name}": "/{copied_route_name}",\n'
                app_content = re.sub(pattern, replacement, app_content)
                results["messages"].append("✅ Updated app.py: launch_path_overrides")
            else:
                results["messages"].append("ℹ️ app.py: launch_path_overrides already has entry")
            
            # Add to special cases list
            special_cases_pattern = r'(if route_name in \{"lottery_wizard", "ceo_driver_dashboard", "ceo_driver_seat",\s*\n\s*"real_estate_evaluator", "agent_builder", "hf_inspector"\}:)'
            # Check if copied_route_name is already in the special cases
            special_cases_section = ""
            if "if route_name in" in app_content:
                parts = app_content.split("if route_name in")
                if len(parts) > 1:
                    special_cases_section = parts[1].split("}:")[0] if "}:" in parts[1] else ""
            
            if f'"{copied_route_name}"' not in special_cases_section:
                replacement = r'\1\n                  "' + copied_route_name + r'",'
                app_content = re.sub(special_cases_pattern, replacement, app_content)
                results["messages"].append("✅ Updated app.py: special cases list")
            else:
                results["messages"].append("ℹ️ app.py: special cases already includes entry")
            
            # Add to query parameter routing (if original exists there)
            if f'elif agent in {{"ceo", "ceo_driver"' in app_content and original_route_name == "ceo_driver_dashboard":
                # Add alias for copied agent
                pattern = r'(elif agent in \{"ceo", "ceo_driver", "driver_dashboard", "ceo_dashboard"\}:)'
                if f'"{copied_route_name}"' not in app_content:
                    # Add new elif block for copied agent
                    new_block = f'''    elif agent in {{"{copied_route_name}", "{copied_route_name.replace("_", "_")}_copy"}}:
        _clear_qp()
        try:
            st.switch_page("pages/{copied_route_name}.py")
        except Exception as e:
            st.warning(f"Could not open {agent_name}: {{e}}")
            st.session_state.stage = "{copied_route_name}"
            st.rerun()
'''
                    # Insert after original block
                    pattern_insert = r'(elif agent in \{"ceo", "ceo_driver", "driver_dashboard", "ceo_dashboard"\}:.*?st\.rerun\(\)\n)'
                    app_content = re.sub(pattern_insert, r'\1' + new_block, app_content, flags=re.DOTALL)
                    results["messages"].append("✅ Updated app.py: query parameter routing")
            
            # Add to stage-based routing
            if f'if  st.session_state.stage == "{copied_route_name}":' not in app_content:
                # Find the original stage block and add copy after it
                pattern = rf'(if\s+st\.session_state\.stage == "{re.escape(original_route_name)}":.*?st\.info\([^)]+\)\n)'
                new_block = f'''if  st.session_state.stage == "{copied_route_name}":
    try:
        st.switch_page("pages/{copied_route_name}.py")
    except Exception as e:
        st.error(f"Could not switch to {agent_name}: {{e}}")
        st.info("Ensure file exists at services/ui/pages/{copied_route_name}.py")
'''
                app_content = re.sub(pattern, r'\1\n' + new_block, app_content, flags=re.DOTALL)
                results["messages"].append("✅ Updated app.py: stage-based routing")
            
            # Write updated content
            with open(app_py, "w", encoding="utf-8") as f:
                f.write(app_content)
                
        except Exception as e:
            results["errors"].append(f"❌ Failed to update app.py: {e}")
            results["success"] = False
    
    # 3. Update agents.py API registry (if file exists and original is registered)
    if agents_py.exists():
        try:
            with open(agents_py, "r", encoding="utf-8") as f:
                agents_content = f.read()
            
            # Check if original is in AGENT_REGISTRY
            if f'"{original_route_name}"' in agents_content and f'"{copied_route_name}"' not in agents_content:
                # Find the original registry entry and create a copy
                pattern = rf'("{re.escape(original_route_name)}":\s*{{[^}}]+}})'
                match = re.search(pattern, agents_content)
                if match:
                    original_entry = match.group(1)
                    # Create copied entry
                    copied_entry = original_entry.replace(f'"{original_route_name}"', f'"{copied_route_name}"')
                    copied_entry = copied_entry.replace(f'"{agent_name}"', f'"{agent_name} (Copy)"')
                    # Add import if needed
                    if f'run_{copied_route_name}' not in agents_content:
                        # Try to add import (this is complex, so we'll just note it)
                        results["messages"].append("⚠️ agents.py: Manual import may be needed for API registry")
                    
                    # Add entry after original
                    agents_content = agents_content.replace(original_entry, original_entry + ",\n    " + copied_entry)
                    results["messages"].append("✅ Updated agents.py: AGENT_REGISTRY")
                else:
                    results["messages"].append("ℹ️ agents.py: Original not in AGENT_REGISTRY (skipping)")
            elif f'"{copied_route_name}"' in agents_content:
                results["messages"].append("ℹ️ agents.py: Already registered in AGENT_REGISTRY")
            
            # Write updated content
            with open(agents_py, "w", encoding="utf-8") as f:
                f.write(agents_content)
                
        except Exception as e:
            results["errors"].append(f"⚠️ Failed to update agents.py: {e} (non-critical)")
            # Don't mark as failure since API registry is optional
    
    return results

def render_preview(agents: List[Dict[str, Any]]):
    """Render a preview of how agents will appear on the landing page."""
    if not agents:
        st.info("No agents to preview. Add some agents first.")
        return
    
    st.markdown("### 📱 Landing Page Preview")
    st.caption("This is how your agents will appear on the landing page")
    st.markdown("---")
    
    # Add preview styling
    st.markdown("""
    <style>
    .preview-card {
        background: linear-gradient(180deg, rgba(15,25,35,0.95), rgba(30,41,59,0.95));
        border: 2px solid rgba(0,200,255,0.4);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        transition: all 0.3s ease;
    }
    .preview-card:hover {
        border-color: rgba(0,240,255,0.6);
        box-shadow: 0 8px 24px rgba(0,200,255,0.3);
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Group by sector
    agents_by_sector = {}
    for agent in agents:
        sector = agent.get('sector', 'Other')
        if sector not in agents_by_sector:
            agents_by_sector[sector] = []
        agents_by_sector[sector].append(agent)
    
    # Render preview cards similar to landing page style
    for sector, sector_agents in agents_by_sector.items():
        st.markdown(f"#### {sector}")
        for idx, agent in enumerate(sector_agents):
            st.markdown('<div class="preview-card">', unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 3, 1])
            with col1:
                emoji = agent.get('emoji', '🤖')
                name = agent.get('agent', 'N/A')
                st.markdown(f"**<span style='font-size: 1.3rem;'>{emoji} {name}</span>**", unsafe_allow_html=True)
                industry = agent.get('industry', '')
                st.caption(f"→ {industry}")
            
            with col2:
                desc = agent.get('description', 'N/A')
                st.markdown(f"📝 <span style='color: #cbd5e1;'>{desc}</span>", unsafe_allow_html=True)
            
            with col3:
                status = agent.get('status', 'N/A')
                status_colors = {
                    "Available": ("🟢", "#22c55e"),
                    "NEW": ("🔵", "#3b82f6"),
                    "Coming Soon": ("🟡", "#f59e0b"),
                    "WIP": ("🟣", "#f472b6"),
                    "Being Built": ("🟠", "#f97316")
                }
                status_emoji, status_color = status_colors.get(status, ("⚪", "#94a3b8"))
                st.markdown(f"<span style='color: {status_color}; font-weight: 700;'>{status_emoji} {status}</span>", unsafe_allow_html=True)
                if agent.get('requires_login', False):
                    st.caption("🔐 Login Required")
                else:
                    st.caption("🔓 No Login")
            
            st.markdown('</div>', unsafe_allow_html=True)

def main():
    page_chrome("admin_agents", "Settings", "Agent configuration and platform administration.")
    st.markdown("**Manage agents displayed on the landing page**")
    st.markdown("Add, edit, or delete agents. Changes are saved to `services/ui/data/agents.json`")
    st.markdown("---")
    
    # Load agents
    agents = load_agents()
    
    # Initialize session state
    if "agents" not in st.session_state:
        st.session_state.agents = agents
    # Initialize history with current state if empty
    if "agent_history" not in st.session_state or not st.session_state.agent_history:
        save_to_undo_history(st.session_state.agents)
    if "editing_index" not in st.session_state:
        st.session_state.editing_index = None
    if "show_add_form" not in st.session_state:
        st.session_state.show_add_form = False
    if "active_tab" not in st.session_state:
        st.session_state.active_tab = "📋 Agent List"
    if "expanded_edit" not in st.session_state:
        st.session_state.expanded_edit = None  # Track which agent's edit form is expanded
    if "agent_history" not in st.session_state:
        st.session_state.agent_history = []  # Store last 3 states for undo
    if "history_index" not in st.session_state:
        st.session_state.history_index = -1  # Current position in history
    
    # Sidebar for actions
    with st.sidebar:
        st.header("Actions")
        if st.button("➕ Add New Agent", use_container_width=True):
            st.session_state.editing_index = None
            st.session_state.show_add_form = True
            st.session_state.active_tab = "agents list"
            st.rerun()
        
        st.markdown("---")
        st.markdown("### Info")
        st.info(f"Total Agents: {len(st.session_state.agents)}")
        st.caption("💡 Use ⬆️⬇️ buttons to reorder agents on the landing page")
        
        st.markdown("---")
        
        # Undo button
        history_count = len(st.session_state.get("agent_history", []))
        undo_steps_available = st.session_state.get("history_index", -1) if can_undo() else 0
        undo_disabled = not can_undo()
        if undo_steps_available > 0:
            undo_label = f"↶ Undo ({undo_steps_available} step{'s' if undo_steps_available > 1 else ''} available)"
        else:
            undo_label = "↶ Undo (No history)"
        
        if st.button(undo_label, use_container_width=True, disabled=undo_disabled):
            if undo_agents():
                st.success(f"✅ Undone! Restored to previous state.")
                st.session_state.expanded_edit = None
                st.session_state.editing_index = None
                st.rerun()
            else:
                st.error("❌ Nothing to undo!")
        
        st.caption(f"📚 History: {history_count}/{3} states saved")
        
        if st.button("👁️ Preview Landing Page", use_container_width=True):
            st.session_state.active_tab = "Preview new landing page"
            st.rerun()
        
        if st.button("🔄 Reload from File", use_container_width=True):
            st.session_state.agents = load_agents()
            st.session_state.editing_index = None
            # Reset history when reloading
            st.session_state.agent_history = []
            st.session_state.history_index = -1
            save_to_undo_history(st.session_state.agents)
            st.rerun()
        
        st.markdown("---")
        st.markdown("### 🐛 Error Logger")
        if st.button("📋 View Recent Errors", use_container_width=True):
            st.session_state.show_error_log = True
        
        if st.button("🗑️ Clear Error Log", use_container_width=True):
            clear_error_log()
            st.success("✅ Error log cleared!")
            st.rerun()
    
    # Show error log if requested
    if st.session_state.get("show_error_log", False):
        st.header("🐛 Error Log")
        errors = get_recent_errors(limit=20)
        if errors:
            for i, entry in enumerate(reversed(errors[-20:])):  # Show most recent first
                entry_type = entry.get("type", "error")
                title = f"❌ {entry.get('error_type', 'Error')} - {entry.get('timestamp', 'Unknown time')}" if entry_type != "form_data" \
                    else f"📝 Form Data - {entry.get('timestamp', 'Unknown time')}"
                with st.expander(title, expanded=(i == 0)):
                    if entry_type == "form_data":
                        st.info("Form submission snapshot")
                        st.json(entry.get("data", {}))
                    else:
                        st.error(f"**Error:** {entry.get('error_message', 'Unknown error')}")
                        if entry.get('user_message'):
                            st.info(f"**User Message:** {entry.get('user_message')}")
                        if entry.get('context'):
                            st.json(entry.get('context'))
                        if entry.get('traceback'):
                            st.code(entry.get('traceback'), language='python')
        else:
            st.success("✅ No errors logged!")
        
        if st.button("❌ Close Error Log"):
            st.session_state.show_error_log = False
            st.rerun()
        st.markdown("---")
    
    # Main content area - use session state to control active tab
    tab_names = [
        "agents list", 
        "Preview new landing page", 
        "save new landing page", 
        "apply new landing page", 
        "load existing landing page"
    ]
    # If editing, default to tab2
    default_tab = 1 if st.session_state.editing_index is not None else 0
    tab1, tab2, tab3, tab4, tab5 = st.tabs(tab_names)
    
    with tab1:
        st.header("📋 Agents List")
        
        # Add New Agent expander
        if st.session_state.show_add_form:
            with st.expander("➕ Add New Agent", expanded=True):
                # Get prefilled options from existing agents
                existing_sectors = get_unique_values_from_agents(st.session_state.agents, "sector")
                existing_industries = get_unique_values_from_agents(st.session_state.agents, "industry")
                existing_agent_names = get_unique_values_from_agents(st.session_state.agents, "agent")
                existing_emojis = get_all_emojis_from_agents(st.session_state.agents)
                
                # Initialize custom input flags
                if "custom_sector_new" not in st.session_state:
                    st.session_state["custom_sector_new"] = False
                if "custom_industry_new" not in st.session_state:
                    st.session_state["custom_industry_new"] = False
                if "custom_emoji_new" not in st.session_state:
                    st.session_state["custom_emoji_new"] = False
                
                with st.form("add_new_agent_form", clear_on_submit=True):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown('<div style="font-size: 1.1rem; color: #7dd3fc; margin-bottom: 0.5rem; font-weight: 600;">🏭 Sector</div>', unsafe_allow_html=True)
                        sector_options = existing_sectors.copy() if existing_sectors else []
                        if not sector_options:
                            sector_options = ["🏦 Banking & Finance", "🛠️ AI Tools & Infrastructure", "💻 Information Technology", "⚡ Energy & Sustainability", "🚗 Automobile & Transport", "⚖️ Legal & Government", "🛍️ Retail / SMB / Creative", "🎰 Entertainment & Games", "🏢 Executive Leadership"]
                        sector_options.append("--- Enter Custom ---")
                        sector_choice = st.selectbox(
                            "Sector",
                            options=sector_options,
                            label_visibility="collapsed",
                            key="new_sector_select"
                        )
                        
                        if sector_choice == "--- Enter Custom ---":
                            st.session_state["custom_sector_new"] = True
                            new_sector = st.text_input(
                                "Custom Sector",
                                placeholder="e.g., 🏦 Banking & Finance",
                                label_visibility="collapsed",
                                key="new_sector_custom"
                            )
                        else:
                            st.session_state["custom_sector_new"] = False
                            new_sector = sector_choice
                        
                        st.markdown('<div style="font-size: 1.1rem; color: #7dd3fc; margin: 1rem 0 0.5rem 0; font-weight: 600;">🧩 Industry</div>', unsafe_allow_html=True)
                        industry_options = existing_industries.copy() if existing_industries else []
                        if not industry_options:
                            industry_options = ["💰 Retail Banking Suite", "🧩 Agent Builder", "🤖 Hugging Face Tools", "🎯 Agent Management"]
                        industry_options.append("--- Enter Custom ---")
                        industry_choice = st.selectbox(
                            "Industry",
                            options=industry_options,
                            label_visibility="collapsed",
                            key="new_industry_select"
                        )
                        
                        if industry_choice == "--- Enter Custom ---":
                            st.session_state["custom_industry_new"] = True
                            new_industry = st.text_input(
                                "Custom Industry",
                                placeholder="e.g., 💰 Retail Banking Suite",
                                label_visibility="collapsed",
                                key="new_industry_custom"
                            )
                        else:
                            st.session_state["custom_industry_new"] = False
                            new_industry = industry_choice
                        
                        st.markdown('<div style="font-size: 1.1rem; color: #7dd3fc; margin: 1rem 0 0.5rem 0; font-weight: 600;">🤖 Agent Name</div>', unsafe_allow_html=True)
                        new_agent_name = st.text_input(
                            "Agent Name",
                            placeholder="e.g., 💳 Credit Appraisal Agent",
                            label_visibility="collapsed",
                            key="new_agent_name"
                        )
                        if existing_agent_names:
                            st.caption(f"💡 Existing names: {', '.join(existing_agent_names[:5])}{'...' if len(existing_agent_names) > 5 else ''}")
                    
                    with col2:
                        st.markdown('<div style="font-size: 1.1rem; color: #7dd3fc; margin-bottom: 0.5rem; font-weight: 600;">😀 Emoji</div>', unsafe_allow_html=True)
                        emoji_options = existing_emojis.copy() if existing_emojis else ["🤖", "💳", "🏦", "🛡️", "⚖️", "🧩", "💬", "🧠", "🩺", "⚡", "☀️", "🚗", "🔋", "🛻", "🔐", "🏛️", "📈", "🎬", "🎰"]
                        emoji_options.append("--- Enter Custom ---")
                        emoji_choice = st.selectbox(
                            "Emoji",
                            options=emoji_options,
                            format_func=lambda x: f"{x} {x}" if x != "--- Enter Custom ---" else "--- Enter Custom ---",
                            label_visibility="collapsed",
                            key="new_emoji_select"
                        )
                        
                        if emoji_choice == "--- Enter Custom ---":
                            st.session_state["custom_emoji_new"] = True
                            new_emoji = st.text_input(
                                "Custom Emoji",
                                placeholder="e.g., 💳",
                                label_visibility="collapsed",
                                key="new_emoji_custom"
                            )
                        else:
                            st.session_state["custom_emoji_new"] = False
                            new_emoji = emoji_choice
                        
                        st.markdown('<div style="font-size: 1.1rem; color: #7dd3fc; margin: 1rem 0 0.5rem 0; font-weight: 600;">📶 Status</div>', unsafe_allow_html=True)
                        new_status = st.selectbox(
                            "Status",
                            options=STATUS_OPTIONS,
                            label_visibility="collapsed",
                            key="new_status"
                        )
                        st.markdown('<div style="margin: 1rem 0;">', unsafe_allow_html=True)
                        st.markdown('<div style="font-size: 1rem; color: #94a3b8; margin-bottom: 0.5rem;">Access Control:</div>', unsafe_allow_html=True)
                        new_requires_login = st.checkbox(
                            "🔐 Login Required - Users must login to access this agent",
                            value=False,
                            key="new_requires_login"
                        )
                        st.markdown('<div style="font-size: 1rem; color: #94a3b8; margin: 0.5rem 0;">Logging:</div>', unsafe_allow_html=True)
                        new_enable_logging = st.checkbox(
                            "📊 Logging Enabled - Agent activities will be logged",
                            value=True,
                            key="new_enable_logging"
                        )
                        st.markdown('<div style="font-size: 1rem; color: #94a3b8; margin: 0.5rem 0;">Action Button</div>', unsafe_allow_html=True)
                        new_action = st.selectbox(
                            "Action Button",
                            options=ACTION_OPTIONS,
                            key="new_action_mode",
                            label_visibility="collapsed"
                        )
                        st.markdown('</div>', unsafe_allow_html=True)
                        st.markdown('<div style="font-size: 1.1rem; color: #7dd3fc; margin: 1rem 0 0.5rem 0; font-weight: 600;">📝 Description</div>', unsafe_allow_html=True)
                        new_description = st.text_area(
                            "Description",
                            placeholder="Brief description of what the agent does",
                            height=100,
                            label_visibility="collapsed",
                            key="new_description"
                        )
                    
                    col_submit, col_cancel = st.columns(2)
                    with col_submit:
                        submitted = st.form_submit_button("➕ Add Agent", use_container_width=True, type="primary")
                    with col_cancel:
                        cancel_clicked = st.form_submit_button("❌ Cancel", use_container_width=True)
                    
                    if cancel_clicked:
                        st.session_state.show_add_form = False
                        st.rerun()
                    
                    if submitted:
                        # Handle custom inputs
                        final_new_sector = new_sector if isinstance(new_sector, str) and new_sector else ""
                        final_new_industry = new_industry if isinstance(new_industry, str) and new_industry else ""
                        final_new_emoji = new_emoji if isinstance(new_emoji, str) and new_emoji else ""
                        
                        if not all([final_new_sector, final_new_industry, new_agent_name, final_new_emoji, new_description]):
                            st.error("❌ Please fill in all fields!")
                        elif len(final_new_emoji.strip()) > 2:
                            st.error("❌ Emoji should be a single emoji character")
                        else:
                            new_agent = {
                                "sector": final_new_sector.strip(),
                                "industry": final_new_industry.strip(),
                                "agent": new_agent_name.strip(),
                                "description": new_description.strip(),
                                "status": new_status,
                                "emoji": final_new_emoji.strip(),
                                "requires_login": new_requires_login,
                                "enable_logging": new_enable_logging,
                                "action": new_action
                            }
                            st.session_state.agents.append(new_agent)
                            if save_agents(st.session_state.agents):
                                st.success("✅ Agent added successfully!")
                                st.session_state.show_add_form = False
                                st.rerun()
                            else:
                                st.error("❌ Failed to save agent!")
        
        # Show message if editing (for tab2 compatibility)
        if st.session_state.editing_index is not None and st.session_state.expanded_edit is None:
            edit_idx = st.session_state.editing_index
            if 0 <= edit_idx < len(st.session_state.agents):
                agent_name = st.session_state.agents[edit_idx].get('agent', 'Unknown')
                st.info(f"💡 Click ✏️ Edit on any agent card to edit inline")
        
        if not st.session_state.agents:
            st.info("No agents found. Add a new agent to get started.")
        else:
            # Search and filter - bigger input
            st.markdown('<div style="margin-bottom: 1.5rem;">', unsafe_allow_html=True)
            search_term = st.text_input(
                "🔍 Search agents", 
                placeholder="Search by name, sector, or industry...",
                key="agent_search"
            )
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Filter agents
            filtered_agents = st.session_state.agents
            if search_term:
                search_lower = search_term.lower()
                filtered_agents = [
                    agent for agent in st.session_state.agents
                    if search_lower in agent.get('agent', '').lower() or
                       search_lower in agent.get('sector', '').lower() or
                       search_lower in agent.get('industry', '').lower() or
                       search_lower in agent.get('description', '').lower()
                ]
            
            st.markdown(
                f'<div style="font-size: 1.3rem; color: #7dd3fc; margin-bottom: 1.5rem; font-weight: 600;">'
                f'Showing {len(filtered_agents)} of {len(st.session_state.agents)} agents'
                f'</div>',
                unsafe_allow_html=True
            )
            
            # Display agents with bigger, more prominent cards
            for idx, agent in enumerate(st.session_state.agents):
                # Use the loop index directly - it's already the correct position
                actual_idx = idx
                
                # Skip if filtered out
                if search_term and agent not in filtered_agents:
                    continue
                
                # Create a styled card container
                st.markdown('<div class="agent-card-container">', unsafe_allow_html=True)
                
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    # Agent name - bigger
                    agent_name = agent.get('agent', 'N/A')
                    emoji = agent.get('emoji', '🤖')
                    st.markdown(
                        f'<div class="agent-name">{emoji} {agent_name}</div>',
                        unsafe_allow_html=True
                    )
                    
                    # Sector/Industry - bigger
                    sector = agent.get('sector', '')
                    industry = agent.get('industry', '')
                    st.markdown(
                        f'<div class="agent-meta">{sector} → {industry}</div>',
                        unsafe_allow_html=True
                    )
                    
                    # Description - bigger and full text
                    desc = agent.get('description', 'N/A')
                    st.markdown(
                        f'<div class="agent-description">📝 {desc}</div>',
                        unsafe_allow_html=True
                    )
                
                with col2:
                    # Status - bigger badge
                    status = agent.get('status', 'N/A')
                    status_colors = {
                        "Available": ("🟢", "#22c55e"),
                        "NEW": ("🔵", "#3b82f6"),
                        "Coming Soon": ("🟡", "#f59e0b"),
                        "WIP": ("🟣", "#f472b6"),
                        "Being Built": ("🟠", "#f97316")
                    }
                    status_emoji, status_color = status_colors.get(status, ("⚪", "#94a3b8"))
                    st.markdown(
                        f'<div class="status-badge" style="background-color: {status_color}20; color: {status_color}; border: 2px solid {status_color}; text-align: center; padding: 1rem; border-radius: 12px; margin-bottom: 1rem;">'
                        f'{status_emoji} <strong>{status}</strong>'
                        f'</div>',
                        unsafe_allow_html=True
                    )
                    
                    # Action indicator
                    action_mode = agent.get("action", "Auto")
                    st.markdown(
                        '<div style="text-align: center; font-size: 0.95rem; color: #7dd3fc; margin-bottom: 1rem;">'
                        f'🎯 <strong>Action:</strong> {action_mode}'
                        '</div>',
                        unsafe_allow_html=True
                    )
                    
                    # Login requirement
                    if agent.get('requires_login', False):
                        st.markdown(
                            '<div style="text-align: center; font-size: 1.1rem; color: #f59e0b; margin-bottom: 0.5rem;">'
                            '🔐 <strong>Login Required</strong>'
                            '</div>',
                            unsafe_allow_html=True
                        )
                    else:
                        st.markdown(
                            '<div style="text-align: center; font-size: 1.1rem; color: #22c55e; margin-bottom: 0.5rem;">'
                            '🔓 <strong>No Login</strong>'
                            '</div>',
                            unsafe_allow_html=True
                        )
                    
                    # Logging status
                    if agent.get('enable_logging', True):
                        st.markdown(
                            '<div style="text-align: center; font-size: 0.95rem; color: #3b82f6; margin-bottom: 1rem;">'
                            '📊 <strong>Logging Enabled</strong>'
                            '</div>',
                            unsafe_allow_html=True
                        )
                    else:
                        st.markdown(
                            '<div style="text-align: center; font-size: 0.95rem; color: #94a3b8; margin-bottom: 1rem;">'
                            '📊 <strong>Logging Disabled</strong>'
                            '</div>',
                            unsafe_allow_html=True
                        )
                    
                    # Action buttons - bigger with up/down controls
                    col_up, col_down, col_edit, col_copy, col_del = st.columns(5)
                    
                    with col_up:
                        if actual_idx > 0:
                            if st.button("⬆️", key=f"up_{actual_idx}", help="Move up", use_container_width=True):
                                # Close expander if open
                                if st.session_state.expanded_edit == actual_idx:
                                    st.session_state.expanded_edit = None
                                # Swap with previous agent
                                st.session_state.agents[actual_idx], st.session_state.agents[actual_idx - 1] = \
                                    st.session_state.agents[actual_idx - 1], st.session_state.agents[actual_idx]
                                if save_agents(st.session_state.agents):
                                    st.success("✅ Agent moved up!")
                                    st.rerun()
                        else:
                            st.button("⬆️", key=f"up_{actual_idx}", disabled=True, use_container_width=True)
                    
                    with col_down:
                        if actual_idx < len(st.session_state.agents) - 1:
                            if st.button("⬇️", key=f"down_{actual_idx}", help="Move down", use_container_width=True):
                                # Close expander if open
                                if st.session_state.expanded_edit == actual_idx:
                                    st.session_state.expanded_edit = None
                                # Swap with next agent
                                st.session_state.agents[actual_idx], st.session_state.agents[actual_idx + 1] = \
                                    st.session_state.agents[actual_idx + 1], st.session_state.agents[actual_idx]
                                if save_agents(st.session_state.agents):
                                    st.success("✅ Agent moved down!")
                                    st.rerun()
                        else:
                            st.button("⬇️", key=f"down_{actual_idx}", disabled=True, use_container_width=True)
                    
                    with col_edit:
                        # Toggle expander on edit button click
                        if st.button("✏️ Edit", key=f"edit_{actual_idx}", help="Edit agent", use_container_width=True):
                            if st.session_state.expanded_edit == actual_idx:
                                st.session_state.expanded_edit = None  # Close if already open
                            else:
                                st.session_state.expanded_edit = actual_idx  # Open this one
                            st.rerun()
                    with col_copy:
                        if st.button("📋 Copy", key=f"copy_{actual_idx}", help="Copy agent", use_container_width=True):
                            # Create a copy of the agent
                            agent_copy = agent.copy()
                            # Modify the name to indicate it's a copy
                            agent_copy["agent"] = f"{agent.get('agent', 'Agent')} (Copy)"
                            
                            import re
                            # Get original route_name
                            if "route_name" in agent and agent.get("route_name"):
                                original_route_name = agent.get("route_name")
                            else:
                                # Compute route_name from original agent name
                                original_name = agent.get("agent", "").strip()
                                clean_agent = re.sub(r"[^\w\s-]", "", original_name).strip().lower()
                                original_route_name = re.sub(r"[-\s]+", "_", clean_agent).replace("_agent", "")
                                original_route_name = re.sub(r"_+", "_", original_route_name).strip("_")
                                original_route_name = original_route_name or "agent"
                            
                            # Ask user if they want independent backend or shared backend
                            # For now, default to independent backend (create new files)
                            # Compute copied route_name
                            copied_route_name = f"{original_route_name}_copy"
                            agent_copy["route_name"] = copied_route_name
                            
                            # Automatically update all necessary files for independent backend
                            setup_results = setup_copied_agent_backend(
                                original_route_name=original_route_name,
                                copied_route_name=copied_route_name,
                                agent_name=agent.get("agent", "Agent")
                            )
                            
                            # Insert after current agent
                            st.session_state.agents.insert(actual_idx + 1, agent_copy)
                            if save_agents(st.session_state.agents):
                                # Show success message with details
                                if setup_results["success"]:
                                    st.success("✅ Agent copied successfully! Independent backend created.")
                                    # Show detailed messages
                                    if setup_results["messages"]:
                                        for msg in setup_results["messages"]:
                                            st.info(msg)
                                else:
                                    st.warning("⚠️ Agent copied but some backend setup had issues. Check messages below.")
                                    for msg in setup_results["messages"]:
                                        st.info(msg)
                                    for err in setup_results["errors"]:
                                        st.error(err)
                                
                                # If there were critical errors, still allow the copy but warn
                                if setup_results["errors"]:
                                    st.warning("⚠️ Some files may need manual updates. See COPIED_AGENT_SETUP_GUIDE.md for details.")
                                
                                st.rerun()
                    with col_del:
                        if st.button("🗑️ Delete", key=f"delete_{actual_idx}", help="Delete agent", use_container_width=True):
                            st.session_state.agents.pop(actual_idx)
                            if st.session_state.expanded_edit == actual_idx:
                                st.session_state.expanded_edit = None
                            if save_agents(st.session_state.agents):
                                st.success("✅ Agent deleted successfully!")
                                st.rerun()
                
                st.markdown('</div>', unsafe_allow_html=True)
                
                # ============================================
                # EDIT FORM - COMPLETELY RECREATED FROM SCRATCH
                # ============================================
                is_expanded = st.session_state.expanded_edit == actual_idx
                with st.expander(f"✏️ Edit {agent.get('agent', 'Agent')}", expanded=is_expanded):
                    if is_expanded:
                        agent_data = agent.copy()
                        
                        # Get existing values for dropdowns
                        existing_sectors = get_unique_values_from_agents(st.session_state.agents, "sector")
                        existing_industries = get_unique_values_from_agents(st.session_state.agents, "industry")
                        existing_agent_names = get_unique_values_from_agents(st.session_state.agents, "agent")
                        existing_emojis = get_all_emojis_from_agents(st.session_state.agents)
                        
                        # Create form with unique key
                        form_key = f"edit_agent_{actual_idx}"
                        with st.form(form_key, clear_on_submit=False):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                # SECTOR (text input with suggestions)
                                st.markdown("**🏭 Sector**")
                                current_sector = agent_data.get("sector", "")
                                sector_suggestions = existing_sectors.copy() if existing_sectors else []
                                default_sector_choices = ["🏦 Banking & Finance", "🛠️ AI Tools & Infrastructure", "💻 Information Technology", "⚡ Energy & Sustainability", "🚗 Automobile & Transport", "⚖️ Legal & Government", "🛍️ Retail / SMB / Creative", "🎰 Entertainment & Games", "🏢 Executive Leadership"]
                                for s in default_sector_choices:
                                    if s not in sector_suggestions:
                                        sector_suggestions.append(s)
                                sector_final = st.text_input(
                                    "Sector",
                                    value=current_sector,
                                    key=f"txt_sector_{actual_idx}",
                                    label_visibility="collapsed"
                                )
                                if sector_suggestions:
                                    st.caption("Suggestions: " + ", ".join(sector_suggestions[:5]) + ("…" if len(sector_suggestions) > 5 else ""))
                                
                                # INDUSTRY (text input with suggestions)
                                st.markdown("**🧩 Industry**")
                                current_industry = agent_data.get("industry", "")
                                industry_suggestions = existing_industries.copy() if existing_industries else []
                                default_industry_choices = ["💰 Retail Banking Suite", "🧩 Agent Builder", "🤖 Hugging Face Tools", "🎯 Agent Management"]
                                for ind in default_industry_choices:
                                    if ind not in industry_suggestions:
                                        industry_suggestions.append(ind)
                                industry_final = st.text_input(
                                    "Industry",
                                    value=current_industry,
                                    key=f"txt_industry_{actual_idx}",
                                    label_visibility="collapsed"
                                )
                                if industry_suggestions:
                                    st.caption("Suggestions: " + ", ".join(industry_suggestions[:5]) + ("…" if len(industry_suggestions) > 5 else ""))
                                
                                # AGENT NAME (plain text)
                                st.markdown("**🤖 Agent Name**")
                                current_agent_name = agent_data.get("agent", "")
                                name_final = st.text_input(
                                    "Agent Name",
                                    value=current_agent_name,
                                    key=f"txt_name_{actual_idx}",
                                    label_visibility="collapsed"
                                )
                                
                                # Route name info
                                route_name_val = agent_data.get("route_name")
                                if route_name_val:
                                    st.info(f"🔗 Backend Route: `{route_name_val}` (preserved)")
                            
                            with col2:
                                # EMOJI (dropdown with custom)
                                st.markdown("**😀 Emoji**")
                                current_emoji = agent_data.get("emoji", "🤖")
                                emoji_opts = existing_emojis.copy() if existing_emojis else []
                                default_emoji_choices = ["🤖", "💳", "🏦", "🛡️", "⚖️", "🧩", "💬", "🧠", "🩺", "⚡", "☀️", "🚗", "🔋", "🛻", "🔐", "🏛️", "📈", "🎬", "🎰"]
                                for em in default_emoji_choices:
                                    if em not in emoji_opts:
                                        emoji_opts.append(em)
                                if current_emoji and current_emoji not in emoji_opts:
                                    emoji_opts.insert(0, current_emoji)
                                emoji_opts = sorted(emoji_opts)
                                if "--- Enter Custom ---" not in emoji_opts:
                                    emoji_opts.append("--- Enter Custom ---")
                                emoji_default_idx = emoji_opts.index(current_emoji) if current_emoji in emoji_opts else 0
                                
                                emoji_sel = st.selectbox(
                                    "Emoji",
                                    emoji_opts,
                                    index=emoji_default_idx,
                                    format_func=lambda x: f"{x} {x}" if x not in {"--- Enter Custom ---"} else x,
                                    key=f"sel_emoji_{actual_idx}",
                                    label_visibility="collapsed"
                                )
                                if emoji_sel == "--- Enter Custom ---":
                                    emoji_final = st.text_input("Custom Emoji", value=current_emoji, key=f"txt_emoji_{actual_idx}").strip() or current_emoji
                                else:
                                    emoji_final = emoji_sel.strip()
                                
                                # STATUS
                                st.markdown("**📶 Status**")
                                current_status = agent_data.get("status", "Available")
                                status_options = STATUS_OPTIONS.copy()
                                if current_status not in status_options:
                                    status_options = [current_status] + status_options
                                status_val = st.selectbox(
                                    "Status",
                                    status_options,
                                    index=status_options.index(current_status),
                                    key=f"sel_status_{actual_idx}",
                                    label_visibility="collapsed"
                                )
                                
                                # ACTION BUTTON
                                st.markdown("**🎯 Action Button**")
                                current_action = agent_data.get("action", "Auto")
                                if current_action not in ACTION_OPTIONS:
                                    current_action = "Auto"
                                action_val = st.selectbox(
                                    "Action",
                                    ACTION_OPTIONS,
                                    index=ACTION_OPTIONS.index(current_action),
                                    key=f"sel_action_{actual_idx}",
                                    label_visibility="collapsed"
                                )
                                
                                # CHECKBOXES
                                st.markdown("---")
                                login_val = st.checkbox("🔐 Login Required", value=agent_data.get("requires_login", False), key=f"chk_login_{actual_idx}")
                                logging_val = st.checkbox("📊 Logging Enabled", value=agent_data.get("enable_logging", True), key=f"chk_logging_{actual_idx}")
                                
                                # DESCRIPTION
                                st.markdown("**📝 Description**")
                                desc_val = st.text_area("Description", value=agent_data.get("description", ""), height=100, key=f"txt_desc_{actual_idx}", label_visibility="collapsed")
                            
                            # FORM BUTTONS
                            btn_col1, btn_col2 = st.columns(2)
                            with btn_col1:
                                save_btn = st.form_submit_button("💾 Save Changes", use_container_width=True, type="primary")
                            with btn_col2:
                                cancel_btn = st.form_submit_button("❌ Cancel", use_container_width=True)
                            
                            # HANDLE CANCEL
                            if cancel_btn:
                                st.session_state.expanded_edit = None
                                st.rerun()
                            
                            # HANDLE SAVE
                            if save_btn:
                                try:
                                    final_sector = sector_final.strip()
                                    final_industry = industry_final.strip()
                                    final_name = name_final.strip()
                                    final_emoji = emoji_final.strip()
                                    final_status = status_val
                                    final_action = action_val
                                    final_desc = desc_val.strip()
                                    final_login = login_val
                                    final_logging = logging_val
                                    
                                    # Validate
                                    form_snapshot = {
                                        "idx": actual_idx,
                                        "sector": final_sector,
                                        "industry": final_industry,
                                        "agent": final_name,
                                        "emoji": final_emoji,
                                        "status": final_status,
                                        "description": final_desc,
                                        "requires_login": final_login,
                                        "enable_logging": final_logging
                                    }
                                    log_form_data("edit_agent", form_snapshot)
                                    
                                    if not all([final_sector, final_industry, final_name, final_emoji, final_desc]):
                                        st.error("❌ All fields required!")
                                        log_error(Exception("ValidationError"), form_snapshot, "Missing required fields")
                                    elif len(final_emoji.strip()) > 2:
                                        st.error("❌ Emoji must be single character")
                                        log_error(Exception("ValidationError"), form_snapshot, "Emoji must be single character")
                                    else:
                                        # Build updated agent
                                        updated = {
                                            "sector": final_sector.strip(),
                                            "industry": final_industry.strip(),
                                            "agent": final_name.strip(),
                                            "description": final_desc.strip(),
                                            "status": final_status,
                                            "emoji": final_emoji.strip(),
                                            "requires_login": final_login,
                                            "enable_logging": final_logging,
                                            "action": final_action
                                        }
                                        
                                        # Preserve route_name
                                        if agent_data.get("route_name"):
                                            updated["route_name"] = agent_data.get("route_name")
                                        
                                        # Save
                                        st.session_state.agents[actual_idx] = updated
                                        if save_agents(st.session_state.agents):
                                            st.success("✅ Saved!")
                                            st.session_state.expanded_edit = None
                                            st.rerun()
                                        else:
                                            st.error("❌ Save failed!")
                                except Exception as e:
                                    st.error(f"❌ Error: {e}")
                                    log_error(e, {"idx": actual_idx}, str(e))
    
    # Preview Tab
    with tab2:
        st.header("👁️ Preview New Landing Page")
        render_preview(st.session_state.agents)
        st.markdown("---")
        st.info("💡 This preview shows how your agents will appear on the landing page. Make changes in 'agents list' tab and preview here.")
    
    # Save New Landing Page Tab
    with tab3:
        st.header("💾 Save New Landing Page")
        st.markdown("Save the current agent configuration as a new landing page layout.")
        st.markdown("---")
        
        layout_name = st.text_input(
            "Landing Page Name",
            placeholder="e.g., Default Landing, Banking Focus, Marketing Page, etc.",
            key="layout_name_input",
            help="Enter a name for this landing page layout"
        )
        
        st.markdown("### Current Configuration")
        st.info(f"📊 This layout contains **{len(st.session_state.agents)} agents**")
        
        if st.button("💾 Save New Landing Page", use_container_width=True, type="primary"):
            if not layout_name.strip():
                st.error("❌ Please enter a landing page name!")
            else:
                if save_layout(layout_name.strip(), st.session_state.agents):
                    st.success(f"✅ Landing page '{layout_name.strip()}' saved successfully!")
                    st.rerun()
                else:
                    st.error("❌ Failed to save landing page!")
    
    # Apply New Landing Page Tab
    with tab4:
        st.header("🔄 Apply New Landing Page")
        st.markdown("Apply a saved landing page layout to replace the current configuration.")
        st.markdown("---")
        
        saved_layouts = list_saved_layouts()
        if saved_layouts:
            selected_layout = st.selectbox(
                "Select Landing Page to Apply",
                options=saved_layouts,
                key="layout_select_apply",
                help="Choose a saved landing page to apply"
            )
            
            if selected_layout:
                layout_agents = load_layout(selected_layout)
                st.markdown(f"### Preview: **{selected_layout}**")
                st.info(f"📊 This layout contains **{len(layout_agents)} agents**")
                
                # Show preview of what will be applied
                with st.expander("👁️ Preview Agents in This Layout"):
                    for idx, agent in enumerate(layout_agents[:10]):  # Show first 10
                        st.markdown(f"{idx+1}. {agent.get('emoji', '🤖')} **{agent.get('agent', 'N/A')}**")
                    if len(layout_agents) > 10:
                        st.caption(f"... and {len(layout_agents) - 10} more agents")
            
            st.warning("⚠️ **Warning:** Applying a layout will replace all current agents!")
            
            if st.button("🔄 Apply Landing Page", use_container_width=True, type="primary"):
                loaded_agents = load_layout(selected_layout)
                if loaded_agents:
                    st.session_state.agents = loaded_agents
                    if save_agents(st.session_state.agents):
                        st.success(f"✅ Landing page '{selected_layout}' applied successfully! File saved to `services/ui/data/agents.json`")
                        st.info("💡 **Note:** The landing page will automatically reload agents within 5 seconds. If you don't see changes, refresh your browser.")
                        st.rerun()
                    else:
                        st.error("❌ Failed to apply landing page!")
                else:
                    st.error(f"❌ Failed to load landing page '{selected_layout}'!")
        else:
            st.info("No saved landing pages found. Save a landing page first in the 'save new landing page' tab.")
    
    # Load Existing Landing Page Tab
    with tab5:
        st.header("📂 Load Existing Landing Page")
        st.markdown("View and manage all saved landing page layouts.")
        st.markdown("---")
        
        saved_layouts = list_saved_layouts()
        if saved_layouts:
            st.subheader("📚 Saved Landing Pages")
            for layout_name in saved_layouts:
                layout_agents = load_layout(layout_name)
                with st.container():
                    col_info, col_load, col_delete = st.columns([3, 1, 1])
                    with col_info:
                        st.markdown(f"**{layout_name}**")
                        st.caption(f"📊 {len(layout_agents)} agents • Created: {Path(LAYOUTS_DIR / f'{layout_name}.json').stat().st_mtime if (LAYOUTS_DIR / f'{layout_name}.json').exists() else 'Unknown'}")
                    with col_load:
                        if st.button("📂 Load", key=f"load_layout_{layout_name}", help=f"Load {layout_name}", use_container_width=True):
                            loaded_agents = load_layout(layout_name)
                            if loaded_agents:
                                st.session_state.agents = loaded_agents
                                if save_agents(st.session_state.agents):
                                    st.success(f"✅ Landing page '{layout_name}' loaded successfully! File saved to `services/ui/data/agents.json`")
                                    st.info("💡 **Note:** The main landing page (app.py) loads agents at startup. To see changes, refresh the browser or restart the Streamlit app.")
                                    st.rerun()
                    with col_delete:
                        if st.button("🗑️", key=f"delete_layout_{layout_name}", help=f"Delete {layout_name}"):
                            try:
                                layout_file = LAYOUTS_DIR / f"{layout_name}.json"
                                if layout_file.exists():
                                    layout_file.unlink()
                                    st.success(f"✅ Landing page '{layout_name}' deleted!")
                                    st.rerun()
                            except Exception as e:
                                st.error(f"❌ Error deleting landing page: {e}")
                    st.markdown("---")
        else:
            st.info("No saved landing pages. Use 'save new landing page' tab to create one.")

if __name__ == "__main__":
    main()
