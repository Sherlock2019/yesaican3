"""Seed the app with a worked demo: 10 painpoints, 10 helpers, 3 cross-BU projects.

Every record is generated through the same functions the running app uses —
``classify_pain_point``, ``compute_pain``, ``compute_opportunity``,
``recommend_metrics``, ``draft_poc``, ``promote_to_agent`` — so the demo cannot
drift from what a real submission produces. Writing the JSON by hand would have
meant inventing scores the engine would never have given.

Three things the sample set is deliberately shaped to demonstrate:

1. **Helpers cure someone else's department.** The helper->painpoint mapping is a
   derangement: nobody fixes their own unit's problem, and the script refuses to
   seed if that ever stops being true. That is the whole premise of the
   community, and a demo where Billing helps Billing shows none of it.

2. **Pain types cluster on purpose.** Billing+Finance share an invoice/ledger
   problem, Sales+Legal a contract-extraction one, Marketing+Security an
   approval-chasing one, and CS+Delivery+Product a status-assembly one. That
   gives "most similar painpoints" and "painpoints felt across departments" real
   overlap to find instead of coincidences of wording.

3. **One deep, narrow outlier.** Support's ticket painpoint carries the most
   hours of anything here but touches a single unit, so the reach ranking has
   something to correctly rank *below* smaller problems that several teams share.

Everything written here carries ``"is_sample": true``. Run with --remove to take
it all back out and leave real submissions untouched.

    python3 scripts/seed_demo_data.py            # add
    python3 scripts/seed_demo_data.py --remove   # take it back out
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.shared import business_flow as bf  # noqa: E402
from services.shared.pain_metrics import (  # noqa: E402
    classify_pain_point,
    compute_opportunity,
    compute_pain,
    recommend_metrics,
)
from services.shared.pipeline import draft_poc, promote_to_agent  # noqa: E402

META = ROOT / "services" / ".sandbox_meta"
SUBMISSIONS = META / "how_ai_help_submissions.json"
SOLUTIONS = META / "how_ai_help_solutions.json"
HUMANS = META / "humans.json"
PROJECTS = META / "projects.json"
LIBRARY = ROOT / "services" / "ui" / "data" / "agents.json"

NOW = datetime.now(timezone.utc)


class Painpoint:
    """One department's problem, in the words its owner would use."""

    def __init__(self, unit, submitter, title, description, task, source,
                 destination, steps, minutes, per_month, who, outcomes,
                 workflow, stage, expect_type, age_days, upvotes):
        self.unit = unit
        self.submitter = submitter
        self.title = title
        self.description = description
        self.task = task
        self.source = source
        self.destination = destination
        self.steps = steps
        self.minutes = minutes
        self.per_month = per_month
        self.who = who
        self.outcomes = outcomes
        self.workflow = workflow
        self.stage = stage
        self.expect_type = expect_type   # asserted at build time, so a reworded
        self.age_days = age_days         # description cannot silently move a cluster
        self.upvotes = upvotes


# ---------------------------------------------------------------------------
# The ten painpoints - one per business unit.
# ---------------------------------------------------------------------------

