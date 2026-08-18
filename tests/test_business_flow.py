"""The Business Flow Ontology: units, objects, edges, and pain aggregation."""

from __future__ import annotations

import pytest

from services.shared import business_flow as bf
from services.ui.utils.ontology_flow import BUSINESS_UNITS as TWIN_UNITS


class TestModelIntegrity:
    def test_every_edge_references_real_units_and_objects(self):
        # A typo in an edge is invisible until an aggregate silently drops a
        # submission, so this is the check that matters most in the file.
        unit_ids = {u["id"] for u in bf.BUSINESS_UNITS}
        object_ids = {o["id"] for o in bf.BUSINESS_OBJECTS}
        for record in bf.FLOW_EDGES:
            assert record["producer"] in unit_ids, record
            assert record["consumer"] in unit_ids, record
            assert record["object"] in object_ids, record

    def test_edge_activities_are_owned_by_their_units(self):
        for record in bf.FLOW_EDGES:
            producer = bf.unit(record["producer"])
            consumer = bf.unit(record["consumer"])
            assert record["activity"] in producer["activities"], record
            assert record["triggers"] in consumer["activities"], record

    def test_no_unit_hands_work_to_itself(self):
        for record in bf.FLOW_EDGES:
            assert record["producer"] != record["consumer"], record

    def test_edge_ids_are_unique(self):
        ids = [bf.edge_id(r) for r in bf.FLOW_EDGES]
        assert len(ids) == len(set(ids))

    def test_every_unit_participates_in_the_chain(self):
        # An isolated unit means either a missing edge or a unit that should
        # not be modelled; both are worth failing a test over.
        touched = {r["producer"] for r in bf.FLOW_EDGES} | {r["consumer"] for r in bf.FLOW_EDGES}
        assert touched == {u["id"] for u in bf.BUSINESS_UNITS}

    def test_every_object_is_carried_by_some_edge(self):
        carried = {r["object"] for r in bf.FLOW_EDGES}
        assert carried == {o["id"] for o in bf.BUSINESS_OBJECTS}

    def test_chain_order_covers_every_unit(self):
        assert set(bf.chain_order) == {u["id"] for u in bf.BUSINESS_UNITS}

    def test_objects_declare_sensitivity_and_system_of_record(self):
        # These two decide what an agent may do with the object, so a blank one
        # is worse than no object at all.
        for obj in bf.BUSINESS_OBJECTS:
            assert obj["sensitivity"]
            assert obj["system_of_record"]

    def test_every_unit_is_reachable_from_the_front_of_the_chain(self):
        # Work has to be able to arrive. A unit no path reaches is either
        # missing an inbound edge or should not be in the model.
        reached = {"marketing"}
        changed = True
        while changed:
            changed = False
            for record in bf.FLOW_EDGES:
                if record["producer"] in reached and record["consumer"] not in reached:
                    reached.add(record["consumer"])
                    changed = True
        assert reached == {u["id"] for u in bf.BUSINESS_UNITS}


class TestTwinAlignment:
    def test_units_claiming_a_twin_actually_match_one(self):
        twin_names = {u["name"] for u in TWIN_UNITS}
        for record in bf.BUSINESS_UNITS:
            if record["twin"] is not None:
                assert record["twin"] in twin_names, record["name"]

    def test_the_twin_units_missing_from_the_flow_are_a_known_set(self):
        # The value chain is the commercial flow, so a governance function that
        # signs off across every unit has no single place in it. Documented
        # here so the gap growing is a deliberate change, not a drift.
        covered = {u["twin"] for u in bf.BUSINESS_UNITS if u["twin"]}
        missing = {u["name"] for u in TWIN_UNITS} - covered
        assert missing == {"Security, Risk & Compliance"}


