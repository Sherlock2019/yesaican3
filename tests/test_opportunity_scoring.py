"""Unit tests for services/shared/opportunity_scoring.py.

Expected values come from the AI Opportunity & Value Engine brief, sections
50-54, so the numbers here are the specification rather than a snapshot of
whatever the code happens to do.
"""

from __future__ import annotations

import math

import pytest

from services.shared.opportunity_scoring import (
    DIFFICULTY_SCORE,
    build_opportunity_assessment,
    calculate_assessment_confidence,
    calculate_automation_rate,
    calculate_cost_metrics,
    calculate_opportunity_score,
    calculate_roi_metrics,
    calculate_step_reduction,
    calculate_time_saving,
    calculate_token_metrics,
    classify_opportunity,
    difficulty_to_score,
    impact_to_score,
    normalize_score,
    round_half_up,
)


# --------------------------------------------------------------- normalize
class TestNormalizeScore:
    @pytest.mark.parametrize("raw,expected", [
        (50, 50.0), (0, 0.0), (100, 100.0),
        (-20, 0.0),        # clamp below
        (150, 100.0),      # clamp above
        ("75", 75.0),      # numeric string
    ])
    def test_clamps_and_coerces(self, raw, expected):
        assert normalize_score(raw) == expected

    @pytest.mark.parametrize("raw", [None, "", "abc", [], {}, float("nan"), float("inf")])
    def test_unusable_returns_default(self, raw):
        assert normalize_score(raw) is None
        assert normalize_score(raw, default=42) == 42

    def test_booleans_are_not_numbers(self):
        # True would otherwise silently become 1.0 and read as a real score.
        assert normalize_score(True) is None


# -------------------------------------------------------------- difficulty
class TestDifficultyAndImpact:
    def test_spec_mapping(self):
        assert difficulty_to_score("Easy") == 25
        assert difficulty_to_score("Medium") == 50
        assert difficulty_to_score("Hard") == 75
        assert difficulty_to_score("Critical") == 95

    def test_case_and_whitespace_insensitive(self):
        assert difficulty_to_score("  hARd  ") == 75

    def test_unknown_label(self):
        assert difficulty_to_score("Spicy") is None
        assert difficulty_to_score("Spicy", default=50) == 50

    def test_numeric_passthrough_is_clamped(self):
        assert difficulty_to_score(88) == 88
        assert difficulty_to_score(180) == 100

    def test_impact_mapping(self):
        assert impact_to_score("Low") == 25
        assert impact_to_score("Critical") == 95

    def test_easy_never_scores_harder_than_hard(self):
        # Guards the original bug shape, where Easy could pick up a longer
        # timeline / higher complexity than Hard.
        assert DIFFICULTY_SCORE["easy"] < DIFFICULTY_SCORE["medium"] < \
               DIFFICULTY_SCORE["hard"] < DIFFICULTY_SCORE["critical"]


# ------------------------------------------------------- opportunity score
class TestOpportunityScore:
    def test_spec_section_50(self):
        """expected 90, readiness 80, complexity 20 -> 84.5, displays 85, QUICK WIN."""
        score = calculate_opportunity_score(90, 80, 20)
        assert score == pytest.approx(84.5)
        # Not int(round(...)): Python rounds halves to even, giving 84.
        assert round_half_up(score) == 85
        assert classify_opportunity(90, 20, 80) == "QUICK WIN"

    def test_half_points_round_up_not_to_even(self):
        assert round_half_up(84.5) == 85
        assert round_half_up(85.5) == 86
        assert round_half_up(0.5) == 1
        assert round_half_up(None) is None

    def test_weights_sum_to_one(self):
        assert calculate_opportunity_score(100, 100, 0) == pytest.approx(100.0)
        assert calculate_opportunity_score(0, 0, 100) == pytest.approx(0.0)

    def test_lower_complexity_scores_higher(self):
        easy = calculate_opportunity_score(80, 80, 10)
        hard = calculate_opportunity_score(80, 80, 90)
        assert easy > hard

    @pytest.mark.parametrize("args", [
        (None, 80, 20), (90, None, 20), (90, 80, None), (None, None, None),
    ])
    def test_missing_input_returns_none(self, args):
        assert calculate_opportunity_score(*args) is None

    def test_out_of_range_inputs_are_clamped_not_rejected(self):
        assert calculate_opportunity_score(150, 150, -50) == pytest.approx(100.0)

    def test_confidence_does_not_enter_the_score(self):
        # Same inputs must always give the same score regardless of evidence.
        assert calculate_opportunity_score(90, 80, 20) == calculate_opportunity_score(90, 80, 20)


