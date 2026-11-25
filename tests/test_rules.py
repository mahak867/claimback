from datetime import date

from claimback.rules import Case, months_between, run_rules, strength


def sample(**kw):
    base = dict(
        policy_inception=date(2019, 4, 12),
        continuous_cover=True,
        admission=date(2026, 8, 14),
        rejection_ground="non_disclosure_proposal",
    )
    base.update(kw)
    return Case(**base)


def rules_hit(case):
    return {g.rule for g in run_rules(case)}


def test_months_between():
    assert months_between(date(2019, 4, 12), date(2026, 8, 14)) == 88
    assert months_between(date(2019, 4, 12), date(2024, 4, 11)) == 59
    assert months_between(date(2019, 4, 12), date(2024, 4, 12)) == 60


def test_moratorium_applies_after_60_months():
    assert "moratorium" in rules_hit(sample())


def test_moratorium_not_before_60_months():
    assert "moratorium" not in rules_hit(sample(admission=date(2024, 4, 11)))


def test_moratorium_blocked_by_fraud_or_break_in_cover():
    assert "moratorium" not in rules_hit(sample(fraud_alleged=True))
    assert "moratorium" not in rules_hit(sample(continuous_cover=False))


def test_moratorium_ignores_unrelated_grounds():
    assert "moratorium" not in rules_hit(sample(rejection_ground="amount_limited"))


def test_ped_wait_cap():
    case = sample(rejection_ground="pre_existing_disease", ped_wait_months_in_policy=48,
                  policy_inception=date(2022, 6, 1))
    assert "ped_wait_cap" in rules_hit(case)
    assert "ped_wait_cap" not in rules_hit(sample(rejection_ground="pre_existing_disease",
                                                  ped_wait_months_in_policy=36))


def test_cashless_delay():
    assert "cashless_delay" in rules_hit(sample(cashless_decision_hours=5))
    assert "cashless_delay" not in rules_hit(sample(cashless_decision_hours=0.5))


def test_strength_matches_prototype_case():
    grounds = run_rules(sample(pre_policy_check_normal=True))
    assert {g.rule for g in grounds} == {"moratorium", "pre_policy_check"}
    assert strength(grounds) == "Strong"


def test_strength_weak_when_nothing_found():
    assert strength(run_rules(sample(admission=date(2020, 1, 1)))) == "Weak"
