# Global Search — YES AI CAN
# Cross-platform search engine

import streamlit as st
import json
import os
from pathlib import Path
from typing import Dict, List, Any
from services.ui.utils.page_template import page_chrome

st.set_page_config(
    page_title="Search — YES AI CAN",
    layout="wide"
)

# Metadata storage
META_DIR = Path(__file__).parent.parent.parent.parent / ".sandbox_meta"
HUMANS_FILE = META_DIR / "humans.json"
PROJECTS_FILE = META_DIR / "projects.json"
AGENTS_FILE = META_DIR / "agents.json"
PATTERNS_FILE = META_DIR / "patterns.json"
META_DIR.mkdir(exist_ok=True)

def load_all_data():
    """Load all searchable data."""
    humans = []
    projects = []
    agents = []
    patterns = []
    
    if HUMANS_FILE.exists():
        try:
            with open(HUMANS_FILE, "r", encoding="utf-8") as f:
                humans = json.load(f)
        except:
            pass
    
    if PROJECTS_FILE.exists():
        try:
            with open(PROJECTS_FILE, "r", encoding="utf-8") as f:
                projects = json.load(f)
        except:
            pass
    
    if AGENTS_FILE.exists():
        try:
            with open(AGENTS_FILE, "r", encoding="utf-8") as f:
                agents = json.load(f)
        except:
            pass
    
    if PATTERNS_FILE.exists():
        try:
            with open(PATTERNS_FILE, "r", encoding="utf-8") as f:
                patterns = json.load(f)
        except:
            pass
    
    return humans, projects, agents, patterns

# Page header
page_chrome("", "Search", "One search across challenges, people, solutions and agents.")
st.markdown("**YES AI CAN — Rackers Lab & Community**")
st.markdown("---")

# Search input
search_query = st.text_input("🔍 Search across profiles, projects, agents, patterns, skills, and tags", 
                             placeholder="Enter keywords...")

humans, projects, agents, patterns = load_all_data()

if search_query:
    query_lower = search_query.lower()
    query_terms = [term.strip() for term in query_lower.split() if term.strip()]
    
    # Search humans
    matching_humans = []
    for human in humans:
        score = 0
        name = human.get('name', '').lower()
        skills = ' '.join(human.get('skills', [])).lower()
        bio = human.get('bio', '').lower()
        domain = human.get('domain_expertise', '').lower()
        
        for term in query_terms:
            if term in name:
                score += 10
            if term in skills:
                score += 5
            if term in bio:
                score += 3
            if term in domain:
                score += 3
        
        if score > 0:
            matching_humans.append((human, score))
    
    matching_humans.sort(key=lambda x: x[1], reverse=True)
    
    # Search projects
    matching_projects = []
    for project in projects:
        score = 0
        title = project.get('title', '').lower()
        desc = project.get('description', '').lower()
        tags = ' '.join(project.get('tags', [])).lower()
        authors = ' '.join(project.get('authors', [])).lower()
        
        for term in query_terms:
            if term in title:
                score += 10
            if term in desc:
                score += 5
            if term in tags:
                score += 5
            if term in authors:
                score += 3
        
        if score > 0:
            matching_projects.append((project, score))
    
    matching_projects.sort(key=lambda x: x[1], reverse=True)
    
    # Search agents
    matching_agents = []
    for agent in agents:
        score = 0
        name = agent.get('name', '').lower()
        desc = agent.get('description', '').lower()
        industry = agent.get('industry', '').lower()
        
        for term in query_terms:
            if term in name:
                score += 10
            if term in desc:
                score += 5
            if term in industry:
                score += 5
        
        if score > 0:
            matching_agents.append((agent, score))
    
    matching_agents.sort(key=lambda x: x[1], reverse=True)
    
    # Search patterns
    matching_patterns = []
    for pattern in patterns:
        score = 0
        name = pattern.get('name', '').lower()
        desc = pattern.get('description', '').lower()
        category = pattern.get('category', '').lower()
        
        for term in query_terms:
            if term in name:
                score += 10
            if term in desc:
                score += 5
            if term in category:
                score += 3
        
        if score > 0:
            matching_patterns.append((pattern, score))
    
    matching_patterns.sort(key=lambda x: x[1], reverse=True)
    
    # Display results
    total_results = len(matching_humans) + len(matching_projects) + len(matching_agents) + len(matching_patterns)
    st.write(f"**Found {total_results} result(s) for '{search_query}'**")
    st.markdown("---")
    
    # Humans
    if matching_humans:
        st.subheader(f"👤 Rackers ({len(matching_humans)})")
        for human, score in matching_humans[:10]:  # Top 10
            with st.expander(f"👤 {human.get('name', 'Unknown')} (Relevance: {score})"):
                st.write(f"**Role:** {human.get('role', 'N/A')}")
                st.write(f"**Department:** {human.get('department', 'N/A')}")
                st.write(f"**Skills:** {', '.join(human.get('skills', []))}")
                if human.get('bio'):
                    st.write(f"**Bio:** {human.get('bio')}")
        st.markdown("---")
    
    # Projects
    if matching_projects:
        st.subheader(f"🧱 Projects ({len(matching_projects)})")
        for project, score in matching_projects[:10]:  # Top 10
            with st.expander(f"🧱 {project.get('title', 'Untitled')} (Relevance: {score})"):
                st.write(f"**Description:** {project.get('description', 'N/A')}")
                st.write(f"**Authors:** {', '.join(project.get('authors', []))}")
                st.write(f"**Tags:** {', '.join(project.get('tags', []))}")
                st.write(f"**Phase:** {project.get('phase', 'N/A')}")
        st.markdown("---")
    
    # Agents
    if matching_agents:
        st.subheader(f"🤖 Agents ({len(matching_agents)})")
        for agent, score in matching_agents[:10]:  # Top 10
            with st.expander(f"🤖 {agent.get('name', 'Unknown')} (Relevance: {score})"):
                st.write(f"**Description:** {agent.get('description', 'N/A')}")
                st.write(f"**Industry:** {agent.get('industry', 'N/A')}")
                st.write(f"**Status:** {agent.get('status', 'N/A')}")
        st.markdown("---")
    
    # Patterns
    if matching_patterns:
        st.subheader(f"📚 Patterns ({len(matching_patterns)})")
        for pattern, score in matching_patterns[:10]:  # Top 10
            with st.expander(f"📚 {pattern.get('name', 'Unknown')} (Relevance: {score})"):
                st.write(f"**Description:** {pattern.get('description', 'N/A')}")
                st.write(f"**Category:** {pattern.get('category', 'N/A')}")
        st.markdown("---")
    
    if total_results == 0:
        st.info("🔍 No results found. Try different keywords or check spelling.")
else:
    st.info("🔍 Enter a search query to find profiles, projects, agents, patterns, skills, and tags across the platform.")
