from __future__ import annotations

import asyncio
from types import SimpleNamespace

from redclaw.skills import skill_nim


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {"choices": [{"message": {"content": "ok"}}]}


class FakeClient:
    payloads = []

    def __init__(self, timeout):
        self.timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def post(self, endpoint, headers, json):
        self.payloads.append(json)
        return FakeResponse()


def make_context():
    settings = SimpleNamespace(
        nvidia_nim_api_key="test-key",
        nvidia_nim_base_url="https://example.test/v1",
        nvidia_nim_model="test-model",
        nvidia_nim_max_tokens=16384,
        nvidia_nim_temperature=1.0,
        nvidia_nim_top_p=0.95,
        nvidia_nim_enable_thinking=True,
        nvidia_nim_timeout=240,
    )
    return SimpleNamespace(settings=settings)


def test_nim_uses_fast_payload_for_normal_questions(monkeypatch):
    FakeClient.payloads = []
    monkeypatch.setattr(skill_nim.httpx, "AsyncClient", FakeClient)

    answer = asyncio.run(skill_nim.run("NIM was ist los?", make_context()))

    assert answer == "ok"
    assert FakeClient.payloads[0]["max_tokens"] == 1024
    assert "chat_template_kwargs" not in FakeClient.payloads[0]


def test_nim_allows_long_payload_for_explicit_long_answers(monkeypatch):
    FakeClient.payloads = []
    monkeypatch.setattr(skill_nim.httpx, "AsyncClient", FakeClient)

    asyncio.run(skill_nim.run("erkläre das ausführlich", make_context()))

    assert FakeClient.payloads[0]["max_tokens"] == 16384
    assert FakeClient.payloads[0]["chat_template_kwargs"] == {"enable_thinking": True}
