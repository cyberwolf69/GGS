from __future__ import annotations

import os
import re
import time
from typing import Any

import requests

from ..live.client import LiveUnavailable, get_live_client
from ..state import (
    EVENTS_FILE, STATE_FILE, TRADES_FILE, TELEGRAM_SESSION_FILE,
    add_watch_wallet, get_control, get_settings, get_wallets,
    load_json, load_jsonl, reset_settings, save_json, set_paused, update_settings,
)
from .views import (
    balance_text, last_trade_text, market_text, menu_text, mode_text, modules_text,
    performance_text, position_text, settings_text, status_text,
)

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
OWNER_ID_RAW = os.environ.get("TELEGRAM_OWNER_ID", "").strip()
OWNER_ID = int(OWNER_ID_RAW) if OWNER_ID_RAW.isdigit() else None
API = f"https://api.telegram.org/bot{TOKEN}"


def kb(rows: list[list[tuple[str, str]]]) -> dict[str, Any]:
    return {"inline_keyboard": [[{"text": text, "callback_data": data} for text, data in row] for row in rows]}


def main_keyboard() -> dict[str, Any]:
    return kb([
        [("Status", "view:status"), ("Market", "view:market")],
        [("Position", "view:position"), ("Performance", "view:performance")],
        [("Modules", "view:modules"), ("Last Trade", "view:last")],
        [("Balance", "view:balance"), ("Withdrawal", "view:withdrawal")],
        [("Pause", "ctl:pause"), ("Resume", "ctl:resume")],
        [("MODE", "view:mode")],
        [("SETTINGS", "view:settings")],
    ])


def view_keyboard(view: str) -> dict[str, Any]:
    return kb([[("Refresh", f"refresh:{view}"), ("Main Menu", "view:menu")]])


def mode_keyboard() -> dict[str, Any]:
    return kb([
        [("PAPER", "mode:paper"), ("LIVE", "mode:live")],
        [("Refresh", "refresh:mode"), ("Main Menu", "view:menu")],
    ])


def live_setup_keyboard() -> dict[str, Any]:
    return kb([
        [("READ ONLY", "mode:live_readonly"), ("SHADOW", "mode:live_shadow")],
        [("LIVE REAL", "mode:live_real")],
        [("Saved Wallets", "wallet:saved"), ("Add Watch Address", "wallet:add_watch")],
        [("Signer Setup", "wallet:signer_info")],
        [("Back", "view:mode")],
    ])


def settings_keyboard() -> dict[str, Any]:
    return kb([
        [("Bet / Entry", "settings:bet"), ("Risk Settings", "settings:risk")],
        [("Signal Settings", "settings:signal"), ("Reset Defaults", "settings:reset")],
        [("Refresh", "refresh:settings"), ("Main Menu", "view:menu")],
    ])


def bet_keyboard() -> dict[str, Any]:
    return kb([
        [("$2", "bet:2"), ("$4", "bet:4"), ("$6", "bet:6")],
        [("$8", "bet:8"), ("$10", "bet:10"), ("Custom", "bet:custom")],
        [("Back", "view:settings")],
    ])


def confirm_bet_keyboard() -> dict[str, Any]:
    return kb([[("Confirm", "bet:confirm"), ("Cancel", "bet:cancel")]])


def alert_keyboard() -> dict[str, Any]:
    return kb([[("Refresh Status", "view:status"), ("View Position", "view:position")]])


def withdrawal_confirm_keyboard() -> dict[str, Any]:
    return kb([[('Confirm', 'withdraw:confirm'), ('Cancel', 'withdraw:cancel')]])


def register_commands() -> None:
    commands = [
        {'command':'start','description':'Open GGS main menu'},
        {'command':'status','description':'Show current GGS status'},
        {'command':'market','description':'Show active BTC 5m market'},
        {'command':'position','description':'Show current position'},
        {'command':'performance','description':'Show PnL and performance'},
        {'command':'modules','description':'Show runtime module activity'},
        {'command':'last','description':'Show last resolved trade'},
        {'command':'balance','description':'Show balance information'},
        {'command':'mode','description':'Switch PAPER / LIVE modes'},
        {'command':'settings','description':'Open trading settings'},
        {'command':'pause','description':'Pause new entries'},
        {'command':'resume','description':'Resume new entries'},
        {'command':'withdrawal','description':'Open LIVE withdrawal flow'},
        {'command':'help','description':'Show GGS command help'},
    ]
    _call('setMyCommands', commands=commands)


