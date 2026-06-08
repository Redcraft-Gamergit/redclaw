from __future__ import annotations

import asyncio
import re
import time
from collections import deque
from typing import Any

import httpx

SKILL = {
    "name": "nim",
    "description": "Nutzt NVIDIA NIM ueber den OpenAI-kompatiblen Chat-Endpunkt.",
    "permissions": ["network", "llm"],
    "enabled": True,
}

_request_times: deque[float] = deque()
_rate_lock = asyncio.Lock()
_circuit_open_until = 0.0
_consecutive_failures = 0


async def run(query, context):
    if not context.settings.nvidia_nim_api_key:
        return "NVIDIA NIM API-Key fehlt. Du kannst ihn in der Web-Config oder per NVIDIA_NIM_API_KEY setzen."

    global _consecutive_failures
    cooldown = _cooldown_seconds()
    if cooldown > 0:
        return f"NVIDIA NIM ist gerade im Cooldown ({cooldown}s), weil die API zuletzt mehrfach nicht sauber geantwortet hat."

    prompt = re.sub(r"\b(nvidia|nim)\b", "", query, flags=re.IGNORECASE).strip() or query
    lowered_prompt = prompt.lower()
    wants_long_answer = any(
        word in lowered_prompt
        for word in ("ausfuehrlich", "ausführlich", "detail", "lange antwort", "lang erklaeren", "lang erklären", "essay", "komplett")
    )
    max_tokens = context.settings.nvidia_nim_max_tokens if wants_long_answer else min(context.settings.nvidia_nim_max_tokens, 768)
    enable_thinking = context.settings.nvidia_nim_enable_thinking and wants_long_answer
    memory_context = _build_memory_context(prompt, context)

    endpoint = context.settings.nvidia_nim_base_url.rstrip("/") + "/chat/completions"
    payload: dict[str, Any] = {
        "model": context.settings.nvidia_nim_model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Du bist RedClaw, ein knapper deutscher Assistent fuer Redcrafter. "
                    "Nutze den Memory-Kontext, um dich an fruehere Nachrichten, Themen und Dateiorte zu erinnern. "
                    "Wenn du eine Datei erwaehnst, nenne den bekannten Pfad. Antworte direkt, klar und ohne lange Vorrede."
                    f"\n\n{memory_context}"
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": context.settings.nvidia_nim_temperature,
        "top_p": context.settings.nvidia_nim_top_p,
        "max_tokens": max_tokens,
    }
    if enable_thinking:
        payload["chat_template_kwargs"] = {"enable_thinking": True}

    headers = {
        "Authorization": f"Bearer {context.settings.nvidia_nim_api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    timeout = httpx.Timeout(context.settings.nvidia_nim_timeout, connect=10)

    try:
        await _wait_for_rate_slot(max(1, int(getattr(context.settings, "nvidia_nim_rpm_limit", 36))))
        async with httpx.AsyncClient(timeout=timeout) as client:
            data = await _post_with_retries(client, endpoint, headers, payload)
    except httpx.TimeoutException:
        _mark_failure()
        return "NVIDIA NIM war zu langsam. Ich habe abgebrochen, damit RedClaw nicht haengt. Nutze eine kuerzere Frage oder deaktiviere Thinking."
    except httpx.HTTPStatusError as exc:
        _mark_failure()
        status = exc.response.status_code
        if status == 401:
            return "NVIDIA NIM lehnt den API-Key ab (401). Pruefe den Key in der Web-Config."
        if status == 429:
            return "NVIDIA NIM ist rate-limited. Ich warte automatisch, aber diese Anfrage wurde abgelehnt."
        if status in {500, 502, 503, 504}:
            return f"NVIDIA NIM ist gerade instabil ({status}). Versuche es gleich nochmal oder nutze eine kuerzere Anfrage."
        return f"NVIDIA NIM Fehler {status}: {_safe_error_text(exc.response)}"
    except (httpx.HTTPError, ValueError, KeyError, IndexError) as exc:
        _mark_failure()
        return f"NVIDIA NIM konnte nicht sauber antworten: {type(exc).__name__}"

    _consecutive_failures = 0
    return _extract_answer(data)


async def _wait_for_rate_slot(rpm_limit: int) -> None:
    window = 60.0
    now = time.monotonic()
    async with _rate_lock:
        while _request_times and now - _request_times[0] >= window:
            _request_times.popleft()
        if len(_request_times) >= rpm_limit:
            wait = window - (now - _request_times[0]) + 0.1
            await asyncio.sleep(max(wait, 0.1))
            now = time.monotonic()
            while _request_times and now - _request_times[0] >= window:
                _request_times.popleft()
        _request_times.append(now)


async def _post_with_retries(client: httpx.AsyncClient, endpoint: str, headers: dict[str, str], payload: dict[str, Any]) -> dict[str, Any]:
    retry_statuses = {408, 429, 500, 502, 503, 504}
    for attempt in range(3):
        response = await client.post(endpoint, headers=headers, json=payload)
        if response.status_code not in retry_statuses:
            response.raise_for_status()
            return response.json()
        if attempt == 2:
            response.raise_for_status()
        await asyncio.sleep(_retry_delay(response, attempt))
    raise RuntimeError("unreachable")


def _retry_delay(response: httpx.Response, attempt: int) -> float:
    raw = response.headers.get("retry-after")
    if raw:
        try:
            return min(float(raw), 20.0)
        except ValueError:
            pass
    return min(2.0 * (attempt + 1), 8.0)


def _mark_failure() -> None:
    global _consecutive_failures, _circuit_open_until
    _consecutive_failures += 1
    if _consecutive_failures >= 3:
        _circuit_open_until = time.monotonic() + 60


def _cooldown_seconds() -> int:
    remaining = _circuit_open_until - time.monotonic()
    return max(0, int(remaining) + 1)


def _extract_answer(data: dict[str, Any]) -> str:
    answer = data["choices"][0]["message"]["content"]
    if isinstance(answer, list):
        parts = []
        for part in answer:
            if isinstance(part, dict):
                parts.append(str(part.get("text") or part.get("content") or ""))
            else:
                parts.append(str(part))
        answer = "\n".join(part for part in parts if part)
    answer = str(answer).strip()
    return answer or "NVIDIA NIM hat leer geantwortet."


def _safe_error_text(response: httpx.Response) -> str:
    text = response.text.strip().replace("\n", " ")
    return text[:240] if text else "keine Fehlerdetails"


def _build_memory_context(prompt: str, context) -> str:
    lines = ["Memory-Kontext:"]
    recent = context.memory.recent_conversation(limit=6)
    if recent:
        lines.append("Letzte Nachrichten:")
        for item in recent:
            lines.append(f"- {item.value}")
    matches = context.memory.search(prompt, limit=5) if prompt.strip() else []
    matches = [item for item in matches if item.category != "conversation"]
    if matches:
        lines.append("Relevante gespeicherte Fakten:")
        for item in matches:
            lines.append(f"- [{item.category}] {item.value}")
    files = context.memory.list_by_category("files", limit=5)
    if files:
        lines.append("Bekannte Dateien:")
        for item in files:
            lines.append(f"- {item.value}")
    if len(lines) == 1:
        lines.append("- Noch kein Kontext gespeichert.")
    return "\n".join(lines)[:3500]