PAINPOINTS = [
    # ---- invoice / ledger cluster: Billing and Finance feel the same problem ----
    Painpoint(
        unit="Billing", submitter="Gerry Osei",
        title="Every customer wants their invoice in a different layout",
        description=(
            "Each account has its own invoice format, so every billing run I take our "
            "standard invoice export and rebuild it by hand per customer - different "
            "column names, different date formats, different line-item grouping. One "
            "wrong charge line and the customer disputes the whole invoice."),
        task="Create invoice", source="Billing export", destination="Finance",
        steps=14, minutes=45, per_month=250, who="My department",
        outcomes=["save_time", "reduce_errors", "fewer_steps"],
        workflow=[
            "Export the billing run from the billing platform",
            "Open the customer's format template",
            "Map our columns onto theirs by hand",
            "Re-check every charge line against the source",
            "Send the invoice and file a copy for Finance",
        ],
        stage="published", expect_type="billing", age_days=61, upvotes=12),

    Painpoint(
        unit="Finance", submitter="Marta Lindqvist",
        title="Payments that do not match the invoice get chased by hand",
        description=(
            "When a payment lands that does not reconcile to an invoice, I work backwards "
            "through bank statements, credit notes and email to find where the difference "
            "came from. Most turn out to be a partial payment or a credit note that nobody "
            "applied to the ledger."),
        task="Reconcile ledger", source="Invoice from Billing", destination="Customer Success",
        steps=18, minutes=65, per_month=60, who="My team",
        outcomes=["save_time", "reduce_errors"],
        workflow=[
            "Pull the unmatched payments report",
            "Open the invoice and the bank statement side by side",
            "Trace credit notes and partial payments",
            "Email the account owner if it still does not tie out",
            "Post the adjustment and note the reason",
        ],
        stage="proven", expect_type="billing", age_days=34, upvotes=7),

    # ---- contract / form extraction cluster: Sales and Legal ----
    Painpoint(
        unit="Sales", submitter="Chidi Nwosu",
        title="Order forms and contracts get retyped into the CRM",
        description=(
            "A signed order form arrives as a scanned PDF attachment. I read it and retype "
            "the terms, dates and pricing into the CRM. Extracting the same fields from a "
            "document the customer already filled in is not selling."),
        task="Create proposal", source="Signed order form (PDF)", destination="Legal",
        steps=12, minutes=35, per_month=90, who="My team",
        outcomes=["save_time", "reduce_errors"],
        workflow=[
            "Open the signed order form attachment",
            "Read off terms, dates, pricing and entity name",
            "Retype each field into the CRM opportunity",
            "Re-read the document to check nothing was missed",
            "Attach the PDF and hand off to Legal",
        ],
        stage="published", expect_type="document", age_days=48, upvotes=9),

    Painpoint(
        unit="Legal", submitter="Elena Varga",
        title="Which clause version is current lives in an email thread",
        description=(
            "Every redline round on a contract arrives as a new document attachment in a "
            "long email chain. To answer 'what does the liability clause say right now' I "
            "have to read the whole thread and diff the attachments by eye."),
        task="Review contract", source="Proposal from Sales", destination="Billing",
        steps=9, minutes=90, per_month=25, who="My team",
        outcomes=["fewer_steps", "compliance"],
        workflow=[
            "Find the latest redline attachment in the thread",
            "Open it against the previous version",
            "Diff the clause by eye",
            "Record the agreed wording in the tracker",
            "Send the next round back to the counterparty",
        ],
        stage="proven", expect_type="document", age_days=27, upvotes=6),

    # ---- approval-chasing cluster: Marketing and Security ----
    Painpoint(
        unit="Marketing", submitter="Sinead Byrne",
        title="Campaign creative waits on three separate sign-offs",
        description=(
            "Every campaign asset needs approval from brand, legal and the product owner. "
            "Each review cycle is chased separately, nobody can see who the approval is "
            "currently sitting with, and launch dates slip waiting on a gate that the "
            "approver did not know was theirs."),
        task="Produce qualified lead", source="Campaign brief", destination="Sales",
        steps=11, minutes=40, per_month=30, who="My team",
        outcomes=["save_time", "fewer_steps"],
        workflow=[
            "Send the asset to brand for sign-off",
            "Chase brand, then forward to legal",
            "Chase legal, then forward to the product owner",
            "Collate the three approvals into the launch checklist",
            "Release the campaign to Sales",
        ],
        stage="poc", expect_type="approval", age_days=15, upvotes=8),

    Painpoint(
        unit="Security, Risk & Compliance", submitter="Yusuf Demir",
        title="Control exceptions need sign-off before every audit",
        description=(
            "Ahead of each audit I chase an approval for every open control exception - who "
            "authorised it, until when, and on what basis. The review cycle runs across six "
            "teams and the gate stays invisible until the auditor asks."),
        task="Sign off control", source="Control exception register",
        destination="Service Delivery",
        steps=16, minutes=70, per_month=14, who="Our customers",
        outcomes=["compliance", "fewer_steps"],
        workflow=[
            "Pull the open exception register",
            "Identify the owning team for each exception",
            "Request sign-off and chase it",
            "Record the authorisation and its expiry",
            "Assemble the pack for the auditor",
        ],
        stage="captured", expect_type="approval", age_days=6, upvotes=4),

    # ---- status-assembly cluster: Customer Success, Service Delivery, Product ----
    Painpoint(
        unit="Customer Success", submitter="Lena Fischer",
        title="The account review deck is rebuilt from five dashboards",
        description=(
            "Before every account review I query five dashboards for usage, tickets, "
            "invoices, adoption and open actions, then paste the metrics into a slide. The "
            "report is stale the moment it is built."),
        task="Onboard customer", source="Provisioned service", destination="Support",
        steps=16, minutes=50, per_month=45, who="My department",
        outcomes=["save_time", "faster_response"],
        workflow=[
            "Open each of the five dashboards in turn",
            "Query the account's numbers for the period",
            "Paste the metrics into the review template",
            "Write the commentary from memory",
            "Send the deck to the account team",
        ],
        stage="poc", expect_type="analysis", age_days=19, upvotes=5),

    Painpoint(
        unit="Service Delivery", submitter="Kofi Mensah",
        title="Delivery status is a query across four trackers",
        description=(
            "'Where is this deployment' means opening four trackers and reading them "
            "against each other. Building the weekly delivery report is an analyst job that "
            "produces a metric nobody can drill into afterwards."),
        task="Provision service", source="Signed contract", destination="Customer Success",
        steps=22, minutes=40, per_month=35, who="My team",
        outcomes=["fewer_steps", "improve_quality"],
        workflow=[
            "Open each delivery tracker",
            "Reconcile the four views of the same deployment",
            "Build the weekly status report",
            "Circulate it and answer the follow-up questions",
            "Hand the account over to Customer Success",
        ],
        stage="poc", expect_type="analysis", age_days=23, upvotes=3),

    Painpoint(
        unit="Product", submitter="Sofia Rossi",
        title="Roadmap themes are tallied by hand once a quarter",
        description=(
            "Every quarter an analyst reads through the feedback backlog and tallies the "
            "themes in a spreadsheet to produce the roadmap report. By the time the analysis "
            "lands, the quarter it describes is over."),
        task="Prioritize improvement", source="Customer feedback", destination="Marketing",
        steps=26, minutes=120, per_month=4, who="My department",
        outcomes=["save_time", "improve_quality"],
        workflow=[
            "Export the quarter's feedback backlog",
            "Read every item and label it by hand",
            "Tally the labels in a spreadsheet",
            "Write the roadmap report from the tallies",
            "Present it and hand the themes to Marketing",
        ],
        stage="captured", expect_type="analysis", age_days=11, upvotes=6),

    # ---- the deep, narrow outlier ----
    Painpoint(
        unit="Support", submitter="Diego Santos",
        title="The same twenty tickets get triaged from scratch every week",
        description=(
            "The same known issues arrive as support tickets week after week, and each one "
            "is triaged from the beginning - read the complaint, reproduce it, search "
            "whether we have seen it before, then escalate. The SLA clock runs the whole "
            "time."),
        task="Resolve issue", source="Support cases", destination="Product",
        steps=8, minutes=25, per_month=400, who="Our customers",
        outcomes=["faster_response", "avoid_repetition"],
        workflow=[
            "Read the incoming ticket",
            "Try to reproduce the reported behaviour",
            "Search past tickets for the same symptom",
            "Escalate if no known resolution is found",
            "Reply to the customer and close",
        ],
        stage="captured", expect_type="support", age_days=4, upvotes=11),

    # ---- the near-duplicate trio -------------------------------------------
    # Three units doing the identical job — read fields off a PDF, type them
    # into a system of record — in three different vocabularies. Nothing here
    # says "invoice" or "CRM", so plain word overlap barely links them, while
    # the signature (extract + document + cross-unit) puts all three in the
    # "likely the same problem" band, together with Sales' order-form painpoint.
    # This is the set the similarity feature exists to find.
    Painpoint(
        unit="Operations / Cloud Services", submitter="Tobias Krause",
        title="Datacentre asset forms are retyped into the CMDB",
        description=(
            "Hardware arrives with a printed asset form. Someone scans it, reads off the "
            "serial, rack position, model and support dates, and retypes all of it into "
            "the CMDB. A single mistyped serial makes the record unfindable later."),
        task="Record asset", source="Asset handover form (PDF)", destination="Service Delivery",
        steps=10, minutes=30, per_month=120, who="My team",
        outcomes=["save_time", "reduce_errors"],
        workflow=[
            "Scan the printed asset handover form",
            "Read off serial, rack position, model and support dates",
            "Retype each field into the CMDB",
            "Re-check the serial against the document",
            "File the scan against the asset record",
        ],
        stage="captured", expect_type="document", age_days=9, upvotes=5),

    Painpoint(
        unit="Engineering & Delivery", submitter="Ravi Patel",
        title="Supplier warranty documents are retyped into the asset register",
        description=(
            "Each supplier sends warranty certificates as scanned PDF attachments. I read "
            "the cover dates, entitlement level and contract reference off the document and "
            "retype them into the asset register so renewals can be tracked."),
        task="Record warranty", source="Warranty certificate (PDF)", destination="Finance",
        steps=11, minutes=28, per_month=80, who="My team",
        outcomes=["save_time", "reduce_errors"],
        workflow=[
            "Open the warranty certificate attachment",
            "Read off cover dates, entitlement level and contract reference",
            "Retype the fields into the asset register",
            "Check the reference against the supplier's document",
            "Attach the scan to the register entry",
        ],
        stage="captured", expect_type="document", age_days=7, upvotes=4),

    Painpoint(
        unit="Product & Solutions", submitter="Hana Sato",
        title="Partner spec sheets are retyped into the product catalogue",
        description=(
            "Partners send product spec sheets as PDF documents. To list anything I read "
            "off the model names, capabilities and support tiers and retype them into the "
            "catalogue, then re-read the sheet to check nothing was missed."),
        task="List product", source="Partner spec sheet (PDF)", destination="Marketing",
        steps=13, minutes=42, per_month=45, who="My department",
        outcomes=["save_time", "reduce_errors", "improve_quality"],
        workflow=[
            "Open the partner spec sheet",
            "Read off model names, capabilities and support tiers",
            "Retype each entry into the product catalogue",
            "Re-read the sheet to check nothing was missed",
            "Publish the catalogue entry",
        ],
        stage="captured", expect_type="document", age_days=5, upvotes=3),
]