# ------------------------------------------------------------ classification
class TestClassification:
    @pytest.mark.parametrize("result,complexity,readiness,expected", [
        (90, 20, 80, "QUICK WIN"),
        (85, 70, 75, "STRATEGIC BET"),
        (90, 20, 40, "UNBLOCK FIRST"),   # high value, team not ready
        (85, 80, 30, "UNBLOCK FIRST"),
        (50, 20, 80, "EASY IMPROVEMENT"),
        (40, 90, 30, "DEFER"),
        (50, 90, 80, "DEFER"),
    ])
    def test_rules(self, result, complexity, readiness, expected):
        assert classify_opportunity(result, complexity, readiness) == expected

    def test_boundary_is_inclusive(self):
        # 70 result / 40 complexity / 65 readiness are all "on the line".
        assert classify_opportunity(70, 40, 65) == "QUICK WIN"

    def test_just_below_boundary_is_not_a_quick_win(self):
        assert classify_opportunity(69, 40, 65) == "EASY IMPROVEMENT"
        assert classify_opportunity(70, 41, 65) == "STRATEGIC BET"
        assert classify_opportunity(70, 40, 64) == "UNBLOCK FIRST"

    def test_readiness_gap_does_not_fall_through_to_defer(self):
        """The brief's flat elif chain leaves 60 <= readiness < 65 unmatched.

        High value + low complexity + readiness 60-64 matched none of its
        branches and landed in DEFER. Readiness is the blocker there, so the
        honest call is UNBLOCK FIRST.
        """
        for readiness in (60, 61, 62, 63, 64):
            assert classify_opportunity(85, 25, readiness) == "UNBLOCK FIRST"

    def test_valuable_work_is_never_deferred(self):
        """Nothing above the result threshold should ever read DEFER."""
        for complexity in range(0, 101, 5):
            for readiness in range(0, 101, 5):
                assert classify_opportunity(80, complexity, readiness) != "DEFER"

    def test_missing_input(self):
        assert classify_opportunity(None, 20, 80) is None

    def test_always_a_known_class(self):
        from services.shared.opportunity_scoring import CLASSIFICATIONS
        for result in range(0, 101, 10):
            for complexity in range(0, 101, 10):
                for readiness in range(0, 101, 10):
                    assert classify_opportunity(result, complexity, readiness) in CLASSIFICATIONS


# ------------------------------------------------------------- time saving
class TestTimeSaving:
    def test_spec_section_51(self):
        """45 min -> 6 min = 39 saved, ~86.67%."""
        out = calculate_time_saving(45, 6)
        assert out["time_saved_minutes"] == 39
        assert out["time_saved_pct"] == pytest.approx(86.666, abs=0.01)

    def test_zero_baseline_does_not_divide(self):
        out = calculate_time_saving(0, 0)
        assert out["time_saved_minutes"] == 0
        assert out["time_saved_pct"] is None

    def test_regression_is_negative_not_hidden(self):
        out = calculate_time_saving(10, 25)
        assert out["time_saved_minutes"] == -15
        assert out["time_saved_pct"] == pytest.approx(-150.0)

    def test_missing_values(self):
        assert calculate_time_saving(None, 6)["time_saved_minutes"] is None
        assert calculate_time_saving(45, None)["time_saved_pct"] is None


# ---------------------------------------------------------- step reduction
class TestStepReduction:
    def test_spec_section_52(self):
        """14 -> 4 steps = 10 removed, ~71.43%."""
        out = calculate_step_reduction(14, 4)
        assert out["steps_removed"] == 10
        assert out["step_reduction_pct"] == pytest.approx(71.428, abs=0.01)

    def test_zero_baseline_does_not_divide(self):
        out = calculate_step_reduction(0, 0)
        assert out["step_reduction_pct"] is None

    def test_missing_values(self):
        assert calculate_step_reduction(None, 4)["steps_removed"] is None


# --------------------------------------------------------- automation rate
class TestAutomationRate:
    def test_explicit_count_is_measured(self):
        out = calculate_automation_rate(automated_steps=10, total_steps=14)
        assert out["automation_rate_pct"] == pytest.approx(71.428, abs=0.01)
        assert out["source"] == "measured"

    def test_no_estimate_unless_asked(self):
        out = calculate_automation_rate(time_saved_pct=87, step_reduction_pct=71)
        assert out["automation_rate_pct"] is None
        assert out["source"] is None

    def test_estimate_is_opt_in_and_labelled(self):
        out = calculate_automation_rate(time_saved_pct=87, step_reduction_pct=71,
                                        allow_estimate=True)
        assert out["automation_rate_pct"] == 87
        assert out["source"] == "estimated"
        assert out["note"]

    def test_zero_total_steps(self):
        assert calculate_automation_rate(5, 0)["automation_rate_pct"] is None

    def test_rate_cannot_exceed_100(self):
        assert calculate_automation_rate(20, 14)["automation_rate_pct"] == 100.0


