from __future__ import annotations

from typing import Any


def _money(v: Any) -> str:
    try:
        return f"${float(v):,.2f}"
    except Exception:
        return "—"


def _pct(v: Any) -> str:
    try:
        return f"{float(v):.1f}%"
    except Exception:
        return "—"


def _num(v: Any, digits: int = 3) -> str:
    try:
        return f"{float(v):.{digits}f}"
    except Exception:
        return "—"


def menu_text(state: dict[str, Any]) -> str:
    return (
        "GGS — Ganteng-Ganteng Signature\n\n"
        f"Mode: {state.get('mode', 'PAPER')}\n"
        f"Engine: {state.get('status', 'STARTING')}\n"
        f"Trading: {'PAUSED' if state.get('paused') else 'ACTIVE'}\n\n"
        "Choose a panel below."
    )


def status_text(state: dict[str, Any]) -> str:
    m = state.get("market") or {}; mt = state.get("metrics") or {}; p = state.get("position") or {}; live=state.get('live') or {}
    pos = "NONE" if not p else f"{p.get('side','?')} @ {_num(p.get('entry_price'))}"
    sec=max(0,float(m.get('seconds_left') or 0)); mode=str(state.get('mode','PAPER')).upper()
    shown_balance=live.get('balance_usd') if mode.startswith('LIVE') else mt.get('balance')
    return (
        "GGS STATUS\n\n"
        f"Mode:          {mode}\n"
        f"Engine:        {state.get('status','STARTING')}\n"
        f"Trading:       {'PAUSED' if state.get('paused') else 'ACTIVE'}\n"
        f"Balance:       {_money(shown_balance)}\n"
        f"Net PnL:       {_money(mt.get('net_pnl'))}\n"
        f"Open Position: {pos}\n"
        f"WR:            {_pct(mt.get('wr_pct'))}\n"
        f"Max DD:        {_pct(mt.get('max_drawdown_pct'))}\n"
        f"Market Ends:   {int(sec//60):02d}:{int(sec%60):02d}"
    )


def market_text(state: dict[str, Any]) -> str:
    m=state.get('market') or {}; sec=max(0,float(m.get('seconds_left') or 0))
    return (
        "BTC 5 MIN MARKET\n\n"
        f"Price To Beat: {_money(m.get('price_to_beat'))}\n"
        f"Actual Price:  {_money(m.get('current_price'))}\n"
        f"UP Ask:        {_num(m.get('up_ask'))}\n"
        f"DOWN Ask:      {_num(m.get('down_ask'))}\n"
        f"Countdown:     {int(sec//60):02d}:{int(sec%60):02d}\n"
        f"Feed Age:      {_num(m.get('reference_age_ms'),0)} ms\n"
        f"Source:        {m.get('reference_source','—')}"
    )


def position_text(state: dict[str, Any]) -> str:
    p=state.get('position') or None; d=state.get('decision') or {}
    if not p:
        return "CURRENT POSITION\n\nNONE\n\n"+f"Decision: {d.get('decision','NO_TRADE')}\nReason: {d.get('reason','—')}"
    ds=p.get('decision_snapshot') or d; edge=ds.get('edge') or {}
    return (
        "CURRENT POSITION\n\n"
        f"Side:       {p.get('side','—')}\n"
        f"Entry:      {_num(p.get('entry_price'))}\n"
        f"Stake:      {_money(p.get('stake_usd'))}\n"
        f"Payout:     {_num(p.get('payout_multiple'),2)}x\n"
        f"Confidence: {_pct(ds.get('confidence_pct'))}\n"
        f"Net Edge:   {_pct((edge.get('net_edge') or 0)*100)}"
    )


def performance_text(state: dict[str, Any]) -> str:
    mt=state.get('metrics') or {}; pf=mt.get('profit_factor')
    return (
        "GGS PERFORMANCE\n\n"
        f"Balance:       {_money(mt.get('balance'))}\n"
        f"Peak Balance:  {_money(mt.get('peak_balance'))}\n"
        f"Net PnL:       {_money(mt.get('net_pnl'))}\n"
        f"ROI:           {_pct(mt.get('roi_pct'))}\n"
        f"W / L:         {mt.get('wins',0)} / {mt.get('losses',0)}\n"
        f"WR:            {_pct(mt.get('wr_pct'))}\n"
        f"Expectancy:    {_money(mt.get('expectancy'))}\n"
        f"Profit Factor: {'—' if pf is None else _num(pf,2)}\n"
        f"Current DD:    {_pct(mt.get('current_drawdown_pct'))}\n"
        f"Max DD:        {_pct(mt.get('max_drawdown_pct'))}\n"
        f"Avg Payout:    {'—' if mt.get('avg_payout_multiple') is None else _num(mt.get('avg_payout_multiple'),2)+'x'}"
    )


