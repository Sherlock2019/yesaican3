"""Dashboard analysis: counts, people, units, similarity and cross-unit reach."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from services.shared import business_flow as bf
from services.shared import insights

NOW = datetime(2026, 8, 18, tzinfo=timezone.utc)


def _painpoint(**overrides):
    base = {
        "id": "challenge_1",
        "title": "Reformat customer billing files",
        "description": "Every month I reformat customer billing files by hand.",
        "pain_type": "billing",
        "submitter": {"name": "Gerry", "department": "Billing"},
        "twin_context": {"business_unit": "Billing"},
        "baseline": {"annual_hours": 1000},
        "opportunity": {"score": 80},
        "created_at": (NOW - timedelta(days=3)).isoformat(),
    }
    base.update(overrides)
    return base


def _cure(challenge_id="challenge_1", helper="Dzoan"):
    return {"id": "solution_1", "challenge_id": challenge_id, "helper": helper}


class TestOverview:
    def test_counts_the_headline_numbers(self):
        subs = [_painpoint(), _painpoint(id="challenge_2", title="Other")]
        result = insights.overview(subs, [_cure()], [], now=NOW)
        assert result["painpoints_total"] == 2
        assert result["painpoints_solved"] == 1
        assert result["painpoints_open"] == 1
        assert result["cures_proposed"] == 1

    def test_new_uses_the_window_not_everything(self):
        old = _painpoint(id="old", created_at=(NOW - timedelta(days=200)).isoformat())
        result = insights.overview([_painpoint(), old], [], [], now=NOW)
        assert result["painpoints_total"] == 2
        assert result["painpoints_new"] == 1

    def test_a_record_with_no_timestamp_is_not_counted_as_new(self):
        # Older records predate created_at; calling them new would make the
        # "new this month" number climb every time somebody looked at it.
        result = insights.overview([_painpoint(created_at="")], [], [], now=NOW)
        assert result["painpoints_new"] == 0
        assert result["painpoints_total"] == 1

    def test_poc_counts_split_drafted_from_proven(self):
        drafted = _painpoint(id="a", poc={"acceptance": [{"met": False}]})
        proven = _painpoint(id="b", poc={"acceptance": [{"met": True}, {"met": True}]})
        result = insights.overview([drafted, proven], [], [], now=NOW)
        assert result["pocs_current"] == 2
        assert result["pocs_proven"] == 1

    def test_production_library_counts_agents_from_painpoints(self):
        agents = [{"agent": "X", "origin_challenge": "challenge_1"}, {"agent": "Stock"}]
        result = insights.overview([_painpoint()], [], agents, now=NOW)
        assert result["in_production_library"] == 1
        assert result["agents_total"] == 2

    def test_hours_addressed_only_counts_solved(self):
        subs = [_painpoint(), _painpoint(id="challenge_2", baseline={"annual_hours": 500})]
        result = insights.overview(subs, [_cure()], [], now=NOW)
        assert result["hours_on_the_board"] == 1500
        assert result["hours_addressed"] == 1000


class TestPeople:
    def test_ranks_by_submissions_plus_cures(self):
        subs = [_painpoint(), _painpoint(id="c2", submitter={"name": "Ben"})]
        rows = insights.most_active_people(subs, [_cure(helper="Ben"), _cure(helper="Ben")])
        assert rows[0]["name"] == "Ben"
        assert rows[0]["submitted"] == 1 and rows[0]["cures"] == 2

    def test_anonymous_is_not_a_person(self):
        rows = insights.most_active_people([_painpoint(submitter={"name": "Anonymous"})], [])
        assert rows == []

    def test_a_helper_who_never_submitted_still_appears(self):
        rows = insights.most_active_people([], [_cure(helper="Mia")])
        assert [r["name"] for r in rows] == ["Mia"]


class TestUnits:
    def test_ranks_units_by_painpoint_count(self):
        subs = [
            _painpoint(),
            _painpoint(id="c2", twin_context={"business_unit": "Sales"}),
            _painpoint(id="c3", twin_context={"business_unit": "Sales"}),
        ]
        rows = insights.by_business_unit(subs)
        assert rows[0]["unit"] == "Sales"
        assert rows[0]["painpoints"] == 2

    def test_falls_back_to_the_submitters_department(self):
        # Everything submitted before twin_context existed would otherwise
        # vanish from every per-unit count.
        legacy = _painpoint(twin_context={}, submitter={"name": "Ben", "department": "Support"})
        rows = insights.by_business_unit([legacy])
        assert rows[0]["unit"] == "Support"

    def test_no_unit_at_all_is_reported_not_dropped(self):
        rows = insights.by_business_unit([_painpoint(twin_context={}, submitter={})])
        assert rows[0]["unit"] == "Unassigned"


class TestSimilarity:
    def test_finds_two_painpoints_describing_the_same_job(self):
        a = _painpoint(id="a", title="Reformat customer billing files",
                       description="reformat customer billing files by hand each month")
        b = _painpoint(id="b", title="Customer billing files reformatting",
                       description="reformat the customer billing files manually")
        pairs = insights.similar_pairs([a, b])
        assert pairs and pairs[0]["score"] > 0.18

    def test_unrelated_painpoints_do_not_pair(self):
        a = _painpoint(id="a", title="Billing", description="reformat invoices",
                       pain_type="billing")
        b = _painpoint(id="b", title="Hiring", description="schedule candidate interviews",
                       pain_type="hr")
        assert insights.similar_pairs([a, b]) == []

    def test_flags_when_a_pair_spans_two_units(self):
        a = _painpoint(id="a", twin_context={"business_unit": "Billing"})
        b = _painpoint(id="b", twin_context={"business_unit": "Finance"})
        pairs = insights.similar_pairs([a, b])
        assert pairs and pairs[0]["cross_unit"] is True


class TestReach:
    def test_a_painpoint_in_one_unit_reaches_one(self):
        rows = insights.top_reach([_painpoint()])
        assert rows[0]["units"] == 1

    def test_the_same_pain_type_in_two_units_reaches_both(self):
        subs = [
            _painpoint(id="a", twin_context={"business_unit": "Billing"}),
            _painpoint(id="b", twin_context={"business_unit": "Finance"}),
        ]
        rows = insights.top_reach(subs)
        assert rows[0]["units"] == 2
        assert set(rows[0]["unit_names"]) == {"Billing", "Finance"}

    def test_a_flow_edge_adds_both_of_its_ends(self):
        # The ontology's own answer to "who else does this touch".
        edge = bf.FLOW_EDGES[0]
        record = _painpoint(
            pain_type="unique_type_xyz",
            twin_context={"business_unit": "Marketing", "flow_edge": bf.edge_id(edge)},
        )
        rows = insights.top_reach([record])
        names = set(rows[0]["unit_names"])
        assert bf.unit(edge["producer"])["name"] in names
        assert bf.unit(edge["consumer"])["name"] in names

    def test_reach_beats_raw_hours_in_the_ranking(self):
        # A problem five teams share is worth fixing before a bigger one that
        # bothers a single team — that is the whole point of the ranking.
        wide_a = _painpoint(id="a", pain_type="support",
                            twin_context={"business_unit": "Support"},
                            baseline={"annual_hours": 10})
        wide_b = _painpoint(id="b", pain_type="support",
                            twin_context={"business_unit": "Sales"},
                            baseline={"annual_hours": 10})
        deep = _painpoint(id="c", pain_type="billing",
                          twin_context={"business_unit": "Billing"},
                          baseline={"annual_hours": 9000})
        rows = insights.top_reach([wide_a, wide_b, deep])
        assert rows[0]["units"] == 2
        assert rows[-1]["title"] == deep["title"]

    def test_cross_department_excludes_single_unit_painpoints(self):
        subs = [
            _painpoint(id="a", pain_type="support", twin_context={"business_unit": "Support"}),
            _painpoint(id="b", pain_type="support", twin_context={"business_unit": "Sales"}),
            _painpoint(id="c", pain_type="hr", twin_context={"business_unit": "Legal"}),
        ]
        rows = insights.cross_department(subs)
        assert all(row["units"] > 1 for row in rows)
        assert "hr" not in {row["pain_type"] for row in rows}

    def test_top_reach_respects_the_limit(self):
        subs = [_painpoint(id=f"c{i}", title=f"P{i}") for i in range(15)]
        assert len(insights.top_reach(subs, limit=10)) == 10


class TestAnalyse:
    def test_returns_every_section_the_dashboard_renders(self):
        result = insights.analyse([_painpoint()], [_cure()], [])
        for key in ("overview", "people", "units", "similar",
                    "cross_department", "top_reach"):
            assert key in result

    def test_empty_data_gives_empty_sections_not_an_error(self):
        result = insights.analyse([], [], [])
        assert result["overview"]["painpoints_total"] == 0
        assert result["people"] == []
        assert result["top_reach"] == []
