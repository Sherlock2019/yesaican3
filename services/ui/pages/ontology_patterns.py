# Ontology & Pattern Library — YES AI CAN
# Business logic and reusable AI design patterns

import streamlit as st
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
from services.ui.utils.page_template import page_chrome

st.set_page_config(
    page_title="Ontology & Patterns — YES AI CAN",
    layout="wide"
)

# Metadata storage
META_DIR = Path(__file__).parent.parent.parent.parent / ".sandbox_meta"
PATTERNS_FILE = META_DIR / "patterns.json"
ONTOLOGY_FILE = META_DIR / "ontology.json"
META_DIR.mkdir(exist_ok=True)

def load_patterns() -> List[Dict]:
    """Load all patterns."""
    if PATTERNS_FILE.exists():
        try:
            with open(PATTERNS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def save_patterns(patterns: List[Dict]):
    """Save all patterns."""
    with open(PATTERNS_FILE, "w", encoding="utf-8") as f:
        json.dump(patterns, f, ensure_ascii=False, indent=2)

def load_ontology() -> List[Dict]:
    """Load ontology."""
    if ONTOLOGY_FILE.exists():
        try:
            with open(ONTOLOGY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def save_ontology(ontology: List[Dict]):
    """Save ontology."""
    with open(ONTOLOGY_FILE, "w", encoding="utf-8") as f:
        json.dump(ontology, f, ensure_ascii=False, indent=2)

# Page header
page_chrome("", "Ontology & Patterns", "Reusable logic, prompts and governance templates.")
st.markdown("**YES AI CAN — Rackers Lab & Community**")
st.markdown("---")

# Tabs: Ontology, Patterns, Add New
tab1, tab2, tab3 = st.tabs(["🧠 Ontology", "📚 Patterns", "➕ Add New"])

patterns = load_patterns()
ontology = load_ontology()

with tab1:
    st.subheader("Business Logic Ontology")
    
    if not ontology:
        st.info("🧠 No ontology entries yet. Add your first entity, relationship, or policy!")
    else:
        # Group by type
        entities = [o for o in ontology if o.get('type') == 'entity']
        relationships = [o for o in ontology if o.get('type') == 'relationship']
        policies = [o for o in ontology if o.get('type') == 'policy']
        rules = [o for o in ontology if o.get('type') == 'rule']
        decision_nodes = [o for o in ontology if o.get('type') == 'decision_node']
        
        if entities:
            st.markdown("### Entities")
            for entity in entities:
                with st.expander(f"📦 {entity.get('name', 'Unknown')}"):
                    st.write(f"**Description:** {entity.get('description', 'N/A')}")
                    if entity.get('attributes'):
                        st.write(f"**Attributes:** {', '.join(entity.get('attributes', []))}")
        
        if relationships:
            st.markdown("### Relationships")
            for rel in relationships:
                with st.expander(f"🔗 {rel.get('name', 'Unknown')}"):
                    st.write(f"**From:** {rel.get('from_entity', 'N/A')}")
                    st.write(f"**To:** {rel.get('to_entity', 'N/A')}")
                    st.write(f"**Description:** {rel.get('description', 'N/A')}")
        
        if policies:
            st.markdown("### Policies")
            for policy in policies:
                with st.expander(f"📋 {policy.get('name', 'Unknown')}"):
                    st.write(f"**Description:** {policy.get('description', 'N/A')}")
                    if policy.get('rules'):
                        st.write(f"**Rules:** {', '.join(policy.get('rules', []))}")
        
        if rules:
            st.markdown("### Rules")
            for rule in rules:
                with st.expander(f"⚖️ {rule.get('name', 'Unknown')}"):
                    st.write(f"**Description:** {rule.get('description', 'N/A')}")
                    if rule.get('condition'):
                        st.write(f"**Condition:** {rule.get('condition')}")
                    if rule.get('action'):
                        st.write(f"**Action:** {rule.get('action')}")
        
        if decision_nodes:
            st.markdown("### Decision Nodes")
            for node in decision_nodes:
                with st.expander(f"🎯 {node.get('name', 'Unknown')}"):
                    st.write(f"**Description:** {node.get('description', 'N/A')}")
                    if node.get('criteria'):
                        st.write(f"**Criteria:** {node.get('criteria')}")

with tab2:
    st.subheader("Reusable AI Design Patterns")
    
    if not patterns:
        st.info("📚 No patterns yet. Add your first reusable pattern!")
    else:
        # Filter by category
        categories = list(set([p.get('category', 'Other') for p in patterns]))
        category_filter = st.selectbox("Filter by Category", ["All"] + categories)
        
        filtered = patterns
        if category_filter != "All":
            filtered = [p for p in patterns if p.get('category') == category_filter]
        
        for pattern in filtered:
            with st.expander(f"📚 {pattern.get('name', 'Unknown')} — {pattern.get('category', 'N/A')}"):
                st.write(f"**Description:** {pattern.get('description', 'N/A')}")
                if pattern.get('use_case'):
                    st.write(f"**Use Case:** {pattern.get('use_case')}")
                if pattern.get('template_code'):
                    st.code(pattern.get('template_code'), language='python')
                if pattern.get('example'):
                    st.write(f"**Example:** {pattern.get('example')}")

with tab3:
    st.subheader("Add Ontology Entry or Pattern")
    
    entry_type = st.radio("Type", ["Ontology Entry", "Pattern"])
    
    if entry_type == "Ontology Entry":
        with st.form("ontology_form"):
            ont_type = st.selectbox("Ontology Type", 
                                   ["entity", "relationship", "policy", "rule", "decision_node"])
            name = st.text_input("Name *")
            description = st.text_area("Description *")
            
            if ont_type == "entity":
                attributes = st.text_input("Attributes (comma-separated)")
            elif ont_type == "relationship":
                from_entity = st.text_input("From Entity")
                to_entity = st.text_input("To Entity")
            elif ont_type == "policy":
                rules = st.text_input("Rules (comma-separated)")
            elif ont_type == "rule":
                condition = st.text_input("Condition")
                action = st.text_input("Action")
            elif ont_type == "decision_node":
                criteria = st.text_input("Criteria")
            
            submitted = st.form_submit_button("💾 Add Ontology Entry")
            
            if submitted:
                if not name or not description:
                    st.error("⚠️ Name and Description are required!")
                else:
                    entry = {
                        "id": f"ont_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(ontology)}",
                        "type": ont_type,
                        "name": name,
                        "description": description,
                        "created_at": datetime.now().isoformat()
                    }
                    
                    if ont_type == "entity" and attributes:
                        entry["attributes"] = [a.strip() for a in attributes.split(',') if a.strip()]
                    elif ont_type == "relationship":
                        entry["from_entity"] = from_entity
                        entry["to_entity"] = to_entity
                    elif ont_type == "policy" and rules:
                        entry["rules"] = [r.strip() for r in rules.split(',') if r.strip()]
                    elif ont_type == "rule":
                        entry["condition"] = condition
                        entry["action"] = action
                    elif ont_type == "decision_node":
                        entry["criteria"] = criteria
                    
                    ontology.append(entry)
                    save_ontology(ontology)
                    st.success("✅ Ontology entry added!")
                    st.rerun()
    
    else:  # Pattern
        with st.form("pattern_form"):
            name = st.text_input("Pattern Name *")
            category = st.selectbox("Category", 
                                   ["Appraisal", "KYC", "AIOps", "Data Pipeline", "Prompt", "Validation", "Other"])
            description = st.text_area("Description *")
            use_case = st.text_area("Use Case")
            template_code = st.text_area("Template Code (Python)", height=200)
            example = st.text_area("Example")
            
            submitted = st.form_submit_button("💾 Add Pattern")
            
            if submitted:
                if not name or not description:
                    st.error("⚠️ Name and Description are required!")
                else:
                    pattern = {
                        "id": f"pattern_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(patterns)}",
                        "name": name,
                        "category": category,
                        "description": description,
                        "use_case": use_case,
                        "template_code": template_code,
                        "example": example,
                        "created_at": datetime.now().isoformat()
                    }
                    
                    patterns.append(pattern)
                    save_patterns(patterns)
                    st.success("✅ Pattern added!")
                    st.rerun()
