"""Similarity: would one agent close both painpoints, and is a cure reusable?

The cases that matter are the ones plain token overlap gets wrong — two teams
describing the same job in different vocabulary, and two unrelated jobs that
happen to share words.
"""

from __future__ import annotations

import pytest

from services.shared import similarity


def _painpoint(**overrides):
    base = {
        "id": "c1",
        "title": "Order forms get retyped into the CRM",
        "description": "A signed order form arrives as a scanned PDF and I retype "
                       "the terms and pricing into the CRM.",
        "pain_type": "document",
        "submitter": {"name": "Chidi", "department": "Sales"},
        "twin_context": {
            "business_unit": "Sales",
            "task": "Create proposal",
            "input": "Signed order form (PDF)",
            "output_to": "Legal",
            "flow_object": "Proposal",
        },
        "outcomes": ["save_time", "reduce_errors"],
        "current_workflow": ["Open the attachment", "Read off the fields"],
    }
    base.update(overrides)
    return base


def _cure(**overrides):
    base = {
        "id": "s1",
        "challenge_id": "c1",
        "helper": "Aisha",
        "what_features": "Extract the order-form fields straight into the CRM",
        "how_components": "Parse the PDF, extract terms and pricing, confidence-score each field",
        "ai_tools_used": "Document parser, field extractor",
        "difficulty": "Medium",
        "status": "In production",
    }
    base.update(overrides)
    return base


class TestSignature:
    def test_reads_the_verb_from_the_prose(self):
        assert similarity.signature(_painpoint())["verb"] == "extract"

    def test_reads_the_artifact_from_the_declared_input(self):
        assert similarity.signature(_painpoint())["artifact"] == "document"

    def test_falls_back_to_the_prose_when_no_input_was_captured(self):
        record = _painpoint(twin_context={"business_unit": "Sales"})
        assert similarity.signature(record)["artifact"] == "document"

    def test_a_record_with_nothing_useful_yields_empty_parts(self):
        sig = similarity.signature({"title": "", "description": ""})
        assert sig["verb"] == "" and sig["artifact"] == ""

    def test_no_keyword_is_a_substring_of_another_in_the_same_class(self):
        # "mail" inside "email" scored one word twice and dragged records into
        # that class on a single mention. Guard the whole lexicon, not the one
        # pair that happened to bite.
        for name, lexicon in (("verb", similarity.VERBS),
                              ("artifact", similarity.ARTIFACTS)):
            for key, spec in lexicon.items():
                words = spec["keywords"]
                for word in words:
                    others = [w for w in words if w != word and word in w]
                    assert not others, f"{name}/{key}: {word!r} is inside {others!r}"

    def test_a_review_cycle_is_not_customer_feedback(self):
        record = {"title": "Creative waits on sign-off",
                  "description": "Each review cycle is chased separately."}
        assert similarity.signature(record)["artifact"] != "feedback"

    def test_hunting_the_current_version_reads_as_a_search(self):
        record = {"title": "Which clause version is current lives in an email thread",
                  "description": "I have to read the thread and diff the attachments."}
        assert similarity.signature(record)["verb"] == "search"

    @pytest.mark.parametrize("text,expected", [
        ("I reconcile payments that do not match the invoice", "reconcile"),
        ("Every ticket is triaged from scratch and escalated", "route"),
        ("I assemble the report from five dashboards", "assemble"),
        ("Each asset needs approval and I chase the sign-off", "approve"),
        ("I reformat the export into a different layout", "convert"),
    ])
    def test_recognises_each_verb(self, text, expected):
        assert similarity.signature({"title": "", "description": text})["verb"] == expected


