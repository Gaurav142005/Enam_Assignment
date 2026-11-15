"""What can move a share price, and what can't."""

from app.services.materiality import assess


def ok(*a, **k):
    return assess(*a, **k)[0]


def test_management_changes():
    assert ok("management_change", "", role="Managing Director and Chief Executive Officer")
    assert ok("management_change", "", role="Chief Financial Officer")
    assert not ok("management_change", "", role="CEO (Helicopter Complex)")
    assert not ok("management_change", "", role="Whole-time Director (designated as Executive Director)")
    assert not ok("management_change", "", role="Non-executive independent director")
    assert not ok("management_change", "", role="Company Secretary & Compliance Officer")


def test_other_categories():
    assert ok("results", "Q2 results")
    assert not ok("credit_rating", "S&P reaffirmed the rating at A- with Stable outlook")
    assert ok("credit_rating", "CRISIL upgraded the long-term rating to AA+")
    assert ok("press_release", "L&T secured a significant order from Noida Metro")
    assert not ok("press_release", "Launch of a new range of fans")
    assert not ok("press_release", "Six Promising Researchers Win the Infosys Prize 2026 Awarded by the Infosys Science Foundation")
    assert ok("press_release", "Bagging/Receiving of orders/contracts")
    assert ok("press_release", "Received Letter of Award for a ₹2,000 crore EPC contract")
    assert not ok("fund_raise", "Bajaj Finance submitted its half-yearly report for FY2026-27")
    assert ok("fund_raise", "Allotment of shares pursuant to Preferential Issue")
    assert not ok("M&A", "Incorporation of a wholly owned subsidiary in Singapore")
    assert ok("M&A", "Acquisition of 100% stake in Wiretech for Rs 240 crore")
    assert not ok("insider_trading", "Trading Plan under PIT")


def test_the_market_reaction_decides_only_unclear_cases():
    # A general announcement the rules can't call: a big move beyond the market makes it price-sensitive.
    assert ok("press_release", "Company update on operations", reaction_pct=-4.2)
    assert not ok("press_release", "Company update on operations", reaction_pct=1.1)
    # A clear "no" stays no, whatever the stock did that day.
    assert not ok("management_change", "", role="CEO (Helicopter Complex)", reaction_pct=-4.2)
    assert not ok("management_change", "", role="Chief Information Security Officer", reaction_pct=-3.3)
    assert not ok("press_release", "Six researchers win the Infosys Prize 2026", reaction_pct=3.4)
    assert not ok("M&A", "Incorporation of a wholly owned subsidiary in Vietnam", reaction_pct=3.9)