class Helper:
    """Someone offering a cure for a painpoint that is not their own unit's."""

    def __init__(self, name, department, region, skills, cures, why, what, how,
                 tools, benefit, difficulty, status):
        self.name = name
        self.department = department
        self.region = region
        self.skills = skills
        self.cures = cures        # painpoint title, so a typo fails loudly
        self.why = why            # why this person, from another unit, can help
        self.what = what
        self.how = how
        self.tools = tools
        self.benefit = benefit
        self.difficulty = difficulty
        self.status = status


# ---------------------------------------------------------------------------
# Ten helpers, each from a different department to the painpoint they cure.
# ---------------------------------------------------------------------------

HELPERS = [
    Helper("Mateo Duarte", "Billing", "Americas",
           ["Schema mapping", "SQL", "Billing systems"],
           cures="Payments that do not match the invoice get chased by hand",
           why="Billing already models partial payments and credit notes - the two "
               "things behind most of Finance's breaks.",
           what="Explain every reconciliation break in one line",
           how="Match statement to invoice, isolate the delta, classify it as partial "
               "payment / credit note / FX / genuine gap, route the exceptions",
           tools="Deterministic matching rules, small LLM for the explanation only",
           benefit="Chasing turns into reviewing - the break arrives already explained",
           difficulty="Hard", status="In production"),

    Helper("Marta Lindqvist", "Finance", "EMEA",
           ["Reconciliation", "Controls", "Excel"],
           cures="Every customer wants their invoice in a different layout",
           why="Finance is the unit that finds these errors downstream, so we know "
               "exactly which fields must never be mapped wrong.",
           what="Convert the billing export into each customer's layout automatically",
           how="Detect the source schema, apply the per-customer mapping, validate the "
               "totals against the source, queue anything that does not tie out",
           tools="Mapping rules, validation harness",
           benefit="45 minutes per invoice down to under 8, and the totals are checked",
           difficulty="Medium", status="In production"),

    Helper("Aisha Kone", "Legal", "EMEA",
           ["Document AI", "Contract law", "Redlining"],
           cures="Order forms and contracts get retyped into the CRM",
           why="Legal reads these same order forms one step later - we know which "
               "fields are binding and which are decoration.",
           what="Extract the order-form fields straight into the CRM",
           how="Parse the PDF, extract terms / dates / pricing / entity, confidence-score "
               "each field, and send anything below threshold to a human rather than the CRM",
           tools="Document parser, field extractor with per-field confidence",
           benefit="No retyping, and low-confidence fields are flagged instead of guessed",
           difficulty="Medium", status="Testing"),

    Helper("Chidi Nwosu", "Sales", "Americas",
           ["CPQ", "Deal desk", "Process design"],
           cures="Which clause version is current lives in an email thread",
           why="Sales sits on the other end of every redline round and feels the delay "
               "directly, so we care about turnaround more than anyone.",
           what="Track redline versions against the clause instead of the thread",
           how="Ingest each redline attachment, diff clause by clause, keep a current "
               "version per clause with who changed it and when",
           tools="Document diff engine, clause index",
           benefit="'What does the liability clause say' becomes a lookup, not a reread",
           difficulty="Medium", status="Testing"),

    Helper("Diego Santos", "Support", "Americas",
           ["Retrieval", "NLP", "Knowledge bases"],
           cures="The account review deck is rebuilt from five dashboards",
           why="Support already aggregates the ticket half of this picture; extending "
               "it to the other four sources is the same pattern.",
           what="Assemble the account review pack automatically",
           how="Pull the five sources on a schedule, normalise onto one account id, "
               "render the deck, flag the metrics that moved since the last review",
           tools="Source connectors, chart renderer",
           benefit="Reviews start from current data instead of from copying",
           difficulty="Medium", status="Prototype"),

    Helper("Lena Fischer", "Customer Success", "EMEA",
           ["Adoption analytics", "Reporting", "Escalations"],
           cures="The same twenty tickets get triaged from scratch every week",
           why="Customer Success sees which repeat issues actually drive churn, so we "
               "can say which twenty are worth matching first.",
           what="Match an incoming ticket to a known resolution before triage",
           how="Classify the intent, retrieve the nearest known issue, propose the "
               "resolution with its confidence, and triage only what stays unmatched",
           tools="Retrieval index over resolved tickets, intent classifier",
           benefit="The repeat twenty stop consuming triage time twice",
           difficulty="Easy", status="Prototype"),

    Helper("Kofi Mensah", "Service Delivery", "Americas",
           ["Automation", "Terraform", "Evidence collection"],
           cures="Control exceptions need sign-off before every audit",
           why="Service Delivery is one of the six teams being chased - we would rather "
               "emit the evidence automatically than answer the email.",
           what="Collect control evidence on a schedule instead of at audit time",
           how="One collector per control, store each result with provenance and "
               "timestamp, assemble the audit pack on demand",
           tools="Scheduled collectors, evidence store with provenance",
           benefit="Audit prep becomes a query rather than a six-team chase",
           difficulty="Hard", status="Draft"),

    Helper("Yusuf Demir", "Security, Risk & Compliance", "EMEA",
           ["GRC", "Approval workflow", "Audit"],
           cures="Campaign creative waits on three separate sign-offs",
           why="Compliance runs approval gates for a living - the pattern is identical, "
               "only the approvers differ.",
           what="Make the three sign-offs one visible gate",
           how="Route the asset to all three reviewers at once, show who it is waiting "
               "on, remind automatically, record each approval with its basis",
           tools="Workflow engine, reminder scheduler",
           benefit="Nobody chases, and the launch date stops slipping invisibly",
           difficulty="Easy", status="Building"),

    Helper("Sofia Rossi", "Product", "EMEA",
           ["Clustering", "Product analytics", "Roadmapping"],
           cures="Delivery status is a query across four trackers",
           why="Product consumes this weekly report - building it somewhere it can be "
               "drilled into serves both of us.",
           what="One delivery status view across the four trackers",
           how="Ingest all four, reconcile onto one deployment id, publish a status view "
               "that the report is generated from so the number stays drillable",
           tools="Connectors, reconciliation rules",
           benefit="The weekly report becomes a view, not an assembly job",
           difficulty="Medium", status="Building"),

    Helper("Priya Raman", "Marketing", "APAC",
           ["Segmentation", "Embeddings", "Python"],
           cures="Roadmap themes are tallied by hand once a quarter",
           why="Marketing runs the same clustering over campaign response data every "
               "month; pointing it at the feedback backlog is a small change.",
           what="Cluster feedback into themes continuously instead of quarterly",
           how="Stream the feedback in, embed it, cluster it, rank themes by volume and "
               "account value, and surface the movement week over week",
           tools="Embeddings, clustering, ranking",
           benefit="Roadmap input is current instead of three months old",
           difficulty="Medium", status="Draft"),
]


