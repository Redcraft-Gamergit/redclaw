from __future__ import annotations

from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
from urllib.parse import parse_qs, unquote, urlparse

import httpx

SKILL = {
    "name": "search",
    "description": "Sucht im Web ueber Brave Search oder ohne Key per DuckDuckGo-Fallback.",
    "permissions": ["network"],
    "enabled": True,
}


@dataclass
class SearchResult:
    title: str
    url: str
    description: str
    source: str


async def run(query, context):
    clean_query = clean_search_query(query)
    if not clean_query:
        return "Wonach soll ich suchen?"

    try:
        results = await search_web(clean_query, context)
    except httpx.TimeoutException:
        return "Die Internetsuche war zu langsam. Versuch es gleich nochmal oder formuliere kuerzer."
    except httpx.HTTPError as exc:
        return f"Internetsuche fehlgeschlagen: {type(exc).__name__}"

    if not results:
        return "Ich habe keine passenden Suchergebnisse gefunden."

    for item in results[:5]:
        context.memory.save("search", f"{clean_query}:{item.url}", f"{item.title} - {item.url}", source=context.source, confidence=0.74)

    return format_results(clean_query, results)


async def search_web(query: str, context, limit: int = 5) -> list[SearchResult]:
    if context.settings.brave_search_api_key:
        results = await _search_brave(query, context.settings.brave_search_api_key, limit=limit)
        if results:
            return results
    return await _search_duckduckgo(query, limit=limit)


def clean_search_query(query: str) -> str:
    clean = query.strip()
    for prefix in ("websuche", "suche im internet nach", "internet suche", "internetsuche", "suche"):
        if clean.lower().startswith(prefix):
            clean = clean[len(prefix) :].strip(" :,-")
            break
    return clean or query.strip()


async def _search_brave(query: str, api_key: str, limit: int = 5) -> list[SearchResult]:
    headers = {"X-Subscription-Token": api_key, "Accept": "application/json"}
    params = {"q": query, "count": limit, "country": "de", "search_lang": "de"}
    async with httpx.AsyncClient(timeout=12, follow_redirects=True) as client:
        response = await client.get("https://api.search.brave.com/res/v1/web/search", headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
    items = data.get("web", {}).get("results", [])
    return [
        SearchResult(
            title=str(item.get("title") or "Ohne Titel"),
            url=str(item.get("url") or ""),
            description=str(item.get("description") or ""),
            source="Brave",
        )
        for item in items[:limit]
        if item.get("url")
    ]


async def _search_duckduckgo(query: str, limit: int = 5) -> list[SearchResult]:
    headers = {
        "User-Agent": "RedClaw/1.0 (+https://local.redclaw)",
        "Accept": "text/html,application/xhtml+xml",
    }
    async with httpx.AsyncClient(timeout=12, follow_redirects=True, headers=headers) as client:
        response = await client.get("https://html.duckduckgo.com/html/", params={"q": query, "kl": "de-de"})
        response.raise_for_status()
    parser = DuckDuckGoParser()
    parser.feed(response.text)
    return parser.results[:limit]


def format_results(query: str, results: list[SearchResult]) -> str:
    lines = [f"Websuche fuer: {query}"]
    for index, item in enumerate(results[:5], 1):
        desc = f"\n  {item.description}" if item.description else ""
        lines.append(f"{index}. {item.title}\n  {item.url}{desc}\n  Quelle: {item.source}")
    return "\n".join(lines)


class DuckDuckGoParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.results: list[SearchResult] = []
        self._current: dict[str, str] | None = None
        self._capture: str | None = None
        self._chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs):
        attrs_dict = dict(attrs)
        classes = set(attrs_dict.get("class", "").split())
        if tag == "a" and "result__a" in classes:
            self._current = {"url": _clean_duckduckgo_url(attrs_dict.get("href", "")), "title": "", "description": ""}
            self._capture = "title"
            self._chunks = []
        elif self._current is not None and tag in {"a", "div"} and ("result__snippet" in classes or "result__body" in classes):
            self._capture = "description"
            self._chunks = []

    def handle_data(self, data: str):
        if self._capture:
            self._chunks.append(data)

    def handle_endtag(self, tag: str):
        if self._current is None or self._capture is None:
            return
        if self._capture == "title" and tag == "a":
            self._current["title"] = _clean_text(" ".join(self._chunks))
            self._capture = None
            self._chunks = []
        elif self._capture == "description" and tag in {"a", "div"}:
            self._current["description"] = _clean_text(" ".join(self._chunks))
            self._capture = None
            self._chunks = []
            self._finish_current()

    def _finish_current(self):
        if not self._current:
            return
        title = self._current.get("title", "")
        url = self._current.get("url", "")
        if title and url and not any(item.url == url for item in self.results):
            self.results.append(SearchResult(title=title, url=url, description=self._current.get("description", ""), source="DuckDuckGo"))
        self._current = None


def _clean_text(text: str) -> str:
    return " ".join(unescape(text).split())


def _clean_duckduckgo_url(url: str) -> str:
    parsed = urlparse(unescape(url))
    if parsed.path == "/l/":
        target = parse_qs(parsed.query).get("uddg", [""])[0]
        if target:
            return unquote(target)
    return unescape(url)
