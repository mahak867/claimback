from pathlib import Path

from claimback.precedents import find, parse_awards

AWARDS = parse_awards((Path(__file__).parent / "fixtures" / "alei_sample_awards.txt").read_text(encoding="utf-8"))


def test_parses_all_three_awards_with_mapped_grounds():
    assert [a.case_id for a in AWARDS] == ["LI/BK-10/05-06", "IO/KCH/LI/21-001-675/2011-12", "21.08.2234."]
    assert AWARDS[0].grounds == {"non_disclosure_proposal", "pre_existing_disease"}
    assert AWARDS[1].grounds == {"non_disclosure_revival"}


def test_outcomes_read_from_decision_text_never_guessed():
    assert [a.outcome for a in AWARDS] == ["dismissed", "allowed", "not stated"]


def test_find_ranks_same_ground_first_and_skips_unrelated():
    query = "non-disclosure of hypertension; insurer did a medical examination before accepting the proposal"
    matches = find("non_disclosure_proposal", query, AWARDS)
    ids = [m.award.case_id for m in matches]
    assert ids[0] == "LI/BK-10/05-06"
    assert "IO/KCH/LI/21-001-675/2011-12" in ids  # related ground (revival)
    assert "21.08.2234." not in ids  # suicide clause: unrelated
    assert "medical" in matches[0].key_sentence.lower()


def test_no_match_for_ground_without_awards():
    assert find("amount_limited", "room rent deduction", AWARDS) == []
