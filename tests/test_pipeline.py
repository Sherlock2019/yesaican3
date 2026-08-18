"""The pain point -> POC -> proven -> agent pipeline."""

from __future__ import annotations

import pytest

from services.shared.pain_metrics import PAIN_TYPES
from services.shared.pipeline import (
    ONTOLOGY_BLUEPRINTS,
    PROVEN_THRESHOLD,
    STAGE_KEYS,
    draft_poc,
    pipeline_counts,
    pipeline_rows,
    poc_progress,
    promote_to_agent,
    stage_of,
)


def _challenge(**overrides):
    base = {
        "id": "challenge_1",
        "title": "Sync RAX billing with customer billing format",
        "pain_type": "billing",
        "category": "Billing",
        "baseline": {"steps": 14, "minutes": 45, "annual_hours": 2250},
        "opportunity": {"score": 89, "complexity": 38, "classification": "QUICK WIN"},
        "current_workflow": ["Receive file", "Open template", "Copy info",
                             "Convert formats", "Convert currency", "Send invoice"],
        "metrics": [
            {"key": "time_per_task", "label": "Time per task", "unit": "min",
             "before": 45, "target": 8, "better": "lower"},
        ],
        "similar_agents": [],
    }
    base.update(overrides)
    return base


class TestOntologyBlueprints:
    def test_every_pain_type_has_a_blueprint(self):
        # A missing blueprint silently falls back to "repetitive", which would
        # quietly hand a billing problem the wrong pattern and tools.
        assert set(PAIN_TYPES) == set(ONTOLOGY_BLUEPRINTS)

    @pytest.mark.parametrize("pain_type", sorted(ONTOLOGY_BLUEPRINTS))
    def test_blueprint_is_complete(self, pain_type):
        blueprint = ONTOLOGY_BLUEPRINTS[pain_type]
        for field in ("objects", "pattern", "capabilities", "tools", "guardrail",
                      "sector", "industry"):
            assert blueprint.get(field), f"{pain_type} is missing {field}"

    @pytest.mark.parametrize("pain_type", sorted(ONTOLOGY_BLUEPRINTS))
    def test_every_pain_type_drafts_a_usable_poc(self, pain_type):
        poc = draft_poc(_challenge(pain_type=pain_type))
        assert poc["pattern"] and poc["objects"] and poc["build_steps"]
        assert poc["effort_days"] >= 2


class TestDraftPoc:
    def test_is_deterministic(self):
        challenge = _challenge()
        first, second = draft_poc(challenge), draft_poc(challenge)
        first.pop("created_at")
        second.pop("created_at")
        assert first == second

    def test_does_not_mutate_the_challenge(self):
        challenge = _challenge()
        before = dict(challenge)
        draft_poc(challenge)
        assert challenge == before

    def test_build_plan_covers_the_whole_workflow(self):
        # A fixed-span split dropped the tail, and the end of a process (send
        # it, file it) is the part people most want taken off them.
        challenge = _challenge()
        plan = " ".join(draft_poc(challenge)["build_steps"])
        for step in challenge["current_workflow"]:
            assert step in plan

    def test_acceptance_comes_from_the_submitters_metrics(self):
        poc = draft_poc(_challenge())
        labels = [c["label"] for c in poc["acceptance"]]
        assert "Time per task" in labels
        assert "Human review path works" in labels

    def test_acceptance_falls_back_when_no_metrics_chosen(self):
        poc = draft_poc(_challenge(metrics=[]))
        assert len(poc["acceptance"]) >= 2

    def test_reuse_reduces_effort(self):
        alone = draft_poc(_challenge())["effort_days"]
        reusing = draft_poc(_challenge(similar_agents=["Billing Formatter"]))["effort_days"]
        assert reusing < alone


class TestStages:
    def test_walks_forward_one_stage_at_a_time(self):
        challenge = _challenge()
        assert stage_of(challenge) == "captured"

        challenge["poc"] = draft_poc(challenge)
        assert stage_of(challenge) == "poc"

        for criterion in challenge["poc"]["acceptance"]:
            criterion["met"] = True
        assert stage_of(challenge) == "proven"

        challenge["published_agent"] = "Normalise — Billing Agent"
        assert stage_of(challenge) == "published"

    def test_partial_acceptance_is_not_proven(self):
        challenge = _challenge()
        challenge["poc"] = draft_poc(challenge)
        challenge["poc"]["acceptance"][0]["met"] = True
        met, total = poc_progress(challenge["poc"])
        assert met / total < PROVEN_THRESHOLD
        assert stage_of(challenge) == "poc"

    def test_every_stage_is_a_known_key(self):
        challenge = _challenge()
        assert stage_of(challenge) in STAGE_KEYS


class TestPromotion:
    def test_agent_record_carries_its_origin(self):
        challenge = _challenge()
        poc = draft_poc(challenge)
        agent = promote_to_agent(challenge, poc)
        assert agent["origin_challenge"] == challenge["id"]
        assert agent["origin_title"] == challenge["title"]
        assert agent["status"] == "Available"

    def test_agent_lands_in_the_blueprints_part_of_the_library(self):
        agent = promote_to_agent(_challenge(pain_type="support"))
        assert agent["sector"] == ONTOLOGY_BLUEPRINTS["support"]["sector"]
        assert agent["industry"] == ONTOLOGY_BLUEPRINTS["support"]["industry"]

    def test_description_reports_the_hours_freed(self):
        agent = promote_to_agent(_challenge())
        assert "2,250" in agent["description"]

    def test_promotion_works_without_a_drafted_poc(self):
        # Publishing straight from a captured record should still produce a
        # complete library entry rather than a half-populated one.
        agent = promote_to_agent(_challenge())
        assert agent["agent"] and agent["capabilities"] and agent["tools"]


