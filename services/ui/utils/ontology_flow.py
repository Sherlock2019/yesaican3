"""Shared Digital Twin ontology data + auto-generated mermaid flowchart.

Used by the home page (services/ui/app.py) and the Digital Twin page
(services/ui/pages/ontology_twin.py) so the diagram stays in sync everywhere.
"""

from __future__ import annotations

from typing import Any, Dict, List

import streamlit as st
import streamlit.components.v1 as components

BUSINESS_UNITS: List[Dict[str, Any]] = [
    {
        "name": "Sales & Marketing",
        "region": "Global",
        "head": "Avery Chen",
        "missions": [
            "Capture customer pain points + renewal risks",
            "Translate field signals into qualified challenges",
            "Share packaged wins with customers",
        ],
        "systems": ["Salesforce", "GTM Planner", "Renewal Radar"],
        "signals": ["NPS delta", "Forecast accuracy", "Pipeline-to-delivery time"],
        "alliances": ["Product & Solutions", "Customer Success"],
    },
    {
        "name": "Product & Solutions",
        "region": "Global",
        "head": "Mia Patel",
        "missions": [
            "Curate backlog of “How Can AI Help” submissions",
            "Design Customer ZERO prototypes with SMEs",
            "Publish reusable Ontology + Pattern assets",
        ],
        "systems": ["Jira Discovery", "Pattern Library", "Ontology Vault"],
        "signals": ["Prototype velocity", "Pattern reuse", "Ambassador engagement"],
        "alliances": ["Engineering", "Sales & Marketing", "Ontology Guild"],
    },
    {
        "name": "Engineering & Delivery",
        "region": "Americas / EMEA",
        "head": "George Harrison",
        "missions": [
            "Operate Agent Factory + ModelOps stack",
            "Convert proven solutions into production pods",
            "Guardrail security, compliance, observability",
        ],
        "systems": ["Agent Factory", "ModelOps Plane", "Deployment Radar"],
        "signals": ["Lead time", "Defect escape rate", "GPU consumption"],
        "alliances": ["Product & Solutions", "Operations", "Security"],
    },
    {
        "name": "Operations / Cloud Services",
        "region": "Global",
        "head": "Kenji Yamamoto",
        "missions": [
            "Run OpenStack, Managed Cloud, and Ops Centers",
            "Feed telemetry into predictive capacity models",
            "Close the loop on automation adoption",
        ],
        "systems": ["OpenStack Control Plane", "Observability Mesh", "Field Ops Portal"],
        "signals": ["Capacity runway", "Incident MTTR", "Automation adoption"],
        "alliances": ["Engineering & Delivery", "Security", "Customer Success"],
    },
    {
        "name": "Customer Success",
        "region": "Global",
        "head": "Nia Thompson",
        "missions": [
            "Shepherd every live account through value playbooks",
            "Capture “voice of the Racker” happy / unhappy flows",
            "Sponsor Customer ONE journeys",
        ],
        "systems": ["SuccessHub", "Community Lab", "Champion Network"],
        "signals": ["Time-to-value", "Champion participation", "Save motions"],
        "alliances": ["Sales & Marketing", "Operations", "Human Stack"],
    },
    {
        "name": "Security, Risk & Compliance",
        "region": "Global",
        "head": "Karim Haddad",
        "missions": [
            "Own policy guardrails + AI governance center",
            "Certify datasets, prompts, and agent actions",
            "Coordinate escalations with SOC + Legal",
        ],
        "systems": ["Policy Checker", "SOC Copilot", "Risk Radar"],
        "signals": ["Control coverage", "Incident SLA", "Policy freshness"],
        "alliances": ["Engineering & Delivery", "Operations", "Legal"],
    },
]

RELATIONSHIPS: List[Dict[str, Any]] = [
    {
        "source": "Sales & Marketing",
        "target": "Product & Solutions",
        "flow": "Customer briefings → challenge charters",
        "artefacts": ["Challenge intake packet", "Voice of customer clips"],
        "cadence": "Weekly",
    },
    {
        "source": "Product & Solutions",
        "target": "Engineering & Delivery",
        "flow": "Approved backlog → build pods",
        "artefacts": ["AI blueprint", "Ontology spec", "Risk notes"],
        "cadence": "Sprint",
    },
    {
        "source": "Engineering & Delivery",
        "target": "Operations / Cloud Services",
        "flow": "Release candidates → deployment plans",
        "artefacts": ["Runbook", "Capacity ask", "Observability hooks"],
        "cadence": "Sprint / release",
    },
    {
        "source": "Operations / Cloud Services",
        "target": "Customer Success",
        "flow": "Operational telemetry → adoption playbooks",
        "artefacts": ["Adoption board", "SLO drift alerts"],
        "cadence": "Daily",
    },
    {
        "source": "Customer Success",
        "target": "Sales & Marketing",
        "flow": "Customer ONE references → revenue stories",
        "artefacts": ["Success briefs", "Metrics pack"],
        "cadence": "Monthly",
    },
    {
        "source": "Security, Risk & Compliance",
        "target": "All units",
        "flow": "Policy + guardrails + sign-offs",
        "artefacts": ["Control checklist", "Audit-ready package"],
        "cadence": "Per launch",
    },
]

