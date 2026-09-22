from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse

from .state import EVENTS_FILE, MODE, STATE_FILE, TRADES_FILE, load_json, load_jsonl

ROOT = Path(os.environ.get("GGS_ROOT", Path(__file__).resolve().parents[1]))
STATIC = ROOT / "dashboard"
app = FastAPI(title="GGS — Ganteng-Ganteng Signature")


@app.middleware("http")
async def no_cache(request, call_next):
    resp = await call_next(request)
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return resp


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html", media_type="text/html")


@app.get("/api/health")
def health():
    s = load_json(STATE_FILE, {})
    return {"ok": True, "name": "GGS", "mode": MODE, "status": s.get("status", "STARTING"), "port": int(os.environ.get("GGS_PORT", "6969"))}


@app.get("/api/state")
def state():
    return JSONResponse(load_json(STATE_FILE, {"status": "STARTING", "name": "GGS"}))


@app.get("/api/events")
def events(limit: int = 80):
    rows = load_jsonl(EVENTS_FILE)
    return JSONResponse(list(reversed(rows[-max(1, min(limit, 500)):])) )


@app.get("/api/trades")
def trades(limit: int = 100):
    rows = load_jsonl(TRADES_FILE)
    resolved = [x for x in rows if x.get("status") == "RESOLVED"]
    return JSONResponse(list(reversed(resolved[-max(1, min(limit, 500)):])) )
