#!/usr/bin/env python3
"""Simple local chatbot with persistent conversation memory."""

from __future__ import annotations

import json
import re
import pathlib
import sys
from typing import Any, Optional

from src.memory.storage import VirtualMemoryStore

STORAGE_DIR = pathlib.Path("chat_memory")
STORAGE_FILE = STORAGE_DIR / "conversation.json"
STORAGE_KEY = "chat_conversation"


class ChatMemory:
    """Conversation store backed by `src.memory.storage.VirtualMemoryStore`.

    The `VirtualMemoryStore` persists JSON under `data_store/` so both the
    chatbot and `brain` can reuse the same underlying storage format.
    """
    def __init__(self, storage_file: pathlib.Path = STORAGE_FILE):
        self.storage_file = storage_file
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)
        self.store = VirtualMemoryStore()
        self.conversation = self._load() or []

    def add_message(self, role: str, text: str) -> None:
        self.conversation.append({"role": role, "text": text})
        self._save()

    def _load(self) -> list[dict[str, str]] | None:
        data = self.store.load(STORAGE_KEY, default=None)
        # maintain backward compatibility: if the local json file exists, prefer it
        if data is None and self.storage_file.exists():
            try:
                return json.loads(self.storage_file.read_text(encoding="utf-8"))
            except Exception:
                return []
        return data

    def _save(self) -> None:
        # keep a local JSON copy for convenience and compatibility
        try:
            self.storage_file.write_text(json.dumps(self.conversation, indent=2), encoding="utf-8")
        except Exception:
            pass
        self.store.save(STORAGE_KEY, self.conversation)

    def get_recent(self, limit: int = 5) -> list[dict[str, str]]:
        return self.conversation[-limit:]

    def find_user_facts(self) -> dict[str, str]:
        facts: dict[str, str] = {}
        for message in self.conversation:
            if message["role"] != "user":
                continue
            match = re.search(r"i am (?:called|named)?\s*(.+?)($|\.|!|\?)", message["text"], re.I)
            if match:
                facts["name"] = match.group(1).strip()
        return facts


class Mind:
    """A lightweight reasoning layer for the chatbot.

    `Mind` coordinates memory, repository search and the optional
    `InvestmentAgent` to produce richer, multi-step responses.
    """
    def __init__(self, bot: 'ChatBot') -> None:
        self.bot = bot

    def think(self, query: str) -> str:
        q = query.strip()
        # delegate explicit research requests
        if q.lower().startswith('research '):
            parts = q.split()
            if len(parts) >= 3:
                ticker, website = parts[1], parts[2]
                if self.bot.investment_agent is None:
                    from brain import InvestmentAgent

                    self.bot.investment_agent = InvestmentAgent()
                return self.bot.investment_agent.research_company(ticker, website)
            return "Usage: research TICKER WEBSITE_URL"

        # detect simple ticker queries like 'AAPL' or 'research AAPL'
        ticker_match = None
        m = __import__('re')
        for token in re.split(r"\s+", q):
            if m.fullmatch(r"[A-Za-z]{1,5}", token):
                ticker_match = token.upper()
                break

        if ticker_match:
            try:
                # lazy import to avoid extra deps at import time
                from src.tools.market_data import MarketDataTool
                md = MarketDataTool()
                summary = md.get_financial_summary(ticker_match)
                # if the query includes a URL, try to scrape it and include text
                url_match = None
                url_search = re.search(r"https?://\S+", q)
                scraped_text = None
                if url_search:
                    url_match = url_search.group(0)
                    try:
                        from src.tools.scraper import WebScraperTool

                        scraper = WebScraperTool()
                        scraped_text = scraper.get_text_from_url(url_match, max_chars=800)
                    except Exception:
                        scraped_text = None
                # persist summary and optional scraped text to chat memory for later retrieval
                try:
                    import json as _json

                    msg = {"market_summary": summary}
                    if scraped_text:
                        msg["scraped_text_snippet"] = scraped_text
                    self.bot.memory.add_message("assistant", f"Market summary for {ticker_match}: {_json.dumps(msg, indent=2)}")
                except Exception:
                    # best-effort only
                    self.bot.memory.add_message("assistant", f"Market summary for {ticker_match} saved.")

                # return a concise summary to the user
                out = (
                    f"Market summary ({summary.get('source')}): ticker={summary.get('ticker')}, "
                    f"market_cap={summary.get('market_cap')}, pe={summary.get('pe_ratio')}, "
                    f"latest_price={summary.get('price_history_30d')[-1] if summary.get('price_history_30d') else 'N/A'}"
                )
                if scraped_text:
                    out += f"\nWebsite snippet: {scraped_text[:300]}"
                return out
            except Exception as exc:
                # continue to generic reasoning if market fetch fails
                summary_err = f"(market fetch failed: {exc})"
                # fall through and include in the reasoning output
                pass

        # Build a short analysis using memory and a repo-scan
        parts = [p for p in re.split(r"\s+", q) if p]
        head = ' '.join(parts[:4])
        summary: list[str] = []
        summary.append(f"Question: {q}")
        facts = self.bot.memory.find_user_facts()
        if facts:
            summary.append(f"Known facts: {facts}")

        # run a lightweight repo search on leading keywords
        try:
            search_text = self.bot._handle_search(f"/search {head}")
        except Exception:
            search_text = "(repo search failed)"
        summary.append("Repository scan:\n" + search_text)

        summary.append("Suggested plan:\n1) Clarify the goal. 2) Gather sources with `/search`. 3) If actionable, call `/research` or request code changes.")

        return "\n\n".join(summary)


