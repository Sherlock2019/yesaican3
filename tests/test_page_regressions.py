"""Regression tests against the real page functions.

These exercise the actual code paths users hit — conversion and upvoting — so
the fixes cannot silently regress the way they did before.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import _stub_streamlit as stub

stub.install()

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def how_can_ai_help():
    return stub.load_page("hcah_page", str(ROOT / "services/ui/pages/how_can_ai_help.py"))


@pytest.fixture(scope="module")
def project_hub():
    return stub.load_page("project_hub_page", str(ROOT / "services/ui/pages/project_hub.py"))


def _scored_submission() -> dict:
    return {
        "id": "challenge_test_1",
        "title": "Custom Billing Conversion",
        "description": "Every month I manually convert billing files.",
        "category": "Billing",
        "difficulty": "Medium",
        "submitter": {"name": "Tester", "department": "Billing", "region": "World"},
        "upvotes": 3,
        "comments": 1,
        "urgency": 7.5,
        "impact_score": 8.6,
        "pain_type": "billing",
        "baseline": {"steps": 14, "minutes_per_task": 45, "annual_hours": 2250.0, "level": "HIGH"},
        "opportunity": {"score": 78, "classification": "QUICK WIN", "complexity": 36},
        "outcomes": ["save_time", "fewer_steps"],
        "metrics": [{"key": "time_per_task", "label": "Human time / task",
                     "before": "45 min", "target": "<9 min", "actual": "—"}],
        "current_workflow": ["Receive request", "Download file", "Reformat"],
        "workflow_source": "llm",
        "similar_agents": [],
        "ai_baseline": {"summary": "plan", "generated_by": "llm"},
    }


CARRIED = ("pain_type", "baseline", "opportunity", "outcomes", "metrics",
           "current_workflow", "workflow_source", "ai_baseline")


class TestConversionKeepsOpportunityData:
    """The bug: both conversion paths dropped everything the intake measured."""

    def test_how_can_ai_help_conversion(self, how_can_ai_help, monkeypatch):
        saved: list[list[dict]] = []
        monkeypatch.setattr(how_can_ai_help, "load_projects", lambda: [])
        monkeypatch.setattr(how_can_ai_help, "save_projects", lambda records: saved.append(records))

        how_can_ai_help.convert_to_project(_scored_submission())

        assert saved, "conversion did not persist a project"
        project = saved[0][0]
        for key in CARRIED:
            assert key in project, f"{key} lost during how_can_ai_help conversion"
        assert project["baseline"]["annual_hours"] == 2250.0
        assert project["opportunity"]["classification"] == "QUICK WIN"
        assert len(project["current_workflow"]) == 3

    def test_project_hub_conversion(self, project_hub, monkeypatch):
        submission = _scored_submission()
        saved: list[list[dict]] = []
        monkeypatch.setattr(project_hub, "load_projects", lambda: [])
        monkeypatch.setattr(project_hub, "save_projects", lambda records: saved.append(records))
        monkeypatch.setattr(project_hub, "find_submission_record",
                            lambda sid, fallback_title=None: submission)

        ok, message, project = project_hub.convert_submission_to_project(
            submission["id"], {"title": submission["title"]})

        assert ok, message
        for key in CARRIED:
            assert key in project, f"{key} lost during project_hub conversion"
        assert project["baseline"]["annual_hours"] == 2250.0
        assert project["opportunity"]["score"] == 78

    def test_conversion_does_not_mutate_the_source_challenge(self, how_can_ai_help, monkeypatch):
        submission = _scored_submission()
        saved: list[list[dict]] = []
        monkeypatch.setattr(how_can_ai_help, "load_projects", lambda: [])
        monkeypatch.setattr(how_can_ai_help, "save_projects", lambda records: saved.append(records))

        how_can_ai_help.convert_to_project(submission)
        saved[0][0]["baseline"]["annual_hours"] = 1.0

        assert submission["baseline"]["annual_hours"] == 2250.0

    def test_legacy_challenge_without_new_fields_still_converts(self, how_can_ai_help, monkeypatch):
        legacy = {"id": "old_1", "title": "Old challenge", "description": "text",
                  "category": "Support", "submitter": {"name": "Someone"},
                  "upvotes": 0, "comments": 0}
        saved: list[list[dict]] = []
        monkeypatch.setattr(how_can_ai_help, "load_projects", lambda: [])
        monkeypatch.setattr(how_can_ai_help, "save_projects", lambda records: saved.append(records))

        how_can_ai_help.convert_to_project(legacy)

        project = saved[0][0]
        assert project["title"] == "Old challenge"
        assert "baseline" not in project  # nothing invented


class TestUpvoteDoesNotTouchUrgency:
    """The bug: an upvote silently raised a business-priority field."""

    def test_urgency_is_unchanged(self, how_can_ai_help, monkeypatch):
        monkeypatch.setattr(how_can_ai_help, "save_submissions", lambda records: None)
        submission = {"upvotes": 4, "urgency": 7.5}

        how_can_ai_help.upvote_submission(submission, [submission])

        assert submission["urgency"] == 7.5, "upvote must not modify urgency"
        assert submission["upvotes"] == 5

    def test_community_interest_is_tracked_separately(self, how_can_ai_help, monkeypatch):
        monkeypatch.setattr(how_can_ai_help, "save_submissions", lambda records: None)
        submission = {"upvotes": 0, "urgency": 6.0}

        for _ in range(3):
            how_can_ai_help.upvote_submission(submission, [submission])

        assert submission["community_interest"] == 3
        assert submission["urgency"] == 6.0

    def test_submission_without_urgency_gains_no_urgency(self, how_can_ai_help, monkeypatch):
        monkeypatch.setattr(how_can_ai_help, "save_submissions", lambda records: None)
        submission: dict = {}

        how_can_ai_help.upvote_submission(submission, [submission])

        assert "urgency" not in submission
        assert submission["community_interest"] == 1


class TestSubmitWithoutAnalyzing:
    """Submitting straight away used to raise instead of saving.

    _pp_save calls _pp_analyze when the form was never analyzed, which drafts a
    workflow into the numbered step cells — and Streamlit refuses assignment to
    a widget-backed key once that widget has been drawn. Both the draft and the
    post-save reset are now staged and applied by _pp_state on the next run.
    """

    def test_filling_step_cells_only_stages_them(self, how_can_ai_help):
        state = how_can_ai_help.st.session_state
        state.clear()
        how_can_ai_help._fill_step_cells(["Receive file", "Open template"])
        assert state["pp_workflow"] == ["Receive file", "Open template"]
        assert state["pp_workflow_pending"] == ["Receive file", "Open template"]
        # Writing the cell directly is what used to raise.
        assert "pp_wf_0" not in state

    def test_reset_is_deferred_rather_than_applied(self, how_can_ai_help):
        state = how_can_ai_help.st.session_state
        state.clear()
        state["pp_bu"] = "Sales"
        how_can_ai_help._pp_reset()
        assert state["pp_reset_pending"] is True
        assert state["pp_bu"] == "Sales"

    def test_the_row_counters_are_not_treated_as_cells(self, how_can_ai_help):
        # pp_point_rows shares the pp_point_ prefix. Blanking it made the next
        # run raise ValueError on int("").
        assert how_can_ai_help._LIST_CELL_KEY.match("pp_point_0")
        assert how_can_ai_help._LIST_CELL_KEY.match("pp_wf_12")
        assert not how_can_ai_help._LIST_CELL_KEY.match("pp_point_rows")
        assert not how_can_ai_help._LIST_CELL_KEY.match("pp_step_rows")


class TestChallengeHubReadsSubmissions:
    """Current Challenges lists what the capture page wrote.

    It used to fetch from the API's own /challenges store, which the pain-point
    form never writes to — so a painpoint someone submitted never appeared. The
    page now reads the same two files, and these tests pin that: a wrong source
    here means submissions silently vanish rather than erroring.
    """

    @pytest.fixture
    def page(self):
        return stub.load_page(
            "challenge_hub_page", str(ROOT / "services/ui/pages/challenge_hub.py"))

    def test_reads_the_same_files_the_capture_page_writes(self, page):
        assert page.SUBMISSIONS_FILE == "how_ai_help_submissions.json"
        assert page.SOLUTIONS_FILE == "how_ai_help_solutions.json"

    def test_does_not_depend_on_the_api(self, page):
        # No base URL at all: the table must render with the API stopped.
        assert not hasattr(page, "API_BASE_URL")

    def test_an_unclaimed_painpoint_reads_as_open(self, page):
        assert page._stage([]) == ("open", "Open — needs a helper")

    def test_a_claimed_painpoint_names_its_status(self, page):
        css, label = page._stage([{"status": "Prototype"}])
        assert css == "taken"
        assert "Prototype" in label

    def test_production_outranks_a_draft_on_the_same_challenge(self, page):
        css, label = page._stage([{"status": "Draft"}, {"status": "In production"}])
        assert (css, label) == ("done", "In production")