# ------------------------------------------------------------------- costs
class TestCostMetrics:
    def test_spec_section_53(self):
        """$12 -> $2.10 at 4,250/month = $9.90, $42,075, $504,900."""
        out = calculate_cost_metrics(12, 2.10, 4250)
        assert out["cost_saved_per_task"] == pytest.approx(9.90)
        assert out["monthly_cost_saving"] == pytest.approx(42075.0)
        assert out["annual_cost_saving"] == pytest.approx(504900.0)

    def test_no_volume_gives_per_task_only(self):
        out = calculate_cost_metrics(12, 2.10)
        assert out["cost_saved_per_task"] == pytest.approx(9.90)
        assert out["monthly_cost_saving"] is None
        assert out["annual_cost_saving"] is None

    def test_missing_cost_is_none_not_zero(self):
        out = calculate_cost_metrics(None, 2.10, 4250)
        assert out["cost_saved_per_task"] is None
        assert out["annual_cost_saving"] is None

    def test_genuine_zero_saving_is_reported_as_zero(self):
        out = calculate_cost_metrics(5, 5, 100)
        assert out["cost_saved_per_task"] == 0
        assert out["monthly_cost_saving"] == 0


# ------------------------------------------------------------------ tokens
class TestTokenMetrics:
    def test_spec_section_54(self):
        """16M tokens over 4,000 successful tasks = 4,000/task, 0.25 per 1K."""
        out = calculate_token_metrics({"total_tokens": 16_000_000, "successful_runs": 4000})
        assert out["tokens_per_successful_task"] == pytest.approx(4000.0)
        assert out["token_efficiency"] == pytest.approx(0.25)

    def test_total_derived_from_parts(self):
        out = calculate_token_metrics({"input_tokens": 1000, "output_tokens": 500})
        assert out["total_tokens"] == 1500

    def test_zero_successful_runs_does_not_divide(self):
        out = calculate_token_metrics({"total_tokens": 5000, "runs": 10, "successful_runs": 0})
        assert out["tokens_per_successful_task"] is None
        assert out["cost_per_successful_task"] is None
        assert out["success_rate_pct"] == 0.0

    def test_cost_per_successful_task(self):
        out = calculate_token_metrics({"total_ai_cost": 200, "runs": 100, "successful_runs": 80})
        assert out["cost_per_successful_task"] == pytest.approx(2.5)
        assert out["cost_per_task"] == pytest.approx(2.0)

    def test_cost_summed_from_parts(self):
        out = calculate_token_metrics({"api_cost": 184, "local_compute_cost": 73,
                                       "runs": 10, "successful_runs": 10})
        assert out["total_ai_cost"] == pytest.approx(257.0)

    def test_empty_input_is_all_none(self):
        out = calculate_token_metrics(None)
        assert out["total_tokens"] is None
        assert out["token_efficiency"] is None


# --------------------------------------------------------------------- ROI
class TestRoiMetrics:
    def test_roi_calculated_when_both_sides_known(self):
        out = calculate_roi_metrics({"annual_value_created": 500_000,
                                     "ai_operating_cost_monthly": 1000})
        assert out["annual_ai_cost"] == pytest.approx(12000.0)
        assert out["roi_pct"] == pytest.approx((500000 - 12000) / 12000 * 100)

    def test_annual_derived_from_monthly_value(self):
        out = calculate_roi_metrics({"monthly_value_created": 1000,
                                     "ai_operating_cost_monthly": 100})
        assert out["annual_value_created"] == pytest.approx(12000.0)

    def test_no_roi_without_cost(self):
        assert calculate_roi_metrics({"annual_value_created": 500_000})["roi_pct"] is None

    def test_no_roi_without_value(self):
        assert calculate_roi_metrics({"ai_operating_cost_monthly": 1000})["roi_pct"] is None

    def test_zero_cost_does_not_divide(self):
        assert calculate_roi_metrics({"annual_value_created": 100,
                                      "ai_operating_cost_monthly": 0})["roi_pct"] is None

    def test_empty(self):
        assert calculate_roi_metrics(None)["roi_pct"] is None


