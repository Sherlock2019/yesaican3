import streamlit as st

st.set_page_config(
    page_title="Challenge Spec — Sync Rax Billing with Customer Billing Format",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.title("Challenge Spec — Sync Rax Billing with Customer Billing Format")

st.markdown(
    """
## 1. Business Problem

Our Community and key enterprise customers maintain **different billing formats** (files, fields, and delivery cadences).
Billing analysts currently massage spreadsheets every month to reconcile invoices, credits, and charge types.
This is **slow, error-prone, and difficult to audit**, especially across APAC multi-entity accounts.

---

## 2. Desired Outcome

Build an **AI-assisted billing sync agent** that can automatically map our Community exports to the customer's target layout,
apply deterministic transformations, and produce customer-ready files.
Success looks like:

1. Field-level mapping suggestions with explainability.
2. Auto-generated customer-ready billing packages.
3. Clear discrepancy reports and logs.

---

## 3. Users & Personas

- **Primary:** Billing Analyst / Finance Ops in APAC.
- **Secondary:** Finance managers and Customer Success for escalations.
- **System:** Scheduled monthly run plus on-demand mode for corrections.

---

## 4. Inputs & Data Sources

- our Community billing exports (CSV/XLSX).
- Customer-provided billing template/spec.
- Historical mapping notes or macros.
- Optional contract metadata (discounts, GL codes).

---

## 5. Outputs & UX Surfaces

- Customer-ready billing file matching the exact column order + formatting.
- Mapping rule artifact (JSON) capturing every transformation.
- Validation dashboard showing transformed rows, skipped rows, and anomalies.

---

## 6. Constraints & Non-Goals

- Not a replacement for the core billing engine.
- Must respect data privacy and regional regulations.
- Must explain every transformation for audit readiness.

---

## 7. Implementation Hints

- Pipeline pattern: ingest → normalize → map → emit.
- Use Pandas for transformations; persist mapping catalogs in JSON/SQLite.
- Allow AI suggestions but require human approval for new mappings.

---

## 8. Test / Acceptance Criteria

- Given sample our Community export + template, generated file matches golden dataset.
- Analyst can run end-to-end in <15 minutes without code.
- Detailed logs highlight unmapped fields or rejected rows.

> Codex: Treat this page as the spec for the "Sync Rax Billing" agent. Use it to drive backlog items and tests.
"""
)
