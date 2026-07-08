from project.research.global_model_selection import (
    return_per_unit_risk,
    risk_per_unit_return,
)


def test_return_per_unit_risk_higher_is_better():
    weak = return_per_unit_risk(0.08, 0.20)
    strong = return_per_unit_risk(0.08, 0.10)

    assert strong > weak


def test_risk_per_unit_return_lower_is_better():
    weak = risk_per_unit_return(0.20, 0.08)
    strong = risk_per_unit_return(0.10, 0.08)

    assert strong < weak
