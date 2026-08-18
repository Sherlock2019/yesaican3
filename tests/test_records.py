"""Tests for services/shared/records.py — the conversion data-loss fix."""

from __future__ import annotations

import pytest

from services.shared.records import (
    OPPORTUNITY_CARRY_FIELDS,
    carry_opportunity_fields,
    normalize_challenge_record,
    normalize_project_record,
)


def _scored_challenge() -> dict:
    """A challenge as the intake wizard writes it."""
    return {
        "id": "challenge_1",
        "title": "Custom Billing Conversion",
        "description": "Every month I manually convert billing files.",
        "pain_type": "billing",
        "baseline": {"steps": 14, "minutes_per_task": 45, "annual_hours": 2250.0, "level": "HIGH"},
        "opportunity": {"score": 78, "classification": "QUICK WIN", "complexity": 36},
        "outcomes": ["save_time", "fewer_steps"],
        "metrics": [{"key": "time_per_task", "before": "45 min", "target": "<9 min"}],
        "current_workflow": ["Receive request", "Download file"],
        "workflow_source": "llm",
        "similar_agents": ["IT Troubleshooter Agent"],
        "ai_baseline": {"summary": "plan", "generated_by": "llm"},
    }


class TestCarryOpportunityFields:
    def test_every_capture_field_survives(self):
        source = _scored_challenge()
        target = {"title": source["title"], "status": "Incubation"}
        carry_opportunity_fields(source, target)
        for key in ("pain_type", "baseline", "opportunity", "outcomes", "metrics",
                    "current_workflow", "workflow_source", "similar_agents", "ai_baseline"):
            assert key in target, f"{key} was dropped during conversion"
        assert target["baseline"]["annual_hours"] == 2250.0
        assert target["opportunity"]["classification"] == "QUICK WIN"

    def test_does_not_clobber_the_target_prose(self):
        target = {"title": "Renamed by the project owner", "status": "MVP"}
        carry_opportunity_fields(_scored_challenge(), target)
        assert target["title"] == "Renamed by the project owner"
        assert target["status"] == "MVP"

    def test_deep_copied_so_edits_do_not_leak_back(self):
        source = _scored_challenge()
        target: dict = {}
        carry_opportunity_fields(source, target)
        target["baseline"]["annual_hours"] = 1.0
        target["outcomes"].append("mutated")
        assert source["baseline"]["annual_hours"] == 2250.0
        assert "mutated" not in source["outcomes"]

    def test_empty_values_are_not_carried_over_real_ones(self):
        source = {"baseline": None, "outcomes": [], "opportunity": {}}
        target = {"baseline": {"annual_hours": 10}}
        carry_opportunity_fields(source, target)
        assert target["baseline"] == {"annual_hours": 10}
        assert "outcomes" not in target

    def test_existing_target_value_wins_unless_overwrite(self):
        source = {"pain_type": "billing"}
        target = {"pain_type": "support"}
        carry_opportunity_fields(source, target)
        assert target["pain_type"] == "support"
        carry_opportunity_fields(source, target, overwrite=True)
        assert target["pain_type"] == "billing"

    def test_legacy_record_without_any_new_fields(self):
        legacy = {"title": "old", "description": "old", "difficulty": "Hard"}
        target = {"title": "old"}
        carry_opportunity_fields(legacy, target)
        assert target == {"title": "old"}   # nothing invented

    def test_none_source_is_safe(self):
        assert carry_opportunity_fields(None, {"a": 1}) == {"a": 1}
        assert carry_opportunity_fields(None) == {}

    def test_returns_a_new_dict_when_no_target_given(self):
        out = carry_opportunity_fields(_scored_challenge())
        assert out["pain_type"] == "billing"

    def test_carry_list_has_no_duplicates(self):
        assert len(OPPORTUNITY_CARRY_FIELDS) == len(set(OPPORTUNITY_CARRY_FIELDS))


class TestNormalizeRecords:
    def test_challenge_defaults_fill_in(self):
        out = normalize_challenge_record({"title": "x"})
        assert out["upvotes"] == 0
        assert out["community_interest"] == 0
        assert out["opportunity_metrics"] == {}
        assert out["metrics"] == []

    def test_project_defaults_fill_in(self):
        out = normalize_project_record({"title": "x"})
        assert out["status"] == "Incubation"
        assert out["model_usage"] == []
        assert out["ai_consumption"] == {}

    def test_existing_values_are_preserved(self):
        out = normalize_project_record({"status": "Production", "stars": 9})
        assert out["status"] == "Production"
        assert out["stars"] == 9

    def test_source_record_is_never_mutated(self):
        original = {"title": "x"}
        normalize_challenge_record(original)
        assert original == {"title": "x"}, "normalization must not write back to the source"

    def test_none_is_safe(self):
        assert normalize_challenge_record(None)["title"] == ""
        assert normalize_project_record(None)["status"] == "Incubation"

    def test_defaults_are_not_shared_between_calls(self):
        first = normalize_project_record({})
        second = normalize_project_record({})
        first["model_usage"].append("x")
        assert second["model_usage"] == []
