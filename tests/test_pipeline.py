from datetime import date

import pytest

from claimback.citations import Citation, normalise, verify, verify_all
from claimback.deadlines import ladder, to_ics
from claimback.demo import SOURCES
from claimback.letter import UnverifiedCitations, grievance_letter
from claimback.rules import Case, run_rules

LETTER = SOURCES["rejection_letter"]


def test_normalise_handles_ocr_noise():
    assert normalise("Non-disclo-\n sure  of “material”\nfacts") == 'nondisclosure of "material" facts'
    assert normalise("Non-\ndisclosure") == normalise("Non-disclosure")


def test_verbatim_quote_verified_with_position():
    c = verify(Citation("stands repudiated under Clause 7.3", "rejection_letter"), SOURCES)
    assert c.verified and c.normalised_offset is not None


def test_paraphrase_is_rejected():
    c = verify(Citation("rejected because of clause 7.3", "rejection_letter"), SOURCES)
    assert not c.verified


def test_unknown_source_and_tiny_quotes_rejected():
    assert not verify(Citation("stands repudiated", "no_such_doc"), SOURCES).verified
    assert not verify(Citation("the", "rejection_letter"), SOURCES).verified


def test_verify_all_splits():
    ok, bad = verify_all([Citation("Accepted at standard rates", "pre_policy_check"),
                          Citation("Accepted with a loading of 20%", "pre_policy_check")], SOURCES)
    assert len(ok) == 1 and len(bad) == 1


def _letter(citations):
    case = Case(policy_inception=date(2019, 4, 12), continuous_cover=True, admission=date(2026, 8, 14),
                rejection_ground="non_disclosure_proposal")
    return grievance_letter(insurer="X Insurance", policy_no="P1", name="A", claim_inr=246500,
                            treatment="angioplasty", rejection_date="02/09/2026",
                            grounds=run_rules(case), citations=citations, sources=SOURCES)


def test_letter_blocked_by_unverified_citation():
    with pytest.raises(UnverifiedCitations):
        _letter([Citation("the insurer admitted liability in full", "rejection_letter")])


def test_letter_built_when_all_verified():
    text = _letter([Citation("stands repudiated under Clause 7.3", "rejection_letter")])
    assert "60 continuous months" in text and "Rs 2,46,500" in text and "[1] rejection_letter" in text


def test_ladder_dates_and_limit():
    steps = ladder(date(2026, 11, 25), 246500)
    assert steps[1].due == date(2026, 12, 9)
    assert steps[-1].name.startswith("Ombudsman") and steps[-1].due == date(2026, 12, 25)
    assert ladder(date(2026, 11, 25), 60_00_000)[-1].due is None


def test_ics_has_one_event_per_dated_step():
    ics = to_ics(ladder(date(2026, 11, 25), 246500))
    assert ics.count("BEGIN:VEVENT") == 4 and "DTSTART;VALUE=DATE:20261209" in ics


def test_inr_grouping():
    from claimback.letter import inr
    assert [inr(x) for x in (500, 246500, 5000000, 12345678)] == ["500", "2,46,500", "50,00,000", "1,23,45,678"]


def test_letter_needs_grounds_and_citations():
    with pytest.raises(ValueError):
        _letter([])


def test_ics_escapes_text():
    ics = to_ics(ladder(date(2026, 11, 25), 246500))
    assert "Free\\; file" in ics and "portal\\, text" in ics


def test_validator_dates_and_non_object(tmp_path):
    import json, subprocess, sys
    letter = "Your claim stands repudiated under Clause 7.3 as the ailment is pre-existing."
    good = {"insurer_name": "X", "policy_number": "P", "policy_inception_date": "12/04/2019",
            "claim_type": "cashless", "claim_amount_inr": 120000, "admission_date": "19/08/2026",
            "discharge_date": "14/08/2026", "diagnosis": "d", "rejection_ground": "pre_existing_disease",
            "clause_cited": "Clause 7.3", "rejection_reason_quote": "as the ailment is pre-existing"}
    f = tmp_path / "d.jsonl"
    f.write_text(json.dumps({"input": letter, "output": good}) + "\n" + json.dumps({"input": letter, "output": "[1, 2]"}) + "\n")
    out = subprocess.run([sys.executable, "tools/validate_dataset.py", str(f)], capture_output=True, text=True, check=True).stdout
    assert "discharge before admission" in out and "output is not a JSON object" in out and "clean: 0" in out
