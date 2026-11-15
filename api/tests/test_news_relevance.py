from app.services.news import relevance


def test_drops_consumer_noise_and_roundups():
    for t in [
        "Bank holidays next week (November 16–22): When will SBI, HDFC, ICICI, PNB and other banks be closed?",
        "Latest FD interest rates in November 2026: HDFC Bank, ICICI Bank, PNB, Canara Bank and 8 other banks offer",
        "Rs 30 lakh betting losses drive Infosys engineer to failed heist in Odisha",
        "Prof. Isha Jain wins Infosys Prize 2026 for pioneering discoveries in oxygen biology",
        "JioBlackRock Flexi Cap Fund exits ITC, BSE, MCX, TCS and 17 more, trim exposure in HDFC Bank",
    ]:
        assert relevance(t) == -1, t


def test_ranks_price_relevant_headlines_first():
    assert relevance("HDFC Bank Board Approves Rangan’s Re-appointment as ED") == 1
    assert relevance("H-1B is ‘not a business model’: Infosys, TCS, Wipro face fresh scrutiny as US visa crackdown widens") == 1
    assert relevance("L&T bags order worth ₹5,000 crore from NHAI") == 1
    assert relevance("Infosys opens new campus in Pune") == 0
