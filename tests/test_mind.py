import re

import importlib.util
import pathlib
import sys
import pytest


def load_chatbot():
    p = pathlib.Path.cwd() / "chatbot.py"
    spec = importlib.util.spec_from_file_location("chatbot", str(p))
    mod = importlib.util.module_from_spec(spec)
    # ensure repo root is on sys.path so `src` imports resolve
    repo_root = str(pathlib.Path.cwd())
    old_path = list(sys.path)
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.path[:] = old_path
    return mod


class DummyMarket:
    def get_financial_summary(self, ticker: str):
        return {
            "ticker": ticker,
            "market_cap": 123456,
            "pe_ratio": 12.34,
            "revenue_ttm": 987654,
            "price_history_30d": [100.0],
            "source": "dummy",
        }


class DummyScraper:
    def get_text_from_url(self, url: str, max_chars: int = 2000):
        return "Dummy scraped content from " + url


def test_mind_fetches_market_and_scrape(monkeypatch):
    chatbot_mod = load_chatbot()
    ChatBot = chatbot_mod.ChatBot
    bot = ChatBot()

    # patch MarketDataTool and WebScraperTool used inside Mind
    monkeypatch.setenv("PYTHONWARNINGS", "ignore")
    monkeypatch.setattr("src.tools.market_data.MarketDataTool", DummyMarket)
    monkeypatch.setattr("src.tools.scraper.WebScraperTool", DummyScraper)

    resp = bot.mind.think("AAPL https://www.apple.com")
    assert "Market summary" in resp
    assert "ticker=AAPL" in resp

    recent = bot.memory.get_recent()
    # last assistant message should include saved summary
    assert any(isinstance(m, dict) and "Market summary for AAPL" in m.get("text", "") for m in recent)
