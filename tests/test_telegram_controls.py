from __future__ import annotations

from ggs import state
from ggs.telegram import bot


def _redirect_runtime(monkeypatch, tmp_path):
    monkeypatch.setattr(state, 'GLOBAL_RUNTIME', tmp_path)
    monkeypatch.setattr(state, 'RUNTIME', tmp_path / 'paper')
    monkeypatch.setattr(state, 'SETTINGS_FILE', tmp_path / 'settings.json')
    monkeypatch.setattr(state, 'CONTROL_FILE', tmp_path / 'control.json')
    monkeypatch.setattr(state, 'WALLETS_FILE', tmp_path / 'wallets.json')
    monkeypatch.setattr(state, 'TELEGRAM_SESSION_FILE', tmp_path / 'telegram_session.json')
    monkeypatch.setattr(state, 'STATE_FILE', tmp_path / 'paper' / 'state.json')
    monkeypatch.setattr(state, 'TRADES_FILE', tmp_path / 'paper' / 'trades.jsonl')
    monkeypatch.setattr(bot, 'STATE_FILE', state.STATE_FILE)
    monkeypatch.setattr(bot, 'TRADES_FILE', state.TRADES_FILE)
    monkeypatch.setattr(bot, 'TELEGRAM_SESSION_FILE', state.TELEGRAM_SESSION_FILE)
    monkeypatch.setattr(bot, 'OWNER_ID', 123)


def _query(data):
    return {'id':'cb1','from':{'id':123},'data':data,'message':{'message_id':7,'chat':{'id':123}}}


def test_bet_button_updates_persistent_setting(monkeypatch, tmp_path):
    _redirect_runtime(monkeypatch, tmp_path)
    monkeypatch.setattr(bot, 'edit', lambda *a, **k: None)
    monkeypatch.setattr(bot, 'answer_callback', lambda *a, **k: None)
    bot.handle_callback(_query('bet:8'))
    assert state.load_json(state.TELEGRAM_SESSION_FILE,{})['pending_bet'] == 8.0
    bot.handle_callback(_query('bet:confirm'))
    assert state.get_settings()['execution']['stake_usd'] == 8.0


def test_mode_paper_persists(monkeypatch, tmp_path):
    _redirect_runtime(monkeypatch, tmp_path)
    monkeypatch.setattr(bot, 'edit', lambda *a, **k: None)
    monkeypatch.setattr(bot, 'answer_callback', lambda *a, **k: None)
    state.update_settings({'mode':'LIVE'})
    bot.handle_callback(_query('mode:paper'))
    assert state.get_settings()['mode'] == 'PAPER'


def test_watch_address_saved_without_signing(monkeypatch, tmp_path):
    _redirect_runtime(monkeypatch, tmp_path)
    sent=[]
    monkeypatch.setattr(bot, 'send', lambda chat_id,text,keyboard=None: sent.append(text))
    state.save_json(state.TELEGRAM_SESSION_FILE, {'awaiting':'watch_address'})
    addr='0x'+'ab'*20
    bot.handle_message({'from':{'id':123},'chat':{'id':123},'text':addr})
    wallets=state.get_wallets()
    assert wallets['active'] == addr
    assert 'WATCH-ONLY' in sent[-1]


def test_private_key_like_input_is_not_accepted_as_wallet(monkeypatch, tmp_path):
    _redirect_runtime(monkeypatch, tmp_path)
    sent=[]
    monkeypatch.setattr(bot, 'send', lambda chat_id,text,keyboard=None: sent.append(text))
    state.save_json(state.TELEGRAM_SESSION_FILE, {'awaiting':'watch_address'})
    bot.handle_message({'from':{'id':123},'chat':{'id':123},'text':'0x'+'ab'*32})
    assert 'Invalid EVM address' in sent[-1]
