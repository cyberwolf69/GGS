from ggs.telegram.views import market_text, menu_text, performance_text, status_text


def fixture_state():
    return {
        "mode": "PAPER",
        "status": "RUNNING",
        "paused": False,
        "market": {
            "price_to_beat": 81624.47,
            "current_price": 81648.72,
            "up_ask": 0.63,
            "down_ask": 0.38,
            "seconds_left": 107,
            "reference_age_ms": 420,
            "reference_source": "Chainlink BTC/USD TWAP 60s",
        },
        "metrics": {
            "balance": 74.22,
            "net_pnl": 14.22,
            "wr_pct": 75.0,
            "max_drawdown_pct": 7.4,
            "roi_pct": 23.7,
            "wins": 18,
            "losses": 6,
            "expectancy": 0.59,
            "profit_factor": 1.88,
            "peak_balance": 76.0,
            "current_drawdown_pct": 2.3,
            "avg_payout_multiple": 1.56,
        },
        "position": None,
    }


def test_menu_is_paper_and_active():
    text = menu_text(fixture_state())
    assert "Mode: PAPER" in text
    assert "Trading: ACTIVE" in text


def test_status_contains_balance_and_countdown():
    text = status_text(fixture_state())
    assert "$74.22" in text
    assert "01:47" in text


def test_market_uses_normal_btc_price():
    text = market_text(fixture_state())
    assert "$81,624.47" in text
    assert "$81,648.72" in text


def test_performance_metrics():
    text = performance_text(fixture_state())
    assert "75.0%" in text
    assert "1.88" in text
