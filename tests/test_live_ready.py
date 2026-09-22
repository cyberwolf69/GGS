from __future__ import annotations

from ggs.fusion.payout_filter import evaluate
from ggs.live.client import LiveClient, LiveUnavailable
from ggs.telegram import bot


def test_payout_range_accepts_150_to_180_net():
    x = evaluate(.625, min_multiple=1.50, max_multiple=1.80, max_entry_price=2/3,
                 min_entry_price=1/1.8, taker_fee_per_share=0, slippage_per_share=0)
    assert x['ok'] is True
    assert 1.50 <= x['payout_multiple'] <= 1.80


def test_payout_range_rejects_above_180():
    x = evaluate(.50, min_multiple=1.50, max_multiple=1.80, max_entry_price=2/3,
                 min_entry_price=1/1.8, taker_fee_per_share=0, slippage_per_share=0)
    assert x['ok'] is False
    assert x['reason'] == 'PAYOUT_TOO_HIGH'


def test_live_client_is_fail_closed_without_secrets(monkeypatch):
    monkeypatch.delenv('POLYMARKET_PRIVATE_KEY', raising=False)
    monkeypatch.delenv('POLYMARKET_WALLET_ADDRESS', raising=False)
    monkeypatch.delenv('GGS_LIVE_ENABLED', raising=False)
    c = LiveClient()
    status = c.readiness(refresh=True)
    assert status['client_connected'] is False
    assert status['error'] == 'POLYMARKET_PRIVATE_KEY_MISSING'
    try:
        c.place_buy(token_id='1', stake_usd=2, max_price=.62)
    except LiveUnavailable:
        pass
    else:
        raise AssertionError('LIVE order must remain locked')


def test_telegram_registers_command_menu(monkeypatch):
    calls=[]
    monkeypatch.setattr(bot, '_call', lambda method, **payload: calls.append((method,payload)) or {'ok':True})
    bot.register_commands()
    assert calls[0][0] == 'setMyCommands'
    commands={x['command'] for x in calls[0][1]['commands']}
    assert {'mode','settings','withdrawal','help'} <= commands
