"""Enhanced WebScraperTool for local testing.

Behavior:
- If `requests` and `bs4` (BeautifulSoup) are installed the tool will fetch
  the URL and extract visible paragraph text.
- Otherwise it returns a small, safe placeholder string.
"""
from __future__ import annotations

from typing import Optional


class WebScraperTool:
    def __init__(self) -> None:
        # detect optional dependencies
        try:
            import requests  # type: ignore
            from bs4 import BeautifulSoup  # type: ignore

            self._requests = requests
            self._bs4 = BeautifulSoup
        except Exception:
            self._requests = None
            self._bs4 = None

    def get_text_from_url(self, url: str, max_chars: int = 2000) -> str:
        """Fetch and extract text from `url` when possible, else a placeholder.

        The method is defensive: network failures or parsing errors return a
        concise placeholder rather than raising.
        """
        url = (url or "").strip()
        if not url:
            return ""

        if self._requests and self._bs4:
            try:
                resp = self._requests.get(url, timeout=5)
                resp.raise_for_status()
                soup = self._bs4(resp.text, "html.parser")
                paragraphs = [p.get_text(separator=" ", strip=True) for p in soup.find_all("p")]
                text = "\n\n".join(paragraphs).strip()
                if not text:
                    # fall back to page title or meta description
                    title = soup.title.string if soup.title else ""
                    desc = ""
                    d = soup.find("meta", attrs={"name": "description"})
                    if d and d.get("content"):
                        desc = d.get("content")
                    text = (title + "\n" + desc).strip()

                return text[:max_chars]
            except Exception:
                return f"[scrape-failed placeholder for {url}]"

        return f"[scraped content placeholder for {url}] This is fallback text."