class TestLookups:
    @pytest.mark.parametrize("key", ["billing", "Billing"])
    def test_unit_resolves_by_id_or_name(self, key):
        assert bf.unit(key)["id"] == "billing"

    def test_unknown_lookups_return_none(self):
        assert bf.unit("nope") is None
        assert bf.business_object("nope") is None
        assert bf.edge("a>b>c") is None

    def test_edge_round_trips_through_its_id(self):
        record = bf.FLOW_EDGES[0]
        assert bf.edge(bf.edge_id(record)) == record

    def test_edges_from_and_into_are_consistent(self):
        for record in bf.edges_from("legal"):
            assert record in bf.edges_into(record["consumer"])

    def test_edge_choices_offer_both_directions(self):
        # Pain is as often about what arrives as about what you hand on.
        choices = dict(bf.edge_choices("Billing"))
        producing = {bf.edge_id(r) for r in bf.edges_from("billing")}
        consuming = {bf.edge_id(r) for r in bf.edges_into("billing")}
        assert producing <= set(choices)
        assert consuming <= set(choices)

    def test_edge_choices_unfiltered_covers_the_whole_chain(self):
        assert len(bf.edge_choices()) == len(bf.FLOW_EDGES)

    def test_edge_choices_do_not_repeat(self):
        ids = [identifier for identifier, _ in bf.edge_choices("Engineering & Delivery")]
        assert len(ids) == len(set(ids))


@pytest.fixture(autouse=True)
def _clean_registry():
    """Proposed edges are module state; never let one test leak into the next."""
    bf.register_extras([], [])
    yield
    bf.register_extras([], [])


class TestFlowBuilder:
    """Every rule here exists because breaking it makes the aggregates lie."""

    def test_rejects_a_self_loop(self):
        problem = bf.validate_edge("Billing", "Invoice", "Billing", "Create invoice")
        assert problem and "itself" in problem

    def test_rejects_a_duplicate_of_the_canonical_chain(self):
        problem = bf.validate_edge("Marketing", "Qualified Lead",
                                   "Sales", "Qualify opportunity")
        assert problem and "already in the chain" in problem

    def test_rejects_a_trigger_the_receiving_unit_does_not_own(self):
        problem = bf.validate_edge("Support", "Customer Feedback",
                                   "Billing", "Resolve issue")
        assert problem and "not something" in problem

    def test_rejects_a_near_duplicate_object_name(self):
        # A second spelling would quietly split every count mentioning it.
        problem = bf.validate_edge("Support", "INVOICE", "Finance", "Collect payment")
        assert problem and "already exists" in problem

    @pytest.mark.parametrize("typed", ["invoice", "  Invoice  "])
    def test_a_recognisable_spelling_reuses_the_existing_object(self, typed):
        # Matching by id or by trimmed name is reuse, not duplication — the
        # submitter gets the canonical Invoice rather than a second one.
        assert bf.validate_edge("Support", typed, "Finance", "Collect payment") is None
        _record, new_object = bf.build_edge("Support", typed, "Finance", "Collect payment")
        assert new_object is None

    def test_rejects_missing_fields(self):
        assert bf.validate_edge("", "Invoice", "Support", "Resolve issue")
        assert bf.validate_edge("Support", "", "Finance", "Collect payment")
        assert bf.validate_edge("Support", "Invoice", "Finance", "")

    def test_accepts_a_genuinely_new_handoff(self):
        # Closing the loop: Support's feedback reaching Marketing is exactly
        # the edge the seeded chain is missing.
        assert bf.validate_edge("Support", "Customer Feedback",
                                "Marketing", "Run campaign") is None

    def test_build_edge_creates_the_object_when_it_is_new(self):
        record, new_object = bf.build_edge(
            "Support", "Escalation Brief", "Product", "Design solution")
        assert new_object is not None
        assert new_object["id"] == "escalation_brief"
        assert new_object["origin"] == "proposed"
        # Unclassified objects default to the more restricted reading.
        assert new_object["sensitivity"] == "Internal"
        assert record["object"] == "escalation_brief"
        assert record["origin"] == "proposed"

    def test_build_edge_reuses_an_existing_object(self):
        record, new_object = bf.build_edge(
            "Support", "Support Case", "Product", "Design solution")
        assert new_object is None
        assert record["object"] == "support_case"

    def test_build_edge_picks_an_activity_the_producer_owns(self):
        record, _ = bf.build_edge(
            "Support", "Support Case", "Product", "Design solution",
            activity="Something nobody does")
        assert record["activity"] in bf.unit("Support")["activities"]

    def test_registered_edges_join_every_lookup(self):
        record, new_object = bf.build_edge(
            "Support", "Escalation Brief", "Product", "Design solution")
        bf.register_extras([record], [new_object])

        assert len(bf.all_edges()) == len(bf.FLOW_EDGES) + 1
        assert bf.edge(bf.edge_id(record)) is not None
        assert record in bf.edges_from("Support")
        assert record in bf.edges_into("Product")
        assert bf.edge_id(record) in dict(bf.edge_choices("Support"))
        assert bf.is_proposed(record)

    def test_registering_replaces_rather_than_appends(self):
        record, obj = bf.build_edge("Support", "Escalation Brief",
                                    "Product", "Design solution")
        bf.register_extras([record], [obj])
        bf.register_extras([record], [obj])
        assert len(bf.all_edges()) == len(bf.FLOW_EDGES) + 1

    def test_a_proposed_edge_cannot_be_added_twice(self):
        record, obj = bf.build_edge("Support", "Escalation Brief",
                                    "Product", "Design solution")
        bf.register_extras([record], [obj])
        problem = bf.validate_edge("Support", "Escalation Brief",
                                   "Product", "Design solution")
        assert problem and "already in the chain" in problem

    def test_canonical_edges_are_never_marked_proposed(self):
        assert not any(bf.is_proposed(record) for record in bf.FLOW_EDGES)

    def test_pain_on_a_proposed_edge_still_aggregates(self):
        record, obj = bf.build_edge("Support", "Escalation Brief",
                                    "Product", "Design solution")
        bf.register_extras([record], [obj])
        load = bf.edge_load([{
            "title": "slow escalations",
            "baseline": {"annual_hours": 500},
            "twin_context": {"flow_edge": bf.edge_id(record)},
        }])
        assert load[bf.edge_id(record)]["annual_hours"] == 500