class ChatBot:
    def __init__(self) -> None:
        self.memory = ChatMemory()
        self.investment_agent: Optional['InvestmentAgent'] = None
        self.mind = Mind(self)

    def run(self) -> None:
        self._print_welcome()
        while True:
            try:
                prompt = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye!")
                break

            if not prompt:
                continue

            # research command: '/research TICKER WEBSITE_URL' or 'research TICKER WEBSITE_URL'
            if prompt.lower().startswith("/research") or prompt.lower().startswith("research "):
                response = self._handle_research(prompt)
                self.memory.add_message("user", prompt)
                self.memory.add_message("assistant", response)
                print(f"Bot: {response}")
                continue

            # search command: '/search QUERY' or 'search QUERY'
            if prompt.lower().startswith("/search") or prompt.lower().startswith("search "):
                response = self._handle_search(prompt)
                self.memory.add_message("user", prompt)
                self.memory.add_message("assistant", response)
                print(f"Bot: {response}")
                continue

            # think command: '/think QUESTION' or 'think QUESTION'
            if prompt.lower().startswith("/think") or prompt.lower().startswith("think "):
                response = self._handle_think(prompt)
                self.memory.add_message("user", prompt)
                self.memory.add_message("assistant", response)
                print(f"Bot: {response}")
                continue

            response = self.generate_response(prompt)
            self.memory.add_message("user", prompt)
            self.memory.add_message("assistant", response)
            print(f"Bot: {response}")

            if self._is_exit_command(prompt):
                break

    def generate_response(self, text: str) -> str:
        text_lower = text.lower()

        if self._is_exit_command(text):
            return "Goodbye! I’ll remember our chat."

        if self._is_thanks(text_lower):
            return "You’re welcome! Anything else you’d like to talk about?"

        if self._is_greeting(text_lower):
            return self._greeting_response()

        if "remember" in text_lower and "that" in text_lower:
            return self._remember_fact(text)

        facts = self.memory.find_user_facts()
        if "name" in facts and re.search(r"what is my name|who am i", text_lower):
            return f"You told me your name is {facts['name']}."

        if "name" in facts and re.search(r"my name|call me", text_lower):
            return f"I remember your name is {facts['name']}."

        if "name" in text_lower and ("my name" in text_lower or "call me" in text_lower):
            return "Nice to meet you. I’ll remember your name for the next conversation."

        return self._fallback_response()

    def _handle_research(self, prompt: str) -> str:
        parts = prompt.split()
        # support '/research' prefix
        if parts[0].startswith('/'):
            parts[0] = parts[0].lstrip('/')

        if len(parts) < 3:
            return "Usage: /research TICKER WEBSITE_URL"

        _, ticker, website = parts[0], parts[1], parts[2]

        try:
            if self.investment_agent is None:
                # lazy import to avoid importing optional dependencies at startup
                from brain import InvestmentAgent

                self.investment_agent = InvestmentAgent()

            result = self.investment_agent.research_company(ticker, website)
            return result
        except Exception as exc:
            return f"Research failed: {exc}"

    def _handle_search(self, prompt: str) -> str:
        parts = prompt.split(maxsplit=1)
        # support '/search' prefix
        if parts[0].startswith('/'):
            parts[0] = parts[0].lstrip('/')

        if len(parts) < 2 or not parts[1].strip():
            return "Usage: /search QUERY"

        query = parts[1].strip()

        import os

        results: list[str] = []
        max_results = 10
        for root, dirs, files in os.walk('.'):
            # skip common large/irrelevant dirs
            if any(skip in root for skip in ['.git', 'venv', 'node_modules', 'data_store', 'chat_memory']):
                continue
            for fname in files:
                path = os.path.join(root, fname)
                try:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as fh:
                        for lineno, line in enumerate(fh, 1):
                            if query.lower() in line.lower():
                                snippet = line.strip()
                                results.append(f"{path}:{lineno}: {snippet}")
                                if len(results) >= max_results:
                                    break
                except Exception:
                    continue
            if len(results) >= max_results:
                break

        if not results:
            return f"No matches for '{query}'."

        return "Search results:\n" + "\n".join(results)

    def _handle_think(self, prompt: str) -> str:
        parts = prompt.split(maxsplit=1)
        # support '/think' prefix
        if parts[0].startswith('/'):
            parts[0] = parts[0].lstrip('/')

        if len(parts) < 2 or not parts[1].strip():
            return "Usage: /think QUESTION"

        query = parts[1].strip()
        try:
            result = self.mind.think(query)
            return result
        except Exception as exc:
            return f"Thinking failed: {exc}"

    def _greeting_response(self) -> str:
        facts = self.memory.find_user_facts()
        if "name" in facts:
            return f"Hello again, {facts['name']}! What would you like to discuss today?"
        return "Hello! I’m your local chatbot. What would you like to talk about?"

    def _remember_fact(self, text: str) -> str:
        match = re.search(r"remember that (.+)", text, re.I)
        if match:
            fact = match.group(1).strip()
            self.memory.add_message("assistant", f"I will remember that: {fact}")
            return f"Okay, I’ll remember that: {fact}"
        return "Sure, what would you like me to remember?"

    def _is_greeting(self, text_lower: str) -> bool:
        return any(word in text_lower for word in ["hello", "hi", "hey", "good morning", "good afternoon", "good evening"])

    def _is_thanks(self, text_lower: str) -> bool:
        return any(word in text_lower for word in ["thanks", "thank you", "thx"])

    def _is_exit_command(self, text: str) -> bool:
        return bool(re.fullmatch(r"(quit|exit|bye|goodbye|stop|end)(\W*)", text.strip().lower()))

    def _fallback_response(self) -> str:
        return (
            "I’m a simple local chatbot. Tell me more, or ask me to remember something. "
            "You can say ‘quit’ to end the conversation."
        )

    def _print_welcome(self) -> None:
        print("Simple Chatbot")
        print("Type a message and press Enter. Type 'quit' to exit.")
        recent = self.memory.get_recent()
        if recent:
            print(f"Loaded {len(recent)} recent messages from memory.")


def main() -> None:
    bot = ChatBot()
    bot.run()


if __name__ == "__main__":
    main()
