"""Pricing engine maths (Phase 7)."""

from decimal import Decimal as D

import pytest

from app.engines.pricing import CostLine, PricingInput, StayRate, convert, price, round_up


def _input(**kw):
    base = dict(
        adults=4, children_with_bed=1, children_without_bed=1, singles=1,
        margins={"hotel": D(10), "transport": D(20), "sightseeing": D(15), "meal": D(10)},
        lines=[
            CostLine("coach", "transport", "per_day", "Coach 5 days", D(500), D(5)),
            CostLine("ticket", "sightseeing", "per_person", "Museum", D(20), D(1)),
            CostLine("meal", "meal", "per_person", "Dinners", D(25), D(4)),
            CostLine("h1d", "hotel", "per_room", "Hotel A double", D(200), D(4)),
            CostLine("h1f", "hotel", "per_room", "Hotel A family", D(300), D(2)),
            CostLine("h2d", "hotel", "per_room", "Hotel B double", D(160), D(6)),
            CostLine("h2f", "hotel", "per_room", "Hotel B family", D(250), D(3)),
        ],
        stays=[StayRate("a", "Hotel A", 2, D(200), D(150)), StayRate("b", "Hotel B", 3, D(160), None, single_is_estimate=True)],
    )
    base.update(kw)
    return PricingInput(**base)


def test_per_person_prices_by_hand():
    r = price(_input())
    # non-hotel per person: coach 2500/6 x1.2 = 500, ticket 20 x1.15 = 23, meals 100 x1.1 = 110 -> 633
    # twin share: 100x2 + 80x3 = 440 -> x1.1 = 484
    assert r.adult_twin == D(1117)
    assert r.single_supplement == D(374)  # ((150-100)x2 + (160-80)x3) x1.1
    assert r.child_with_bed == D(1117) and r.child_without_bed == D(633)
    assert r.total_cost == D(6330)  # hotels 3110 (real room plan) + coach 2500 + tickets 120 + meals 600
    assert r.revenue == D(4 * 1117 + 374 + 1117 + 633)
    assert r.profit == r.revenue - r.total_cost
    assert r.adult_twin_cost == D("976.67")  # 416.67 + 20 + 100 + 440
    assert any("Hotel B" in w and "double room rate" in w for w in r.warnings)
    hotel = next(c for c in r.categories if c.category == "hotel")
    assert hotel.per_person_cost == D(440) and hotel.per_person_selling == D(484) and hotel.cost == D(3110)


def test_discount_adjustment_rounding_and_child_bed_share():
    r = price(_input(discount_pct=D(10), adjustment_per_person=D(15), rounding=D(10), child_bed_pct=D(50)))
    assert r.adult_twin == round_up(D(1117) * D("0.9") + 15, D(10)) == D(1030)
    assert r.single_supplement == D(340)  # 374 x0.9 = 336.6 -> 340 (no per-person adjustment)
    assert r.child_with_bed == round_up((D(633) + D(242)) * D("0.9") + 15, D(10))
    assert r.child_without_bed == D(590)  # 633 x0.9 + 15 = 584.7 -> 590


def test_unpriced_and_excluded_lines_and_only_adults():
    lines = [CostLine("train", "transport", "per_person", "Train Paris-Zurich", None, D(1)),
             CostLine("x", "other", "group", "Excluded extra", D(1000), D(1), included=False),
             CostLine("guide", "guide", "per_day", "Guide", D(240), D(1))]
    r = price(_input(adults=2, children_with_bed=0, children_without_bed=0, singles=0, lines=lines, stays=[]))
    assert r.unpriced == ["Train Paris-Zurich"] and "no price yet" in r.warnings[0]
    assert r.adult_twin == D(120)  # guide 240 / 2, margin 0 for guides
    assert r.child_with_bed is None and r.child_without_bed is None and r.single_supplement is None
    assert r.total_cost == D(240)


def test_below_cost_warning_and_validation():
    r = price(_input(discount_pct=D(60)))
    assert r.profit < 0 and "below cost" in r.warnings[-1]
    with pytest.raises(ValueError):
        price(_input(adults=0, children_with_bed=0, children_without_bed=0))


def test_rounding_and_conversion():
    assert round_up(D("1116.01"), D(10)) == D(1120)
    assert round_up(D("1117.00"), D(5)) == D(1120)
    assert round_up(D("499.999999"), D(1)) == D(500)
    assert round_up(D("12.345"), D(0)) == D("12.35")
    assert convert(D(1117), D("90.5")) == D(101089)  # 101088.5 rounded up
    assert convert(D(1117), None) is None