class TestEditingAFlow:
    """Edits are overrides on the canonical record, never mutations of it."""

    def _first(self):
        return bf.FLOW_EDGES[0], bf.edge_id(bf.FLOW_EDGES[0])

    def test_an_override_changes_what_all_edges_returns(self):
        _record, key = self._first()
        bf.register_extras(overrides={key: {"triggers": "Create proposal"}})
        edited = next(e for e in bf.all_edges() if bf.canonical_id(e) == key)
        assert edited["triggers"] == "Create proposal"
        assert bf.is_edited(edited)

    def test_the_canonical_record_is_never_mutated(self):
        record, key = self._first()
        original = dict(record)
        bf.register_extras(overrides={key: {"triggers": "Create proposal"}})
        bf.all_edges()
        assert bf.FLOW_EDGES[0] == original

    def test_clearing_the_override_restores_the_original(self):
        record, key = self._first()
        bf.register_extras(overrides={key: {"triggers": "Create proposal"}})
        bf.register_extras()
        restored = next(e for e in bf.all_edges() if bf.edge_id(e) == key)
        assert restored["triggers"] == record["triggers"]
        assert not bf.is_edited(restored)

    def test_an_edge_does_not_clash_with_itself_when_edited(self):
        # Changing only the trigger must not trip the duplicate check.
        record, key = self._first()
        producer = bf.unit(record["producer"])["name"]
        consumer = bf.unit(record["consumer"])["name"]
        obj = bf.business_object(record["object"])["name"]
        assert bf.validate_edge(producer, obj, consumer,
                                bf.unit(record["consumer"])["activities"][-1],
                                editing=key) is None

    def test_editing_into_an_existing_handoff_is_still_refused(self):
        _record, key = self._first()
        second = bf.FLOW_EDGES[1]
        problem = bf.validate_edge(
            bf.unit(second["producer"])["name"],
            bf.business_object(second["object"])["name"],
            bf.unit(second["consumer"])["name"],
            second["triggers"],
            editing=key,
        )
        assert problem and "already in the chain" in problem

    def test_only_editable_fields_are_applied(self):
        _record, key = self._first()
        bf.register_extras(overrides={key: {"origin": "canonical", "bogus": "x"}})
        edited = next(e for e in bf.all_edges() if bf.canonical_id(e) == key)
        assert "bogus" not in edited
        assert bf.is_edited(edited)

    def test_pain_on_an_edited_edge_still_finds_it_by_its_new_id(self):
        record, key = self._first()
        bf.register_extras(overrides={key: {"consumer": "product",
                                            "triggers": "Design solution"}})
        edited = next(e for e in bf.all_edges() if bf.canonical_id(e) == key)
        load = bf.edge_load([{
            "title": "leads go nowhere",
            "baseline": {"annual_hours": 120},
            "twin_context": {"flow_edge": bf.edge_id(edited)},
        }])
        assert load[bf.edge_id(edited)]["count"] == 1