# ---------------------------------------------------------------------------
# A second wave of cures: the four painpoints still without a helper, plus
# three second opinions on painpoints somebody is already working.
# ---------------------------------------------------------------------------
# The first three deliberately propose the *same* extraction service pointed at
# three different documents. That is what the duplicate cluster is for: it gives
# cure-to-cure similarity something real to find, so "reuse before you rebuild"
# has content instead of being a permanently empty panel.

EXTRA_CURES = [
    Helper("Aisha Kone", "Legal", "EMEA",
           ["Document AI", "Contract law", "Redlining"],
           cures="Datacentre asset forms are retyped into the CMDB",
           why="This is the same extractor Legal built for order forms, pointed at a "
               "different document. The parsing work is already done.",
           what="Extract asset-form fields straight into the CMDB",
           how="Parse the scanned document, extract the fields, confidence-score each "
               "one, and send anything below threshold to a human rather than the record",
           tools="Document parser, field extractor with per-field confidence",
           benefit="No retyping, and a mistyped serial stops being possible",
           difficulty="Medium", status="Prototype"),

    Helper("Mateo Duarte", "Billing", "Americas",
           ["Schema mapping", "SQL", "Billing systems"],
           cures="Supplier warranty documents are retyped into the asset register",
           why="Same shape as the order-form extractor — a document in, a system of "
               "record out. Worth building once for all of them.",
           what="Extract warranty fields straight into the asset register",
           how="Parse the scanned document, extract the fields, confidence-score each "
               "one, and send anything below threshold to a human rather than the record",
           tools="Document parser, field extractor with per-field confidence",
           benefit="Renewals stop depending on somebody retyping a contract reference",
           difficulty="Medium", status="Draft"),

    Helper("Tobias Krause", "Operations / Cloud Services", "EMEA",
           ["CMDB", "Automation", "Data quality"],
           cures="Partner spec sheets are retyped into the product catalogue",
           why="Operations hits this same retyping problem on asset forms; one shared "
               "extractor covers both and the catalogue too.",
           what="Extract spec-sheet fields straight into the product catalogue",
           how="Parse the document, extract the fields, confidence-score each one, and "
               "send anything below threshold to a human rather than the catalogue",
           tools="Document parser, field extractor with per-field confidence",
           benefit="Listing a partner product stops being a re-read-and-check job",
           difficulty="Medium", status="Draft"),

    Helper("Marta Lindqvist", "Finance", "EMEA",
           ["Reconciliation", "Controls", "Excel"],
           cures="Bill Length Reduction Project",
           why="Finance reads these bills at the other end — we know which lines "
               "customers actually query and which are never read.",
           what="Cut the bill to the lines a customer actually reads",
           how="Group repeated charge lines, summarise the long tail, and keep the full "
               "detail one click away rather than on page one",
           tools="Aggregation rules, summariser with a fixed template",
           benefit="A shorter bill, with nothing removed that anyone actually queries",
           difficulty="Easy", status="Draft"),

    Helper("Hana Sato", "Product & Solutions", "APAC",
           ["Product analytics", "Taxonomy", "Retrieval"],
           cures="The same twenty tickets get triaged from scratch every week",
           why="Product owns the defect taxonomy these tickets map onto, so we can name "
               "the twenty rather than letting a model guess them.",
           what="Name the twenty repeat issues explicitly and match against that list",
           how="Curate the known-issue list from the defect taxonomy, match each ticket "
               "against it first, and only fall back to classification when nothing fits",
           tools="Curated known-issue index, matcher",
           benefit="The match is explainable — you can see which known issue it hit",
           difficulty="Easy", status="Draft"),

    Helper("Diego Santos", "Support", "Americas",
           ["Retrieval", "NLP", "Knowledge bases"],
           cures="Campaign creative waits on three separate sign-offs",
           why="Support runs the same waiting-on-somebody problem all day; the fix that "
               "works there is showing the queue, not chasing it.",
           what="Show the approval queue instead of chasing it",
           how="One board per asset showing who each approval is waiting on and for how "
               "long, with an escalation once a gate goes stale",
           tools="Workflow board, staleness timer",
           benefit="The slipping gate is visible before the launch date moves",
           difficulty="Easy", status="Draft"),

    Helper("Kofi Mensah", "Service Delivery", "Americas",
           ["Automation", "Terraform", "Evidence collection"],
           cures="Roadmap themes are tallied by hand once a quarter",
           why="Service Delivery already streams delivery signals continuously; the same "
               "pipeline shape works for feedback.",
           what="Stream the feedback backlog into a live theme count",
           how="Ingest feedback as it arrives, label against the existing theme list, and "
               "keep a running count that the roadmap report reads from",
           tools="Ingestion pipeline, labeller",
           benefit="The roadmap report becomes a query rather than a quarterly project",
           difficulty="Medium", status="Draft"),
]


