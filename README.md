# YES AI CAN — Community LAB

**A place where anyone can say "this part of my job hurts", and someone from another
team can say "I can fix that".**

YES AI CAN turns scattered, unrecorded frustration into a queue of scoped, scored,
comparable problems — then routes each one to a person who can solve it, tracks the
proof-of-concept, and publishes what works to a shared agent library.

The premise is simple: in any organisation of a few thousand people, the person who
can fix your problem almost certainly exists and almost certainly does not know your
problem exists. This is the connective tissue.

---

## The workflow

```
Painpoint  →  Cure  →  POC  →  Proven  →  Community Agent Library
 (anyone)   (a helper) (built) (measured)      (reusable)
```

Every stage is a page in the app, and every record carries the ontology context that
lets the next stage be automatic rather than a fresh conversation.

| Stage | What happens | Page |
|---|---|---|
| **Painpoint** | One sentence about a slow, manual or error-prone task. Scored for pain, opportunity and cross-unit reach. | Submit My PainPoints |
| **Cure** | Someone — usually from a *different* department — proposes what to build and why they are the right person. | Propose a Cure |
| **POC** | A blueprint drafted from the ontology, with acceptance criteria, repo and deploy target. | Current POC |
| **Proven** | Acceptance criteria met and measured against the original baseline. | Current Challenge Pipeline |
| **Library** | Promoted to a reusable internal agent. | Community Agent Library |

---

## Quick start

```bash
git clone git@github.com:Sherlock2019/yesaican3.git
cd yesaican3

python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

./start.sh                 # UI on http://localhost:8520, opens your browser
```

`start.sh` frees the ports, starts the API and the Streamlit UI, waits for HTTP 200 and
opens a browser. Useful overrides:

```bash
UIPORT=8600 ./start.sh      # different port
NO_BROWSER=1 ./start.sh     # CI, SSH, or a headless server
```

To run the UI alone:

```bash
PYTHONPATH="$PWD" .venv/bin/streamlit run services/ui/app.py --server.port 8520
```

### Load the demo

The app is more legible with data in it. One command seeds a complete worked example —
13 painpoints across every business unit, 23 cures, 3 cross-unit engineering projects,
15 people, and 2 published agents:

```bash
python3 scripts/seed_demo_data.py            # add
python3 scripts/seed_demo_data.py --remove   # take it back out
```

Every seeded record carries `"is_sample": true`, so `--remove` is exact and leaves real
submissions untouched. The seed runs through the same scoring, POC-drafting and
promotion functions the live app uses, so demo data cannot drift from what a real
submission produces — the script refuses to run if it would.

---

## What makes it more than a form

### Business Flow Ontology

Not an org chart. Units own **activities**, activities produce **business objects**, and
an object landing in another unit's inbox **triggers** that unit's next activity:

```
Business Unit → performs Activity → produces Business Object
              → becomes input to another BU → triggers its next Activity
```

Nine units, eight objects, eight edges model the value chain from Marketing through to
Product. Because a painpoint is captured *on an edge* rather than floating free, the app
can answer questions a ticket queue cannot: which handoffs cost the most hours, which
units are downstream of a bottleneck, and who else is affected by a problem they never
reported.

See `services/shared/business_flow.py`.

### Similarity — "would the same agent close both?"

The interesting question is not whether two painpoints *read* alike. Billing says
"invoice layout" and Finance says "reconciliation break" about work that wants the same
fix, while two unrelated problems can share plenty of words. Token overlap misses exactly
the pairs worth finding.

So each painpoint is reduced to a **four-part signature**:

| Part | Question |
|---|---|
| **Input artifact** | what arrives — a PDF, an export, a ticket, a dashboard query |
| **Transformation verb** | what is done to it — extract, convert, reconcile, route, assemble, approve, search, summarise |
| **Destination** | where the result goes — the ontology's object and consuming unit |
| **Failure mode** | what goes wrong — errors, waiting, repetition |

Scoring weights (summing to 100), then one multiplier that matters more than any of them:

| Signal | Weight |
|---|---|
| Same transformation verb | 30 |
| Same input artifact | 20 |
| Same pain type | 15 |
| Same business object / flow edge | 15 |
| Same task | 10 |
| Text overlap | 10 |

**Cross-unit match → ×1.25.** Two people in one unit with the same problem is a
*duplicate to merge*. Two different units with the same problem is a *shared fix that
ships twice*. The second is worth more, so it ranks higher rather than merely being
flagged.

Results are banded, because the advice differs:

- **≥70** — likely the same problem; merge or co-sponsor
- **45–69** — same pattern, different context; one agent could serve both
- **25–44** — worth a look

For cures the question changes from "is this the same" to "can I reuse this build", so
similarity is multiplied by **maturity**: `Draft ×0.6 · Prototype ×0.8 · Building/Testing
×0.9 · In production ×1.3`. A shipped cure at 50% beats an identical draft at 70% —
nobody wants to be pointed at someone's unstarted idea.

Deliberately excluded from similarity: submitter, region, upvotes, recency, and hours.
If impact fed similarity, every large painpoint would look similar to every other large
painpoint purely for being large. Those belong to *ranking*, applied after matching.

See `services/shared/similarity.py`.

### Where it surfaces

1. **At submit time** — "3 teams have described something like this", *before* you
   submit. The highest-value moment: it turns a duplicate into a co-sponsor.
2. **On the board** — a similarity column with jump links to every match.
3. **On the cures list** — "reuse before you rebuild".

