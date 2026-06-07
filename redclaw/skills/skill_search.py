from __future__ import annotations

import httpx

SKILL = {
    "name": "search",
    "description": "Sucht im Web ueber Brave Search API.",
    "permissions": ["network"],
    "enabled": True,
}


async def run(query, context):
    api_key = context.settings.brave_search_api_key
    if not api_key:
        return "Brave Search API-Key fehlt. Du kannst ihn in der Web-Config setzen."
    clean_query = query.replace("websuche", "").replace("suche", "").strip() or query
    headers = {"X-Subscription-Token": api_key}
    params = {"q": clean_query, "count": 5, "country": "de", "search_lang": "de"}
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get("https://api.search.brave.com/res/v1/web/search", headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
    results = data.get("web", {}).get("results", [])
    if not results:
        return "Ich habe keine passenden Suchergebnisse gefunden."
    lines = [f"Websuche fuer: {clean_query}"]
    for item in results[:5]:
        title = item.get("title", "Ohne Titel")
        url = item.get("url", "")
        desc = item.get("description", "")
        lines.append(f"- {title}\n  {url}\n  {desc}")
    return "\n".join(lines)
