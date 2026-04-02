from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import markdown as md

# Ensure src/ is importable when running from app/
sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv()

from src.storage.database import BriefingDatabase

app = FastAPI(title="News Briefing")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
app.mount(
    "/static",
    StaticFiles(directory=str(Path(__file__).parent / "static")),
    name="static",
)


def _get_db() -> BriefingDatabase:
    db_path = os.getenv("DB_PATH", "data/processed/briefings.db")
    return BriefingDatabase(db_path)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    db = _get_db()
    briefings = db.load_briefings(limit=1)
    briefing = briefings[0] if briefings else None
    briefing_html = md.markdown(briefing["content"], extensions=["tables"]) if briefing else None
    market = db.load_latest_market_snapshot()
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "briefing": briefing,
            "briefing_html": briefing_html,
            "market": market,
        },
    )


@app.get("/history", response_class=HTMLResponse)
async def history(request: Request) -> HTMLResponse:
    db = _get_db()
    briefings = db.load_briefings(limit=30)
    return templates.TemplateResponse(
        "history.html",
        {"request": request, "briefings": briefings},
    )


@app.get("/briefing/{briefing_id}", response_class=HTMLResponse)
async def briefing_detail(request: Request, briefing_id: str) -> HTMLResponse:
    db = _get_db()
    all_briefings = db.load_briefings(limit=100)
    briefing = next((b for b in all_briefings if b["briefing_id"] == briefing_id), None)
    briefing_html = md.markdown(briefing["content"], extensions=["tables"]) if briefing else None
    return templates.TemplateResponse(
        "briefing.html",
        {"request": request, "briefing": briefing, "briefing_html": briefing_html},
    )


@app.get("/market", response_class=HTMLResponse)
async def market(request: Request) -> HTMLResponse:
    db = _get_db()
    snapshots = db.load_latest_market_snapshot()
    GROUPS = {
        "Indices": ("SP500", "NASDAQ", "CAC40", "VIX"),
        "Tech": ("NVDA", "MSFT", "GOOGL", "META", "AAPL"),
        "Crypto": ("BTC", "ETH"),
        "Commodités": ("GOLD", "OIL"),
        "FX": ("EURUSD",),
    }
    by_ticker = {s["ticker"]: s for s in snapshots}
    grouped = {
        group: [by_ticker[t] for t in tickers if t in by_ticker]
        for group, tickers in GROUPS.items()
    }
    return templates.TemplateResponse(
        "market.html",
        {"request": request, "grouped": grouped},
    )


@app.post("/run")
async def trigger_run(mode: str = "no-llm") -> RedirectResponse:
    from src.main import run
    run(mode=mode)
    return RedirectResponse(url="/", status_code=303)
