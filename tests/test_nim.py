from __future__ import annotations

import asyncio
from types import SimpleNamespace

from redclaw.skills import skill_nim


class FakeMemoryItem:
    def __init__(self, category, value):
        self.category = category
        self.value = value


class FakeResponse:
    status_code = 200
    headers = {}
    text = ""

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
        nvidia_nim_rpm_limit=36,
    )
    memory = SimpleNamespace(
        recent_conversation=lambda limit=10: [
            FakeMemoryItem("conversation", "user: Wir bauen RedClaw"),
            FakeMemoryItem("conversation", "assistant: Ich habe das Dashboard erstellt"),
        ],
        search=lambda prompt, limit=8: [FakeMemoryItem("facts", "Redcrafter nutzt Raspberry Pi 5")],
        list_by_category=lambda category, limit=8: [FakeMemoryItem("files", "Erstellte/geschriebene Datei: /home/redcraft/redclaw_workspace/notiz.txt")]
        if category == "files"
        else [],
    )
    return SimpleNamespace(settings=settings, memory=memory)


def test_nim_uses_fast_payload_for_normal_questions(monkeypatch):
    FakeClient.payloads = []
    monkeypatch.setattr(skill_nim.httpx, "AsyncClient", FakeClient)

    answer = asyncio.run(skill_nim.run("NIM was ist los?", make_context()))

    assert answer == "ok"
    assert FakeClient.payloads[0]["max_tokens"] == 768
    assert "chat_template_kwargs" not in FakeClient.payloads[0]


def test_nim_allows_long_payload_for_explicit_long_answers(monkeypatch):
    FakeClient.payloads = []
    monkeypatch.setattr(skill_nim.httpx, "AsyncClient", FakeClient)

    asyncio.run(skill_nim.run("erkläre das ausführlich", make_context()))

    assert FakeClient.payloads[0]["max_tokens"] == 16384
    assert FakeClient.payloads[0]["chat_template_kwargs"] == {"enable_thinking": True}


def test_nim_includes_memory_context(monkeypatch):
    FakeClient.payloads = []
    monkeypatch.setattr(skill_nim.httpx, "AsyncClient", FakeClient)

    asyncio.run(skill_nim.run("wo liegt die notiz?", make_context()))

    system = FakeClient.payloads[0]["messages"][0]["content"]
    assert "Wir bauen RedClaw" in system
    assert "Raspberry Pi 5" in system
    assert "/home/redcraft/redclaw_workspace/notiz.txt" in system


def test_nim_retries_rate_limited_requests(monkeypatch):
    class RetryResponse(FakeResponse):
        calls = 0

        def __init__(self, status_code):
            self.status_code = status_code
            self.headers = {"retry-after": "0"}
            self.text = "rate limited"

        def json(self):
            return {"choices": [{"message": {"content": "retry-ok"}}]}

        def raise_for_status(self):
            if self.status_code >= 400:
                request = httpx.Request("POST", "https://example.test")
                raise httpx.HTTPStatusError("error", request=request, response=httpx.Response(self.status_code, request=request, text=self.text))

    class RetryClient(FakeClient):
        async def post(self, endpoint, headers, json):
            RetryResponse.calls += 1
            return RetryResponse(429 if RetryResponse.calls == 1 else 200)

    import httpx

    monkeypatch.setattr(skill_nim.httpx, "AsyncClient", RetryClient)
    answer = asyncio.run(skill_nim.run("NIM test", make_context()))

    assert answer == "retry-ok"
    assert RetryResponse.calls == 2


def test_nim_circuit_breaker_after_failures(monkeypatch):
    skill_nim._consecutive_failures = 0
    skill_nim._circuit_open_until = 0

    class FailingResponse(FakeResponse):
        status_code = 503
        headers = {"retry-after": "0"}
        text = "down"

        def raise_for_status(self):
            request = httpx.Request("POST", "https://example.test")
            raise httpx.HTTPStatusError("error", request=request, response=httpx.Response(503, request=request, text="down"))

    class FailingClient(FakeClient):
        async def post(self, endpoint, headers, json):
            return FailingResponse()

    import httpx

    monkeypatch.setattr(skill_nim.httpx, "AsyncClient", FailingClient)
    context = make_context()
    for _ in range(3):
        asyncio.run(skill_nim.run("NIM test", context))

    answer = asyncio.run(skill_nim.run("NIM test", context))
    assert "Cooldown" in answer