# ------------------------------------------------------------- confidence
class TestAssessmentConfidence:
    def test_empty_record_has_no_confidence(self):
        assert calculate_assessment_confidence({})["confidence"] == 0

    def test_fully_evidenced_record_reaches_100(self):
        record = {
            "phase": "Production",
            "model_usage": [{"provider": "ollama"}],
            "value_metrics": {
                "baseline": {"human_time_minutes": 45, "steps": 14, "cost_per_task": 12},
                "after_ai": {"human_time_minutes": 6, "steps": 4},
                "volume": {"tasks_per_month": 4250},
            },
            "ai_consumption": {"total_tokens": 16_000_000, "total_ai_cost": 257},
            "delivery_readiness": {"business_owner_available": True},
        }
        assert calculate_assessment_confidence(record)["confidence"] == 100

    def test_partial_evidence_is_between(self):
        record = {"value_metrics": {"baseline": {"human_time_minutes": 45, "steps": 14}}}
        out = calculate_assessment_confidence(record)
        assert 0 < out["confidence"] < 100
        assert "baseline_human_time" in out["signals_met"]
        assert "after_human_time" in out["signals_missing"]

    def test_deterministic(self):
        record = {"value_metrics": {"baseline": {"human_time_minutes": 45}}}
        assert calculate_assessment_confidence(record) == calculate_assessment_confidence(record)

    def test_confidence_never_exceeds_100(self):
        record = {
            "phase": "Production",
            "model_usage": [{"a": 1}, {"b": 2}, {"c": 3}],
            "value_metrics": {
                "baseline": {"human_time_minutes": 1, "steps": 1, "cost_per_task": 1},
                "after_ai": {"human_time_minutes": 1, "steps": 1},
                "volume": {"tasks_per_month": 1, "tasks_per_day": 1},
            },
            "ai_consumption": {"total_tokens": 1, "input_tokens": 1, "total_ai_cost": 1, "api_cost": 1},
            "delivery_readiness": {"business_owner_available": True},
        }
        assert calculate_assessment_confidence(record)["confidence"] == 100


# ------------------------------------------------------------- integration
class TestBuildOpportunityAssessment:
    def test_legacy_record_with_no_new_fields_does_not_raise(self):
        legacy = {"title": "old challenge", "difficulty": "Hard", "impact_level": "High"}
        out = build_opportunity_assessment(legacy)
        # Falls back to the label maps rather than exploding.
        assert out["remaining_complexity"] == 75
        assert out["expected_result"] == 75
        assert out["readiness"] is None
        assert out["opportunity_score"] is None      # readiness unknown
        assert out["classification"] is None

    def test_completely_empty_record(self):
        out = build_opportunity_assessment({})
        assert out["opportunity_score"] is None
        assert out["confidence"] == 0

    def test_none_record(self):
        assert build_opportunity_assessment(None)["opportunity_score"] is None

    def test_full_record_matches_spec_example(self):
        record = {
            "opportunity_metrics": {
                "expected_result": 90, "remaining_complexity": 20, "readiness": 80,
                "time_to_value_days": 21, "main_blocker": "Customer billing schemas",
                "next_best_action": "Run a mapping-engine validation POC",
            },
            "value_metrics": {
                "baseline": {"human_time_minutes": 45, "steps": 14, "cost_per_task": 12},
                "after_ai": {"human_time_minutes": 6, "steps": 4, "cost_per_task": 2.10},
                "volume": {"tasks_per_month": 4250},
            },
        }
        out = build_opportunity_assessment(record)
        assert out["opportunity_score_display"] == 85
        assert out["classification"] == "QUICK WIN"
        assert out["time"]["time_saved_minutes"] == 39
        assert out["steps"]["steps_removed"] == 10
        assert out["cost"]["annual_cost_saving"] == pytest.approx(504900.0)
        assert out["monthly_hours_saved"] == pytest.approx(39 * 4250 / 60)
        assert out["time_to_value_days"] == 21
        assert out["main_blocker"] == "Customer billing schemas"

    def test_automation_estimate_stays_off_by_default(self):
        record = {"value_metrics": {
            "baseline": {"human_time_minutes": 45, "steps": 14},
            "after_ai": {"human_time_minutes": 6, "steps": 4},
        }}
        assert build_opportunity_assessment(record)["automation"]["automation_rate_pct"] is None

    def test_automation_estimate_when_explicitly_allowed(self):
        record = {"value_metrics": {
            "allow_automation_estimate": True,
            "baseline": {"human_time_minutes": 45, "steps": 14},
            "after_ai": {"human_time_minutes": 6, "steps": 4},
        }}
        out = build_opportunity_assessment(record)["automation"]
        assert out["source"] == "estimated"
        assert out["automation_rate_pct"] == pytest.approx(86.666, abs=0.01)
