from __future__ import annotations

import re

import httpx

SKILL = {
    "name": "nim",
    "description": "Nutzt NVIDIA NIM über den OpenAI-kompatiblen Chat-Endpunkt.",
    "permissions": ["network", "llm"],
    "enabled": True,
}


async def run(query, context):
    if not context.settings.nvidia_nim_api_key:
        return "NVIDIA NIM API-Key fehlt. Du kannst ihn in der Web-Config oder per NVIDIA_NIM_API_KEY setzen."

    prompt = re.sub(r"\b(nvidia|nim)\b", "", query, flags=re.IGNORECASE).strip() or query
    wants_long_answer = any(
        word in prompt.lower()
        for word in ("ausführlich", "detail", "lange antwort", "lang erklären", "essay", "komplett")
    )
    max_tokens = context.settings.nvidia_nim_max_tokens if wants_long_answer else min(context.settings.nvidia_nim_max_tokens, 1024)
    enable_thinking = context.settings.nvidia_nim_enable_thinking and wants_long_answer
    memory_context = _build_memory_context(prompt, context)

    endpoint = context.settings.nvidia_nim_base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": context.settings.nvidia_nim_model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Du bist RedClaw, ein knapper deutscher Assistent für Redcrafter. "
                    "Nutze den Memory-Kontext, um dich an frühere Nachrichten, Themen und Dateiorte zu erinnern. "
                    "Wenn du eine Datei erwähnst, nenne den bekannten Pfad. Antworte direkt, klar und ohne lange Vorrede."
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

    headers = {"Authorization": f"Bearer {context.settings.nvidia_nim_api_key}"}
    try:
        async with httpx.AsyncClient(timeout=context.settings.nvidia_nim_timeout) as client:
            response = await client.post(endpoint, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
    except httpx.TimeoutException:
        return "NVIDIA NIM war zu langsam. Ich habe die Anfrage abgebrochen, damit RedClaw nicht hängt. Nutze eine kürzere Frage oder deaktiviere Thinking in der Config."
    return data["choices"][0]["message"]["content"]


def _build_memory_context(prompt: str, context) -> str:
    lines = ["Memory-Kontext:"]
    recent = context.memory.recent_conversation(limit=10)
    if recent:
        lines.append("Letzte Nachrichten:")
        for item in recent:
            lines.append(f"- {item.value}")
    matches = context.memory.search(prompt, limit=8) if prompt.strip() else []
    matches = [item for item in matches if item.category != "conversation"]
    if matches:
        lines.append("Relevante gespeicherte Fakten:")
        for item in matches:
            lines.append(f"- [{item.category}] {item.value}")
    files = context.memory.list_by_category("files", limit=8)
    if files:
        lines.append("Bekannte Dateien:")
        for item in files:
            lines.append(f"- {item.value}")
    if len(lines) == 1:
        lines.append("- Noch kein Kontext gespeichert.")
    return "\n".join(lines)