SUPPORTING_LAYERS = [
    {
        "label": "Data / Telemetry",
        "items": ["Observability Mesh", "Renewal Risk Graph", "Capacity Twins", "Customer Feedback Store"],
        "color": "#7dd3fc",
    },
    {
        "label": "AI Assets",
        "items": ["Agent Library", "Ontology Patterns", "Human Stack Graph", "Prompt / Policy Vault"],
        "color": "#f472b6",
    },
    {
        "label": "Engagement Rituals",
        "items": ["Challenge triage", "Show-and-tell", "Customer ONE reviews", "Guardrail board"],
        "color": "#c084fc",
    },
]


# --------------------------------------------------------------------------
# Twin lookups
# --------------------------------------------------------------------------
# The twin already records who hands work to whom. Intake reads these instead
# of asking a submitter to describe their downstream from scratch — the answer
# is usually already in the model, and a pre-filled one gets corrected far more
# often than a blank one gets filled.

def business_unit_names() -> List[str]:
    """Every business unit in the twin, in diagram order."""
    return [unit["name"] for unit in BUSINESS_UNITS]


def business_unit(name: str) -> Dict[str, Any] | None:
    return next((unit for unit in BUSINESS_UNITS if unit["name"] == name), None)


def downstream_of(name: str) -> Dict[str, Any] | None:
    """Where this unit's work goes next, per the twin's relationship map."""
    return next(
        (rel for rel in RELATIONSHIPS
         if rel["source"] == name and rel["target"] != "All units"),
        None,
    )


def upstream_of(name: str) -> Dict[str, Any] | None:
    """Who hands work to this unit."""
    return next(
        (rel for rel in RELATIONSHIPS
         if rel["target"] == name and rel["source"] != "All units"),
        None,
    )


def _mermaid_node_id(name: str) -> str:
    return "BU_" + "".join(ch if ch.isalnum() else "_" for ch in name)


def build_ontology_mermaid() -> str:
    """Auto-generate a mermaid flowchart from the twin's units, flows, and layers."""
    lines = ["flowchart LR"]
    lines.append('    subgraph UNITS["🏢 Business Units"]')
    for unit in BUSINESS_UNITS:
        nid = _mermaid_node_id(unit["name"])
        label = f'{unit["name"]}<br/><i>{unit["head"]} · {unit["region"]}</i>'
        lines.append(f'        {nid}["{label}"]')
    lines.append("    end")
    lines.append('    subgraph LAYERS["🪄 Enabling Layers"]')
    for idx, layer in enumerate(SUPPORTING_LAYERS):
        items = "<br/>".join(layer["items"])
        lines.append(f'        LAYER{idx}["<b>{layer["label"]}</b><br/>{items}"]')
    lines.append("    end")
    for rel in RELATIONSHIPS:
        src = _mermaid_node_id(rel["source"])
        flow = rel["flow"].replace('"', "'")
        if rel["target"] == "All units":
            for unit in BUSINESS_UNITS:
                if unit["name"] == rel["source"]:
                    continue
                lines.append(f'    {src} -. "🛡️ guardrails" .-> {_mermaid_node_id(unit["name"])}')
        else:
            tgt = _mermaid_node_id(rel["target"])
            lines.append(f'    {src} -- "{flow} ({rel["cadence"]})" --> {tgt}')
    lines.append("    LAYERS --- UNITS")
    lines.append("    classDef bu fill:#0f172a,stroke:#38bdf8,color:#e2e8f0,stroke-width:2px;")
    lines.append("    classDef layer fill:#1e1b4b,stroke:#c084fc,color:#e2e8f0,stroke-width:2px;")
    lines.append("    classDef guard fill:#0f172a,stroke:#f87171,color:#fecaca,stroke-width:2px;")
    for unit in BUSINESS_UNITS:
        cls = "guard" if unit["name"] == "Security, Risk & Compliance" else "bu"
        lines.append(f"    class {_mermaid_node_id(unit['name'])} {cls};")
    for idx in range(len(SUPPORTING_LAYERS)):
        lines.append(f"    class LAYER{idx} layer;")
    return "\n".join(lines)


def render_ontology_flowchart(height: int = 680, title: str | None = "### 🗺️ Ontology Flow Chart — auto-generated from the twin") -> None:
    if title:
        st.markdown(title)
    mermaid_code = build_ontology_mermaid()
    components.html(
        f"""
        <div style="background:#0b1220;border:1px solid rgba(56,189,248,0.35);border-radius:16px;padding:12px;overflow:auto;">
          <pre class="mermaid" style="background:transparent;margin:0;">{mermaid_code}</pre>
        </div>
        <script type="module">
          import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
          mermaid.initialize({{ startOnLoad: true, theme: "dark", securityLevel: "loose", flowchart: {{ curve: "basis" }} }});
        </script>
        """,
        height=height,
        scrolling=True,
    )