def help_text() -> str:
    return (
        'GGS HELP\n\n'
        '/status — runtime status\n'
        '/market — BTC 5m market\n'
        '/position — current position\n'
        '/performance — PnL / WR / drawdown\n'
        '/modules — module state\n'
        '/last — last resolved trade\n'
        '/balance — balance\n'
        '/mode — PAPER / LIVE control\n'
        '/settings — bet and strategy settings\n'
        '/pause / /resume — entry control\n'
        '/withdrawal — LIVE withdrawal\n\n'
        'Private keys are never accepted through Telegram.'
    )


def _call(method: str, **payload: Any) -> dict[str, Any]:
    r = requests.post(f"{API}/{method}", json=payload, timeout=15)
    r.raise_for_status(); data = r.json()
    if not data.get("ok"): raise RuntimeError(data)
    return data


def send(chat_id: int, text: str, keyboard: dict[str, Any] | None = None) -> None:
    payload: dict[str, Any] = {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
    if keyboard: payload["reply_markup"] = keyboard
    _call("sendMessage", **payload)


def edit(chat_id: int, message_id: int, text: str, keyboard: dict[str, Any] | None = None) -> None:
    payload: dict[str, Any] = {"chat_id": chat_id, "message_id": message_id, "text": text, "disable_web_page_preview": True}
    if keyboard: payload["reply_markup"] = keyboard
    try: _call("editMessageText", **payload)
    except Exception as exc:
        if "message is not modified" not in str(exc).lower(): raise


def answer_callback(callback_id: str, text: str | None = None) -> None:
    payload: dict[str, Any] = {"callback_query_id": callback_id}
    if text: payload["text"] = text
    try: _call("answerCallbackQuery", **payload)
    except Exception: pass


def _session() -> dict[str, Any]:
    x=load_json(TELEGRAM_SESSION_FILE,{})
    return x if isinstance(x,dict) else {}


def _set_session(value: dict[str, Any]) -> None:
    save_json(TELEGRAM_SESSION_FILE,value)


def _clear_session() -> None:
    save_json(TELEGRAM_SESSION_FILE,{})


def current_state() -> dict[str, Any]:
    s=load_json(STATE_FILE,{})
    if not isinstance(s,dict): s={}
    settings=get_settings(); s["paused"]=bool(get_control().get("paused",False)); s["mode"]=str(settings.get("mode","PAPER")).upper()
    return s


def render(view: str) -> tuple[str, dict[str, Any]]:
    state=current_state(); settings=get_settings(); wallets=get_wallets(); trades=[t for t in load_jsonl(TRADES_FILE) if t.get("status")=="RESOLVED"]
    if view=="menu": return menu_text(state),main_keyboard()
    if view=="status": return status_text(state),view_keyboard(view)
    if view=="market": return market_text(state),view_keyboard(view)
    if view=="position": return position_text(state),view_keyboard(view)
    if view=="performance": return performance_text(state),view_keyboard(view)
    if view=="modules": return modules_text(state),view_keyboard(view)
    if view=="last": return last_trade_text(trades),view_keyboard(view)
    if view=="balance": return balance_text(state),view_keyboard(view)
    if view=="mode": return mode_text(state,settings,wallets),mode_keyboard()
    if view=="settings": return settings_text(settings),settings_keyboard()
    if view=="withdrawal":
        mode=str(settings.get("mode","PAPER")).upper()
        if mode!="LIVE":
            return f"GGS WITHDRAWAL\n\nWITHDRAWAL DISABLED\nCurrent mode: {mode}",view_keyboard(view)
        if os.environ.get('GGS_LIVE_WITHDRAWALS_ENABLED','false').lower()!='true':
            return "GGS WITHDRAWAL\n\nWITHDRAWAL LOCKED\nSet GGS_LIVE_WITHDRAWALS_ENABLED=true only after LIVE trading is validated.",view_keyboard(view)
        try:
            ready=get_live_client().readiness(refresh=True)
            bal=float(ready.get('balance_usd') or 0)
            address=ready.get('wallet') or '—'
            return (f"GGS WITHDRAWAL\n\nWallet: {address}\nAvailable: ${bal:.2f}\n\nStart a withdrawal?",
                    kb([[('Start Withdrawal','withdraw:start')],[('Refresh','refresh:withdrawal'),('Main Menu','view:menu')]]))
        except Exception as exc:
            return f"GGS WITHDRAWAL\n\nWALLET NOT READY\n{type(exc).__name__}: {exc}",view_keyboard(view)
    if view=="help": return help_text(),view_keyboard('menu')
    return menu_text(state),main_keyboard()


def authorized(user_id: Any) -> bool:
    try: return OWNER_ID is not None and int(user_id)==OWNER_ID
    except Exception: return False


def _bet_menu_text() -> str:
    stake=float((get_settings().get("execution") or {}).get("stake_usd",6.0))
    return f"BET PER ENTRY\n\nCurrent: ${stake:.2f}\n\nChoose amount. Changes apply to the next entry."


def _live_setup_text() -> str:
    wallets=get_wallets(); active=wallets.get('active') or 'NONE'
    return (
        "LIVE MODE SETUP\n\n"
        f"Active wallet: {active}\n\n"
        "An address added through Telegram is WATCH-ONLY.\n"
        "It can be monitored but cannot sign trades or withdrawals.\n\n"
        "A private key is never accepted as a Telegram message.\n\n"
        "Use ./setup-live.sh on the GGS machine to configure MetaMask securely."
    )


def _saved_wallets_text() -> str:
    w=get_wallets(); items=w.get('watch') or []
    if not items: return "SAVED WALLETS\n\nNo saved watch addresses."
    return "SAVED WALLETS\n\n"+"\n".join(f"{i+1}. {a}" for i,a in enumerate(items))


def _valid_evm_address(v: str) -> bool:
    return re.fullmatch(r"0x[a-fA-F0-9]{40}",v.strip()) is not None


def handle_message(msg: dict[str, Any]) -> None:
    user_id=(msg.get('from') or {}).get('id'); chat_id=(msg.get('chat') or {}).get('id')
    if chat_id is None or not authorized(user_id): return
    raw=str(msg.get('text') or '').strip(); text=raw.lower(); sess=_session()

    # Stateful input flows first.
    if sess.get('awaiting')=='bet_custom':
        try: amount=float(raw)
        except Exception:
            send(int(chat_id),"Invalid amount. Enter a number, for example: 7.5",kb([[("Cancel","bet:cancel")]])); return
        if amount<=0 or amount>100000:
            send(int(chat_id),"Bet amount must be greater than 0.",kb([[("Cancel","bet:cancel")]])); return
        _set_session({'awaiting':'bet_confirm','pending_bet':round(amount,8)})
        send(int(chat_id),f"BET UPDATE\n\nCurrent: ${float((get_settings().get('execution') or {}).get('stake_usd',6)):.2f}\nNew: ${amount:.2f}\n\nEffective: next entry",confirm_bet_keyboard()); return

    if sess.get('awaiting')=='watch_address':
        if not _valid_evm_address(raw):
            send(int(chat_id),"Invalid EVM address. Send a 0x address with 40 hex characters.",kb([[("Cancel","wallet:cancel")]])); return
        add_watch_wallet(raw); _clear_session()
        send(int(chat_id),f"WATCH WALLET SAVED\n\nAddress: {raw}\nMode: WATCH-ONLY\n\nThis address cannot sign trades or withdrawals.",kb([[("Mode","view:mode"),("Main Menu","view:menu")]])); return

    if sess.get('awaiting')=='withdraw_address':
        if not _valid_evm_address(raw):
            send(int(chat_id),'Invalid EVM address. Send a 0x address with 40 hex characters.',kb([[('Cancel','withdraw:cancel')]])); return
        _set_session({'awaiting':'withdraw_amount','withdraw_address':raw,'created_at':time.time()})
        send(int(chat_id),f'WITHDRAWAL\n\nDestination: {raw}\n\nSend amount in USDC.',kb([[('Cancel','withdraw:cancel')]])); return

    if sess.get('awaiting')=='withdraw_amount':
        try: amount=float(raw)
        except Exception:
            send(int(chat_id),'Invalid amount. Example: 25',kb([[('Cancel','withdraw:cancel')]])); return
        max_usd=float(os.environ.get('MAX_WITHDRAW_USD','500') or 500)
        if amount<=0 or amount>max_usd:
            send(int(chat_id),f'Amount must be > 0 and <= ${max_usd:.2f}.',kb([[('Cancel','withdraw:cancel')]])); return
        try:
            ready=get_live_client().readiness(refresh=True); bal=float(ready.get('balance_usd') or 0)
        except Exception as exc:
            _clear_session(); send(int(chat_id),f'Withdrawal unavailable: {exc}',view_keyboard('withdrawal')); return
        if amount>bal:
            send(int(chat_id),f'Insufficient balance. Available: ${bal:.2f}',kb([[('Cancel','withdraw:cancel')]])); return
        address=str(sess.get('withdraw_address') or '')
        _set_session({'awaiting':'withdraw_confirm','withdraw_address':address,'withdraw_amount':round(amount,6),'created_at':time.time()})
        send(int(chat_id),f'WITHDRAWAL PREVIEW\n\nAmount: ${amount:.2f} USDC\nTo: {address}\nNetwork: Polygon\n\nConfirm?',withdrawal_confirm_keyboard()); return

    aliases={"/start":"menu","/menu":"menu","/status":"status","/market":"market","/position":"position","/performance":"performance","/modules":"modules","/last":"last","/balance":"balance","/withdrawal":"withdrawal","/mode":"mode","/settings":"settings","/help":"help"}
    if text=="/pause": set_paused(True); send(int(chat_id),"GGS trading paused. Resolution/reconciliation stays active.",view_keyboard('status')); return
    if text=="/resume": set_paused(False); send(int(chat_id),"GGS trading resumed.",view_keyboard('status')); return
    body,keyboard=render(aliases.get(text,'menu')); send(int(chat_id),body,keyboard)


def handle_callback(q: dict[str, Any]) -> None:
    user_id=(q.get('from') or {}).get('id'); cbid=str(q.get('id') or '')
    if not authorized(user_id): answer_callback(cbid,'Not authorized'); return
    msg=q.get('message') or {}; chat_id=(msg.get('chat') or {}).get('id'); message_id=msg.get('message_id')
    if chat_id is None or message_id is None: answer_callback(cbid); return
    data=str(q.get('data') or '')

    if data=='ctl:pause': set_paused(True); body,key=render('status'); edit(int(chat_id),int(message_id),body,key); answer_callback(cbid,'Paused'); return
    if data=='ctl:resume': set_paused(False); body,key=render('status'); edit(int(chat_id),int(message_id),body,key); answer_callback(cbid,'Resumed'); return

    if data=='mode:paper':
        update_settings({'mode':'PAPER'}); body,key=render('mode'); edit(int(chat_id),int(message_id),body,key); answer_callback(cbid,'Paper mode selected'); return
    if data=='mode:live':
        edit(int(chat_id),int(message_id),_live_setup_text(),live_setup_keyboard()); answer_callback(cbid); return
    if data=='mode:live_readonly':
        update_settings({'mode':'LIVE_READONLY'}); body,key=render('mode'); edit(int(chat_id),int(message_id),body,key); answer_callback(cbid,'Live read-only selected'); return
    if data=='mode:live_shadow':
        update_settings({'mode':'LIVE_SHADOW'}); body,key=render('mode'); edit(int(chat_id),int(message_id),body,key); answer_callback(cbid,'Live shadow selected'); return
    if data=='mode:live_real':
        if os.environ.get('GGS_LIVE_ENABLED','false').lower()!='true':
            answer_callback(cbid,'LIVE locked: run setup-live.sh and enable GGS_LIVE_ENABLED'); return
        update_settings({'mode':'LIVE'}); body,key=render('mode'); edit(int(chat_id),int(message_id),body,key); answer_callback(cbid,'LIVE REAL selected'); return
    if data=='wallet:saved': edit(int(chat_id),int(message_id),_saved_wallets_text(),kb([[("Back","mode:live"),("Refresh","wallet:saved")]])); answer_callback(cbid); return
    if data=='wallet:add_watch': _set_session({'awaiting':'watch_address'}); edit(int(chat_id),int(message_id),"ADD WATCH ADDRESS\n\nSend the EVM wallet address now.\n\nAddress-only wallets are monitoring-only.",kb([[("Cancel","wallet:cancel")]])); answer_callback(cbid); return
    if data=='wallet:signer_info':
        edit(int(chat_id),int(message_id),"SIGNER SETUP\n\nFor security, GGS does not accept private keys in Telegram messages.\n\nLive signer storage will use local secure storage on the GGS machine. LIVE trading remains locked until that signer layer is enabled.",kb([[("Back","mode:live")]])); answer_callback(cbid); return
    if data=='wallet:cancel': _clear_session(); body,key=render('mode'); edit(int(chat_id),int(message_id),body,key); answer_callback(cbid,'Cancelled'); return

    if data=='withdraw:start':
        settings=get_settings()
        if str(settings.get('mode','PAPER')).upper()!='LIVE' or os.environ.get('GGS_LIVE_WITHDRAWALS_ENABLED','false').lower()!='true':
            answer_callback(cbid,'Withdrawal locked'); return
        _set_session({'awaiting':'withdraw_address','created_at':time.time()})
        edit(int(chat_id),int(message_id),'WITHDRAWAL\n\nSend destination Polygon address.',kb([[('Cancel','withdraw:cancel')]])); answer_callback(cbid); return
    if data=='withdraw:cancel':
        _clear_session(); body,key=render('withdrawal'); edit(int(chat_id),int(message_id),body,key); answer_callback(cbid,'Cancelled'); return
    if data=='withdraw:confirm':
        sess=_session(); timeout=int(os.environ.get('WITHDRAW_CONFIRM_TIMEOUT','60') or 60)
        if sess.get('awaiting')!='withdraw_confirm' or time.time()-float(sess.get('created_at') or 0)>timeout:
            _clear_session(); answer_callback(cbid,'Confirmation expired'); return
        address=str(sess.get('withdraw_address') or ''); amount=float(sess.get('withdraw_amount') or 0)
        if not _valid_evm_address(address) or amount<=0:
            _clear_session(); answer_callback(cbid,'Invalid withdrawal state'); return
        # Clear first: a double tap cannot reuse the same confirmation state.
        _clear_session()
        try:
            result=get_live_client().withdraw_collateral(recipient=address, amount_usd=amount)
            result_text=str(result.get('result') or result.get('tx_hash') or result.get('transaction_hash') or result)
            edit(int(chat_id),int(message_id),f'WITHDRAWAL SENT\n\nAmount: ${amount:.2f} USDC\nTo: {address}\nStatus: SUBMITTED / CONFIRMED BY SDK\nResult: {result_text}',kb([[('Balance','view:balance'),('Main Menu','view:menu')]]))
            answer_callback(cbid,'Withdrawal sent')
        except Exception as exc:
            edit(int(chat_id),int(message_id),f'WITHDRAWAL FAILED\n\n{type(exc).__name__}: {exc}',kb([[('Withdrawal','view:withdrawal'),('Main Menu','view:menu')]])); answer_callback(cbid,'Failed')
        return

    if data=='settings:bet': edit(int(chat_id),int(message_id),_bet_menu_text(),bet_keyboard()); answer_callback(cbid); return
    if data.startswith('bet:') and data.split(':',1)[1] in {'2','4','6','8','10'}:
        amount=float(data.split(':',1)[1]); _set_session({'awaiting':'bet_confirm','pending_bet':amount}); edit(int(chat_id),int(message_id),f"BET UPDATE\n\nCurrent: ${float((get_settings().get('execution') or {}).get('stake_usd',6)):.2f}\nNew: ${amount:.2f}\n\nEffective: next entry",confirm_bet_keyboard()); answer_callback(cbid); return
    if data=='bet:custom': _set_session({'awaiting':'bet_custom'}); edit(int(chat_id),int(message_id),"CUSTOM BET\n\nSend the amount in USDC.\nExample: 7.5",kb([[("Cancel","bet:cancel")]])); answer_callback(cbid); return
    if data=='bet:confirm':
        sess=_session(); amount=sess.get('pending_bet')
        if amount is None: answer_callback(cbid,'No pending bet'); return
        update_settings({'execution':{'stake_usd':float(amount)}}); _clear_session(); edit(int(chat_id),int(message_id),f"BET UPDATED\n\nBet / Entry: ${float(amount):.2f}\nEffective: next entry",kb([[("Settings","view:settings"),("Main Menu","view:menu")]])); answer_callback(cbid,'Updated'); return
    if data=='bet:cancel': _clear_session(); body,key=render('settings'); edit(int(chat_id),int(message_id),body,key); answer_callback(cbid,'Cancelled'); return
    if data=='settings:risk':
        st=get_settings(); ex=st.get('execution') or {}; mk=st.get('market') or {}
        edit(int(chat_id),int(message_id),f"RISK SETTINGS\n\nMax Open Position: {ex.get('max_positions_per_market',1)}\nMax Spread: {float(mk.get('max_spread',0))*100:.1f}%\n\nEditable controls can be added here without changing strategy code.",kb([[("Back","view:settings"),("Refresh","settings:risk")]])); answer_callback(cbid); return
    if data=='settings:signal':
        st=get_settings(); fu=st.get('fusion') or {}
        edit(int(chat_id),int(message_id),f"SIGNAL SETTINGS\n\nPayout Range: {float(fu.get('min_payout_multiple',1.5)):.2f}x - {float(fu.get('max_payout_multiple',1.8)):.2f}x\nMin Confidence: {float(fu.get('min_confidence_pct',68)):.1f}%\nMin Net Edge: {float(fu.get('min_net_edge',.04))*100:.1f}%",kb([[("Back","view:settings"),("Refresh","settings:signal")]])); answer_callback(cbid); return
    if data=='settings:reset': reset_settings(); body,key=render('settings'); edit(int(chat_id),int(message_id),body,key); answer_callback(cbid,'Defaults restored'); return

    if data.startswith('view:'): view=data.split(':',1)[1]
    elif data.startswith('refresh:'): view=data.split(':',1)[1]
    else: view='menu'
    body,key=render(view); edit(int(chat_id),int(message_id),body,key); answer_callback(cbid)


def event_alert_text(e: dict[str, Any], state: dict[str, Any]) -> str | None:
    typ=str(e.get('type') or '')
    if typ=='PAPER_ENTRY':
        p=state.get('position') or {}; d=state.get('decision') or {}; edge=d.get('edge') or {}
        return f"GGS PAPER ENTRY\n\nSide:       {p.get('side','—')}\nEntry:      {p.get('entry_price','—')}\nStake:      ${float(p.get('stake_usd') or 0):.2f}\nPayout:     {float(p.get('payout_multiple') or 0):.2f}x\nConfidence: {float(d.get('confidence_pct') or 0):.1f}%\nNet Edge:   {float(edge.get('net_edge') or 0)*100:.1f}%"
    if typ in {'RESOLVE_WIN','RESOLVE_LOSS'}:
        mt=state.get('metrics') or {}
        return f"GGS RESOLVED — {'WIN' if typ=='RESOLVE_WIN' else 'LOSS'}\n\nPnL:     ${float(e.get('pnl') or 0):+.2f}\nBalance: ${float(mt.get('balance') or 0):.2f}\nWR:      {float(mt.get('wr_pct') or 0):.1f}%"
    return None


def run() -> None:
    if not TOKEN or OWNER_ID is None: raise SystemExit('Telegram disabled: set TELEGRAM_BOT_TOKEN and TELEGRAM_OWNER_ID in .env')
    try:
        _call('getMe')
        register_commands()
    except Exception as exc: raise SystemExit(f'Telegram connection failed: {exc}')
    offset=0; alert_index=len(load_jsonl(EVENTS_FILE)); last_alert_poll=0.0
    while True:
        try:
            r=requests.get(f"{API}/getUpdates",params={'timeout':20,'offset':offset},timeout=25); r.raise_for_status(); data=r.json()
            for upd in data.get('result',[]):
                offset=max(offset,int(upd.get('update_id',0))+1)
                if 'callback_query' in upd: handle_callback(upd['callback_query'])
                elif 'message' in upd: handle_message(upd['message'])
        except requests.RequestException: time.sleep(2)
        except Exception: time.sleep(1)
        now=time.time()
        if now-last_alert_poll>=1.5:
            events=load_jsonl(EVENTS_FILE)
            if alert_index>len(events): alert_index=len(events)
            new_events=events[alert_index:]; alert_index=len(events); state=current_state()
            for e in new_events:
                text=event_alert_text(e,state)
                if text:
                    try: send(int(OWNER_ID),text,alert_keyboard())
                    except Exception: pass
            last_alert_poll=now


if __name__=='__main__': run()
