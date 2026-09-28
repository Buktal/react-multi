"""Read-only Wikipedia tools with explicit page IDs, not shared current-page state."""

import html
import re
from typing import Any

import httpx

from .engine import Tool

API_URL = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "ReAct-M/0.1 (https://github.com/Buktal/ReAct-M; research example)"


def wikipedia_tools(*, client: httpx.AsyncClient | None = None) -> list[Tool]:
    async def request(params: dict[str, str]) -> dict[str, Any]:
        params = {"action": "query", "format": "json", "utf8": "1", **params}
        try:
            if client is not None:
                response = await client.get(
                    API_URL, params=params, headers={"User-Agent": USER_AGENT}, timeout=15
                )
            else:
                async with httpx.AsyncClient(timeout=15) as session:
                    response = await session.get(
                        API_URL, params=params, headers={"User-Agent": USER_AGENT}
                    )
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Wikipedia request failed ({type(exc).__name__})") from None
        if response.status_code != 200:
            raise RuntimeError(f"Wikipedia returned HTTP {response.status_code}")
        data = response.json()
        if "error" in data or "query" not in data:
            raise ValueError("Wikipedia did not return a query result")
        return data["query"]

    async def search(query: str) -> dict[str, Any]:
        data = await request({"list": "search", "srsearch": query, "srlimit": "5"})
        return {
            "matches": [
                {
                    "id": str(item["pageid"]),
                    "title": item["title"],
                    "snippet": html.unescape(re.sub(r"<[^>]+>", "", item.get("snippet", ""))),
                }
                for item in data.get("search", [])
            ]
        }

    async def read(doc_id: str) -> dict[str, Any]:
        data = await request({"prop": "extracts", "explaintext": "1", "pageids": doc_id})
        page = data.get("pages", {}).get(doc_id, {})
        if "missing" in page or not page.get("extract"):
            raise ValueError(f"Wikipedia page {doc_id} is missing or has no plain-text extract")
        extract = page["extract"]
        return {
            "title": page["title"],
            "text": extract[:12000],
            "source_url": f"https://en.wikipedia.org/?curid={doc_id}",
            "truncated": len(extract) > 12000,
        }

    return [
        Tool(
            "search",
            "Search English Wikipedia. Returns up to five matches with id, title, snippet.",
            {
                "type": "object",
                "properties": {"query": {"type": "string", "minLength": 1}},
                "required": ["query"],
                "additionalProperties": False,
            },
            search,
            timeout=20,
            retry_safe=True,
        ),
        Tool(
            "read",
            "Read a Wikipedia page by its numeric ID; returns text and source_url. "
            "Text is limited to 12000 characters and marked when truncated.",
            {
                "type": "object",
                "properties": {"doc_id": {"type": "string", "pattern": "^[0-9]+$"}},
                "required": ["doc_id"],
                "additionalProperties": False,
            },
            read,
            timeout=20,
            retry_safe=True,
        ),
    ]
