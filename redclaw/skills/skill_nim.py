from __future__ import annotations

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
    prompt = query.replace("nvidia", "").replace("nim", "").strip() or query
    endpoint = context.settings.nvidia_nim_base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": context.settings.nvidia_nim_model,
        "messages": [
            {"role": "system", "content": "Du bist RedClaw, ein knapper deutscher Assistent."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.4,
        "max_tokens": 700,
    }
    headers = {"Authorization": f"Bearer {context.settings.nvidia_nim_api_key}"}
    async with httpx.AsyncClient(timeout=45) as client:
        response = await client.post(endpoint, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
    return data["choices"][0]["message"]["content"]
