"""Offline tests for the ingestion logic (no network)."""

from app.ingest import enrich
from app.services.digest import headline
from app.services.graph import _same_org
from app.services.taxonomy import classify, is_routine


def test_fy_quarter():
    assert enrich.fy_quarter("Sep 2026") == "Q2 FY27"
    assert enrich.fy_quarter("Mar 2026") == "Q4 FY26"
    assert enrich.fy_quarter("Dec 2025") == "Q3 FY26"


def test_period_from_text():
    assert enrich._period_from_text("results for the quarter and half year ended September 30, 2026") == "Sep 2026"
    assert enrich._period_from_text("for the quarter ended 30th June 2026") == "Jun 2026"
    assert enrich._period_from_text("no period here") is None


def test_nse_label_layers():
    assert classify("CO has informed the Exchange about change in Management", "Change in Management") == "management_change"
    assert classify("CO has informed the Exchange about Link of Recording", "Analysts/Institutional Investor Meet/Con. Call Updates") == "earnings_call"
    assert classify("CO has informed the Exchange about Schedule of meet", "Analysts/Institutional Investor Meet/Con. Call Updates") == "investor_meetings"
    assert classify("CO has informed the Exchange about General Updates", "General Updates") is None  # → PDF / LLM


def test_routine_within_material_category():
    text = "allotment of 200000 securities pursuant to Non Convertible Securities"
    cat = classify(text, "Allotment of Securities")
    assert cat == "fund_raise" and is_routine(cat, text)
    notice = "The meeting of the Board is scheduled on October 30, 2026 to consider and approve the financial results"
    assert classify(notice, "General Updates") == "results" and is_routine("results", notice)


def test_headline_strips_boilerplate():
    assert headline("Polycab India Limited has informed the Exchange about General Updates", "General Updates") == "General Updates"
    h = headline("Polycab India Limited has informed the Exchange regarding Demise of Mr X, SMP of the company.", "Demise")
    assert h.startswith("Demise of Mr X")


def test_org_matching():
    assert _same_org("Havells India Ltd.", "Havells India")
    assert _same_org("Polycab India Limited", "Polycab")
    assert not _same_org("Tata Steel", "Tata Motors")


def test_regex_people_dedupes_and_stops_at_roles():
    text = "Appointment of Mr. Anup Bagchi Managing Director and Mr. Leo Puri as Chairman. Mr. Puri will join. Mr. V.N. Srivatsan retires; Mr. V. N. Srivatsan"
    names = [p["name"] for p in enrich._regex_people(text)]
    assert "Anup Bagchi" in names and "Leo Puri" in names
    assert "Puri" not in names and len([n for n in names if "Srivatsan" in n]) == 1


def test_people_from_xbrl():
    xml = (
        '<in-capmkt:TypeOfChange contextRef="D_ChangeInManagement1">Cessation</in-capmkt:TypeOfChange>'
        '<in-capmkt:CategoryOfCessation contextRef="D_ChangeInManagement1">Resignation</in-capmkt:CategoryOfCessation>'
        '<in-capmkt:DesignationOfDesignatedPerson contextRef="D_ChangeInManagement1">SBU Head - Life Sciences</in-capmkt:DesignationOfDesignatedPerson>'
        '<in-capmkt:NameOfDesignatedPerson contextRef="I_ChangeInManagement1">Puneet Sharma</in-capmkt:NameOfDesignatedPerson>'
        '<in-capmkt:EffectiveDateOfReasonOfChange contextRef="I_ChangeInManagement1">2026-08-21</in-capmkt:EffectiveDateOfReasonOfChange>'
    )
    [p] = enrich.people_from_xbrl(xml)
    assert (p["name"], p["role"], p["change"], p["effective_date"]) == ("Puneet Sharma", "SBU Head - Life Sciences", "resigned", "2026-08-21")


def test_headline_keeps_honorifics_together():
    h = headline("Titan Company Limited has informed the Exchange about Retirement of Mr. Noel N. Tata as Director. Next sentence.", "Retirement")
    assert h == "Retirement of Mr. Noel N. Tata as Director"