# ---------------------------------------------------------------------------
# Three AI engineers whose work needs several business units.
# ---------------------------------------------------------------------------
# Each names the painpoints it would close, so a cross-BU project is visible as
# data rather than only as prose.

CROSS_BU_PROJECTS = [
    {
        "title": "Quote-to-Cash Copilot",
        "engineer": "Noor Haddad",
        "summary": "One agent spanning order form, contract and invoice, so a signed deal "
                   "becomes a reconciled payment without three teams re-keying the same "
                   "numbers into three systems.",
        "units_needed": ["Sales", "Legal", "Billing", "Finance"],
        "closes": ["Order forms and contracts get retyped into the CRM",
                   "Which clause version is current lives in an email thread",
                   "Every customer wants their invoice in a different layout",
                   "Payments that do not match the invoice get chased by hand"],
        "expertise_needed": [
            "Sales - which pricing exceptions are real, and how they get approved",
            "Legal - which clause types may be auto-filled and which never may",
            "Billing - the invoice schema and every customer-specific edge case",
            "Finance - what actually counts as a reconciled payment",
        ],
        "phase": "MVP",
        "blocked_on": "Legal sign-off on which clause types can be auto-populated",
        "ask": "Two hours from someone in Legal to classify the clause library.",
    },
    {
        "title": "Account Health Signal Mesh",
        "engineer": "Ravi Patel",
        "summary": "Joins provisioning telemetry, ticket history and adoption data onto one "
                   "account id, so every team reads the same health signal instead of "
                   "assembling its own.",
        "units_needed": ["Service Delivery", "Customer Success", "Support", "Product"],
        "closes": ["The account review deck is rebuilt from five dashboards",
                   "Delivery status is a query across four trackers",
                   "The same twenty tickets get triaged from scratch every week"],
        "expertise_needed": [
            "Service Delivery - what a healthy provisioning run actually looks like",
            "Customer Success - the signals that really precede a churn conversation",
            "Support - how ticket sentiment maps to account risk",
            "Product - which usage metrics predict renewal rather than just activity",
        ],
        "phase": "Prototype",
        "blocked_on": "No single account identifier exists across the four systems",
        "ask": "One person from each unit to agree the joining key. One meeting, four people.",
    },
    {
        "title": "Evidence-on-Demand for Audits",
        "engineer": "Grace Okoro",
        "summary": "Continuous control-evidence collection across every unit, so an audit is "
                   "answered with a query instead of a six-week chase.",
        "units_needed": ["Security, Risk & Compliance", "Service Delivery",
                         "Marketing", "Billing"],
        "closes": ["Control exceptions need sign-off before every audit",
                   "Campaign creative waits on three separate sign-offs"],
        "expertise_needed": [
            "Security - which controls need evidence, and the form an auditor accepts",
            "Service Delivery - where the deployment and provisioning records live",
            "Marketing - the approval trail behind published claims",
            "Billing - evidence for the financial controls specifically",
        ],
        "phase": "Incubation",
        "blocked_on": "Retention policy for evidence containing customer identifiers",
        "ask": "A decision from Security on retention before any collector is written.",
    },
]