class TestPainpointScoring:
    def test_the_same_job_in_two_units_scores_high(self):
        # The case plain word overlap misses: different vocabulary, same fix.
        a = _painpoint()
        b = _painpoint(
            id="c2",
            title="Supplier warranty documents are retyped into the asset register",
            description="A warranty certificate arrives as a scanned PDF and I retype "
                        "the fields into the asset register.",
            submitter={"name": "Ravi", "department": "Engineering & Delivery"},
            twin_context={"business_unit": "Engineering & Delivery",
                          "task": "Create proposal",
                          "input": "Warranty certificate (PDF)",
                          "output_to": "Legal", "flow_object": "Proposal"},
        )
        result = similarity.score_painpoints(a, b)
        assert result["score"] >= 70
        assert result["band"] == "duplicate"
        assert result["reusable"] is True

    def test_unrelated_work_scores_below_the_floor(self):
        a = _painpoint()
        b = _painpoint(
            id="c2", title="Campaign creative waits on three sign-offs",
            description="Every asset needs approval from brand and legal and the "
                        "review cycle is chased separately.",
            pain_type="approval",
            submitter={"name": "Sinead", "department": "Marketing"},
            twin_context={"business_unit": "Marketing", "task": "Produce qualified lead",
                          "input": "Campaign brief", "output_to": "Sales",
                          "flow_object": "Qualified Lead"},
            outcomes=["save_time"], current_workflow=["Send it to brand"],
        )
        assert similarity.score_painpoints(a, b)["score"] < similarity.MIN_SCORE

    def test_cross_unit_outranks_the_same_pair_within_one_unit(self):
        # A problem two units share is a fix that ships twice; the same problem
        # twice inside one unit is a duplicate to merge. The ranking must say so.
        #
        # The wording differs between the two candidates only in the unit, so
        # the text component is equal and the multiplier is what separates them.
        a = _painpoint()
        body = {
            "title": "Warranty documents are retyped into the register",
            "description": "A certificate arrives as a scanned PDF and I retype the "
                           "fields into the register.",
        }
        shared = dict(a["twin_context"])
        same_unit = _painpoint(id="c2", twin_context=dict(shared), **body)
        cross_unit = _painpoint(
            id="c3", submitter={"name": "R", "department": "Engineering & Delivery"},
            twin_context={**shared, "business_unit": "Engineering & Delivery"}, **body)
        assert (similarity.score_painpoints(a, cross_unit)["score"]
                > similarity.score_painpoints(a, same_unit)["score"])

    def test_two_identical_submissions_in_one_unit_are_still_a_duplicate(self):
        # The cap means a same-unit twin can tie a cross-unit pair at 100. That
        # is correct — both need attention — so the advice has to come from the
        # cross_unit flag rather than from the number alone.
        a = _painpoint()
        twin = _painpoint(id="c2")
        result = similarity.score_painpoints(a, twin)
        assert result["band"] == "duplicate"
        assert result["cross_unit"] is False

    def test_cross_unit_flag_is_set(self):
        other = _painpoint(id="c2", submitter={"name": "M", "department": "Finance"},
                           twin_context={"business_unit": "Finance",
                                         "input": "Signed order form (PDF)"})
        assert similarity.score_painpoints(_painpoint(), other)["cross_unit"] is True

    def test_same_verb_but_different_artifact_and_destination_is_not_reusable(self):
        # A shared technique is not a shared build.
        other = _painpoint(
            id="c2", title="Ticket details are retyped into the billing tool",
            description="I retype the ticket details into the billing tool.",
            twin_context={"business_unit": "Support", "task": "Resolve issue",
                          "input": "Support ticket", "output_to": "Product",
                          "flow_object": "Support Case"})
        result = similarity.score_painpoints(_painpoint(), other)
        assert result["same_verb"] is True
        assert result["reusable"] is False

    def test_score_never_exceeds_one_hundred(self):
        a = _painpoint()
        b = _painpoint(id="c2", submitter={"name": "X", "department": "Finance"},
                       twin_context={**a["twin_context"], "business_unit": "Finance"})
        assert similarity.score_painpoints(a, b)["score"] <= 100

    def test_reasons_explain_the_number(self):
        b = _painpoint(id="c2", submitter={"name": "X", "department": "Finance"},
                       twin_context={**_painpoint()["twin_context"],
                                     "business_unit": "Finance"})
        reasons = similarity.score_painpoints(_painpoint(), b)["reasons"]
        assert any("Same job" in r for r in reasons)
        assert any("two units" in r for r in reasons)


class TestBands:
    @pytest.mark.parametrize("score,expected", [
        (95.0, "duplicate"), (70.0, "duplicate"),
        (60.0, "pattern"), (45.0, "pattern"),
        (30.0, "look"), (25.0, "look"),
        (24.9, ""), (0.0, ""),
    ])
    def test_band_boundaries(self, score, expected):
        assert similarity.band(score)[0] == expected