def modules_text(state: dict[str, Any]) -> str:
    m=state.get('market') or {}; d=state.get('decision') or {}; mom=d.get('momentum') or {}
    poly='SCANNING' if state.get('status')=='RUNNING' else state.get('status','WAITING')
    ref='LOCKED' if m.get('reference_ready') else 'WAITING'; prob='READY' if d.get('p_up') is not None else 'WAITING'; momentum='SCORING' if mom.get('score') is not None else 'WAITING'; risk='PASSED' if d.get('reason')=='FUSION_CONFIRMED' else 'FILTERING'
    return f"GGS MODULES\n\nPolymarket      {poly}\nReference Feed  {ref}\nProbability     {prob}\nMomentum        {momentum}\nRisk Engine     {risk}"


def last_trade_text(trades: list[dict[str, Any]]) -> str:
    if not trades: return "LAST TRADE\n\nNo resolved trades yet."
    t=trades[-1]
    return f"LAST TRADE\n\nSide:    {t.get('side','—')}\nEntry:   {_num(t.get('entry_price'))}\nPayout:  {_num(t.get('payout_multiple'),2)}x\nResult:  {t.get('result','—')}\nPnL:     {_money(t.get('pnl'))}\nMethod:  {t.get('resolution_method','—')}"


def balance_text(state: dict[str, Any]) -> str:
    mt=state.get('metrics') or {}; live=state.get('live') or {}; mode=str(state.get('mode','PAPER')).upper()
    if mode.startswith('LIVE'):
        return (f"GGS LIVE BALANCE\n\nWallet:        {live.get('wallet') or '—'}\n"
                f"Collateral:    {_money(live.get('balance_usd'))}\n"
                f"CLOB:          {'CONNECTED' if live.get('client_connected') else 'NOT READY'}\n"
                f"Allowance:     {'READY' if live.get('allowance_ready') else 'NOT READY'}\n"
                f"Execution:     {mode}")
    return f"GGS BALANCE\n\nBalance:       {_money(mt.get('balance'))}\nStarting:      {_money((state.get('config_public') or {}).get('starting_balance'))}\nNet PnL:       {_money(mt.get('net_pnl'))}\nOpen Exposure: {_money(mt.get('open_exposure'))}\nPeak Balance:  {_money(mt.get('peak_balance'))}"


def mode_text(state: dict[str, Any], settings: dict[str, Any], wallets: dict[str, Any]) -> str:
    mode=str(settings.get('mode','PAPER')).upper(); bal=(state.get('metrics') or {}).get('balance'); active=wallets.get('active')
    lines=["GGS MODE CONTROL", "", f"Current Mode: {mode}"]
    if mode=='PAPER':
        lines += [f"Paper Balance: {_money(bal)}", "Execution: SIMULATED"]
    elif mode=='LIVE_READONLY':
        lines += [f"Wallet: {active or state.get('live',{}).get('wallet') or 'NOT CONNECTED'}", "Execution: READ ONLY"]
    elif mode=='LIVE_SHADOW':
        lines += [f"Wallet: {active or state.get('live',{}).get('wallet') or 'NOT CONNECTED'}", "Execution: SHADOW (NO REAL ORDERS)"]
    else:
        lines += [f"Wallet: {active or state.get('live',{}).get('wallet') or 'NOT CONNECTED'}", "Execution: LIVE REAL"]
    live=state.get('live') or {}
    if mode.startswith('LIVE'):
        lines += [f"CLOB: {'CONNECTED' if live.get('client_connected') else 'NOT READY'}", f"Live Balance: {_money(live.get('balance_usd'))}"]
    return "\n".join(lines)


def settings_text(settings: dict[str, Any]) -> str:
    ex=settings.get('execution') or {}; fu=settings.get('fusion') or {}; mk=settings.get('market') or {}; pp=settings.get('paper') or {}
    return (
        "GGS SETTINGS\n\n"
        f"Mode: {settings.get('mode','PAPER')}\n"
        f"Paper Balance: {_money(pp.get('starting_balance'))}\n"
        f"Bet / Entry: {_money(ex.get('stake_usd'))}\n"
        f"Max Open Position: {ex.get('max_positions_per_market',1)}\n"
        f"Payout Range: {_num(fu.get('min_payout_multiple'),2)}x - {_num(fu.get('max_payout_multiple'),2)}x\n"
        f"Min Confidence: {_pct(fu.get('min_confidence_pct'))}\n"
        f"Min Net Edge: {_pct(float(fu.get('min_net_edge') or 0)*100)}\n"
        f"Max Spread: {_pct(float(mk.get('max_spread') or 0)*100)}\n\n"
        "Changes apply to the next entry."
    )
