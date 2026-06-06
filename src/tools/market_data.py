"""Enhanced MarketDataTool for local testing.

Behavior:
- If `yfinance` is installed it will attempt to fetch real data for the ticker.
- Otherwise it produces a deterministic, repeatable simulated summary and
  a simple 30-day synthetic price history derived from the ticker hash.

The goal is useful, deterministic demo data without requiring external
APIs, but allowing a best-effort live fetch when available.
"""
from __future__ import annotations

import hashlib
import random
from typing import Dict, List


class MarketDataTool:
    def __init__(self) -> None:
        self._has_yfinance = False
        try:
            import yfinance as yf  # type: ignore

            self._yf = yf
            self._has_yfinance = True
        except Exception:
            self._yf = None

    def _simulate(self, ticker: str) -> Dict[str, object]:
        # deterministic pseudo-random generator seeded by ticker
        seed = int(hashlib.sha256(ticker.encode("utf-8")).hexdigest()[:16], 16)
        rnd = random.Random(seed)

        market_cap = rnd.uniform(10e9, 1e12)
        pe = round(rnd.uniform(5.0, 50.0), 2)
        revenue = rnd.uniform(1e9, 5e11)

        # synthetic 30-day price series
        base_price = rnd.uniform(10.0, 1500.0)
        prices: List[float] = []
        price = base_price
        for _ in range(30):
            # small daily drift and noise
            price *= rnd.uniform(0.98, 1.02)
            prices.append(round(price, 2))

        return {
            "ticker": ticker.upper(),
            "market_cap": int(market_cap),
            "pe_ratio": pe,
            "revenue_ttm": int(revenue),
            "price_history_30d": prices,
            "source": "simulated",
        }

    def get_financial_summary(self, ticker: str) -> Dict[str, object]:
        """Return a financial summary for `ticker`.

        Attempts to use `yfinance` when available, otherwise returns a
        deterministic simulated summary suitable for testing and demos.
        """
        ticker = ticker.strip().upper()
        if not ticker:
            raise ValueError("ticker must be provided")

        if self._has_yfinance and self._yf is not None:
            try:
                t = self._yf.Ticker(ticker)
                info = t.info if hasattr(t, "info") else {}
                # best-effort mapping; fall back to simulation when fields missing
                market_cap = info.get("marketCap") or info.get("market_cap")
                pe = info.get("trailingPE") or info.get("trailingPE")
                revenue = info.get("totalRevenue") or info.get("revenue")

                if market_cap and pe and revenue:
                    hist = []
                    try:
                        hist_df = t.history(period="30d")
                        hist = [round(float(x), 2) for x in hist_df["Close"].tolist()]
                    except Exception:
                        hist = []

                    return {
                        "ticker": ticker,
                        "market_cap": int(market_cap),
                        "pe_ratio": float(pe),
                        "revenue_ttm": int(revenue),
                        "price_history_30d": hist,
                        "source": "yfinance",
                    }
            except Exception:
                # fall through to simulation on any fetch error
                pass

        return self._simulate(ticker)