class TestTwinContext:
    """Business unit, task, input and downstream, captured at intake."""

    def _with_context(self, **ctx):
        base = {"business_unit": "Sales & Marketing", "task": "Reformat customer billing",
                "input": "Customer billing file", "input_from": "Customer Success",
                "output_to": "Product & Solutions",
                "output_flow": "Customer briefings → challenge charters"}
        base.update(ctx)
        return _challenge(twin_context=base)

    def test_poc_carries_the_integration_points(self):
        poc = draft_poc(self._with_context())
        integration = poc["integration"]
        assert integration["owner"] == "Sales & Marketing"
        assert integration["input"] == "Customer billing file"
        assert integration["output_to"] == "Product & Solutions"

    def test_downstream_becomes_an_acceptance_criterion(self):
        # If the receiving unit will not take the output, the automation is not
        # finished however good its own numbers look.
        poc = draft_poc(self._with_context())
        labels = [c["label"] for c in poc["acceptance"]]
        assert "Output accepted by Product & Solutions" in labels

    def test_no_handoff_criterion_when_the_work_ends_here(self):
        poc = draft_poc(self._with_context(output_to="Nobody — it ends here"))
        assert not any("accepted by" in c["label"] for c in poc["acceptance"])

    def test_no_handoff_criterion_without_context(self):
        poc = draft_poc(_challenge())
        assert not any("accepted by" in c["label"] for c in poc["acceptance"])

    def test_published_agent_names_the_unit_and_task(self):
        agent = promote_to_agent(self._with_context())
        assert agent["business_unit"] == "Sales & Marketing"
        assert agent["task"] == "Reformat customer billing"
        assert "Reformat customer billing" in agent["description"]
        assert "Sales & Marketing" in agent["description"]

    def test_context_survives_challenge_to_project_conversion(self):
        from services.shared.records import carry_opportunity_fields
        challenge = self._with_context()
        project = carry_opportunity_fields(challenge, {})
        assert project["twin_context"]["business_unit"] == "Sales & Marketing"


class TestTwinLookups:
    def test_every_unit_is_reachable_by_name(self):
        from services.ui.utils.ontology_flow import BUSINESS_UNITS, business_unit, business_unit_names
        names = business_unit_names()
        assert len(names) == len(BUSINESS_UNITS)
        for name in names:
            assert business_unit(name) is not None

    def test_downstream_lookup_matches_the_relationship_map(self):
        from services.ui.utils.ontology_flow import downstream_of
        rel = downstream_of("Sales & Marketing")
        assert rel and rel["target"] == "Product & Solutions"

    def test_upstream_is_the_mirror_of_downstream(self):
        from services.ui.utils.ontology_flow import downstream_of, upstream_of
        rel = downstream_of("Product & Solutions")
        assert rel
        assert upstream_of(rel["target"])["source"] == "Product & Solutions"

    def test_all_units_fanout_is_not_treated_as_a_handoff(self):
        # Security publishes to "All units"; that is a broadcast, not a queue
        # to hand a specific piece of work to.
        from services.ui.utils.ontology_flow import downstream_of
        rel = downstream_of("Security, Risk & Compliance")
        assert rel is None or rel["target"] != "All units"


class TestPocTableFields:
    """What the POC table shows: repo, features, status."""

    def test_a_fresh_poc_has_no_repo(self):
        # A POC with a repo it never had would imply work that does not exist.
        assert draft_poc(_challenge())["github"] == ""

    def test_a_fresh_poc_is_not_started(self):
        # Status tracks the build, stage tracks whether it is proven. A new
        # blueprint has a plan and nothing running.
        assert draft_poc(_challenge())["status"] == "Not started"

    def test_build_details_start_empty(self):
        poc = draft_poc(_challenge())
        for field in ("github", "platform", "demo_url", "owner", "notes"):
            assert poc[field] == "", field

    def test_rows_carry_the_build_details(self):
        challenge = _challenge()
        challenge["poc"] = draft_poc(challenge)
        challenge["poc"].update({
            "github": "yesaican/billing-normaliser",
            "platform": "Kubernetes",
            "demo_url": "https://demo.example",
            "owner": "Dzoan",
            "status": "Live",
        })
        row = pipeline_rows([challenge])[0]
        assert row["github"] == "yesaican/billing-normaliser"
        assert row["platform"] == "Kubernetes"
        assert row["demo_url"] == "https://demo.example"
        assert row["owner"] == "Dzoan"
        assert row["poc_status"] == "Live"
        assert row["capabilities"]

    def test_live_does_not_imply_proven(self):
        # A POC can be running and still fail its acceptance criteria; the two
        # must stay independent or "proven" stops meaning anything.
        challenge = _challenge()
        challenge["poc"] = draft_poc(challenge)
        challenge["poc"]["status"] = "Live"
        assert stage_of(challenge) == "poc"

    def test_rows_without_a_poc_report_empty_rather_than_missing(self):
        row = pipeline_rows([_challenge()])[0]
        assert row["github"] == ""
        assert row["platform"] == ""
        assert row["capabilities"] == []


class TestBoard:
    def test_counts_cover_every_stage(self):
        rows = [_challenge(), _challenge(id="challenge_2", published_agent="X")]
        counts = pipeline_counts(rows)
        assert set(counts) == set(STAGE_KEYS)
        assert counts["captured"] == 1
        assert counts["published"] == 1

    def test_rows_sort_by_stage_then_score(self):
        rows = pipeline_rows([
            _challenge(id="a", published_agent="X"),
            _challenge(id="b"),
        ])
        assert [row["stage"] for row in rows] == ["captured", "published"]