# ---------------------------------------------------------------------------
# store helpers
# ---------------------------------------------------------------------------

def read(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def strip_samples(records) -> list:
    if not isinstance(records, list):
        return []
    return [r for r in records if isinstance(r, dict) and not r.get("is_sample")]


def _difficulty(complexity: float) -> str:
    if complexity <= 30:
        return "Easy"
    if complexity <= 55:
        return "Medium"
    if complexity <= 75:
        return "Hard"
    return "Critical"


# ---------------------------------------------------------------------------
# builders
# ---------------------------------------------------------------------------

def build_painpoint(index: int, spec: Painpoint, owner: str) -> dict:
    pain = compute_pain(spec.steps, spec.minutes, spec.per_month, "per month", spec.who)
    pain_type, type_label = classify_pain_point(f"{spec.title} {spec.description}")
    if pain_type != spec.expect_type:
        raise SystemExit(
            f"{spec.title!r} classified as {pain_type!r}, expected {spec.expect_type!r}. "
            "The clustering this demo depends on has moved - reword the description or "
            "update expect_type deliberately."
        )
    opportunity = compute_opportunity(pain, spec.outcomes, reusable_agents=[])
    metrics = recommend_metrics(pain_type, spec.outcomes, pain)

    edge = bf.edge_between(spec.unit, spec.destination)
    obj = bf.business_object(edge["object"]) if edge else None

    record = {
        "id": f"sample_challenge_{index + 1}",
        "is_sample": True,
        "title": spec.title,
        "description": spec.description,
        "submitter": {"name": spec.submitter, "department": spec.unit,
                      "region": "Global", "role": "Practitioner"},
        "category": type_label,
        "pain_type": pain_type,
        "difficulty": _difficulty(opportunity["complexity"]),
        "confidentiality": "Internal",
        "upvotes": spec.upvotes,
        "comments": 0,
        "urgency": {"LOW": 3.0, "MODERATE": 5.5, "HIGH": 7.5,
                    "SEVERE": 9.0}.get(pain["level"], 5.5),
        "impact_score": round(opportunity["impact"] / 10.0, 1),
        "similar_agents": [],
        "created_at": (NOW - timedelta(days=spec.age_days)).isoformat(),
        "twin_context": {
            "business_unit": spec.unit,
            "task": spec.task,
            "input": spec.source,
            "input_from": spec.source,
            "flow_edge": bf.edge_id(edge) if edge else "",
            "flow_object": (obj or {}).get("name", ""),
            "output_to": spec.destination,
            "output_flow": (f"{(obj or {}).get('name', '')} -> {edge['triggers']}"
                            if edge else ""),
        },
        "baseline": pain,
        "opportunity": opportunity,
        "outcomes": list(spec.outcomes),
        "current_workflow": list(spec.workflow),
        "workflow_source": "sample",
        "metrics": [
            {k: row[k] for k in ("key", "label", "icon", "unit", "group",
                                 "better", "before", "target", "actual")}
            for row in metrics if row["selected"]
        ],
    }

    # Advance it through the real pipeline, so a demo POC is exactly what the
    # app would have drafted from this painpoint.
    if spec.stage in {"poc", "proven", "published"}:
        poc = draft_poc(record)
        poc["github"] = "yesaican/" + poc["id"].replace("poc_", "")[:40]
        poc["owner"] = owner
        if spec.stage == "poc":
            poc["status"] = "Building"
            poc["platform"] = ""
            if poc.get("acceptance"):
                poc["acceptance"][0]["met"] = True
        else:
            poc["status"] = "Live"
            poc["platform"] = "Streamlit"
            poc["demo_url"] = f"https://lab.internal/{poc['id']}"
            for criterion in poc.get("acceptance", []):
                criterion["met"] = True
        record["poc"] = poc
    return record


def build_solution(index: int, helper: Helper, challenge: dict) -> dict:
    approach = "\n".join([
        f"- What: {helper.what}",
        f"- How: {helper.how}",
        f"- AI tools: {helper.tools}",
        f"- So what: {helper.benefit}",
        f"- Why me: {helper.why}",
    ])
    # Real submissions predate the sample schema and may carry a bare or missing
    # submitter, so nothing here may assume the nested keys exist.
    submitter = challenge.get("submitter")
    submitter = submitter if isinstance(submitter, dict) else {}
    return {
        "id": f"sample_solution_{index + 1}",
        "is_sample": True,
        "challenge_id": challenge.get("id", ""),
        "challenge": challenge.get("title", ""),
        "submitter": submitter.get("name", ""),
        "submitter_department": submitter.get("department", ""),
        "author": helper.name,
        "helper": helper.name,
        "helper_department": helper.department,
        "approach": approach,
        "what_features": helper.what,
        "how_components": helper.how,
        "ai_tools_used": helper.tools,
        "so_what_benefits": helper.benefit,
        "why_me": helper.why,
        "difficulty": helper.difficulty,
        "status": helper.status,
        "upvotes": 0,
        "comments": 0,
        "created_at": (NOW - timedelta(days=index + 1)).isoformat(),
    }


def build_human(helper: Helper, cured: dict) -> dict:
    submitter = cured.get("submitter")
    submitter = submitter if isinstance(submitter, dict) else {}
    cured_unit = submitter.get("department") or "another team"
    return {
        "id": f"sample_human_{helper.name.lower().replace(' ', '_')}",
        "is_sample": True,
        "name": helper.name,
        "department": helper.department,
        "region": helper.region,
        "role": "AI Ambassador",
        "skills": list(helper.skills),
        "projects_built": [helper.what],
        "ai_services": [helper.what],
        "bio": (f"{helper.department}. Currently helping {cured_unit} with "
                f"\"{str(cured.get('title', '')).lower()}\"."),
        "ambassador": True,
        "created_at": NOW.isoformat(),
        "updated_at": NOW.isoformat(),
    }


def build_project(index: int, spec: dict, by_title: dict) -> dict:
    return {
        "id": f"sample_project_{index + 1}",
        "is_sample": True,
        "title": spec["title"],
        "summary": spec["summary"],
        "description": spec["summary"],
        "authors": [spec["engineer"]],
        "lead_engineer": spec["engineer"],
        "phase": spec["phase"],
        "status": spec["phase"],
        "business_units": list(spec["units_needed"]),
        "expertise_needed": list(spec["expertise_needed"]),
        "closes_painpoints": [by_title[title]["id"] for title in spec["closes"]],
        "closes_titles": list(spec["closes"]),
        "blocked_on": spec["blocked_on"],
        "ask": spec["ask"],
        "tags": ["cross-BU", "AI engineering"] + list(spec["units_needed"]),
        "stars": [6, 4, 3][index],
        "upvotes": [6, 4, 3][index],
        "created_at": (NOW - timedelta(days=(index + 1) * 11)).isoformat(),
    }


def build_engineer(spec: dict) -> dict:
    return {
        "id": f"sample_human_{spec['engineer'].lower().replace(' ', '_')}",
        "is_sample": True,
        "name": spec["engineer"],
        "department": "Engineering & Delivery",
        "region": "Global",
        "role": "AI Engineer",
        "skills": ["Agent design", "Retrieval", "Evaluation", "Python"],
        "projects_built": [spec["title"]],
        "ai_services": [spec["title"]],
        "bio": (f"Leading {spec['title']}, which closes {len(spec['closes'])} painpoints "
                f"across {len(spec['units_needed'])} units. Needs expertise from "
                f"{', '.join(spec['units_needed'])}. Blocked on: {spec['blocked_on']}"),
        "ambassador": False,
        "created_at": NOW.isoformat(),
        "updated_at": NOW.isoformat(),
    }


# ---------------------------------------------------------------------------

def seed() -> None:
    submissions = strip_samples(read(SUBMISSIONS, []))
    solutions = strip_samples(read(SOLUTIONS, []))
    humans = strip_samples(read(HUMANS, []))
    projects = strip_samples(read(PROJECTS, []))
    library = strip_samples(read(LIBRARY, []))

    # Whoever offered the cure owns the POC that came out of it.
    owner_of = {helper.cures: helper.name for helper in HELPERS}
    new_painpoints = [
        build_painpoint(i, spec, owner_of.get(spec.title, spec.submitter))
        for i, spec in enumerate(PAINPOINTS)
    ]
    by_title = {record["title"]: record for record in new_painpoints}
    # The second wave also cures real submissions, so they have to be findable —
    # sample records take precedence on a title clash, since those are the ones
    # this script owns.
    for record in submissions:
        by_title.setdefault(str(record.get("title") or ""), record)

    new_solutions, new_humans = [], []
    seen_humans: set[str] = set()
    for i, helper in enumerate(HELPERS + EXTRA_CURES):
        target = by_title.get(helper.cures)
        if target is None:
            raise SystemExit(
                f"{helper.name} cures {helper.cures!r}, which is not a painpoint title."
            )
        submitter = target.get("submitter")
        department = str((submitter or {}).get("department") or "") \
            if isinstance(submitter, dict) else ""
        if department and department == helper.department:
            raise SystemExit(
                f"{helper.name} ({helper.department}) is curing their own department's "
                "painpoint - the point of this sample set is that help crosses units."
            )
        new_solutions.append(build_solution(i, helper, target))

        # Several people cure more than one painpoint; they belong in the
        # directory once.
        human = build_human(helper, target)
        if human["id"] not in seen_humans:
            seen_humans.add(human["id"])
            new_humans.append(human)

    new_agents = []
    for record, spec in zip(new_painpoints, PAINPOINTS):
        if spec.stage != "published":
            continue
        agent = promote_to_agent(record, record["poc"])
        agent["is_sample"] = True
        record["published_agent"] = agent.get("agent", record["title"])
        new_agents.append(agent)

    for title in (t for spec in CROSS_BU_PROJECTS for t in spec["closes"]):
        if title not in by_title:
            raise SystemExit(f"project references {title!r}, which is not a painpoint title.")
    new_projects = [build_project(i, spec, by_title)
                    for i, spec in enumerate(CROSS_BU_PROJECTS)]
    new_humans += [build_engineer(spec) for spec in CROSS_BU_PROJECTS]

    write(SUBMISSIONS, new_painpoints + submissions)
    write(SOLUTIONS, new_solutions + solutions)
    write(HUMANS, new_humans + humans)
    write(PROJECTS, new_projects + projects)
    write(LIBRARY, new_agents + library)

    stages: dict[str, int] = {}
    types: dict[str, int] = {}
    for spec in PAINPOINTS:
        stages[spec.stage] = stages.get(spec.stage, 0) + 1
        types[spec.expect_type] = types.get(spec.expect_type, 0) + 1
    print(f"painpoints : {len(new_painpoints)}  stages={stages}")
    print(f"             clusters={types}")
    print(f"cures      : {len(new_solutions)} ({len(HELPERS)} first wave + "
          f"{len(EXTRA_CURES)} second), every one from another department")
    print(f"library    : {len(new_agents)} agents published from proven POCs")
    print(f"projects   : {len(new_projects)} cross-BU, covering "
          f"{len({t for s in CROSS_BU_PROJECTS for t in s['closes']})} painpoints")
    print(f"people     : {len(new_humans)}")
    print(f"kept       : {len(submissions)} real painpoints, {len(solutions)} real cures")


def remove() -> None:
    counts = {}
    for path in (SUBMISSIONS, SOLUTIONS, HUMANS, PROJECTS, LIBRARY):
        records = read(path, [])
        if not isinstance(records, list):
            continue
        kept = strip_samples(records)
        counts[path.name] = len(records) - len(kept)
        write(path, kept)
    print("removed:", ", ".join(f"{k}={v}" for k, v in counts.items()))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remove", action="store_true",
                        help="take the sample data back out")
    args = parser.parse_args()
    remove() if args.remove else seed()
