from app.services.titles import tidy


def test_press_release_framing_and_lost_apostrophe():
    t = 'A press release dated October 29, 2026, titled "Maruti Suzuki, India s No. 1 Electric Vehicle exporter, crosses EV exports of 50,000 units"'
    assert tidy(t) == "Maruti Suzuki, India's No. 1 Electric Vehicle exporter, crosses EV exports of 50,000 units"


def test_results_become_fiscal_quarter():
    assert tidy("Unaudited Financial Results for the quarter and half year ended 30 September 2026") == "Q2 FY27 results"
    assert tidy("Financial Results for the quarter and half year ended September 30, 2026 and declaration of interim dividend") == "Q2 FY27 results · dividend declared"
    assert tidy("Audited financial results for the quarter and year ended March 31, 2026") == "Q4 FY26 results"
    assert tidy("Outcome of Board Meeting held on November 04, 2026 for approval of Unaudited Standalone and Consolidated Financial Results for the…") == "Board approves results"
    assert tidy("In continuation of our letter of today's date on the Unaudited Financial Results (Consolidated and Standalone) for the quarter and half…") == "Results: follow-up filing"


def test_designation_and_boilerplate():
    assert tidy("V. Srinivasa Rangan appointed Whole-time Director (designated as Executive Director)") == "V. Srinivasa Rangan appointed Executive Director"
    assert tidy("Board of Directors of the Company approved the proposal of incorporation of a wholly owned subsidiary of the Company in Vietnam") == (
        "Board approved the proposal of incorporation of a wholly owned subsidiary in Vietnam")
    assert tidy("NCLAT reserved its order on October 15, 2026, in the appeal involving Asier Metals and Polycab India") == (
        "NCLAT reserved its order in the appeal involving Asier Metals and Polycab India")
    assert tidy("Noel N. Tata retires as Non- Executive, Non-Independent Director and Vice-Chairman").startswith("Noel N. Tata retires as Non-Executive")


def test_leaves_plain_headlines_alone_and_cuts_cleanly():
    t = "L&T secured an order from Noida Metro Rail Corporation for the Aqua Line Extension Project"
    assert tidy(t) == t
    long = "word " * 40
    out = tidy(long)
    assert len(out) <= 96 and out.endswith("…") and not out.endswith(" …")


def test_bare_results_title_borrows_quarter_from_text():
    text = "Hindustan Aeronautics Limited has submitted to the Exchange, the financial results for the period ended September 30, 2026."
    assert tidy("Results", text) == "Q2 FY27 results"
    assert tidy("Outcome of Board Meeting for approval of Financial Results", text) == "Board approves Q2 FY27 results"
