from __future__ import annotations

import asyncio
from types import SimpleNamespace

from redclaw.skills import skill_search


class FakeMemory:
    def __init__(self):
        self.saved = []

    def save(self, *args, **kwargs):
        self.saved.append((args, kwargs))


def test_clean_search_query():
    assert skill_search.clean_search_query("suche RedClaw") == "RedClaw"
    assert skill_search.clean_search_query("websuche NVIDIA NIM") == "NVIDIA NIM"
    assert skill_search.clean_search_query("internetsuche Raspberry Pi") == "Raspberry Pi"


def test_duckduckgo_parser_extracts_results():
    html = """
    <a class="result__a" href="/l/?uddg=https%3A%2F%2Fexample.com">Example Result</a>
    <a class="result__snippet">A small description.</a>
    """
    parser = skill_search.DuckDuckGoParser()
    parser.feed(html)

    assert parser.results[0].title == "Example Result"
    assert parser.results[0].url == "https://example.com"
    assert parser.results[0].description == "A small description."


def test_search_run_saves_results(monkeypatch):
    async def fake_search(query, context, limit=5):
        return [skill_search.SearchResult("Title", "https://example.com", "Desc", "Test")]

    memory = FakeMemory()
    context = SimpleNamespace(settings=SimpleNamespace(brave_search_api_key=""), memory=memory, source="test")
    monkeypatch.setattr(skill_search, "search_web", fake_search)

    answer = asyncio.run(skill_search.run("suche test", context))

    assert "Websuche fuer: test" in answer
    assert "Title" in answer
    assert memory.saved