---

## Architecture

Streamlit multipage app over plain JSON stores. No database is required to run it, and
no API call sits in the path of anything a person is typing — that matters because
drafting happens exactly when the backend is down.

```
services/
  shared/                    pure logic, no Streamlit, fully unit-tested
    pain_metrics.py          pain + opportunity scoring, pain-type lexicon, metrics
    business_flow.py         the ontology: units, objects, edges, validation
    pipeline.py              POC blueprints, stage_of(), promote_to_agent()
    similarity.py            signature, scoring, bands, maturity
    insights.py              dashboard analysis: counts, reach, cross-department
  ui/
    app.py                   home
    pages/                   one file per nav entry
    utils/
      app_shell.py           fixed sidebar + top bar, nav definition
      page_template.py       shared chrome and CSS
      meta_store.py          JSON read/write
  .sandbox_meta/             the data store (JSON)
scripts/
  seed_demo_data.py          the worked demo, reversible
tests/                       354 tests
```

The split matters: everything in `services/shared/` is importable without Streamlit and
tested directly, so the scoring and matching logic can be verified without driving a
browser.

### Data

| File | Holds |
|---|---|
| `services/.sandbox_meta/how_ai_help_submissions.json` | painpoints |
| `services/.sandbox_meta/how_ai_help_solutions.json` | cures |
| `services/.sandbox_meta/humans.json` | community profiles |
| `services/.sandbox_meta/projects.json` | cross-unit projects |
| `services/ui/data/agents.json` | the published agent library |

---

## Is there an LLM in here?

**Mostly no, and deliberately.** One optional call, everything else deterministic:

- **`_call_baseline_llm()`** in `how_can_ai_help.py` drafts the AI baseline (summary,
  workflow, risks, timeline) from a **local Ollama** instance. It probes first and gives
  up silently if nothing is listening, because a form submit must never block on a model
  load. Disable with `YESAICAN_BASELINE_LLM=0`.
- **Everything else** — pain classification, scoring, POC drafting, similarity, and the
  dashboard analysis — is lexicon and arithmetic. It is fast, reproducible, unit-testable,
  and it explains itself: every similarity score comes with the reasons that produced it.

```bash
YESAICAN_BASELINE_LLM=0        # skip the model entirely
OLLAMA_URL=http://host:11434   # default http://localhost:11434
YESAICAN_BASELINE_MODEL=phi3   # default phi3:latest
```

> The Metrics Dashboard button is labelled "Run AI Analysis" but calls
> `insights.analyse()` — counting and set arithmetic, no model. The numbers are real and
> independently audited against the raw JSON; the label overpromises.

---

## Testing

```bash
.venv/bin/python -m pytest tests -q          # 354 tests, ~1s
```

Coverage is concentrated where correctness is not obvious by reading:

| File | Tests | Covers |
|---|---|---|
| `test_similarity.py` | 44 | signatures, scoring, bands, cross-unit multiplier, maturity |
| `test_business_flow.py` | 74 | ontology integrity, edge validation, activity ownership |
| `test_pipeline.py` | 43 | blueprints, stage transitions, promotion |
| `test_insights.py` | 23 | dashboard counts, reach, cross-department |
| `test_opportunity_scoring.py` | — | pain and opportunity maths |
| `test_page_regressions.py` | — | pages import and render without Streamlit |

Two tests worth knowing about, because they encode judgements rather than mechanics:

- `test_reach_beats_raw_hours_in_the_ranking` — a problem two teams share must outrank a
  bigger one that bothers a single team. That is the entire point of the reach ranking.
- `test_no_keyword_is_a_substring_of_another_in_the_same_class` — lexicon keywords are
  matched as substrings, so `"mail"` beside `"email"` scores one word twice. This caught
  five such pairs that would otherwise have quietly skewed every score.

> Note: `pytest` with no argument also collects `scripts/test_agent_manager.py` and
> `scripts/test_hf_agent_wrapper.py`, which fail to import against current
> `huggingface_hub`. They are unrelated to the app. Run `pytest tests` .

---

## Known gaps

Stated plainly, because a README that only lists strengths is not useful:

- **Authentication is not enforced.** `auth_gate` covers a small number of pages. Access
  control belongs at a reverse proxy in front of the app; do not expose this publicly as-is.
- **JSON stores, not a database.** Fine for a lab; concurrent writes from many users are
  not safe. Moving to SQLite is the obvious next step and touches only `meta_store.py`.
- **Cure-to-cure similarity is weaker than painpoint similarity.** It leans on free-text
  overlap, and cures for genuinely different problems correctly score low. Swapping that
  one component for embeddings (`embeddinggemma` runs locally) is the natural fix — the
  structural signals should stay lexical.
- **Three legacy files do not compile** (`credit_scoring.py`, `lottery_wizard.py`, and one
  backup dashboard). They are unreachable from the nav.
- **`.git` is ~129 MB**, carrying vector stores committed before they were ignored.
- **Auto-generated painpoint titles are unreliable** for very short submissions.

---

## Contributing

The bar for a change is that it must be explainable. If you add a signal to the
similarity scorer, it needs a weight, a reason string that a person can disagree with,
and a test that fails without it.

```bash
.venv/bin/python -m pytest tests -q
```

---

*Our mission: give everyone — regardless of background — the confidence, tools, and
platform to say "YES, AI CAN BE HELPED, or HELP each other."*
