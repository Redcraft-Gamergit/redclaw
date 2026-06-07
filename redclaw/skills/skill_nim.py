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
        "temperature": context.settings.nvidia_nim_temperature,
        "top_p": context.settings.nvidia_nim_top_p,
        "max_tokens": context.settings.nvidia_nim_max_tokens,
    }
    if context.settings.nvidia_nim_enable_thinking:
        payload["chat_template_kwargs"] = {"enable_thinking": True}
    headers = {"Authorization": f"Bearer {context.settings.nvidia_nim_api_key}"}
    try:
        async with httpx.AsyncClient(timeout=context.settings.nvidia_nim_timeout) as client:
            response = await client.post(endpoint, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
    except httpx.TimeoutException:
        return "NVIDIA NIM hat nicht rechtzeitig geantwortet. Das Modell ist erreichbar, braucht aber länger; erhöhe `NVIDIA_NIM_TIMEOUT` oder nutze ein kleineres Modell."
    return data["choices"][0]["message"]["content"]