class TestSimilarPainpoints:
    def test_ranks_best_first_and_respects_the_limit(self):
        target = _painpoint()
        near = _painpoint(id="c2", submitter={"name": "R", "department": "Eng"},
                          twin_context={**target["twin_context"],
                                        "business_unit": "Engineering & Delivery"})
        far = _painpoint(id="c3", title="Tally feedback themes",
                         description="Read through the backlog and tally the themes.",
                         pain_type="analysis",
                         twin_context={"business_unit": "Product", "input": "Feedback"},
                         current_workflow=[])
        rows = similarity.similar_painpoints(target, [far, near], limit=1)
        assert len(rows) == 1 and rows[0]["id"] == "c2"

    def test_never_matches_a_record_against_itself(self):
        target = _painpoint()
        assert similarity.similar_painpoints(target, [target]) == []

    def test_works_on_an_unsaved_record(self):
        # The submit form checks for duplicates before an id exists — if this
        # needed a saved record the most valuable moment would be unreachable.
        draft = {k: v for k, v in _painpoint().items() if k != "id"}
        rows = similarity.similar_painpoints(
            draft, [_painpoint(id="c2", submitter={"name": "R", "department": "Eng"},
                               twin_context={**_painpoint()["twin_context"],
                                             "business_unit": "Eng"})])
        assert rows and rows[0]["score"] >= similarity.MIN_SCORE

    def test_non_mappings_are_skipped_not_fatal(self):
        assert similarity.similar_painpoints(_painpoint(), [None, "junk", 42]) == []


class TestPainpointPairs:
    def test_finds_the_pair_across_the_board(self):
        a = _painpoint()
        b = _painpoint(id="c2", submitter={"name": "R", "department": "Eng"},
                       twin_context={**a["twin_context"], "business_unit": "Eng"})
        pairs = similarity.painpoint_pairs([a, b])
        assert pairs and {pairs[0]["a_id"], pairs[0]["b_id"]} == {"c1", "c2"}

    def test_a_single_painpoint_pairs_with_nothing(self):
        assert similarity.painpoint_pairs([_painpoint()]) == []

    def test_empty_input_is_not_an_error(self):
        assert similarity.painpoint_pairs([]) == []


class TestCureScoring:
    def test_a_shipped_cure_outranks_an_identical_draft(self):
        # Reuse value is similarity x maturity: nobody wants a pointer to a draft.
        target = _cure(id="s0", helper="Someone")
        shipped = _cure(id="s2", helper="A", status="In production")
        draft = _cure(id="s3", helper="B", status="Draft")
        assert (similarity.score_cures(target, shipped)["score"]
                > similarity.score_cures(target, draft)["score"])

    def test_maturity_multiplier_is_reported(self):
        assert similarity.score_cures(_cure(), _cure(status="Draft"))["maturity"] == 0.6

    def test_an_unknown_status_neither_helps_nor_hurts(self):
        assert similarity.score_cures(_cure(), _cure(status="Whatever"))["maturity"] == 1.0

    def test_the_same_author_agreeing_with_themselves_is_flagged(self):
        assert similarity.score_cures(_cure(), _cure(id="s2"))["same_author"] is True

    def test_the_pattern_signal_needs_the_painpoints(self):
        pain = {"c1": _painpoint(), "c2": _painpoint(id="c2")}
        with_pattern = similarity.score_cures(_cure(), _cure(id="s2", helper="B",
                                                            challenge_id="c2"), pain)
        without = similarity.score_cures(_cure(), _cure(id="s2", helper="B",
                                                       challenge_id="c2"))
        assert with_pattern["score"] > without["score"]


class TestSimilarCures:
    def test_excludes_the_same_author_by_default(self):
        rows = similarity.similar_cures(_cure(), [_cure(id="s2")])
        assert rows == []

    def test_can_include_the_same_author_on_request(self):
        rows = similarity.similar_cures(_cure(), [_cure(id="s2")], include_same_author=True)
        assert len(rows) == 1

    def test_never_matches_a_cure_against_itself(self):
        assert similarity.similar_cures(_cure(), [_cure()], include_same_author=True) == []

    def test_unrelated_cures_are_filtered_out(self):
        other = _cure(id="s2", helper="B",
                      what_features="Chase approvals automatically",
                      how_components="Route to reviewers and remind",
                      ai_tools_used="Workflow engine", difficulty="Easy",
                      status="Draft")
        assert similarity.similar_cures(_cure(), [other]) == []