class TestPredefinedWorkflows:
    def test_a_units_workflows_are_its_own_activities(self):
        assert bf.activity_names("Billing") == bf.unit("billing")["activities"]

    def test_with_no_unit_every_activity_is_offered(self):
        every = bf.activity_names()
        for record in bf.BUSINESS_UNITS:
            for activity in record["activities"]:
                assert activity in every

    def test_the_full_list_has_no_duplicates(self):
        every = bf.activity_names()
        assert len(every) == len(set(every))

    def test_an_unknown_unit_offers_nothing_rather_than_everything(self):
        # Silently falling back to every activity would let a task be recorded
        # against a unit that does not own it.
        assert bf.activity_names("Nope") == []


class TestDestinations:
    """Intake asks where output goes; the edge is recovered from the answer."""

    def test_destinations_start_with_the_value_chain(self):
        assert bf.destination_names()[: len(bf.unit_names())] == bf.unit_names()

    def test_wider_org_units_are_appended(self):
        names = bf.destination_names(["Security, Risk & Compliance"])
        assert "Security, Risk & Compliance" in names

    def test_duplicates_are_not_appended_twice(self):
        names = bf.destination_names(["Billing", "Billing", "Legal"])
        assert names.count("Billing") == 1
        assert names.count("Legal") == 1

    def test_blank_extras_are_ignored(self):
        assert bf.destination_names(["", "   "]) == bf.unit_names()

    def test_edge_between_finds_the_modelled_handoff(self):
        record = bf.edge_between("Marketing", "Sales")
        assert record and record["object"] == "qualified_lead"

    def test_edge_between_is_directional(self):
        # Sales does not hand a Qualified Lead back to Marketing.
        assert bf.edge_between("Sales", "Marketing") is None

    def test_edge_between_returns_none_for_an_unmodelled_pair(self):
        # A real answer: the work leaves the chain. The pain point is still
        # recorded, it just does not roll up into a bottleneck.
        assert bf.edge_between("Marketing", "Finance") is None

    def test_edge_between_handles_unknown_names(self):
        assert bf.edge_between("Marketing", "An external auditor") is None
        assert bf.edge_between("", "Sales") is None

    def test_edge_between_sees_a_proposed_edge(self):
        record, obj = bf.build_edge("Support", "Escalation Brief",
                                    "Product", "Design solution")
        bf.register_extras([record], [obj])
        assert bf.edge_between("Support", "Product") is not None


