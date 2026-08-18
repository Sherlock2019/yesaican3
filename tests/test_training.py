"""Production readiness is derived from facts, not declared."""

from __future__ import annotations

import pytest

from services.shared import training


def _record(**overrides):
    base = {
        "agent_id": "poc_1",
        "owner": "Marta Lindqvist",
        "trainers": ["Gerry Osei"],
        "rounds": [{"date": "2026-08-01", "trainer": "Gerry Osei",
                    "kind": training.TRAINING_KINDS[0], "items": 40, "accuracy": 94}],
    }
    base.update(overrides)
    return base


def _poc(met=True):
    return {"acceptance": [{"met": met}, {"met": met}]}


class TestAccuracy:
    def test_reads_the_latest_measured_round(self):
        record = _record(rounds=[
            {"date": "2026-08-01", "accuracy": 70},
            {"date": "2026-08-09", "accuracy": 93},
        ])
        assert training.measured_accuracy(record) == 93

    def test_a_round_without_a_measurement_is_skipped_not_counted_as_zero(self):
        # Somebody supplying examples without re-measuring is not evidence the
        # agent got worse.
        record = _record(rounds=[
            {"date": "2026-08-01", "accuracy": 93},
            {"date": "2026-08-09", "accuracy": None},
        ])
        assert training.measured_accuracy(record) == 93

    def test_no_rounds_means_no_measurement(self):
        assert training.measured_accuracy(_record(rounds=[])) is None

    def test_a_junk_accuracy_value_does_not_raise(self):
        assert training.measured_accuracy(_record(rounds=[{"date": "x", "accuracy": "n/a"}])) is None

    def test_latest_round_is_by_date_not_list_order(self):
        record = _record(rounds=[{"date": "2026-08-09", "items": 2},
                                 {"date": "2026-08-01", "items": 1}])
        assert training.latest_round(record)["items"] == 2


class TestReadiness:
    def test_all_five_gates_pass(self):
        result = training.readiness(_record(), _poc(met=True))
        assert result["gates_met"] == 5
        assert result["score"] == 100.0
        assert result["band"] == "ready"
        assert result["blockers"] == []

    def test_a_missing_owner_blocks_and_is_named(self):
        result = training.readiness(_record(owner=""), _poc(met=True))
        assert result["band"] != "ready"
        assert "Has an owner" in result["blockers"]

    def test_accuracy_below_the_bar_blocks(self):
        record = _record(rounds=[{"date": "2026-08-01", "accuracy": 71}])
        result = training.readiness(record, _poc(met=True))
        assert "Measured accuracy meets the bar" in result["blockers"]
        assert "71% against a 90% bar" in dict(
            (g["key"], g["detail"]) for g in result["gates"])["accuracy"]

    def test_the_bar_is_configurable(self):
        record = _record(rounds=[{"date": "2026-08-01", "accuracy": 80}])
        assert training.readiness(record, _poc(), accuracy_target=75.0)["band"] == "ready"

    def test_failing_acceptance_criteria_block(self):
        assert "POC acceptance criteria pass" in training.readiness(
            _record(), _poc(met=False))["blockers"]

    def test_no_poc_at_all_cannot_claim_acceptance(self):
        # Absence of criteria is not the same as passing them.
        result = training.readiness(_record(), None)
        assert "POC acceptance criteria pass" in result["blockers"]
        assert result["band"] != "ready"

    def test_an_empty_record_is_not_an_error(self):
        result = training.readiness({}, None)
        assert result["score"] == 0.0
        assert result["band"] == "early"
        assert len(result["blockers"]) == 5

    def test_blank_trainer_names_do_not_count(self):
        result = training.readiness(_record(trainers=["", "   "]), _poc())
        assert "Has at least one trainer" in result["blockers"]

    @pytest.mark.parametrize("met,expected", [(5, "ready"), (3, "training"), (1, "early")])
    def test_bands(self, met, expected):
        record = _record(
            owner="Marta" if met >= 1 else "",
            trainers=["Gerry"] if met >= 2 else [],
            rounds=([{"date": "2026-08-01", "accuracy": 94 if met >= 4 else 10}]
                    if met >= 3 else []),
        )
        assert training.readiness(record, _poc(met=met >= 5))["band"] == expected


class TestSuggestTrainers:
    HUMANS = [
        {"name": "Gerry Osei", "department": "Billing"},
        {"name": "Marta Lindqvist", "department": "Finance"},
        {"name": "Ada Lopez", "department": "Billing"},
    ]

    def test_the_person_who_reported_it_leads(self):
        rows = training.suggest_trainers("Billing", "Ada Lopez", self.HUMANS)
        assert rows[0]["name"] == "Ada Lopez"
        assert "reported the painpoint" in rows[0]["why"]

    def test_then_everyone_else_in_that_unit(self):
        names = [r["name"] for r in training.suggest_trainers("Billing", "Ada Lopez", self.HUMANS)]
        assert "Gerry Osei" in names
        assert "Marta Lindqvist" not in names

    def test_nobody_is_listed_twice(self):
        names = [r["name"] for r in training.suggest_trainers("Billing", "Gerry Osei", self.HUMANS)]
        assert len(names) == len(set(names))

    def test_a_submitter_with_no_profile_is_still_suggested(self):
        rows = training.suggest_trainers("Billing", "Unknown Person", self.HUMANS)
        assert rows[0]["name"] == "Unknown Person"

    def test_respects_the_limit(self):
        assert len(training.suggest_trainers("Billing", "Ada Lopez", self.HUMANS, limit=1)) == 1

    def test_no_unit_and_no_submitter_gives_nothing(self):
        assert training.suggest_trainers("", "", self.HUMANS) == []