class TestCustomWorkflows:
    """Workflows a unit adds for itself, through the task-workflow editor."""

    def test_a_custom_workflow_joins_the_units_dropdown(self):
        seeded = bf.activity_names("Sales")
        bf.register_extras(activities={"sales": ["Reformat customer billing"]})
        offered = bf.activity_names("Sales")
        assert offered[: len(seeded)] == seeded
        assert "Reformat customer billing" in offered

    def test_custom_activities_lists_only_what_was_added(self):
        bf.register_extras(activities={"sales": ["Reformat customer billing"]})
        assert bf.custom_activities("Sales") == ["Reformat customer billing"]
        # Seeded ones are not removable, so they must not appear here.
        for seeded in bf.unit("sales")["activities"]:
            assert seeded not in bf.custom_activities("Sales")

    def test_a_custom_workflow_is_scoped_to_its_own_unit(self):
        bf.register_extras(activities={"sales": ["Reformat customer billing"]})
        assert "Reformat customer billing" not in bf.activity_names("Billing")

    def test_custom_workflows_reach_the_all_units_list(self):
        bf.register_extras(activities={"sales": ["Reformat customer billing"]})
        assert "Reformat customer billing" in bf.activity_names()

    def test_a_custom_workflow_can_be_a_flow_trigger(self):
        # A workflow a unit added is as valid a trigger as one it shipped with.
        bf.register_extras(activities={"marketing": ["Re-run campaign"]})
        assert bf.validate_edge("Support", "Customer Feedback",
                                "Marketing", "Re-run campaign") is None

    def test_rejects_a_blank_name(self):
        assert bf.validate_activity("Sales", "   ")

    def test_rejects_an_unknown_unit(self):
        assert bf.validate_activity("Nope", "Anything")

    def test_rejects_a_duplicate_of_a_seeded_workflow(self):
        problem = bf.validate_activity("Sales", "Create proposal")
        assert problem and "already one of" in problem

    def test_duplicate_check_ignores_case_and_spacing(self):
        # "Create invoice" and "create  invoice" as two workflows would split
        # every count that mentions either.
        assert bf.validate_activity("Billing", "create  invoice")

    def test_rejects_a_duplicate_of_an_already_added_workflow(self):
        bf.register_extras(activities={"sales": ["Reformat customer billing"]})
        assert bf.validate_activity("Sales", "REFORMAT CUSTOMER BILLING")

    def test_rejects_an_unreasonably_long_name(self):
        assert bf.validate_activity("Sales", "x" * 61)

    def test_accepts_a_genuinely_new_workflow(self):
        assert bf.validate_activity("Sales", "Reformat customer billing") is None

    def test_registering_replaces_rather_than_accumulates(self):
        bf.register_extras(activities={"sales": ["One"]})
        bf.register_extras(activities={"sales": ["Two"]})
        assert bf.custom_activities("Sales") == ["Two"]


def _pain(edge_record, hours, title):
    return {
        "title": title,
        "baseline": {"annual_hours": hours},
        "twin_context": {"flow_edge": bf.edge_id(edge_record)},
    }


class TestAggregation:
    def test_load_counts_pain_and_hours_per_edge(self):
        first, second = bf.FLOW_EDGES[0], bf.FLOW_EDGES[1]
        load = bf.edge_load([
            _pain(first, 100, "A"), _pain(first, 250, "B"), _pain(second, 40, "C"),
        ])
        assert load[bf.edge_id(first)]["count"] == 2
        assert load[bf.edge_id(first)]["annual_hours"] == 350
        assert load[bf.edge_id(second)]["count"] == 1

    def test_submissions_without_an_edge_are_ignored(self):
        assert bf.edge_load([{"title": "loose", "twin_context": {}}]) == {}

    def test_unknown_edge_ids_are_ignored(self):
        stale = {"title": "x", "twin_context": {"flow_edge": "gone>gone>gone"}}
        assert bf.edge_load([stale]) == {}

    def test_bottlenecks_rank_by_hours_not_by_count(self):
        # Three cheap complaints must not outrank one expensive one — that is
        # how a loud team beats a costly problem.
        loud, costly = bf.FLOW_EDGES[0], bf.FLOW_EDGES[1]
        ranked = bf.bottlenecks([
            _pain(loud, 10, "a"), _pain(loud, 10, "b"), _pain(loud, 10, "c"),
            _pain(costly, 2000, "big"),
        ])
        assert ranked[0]["edge"] == costly
        assert ranked[0]["annual_hours"] == 2000

    def test_bottlenecks_respect_the_limit(self):
        pains = [_pain(r, 100, f"p{i}") for i, r in enumerate(bf.FLOW_EDGES)]
        assert len(bf.bottlenecks(pains, limit=3)) == 3

    def test_bottlenecks_on_no_data_is_empty_not_an_error(self):
        assert bf.bottlenecks([]) == []
