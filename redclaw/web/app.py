from __future__ import annotations

import json
import asyncio
from html import escape
from datetime import datetime
from pathlib import Path

import yaml
from fastapi import FastAPI, Form, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from redclaw.agent.systemcheck import run_systemcheck
from redclaw.bootstrap import get_runtime
from redclaw.skills.base import SkillContext
from redclaw.skills.skill_search import clean_search_query, search_web
from redclaw.web.auth import SESSION_COOKIE, is_authenticated, session_token, verify_password
from redclaw.web.voice import synthesize

BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(title="RedClaw")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")
runtime = get_runtime()
live_clients: set[WebSocket] = set()
reminder_task: asyncio.Task | None = None


def _job_event(job, text: str) -> None:
    runtime.logger.log("info", job.kind, text, {"job_id": job.id})
    try:
        asyncio.create_task(broadcast({"kind": job.kind, "text": text}))
    except RuntimeError:
        pass


runtime.jobs.subscribe(_job_event)


async def broadcast(payload: dict) -> None:
    dead: list[WebSocket] = []
    for ws in live_clients:
        try:
            await ws.send_text(json.dumps(payload, ensure_ascii=False))
        except Exception:
            dead.append(ws)
    for ws in dead:
        live_clients.discard(ws)


@app.middleware("http")
async def auth_wall(request: Request, call_next):
    public = request.url.path.startswith("/static") or request.url.path in {"/login"}
    if not public and not is_authenticated(request, runtime.settings):
        return RedirectResponse("/login", status_code=303)
    return await call_next(request)


@app.on_event("startup")
async def startup() -> None:
    global reminder_task
    if reminder_task is None:
        reminder_task = asyncio.create_task(_reminder_loop())


async def _reminder_loop() -> None:
    while True:
        rows = runtime.memory.conn.execute(
            "SELECT * FROM reminders WHERE done = 0 AND due_at <= ? ORDER BY due_at ASC",
            (datetime.utcnow().isoformat(),),
        ).fetchall()
        for row in rows:
            text = f"Reminder: {row['text']}"
            runtime.memory.conn.execute("UPDATE reminders SET done = 1 WHERE id = ?", (row["id"],))
            runtime.memory.conn.commit()
            runtime.logger.log("info", "reminder", "Reminder fällig", {"text": row["text"]})
            await broadcast({"kind": "reminder", "text": text})
        await asyncio.sleep(10)


@app.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": ""})


@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == runtime.settings.admin_username and verify_password(password, runtime.settings.admin_password):
        response = RedirectResponse("/", status_code=303)
        response.set_cookie(SESSION_COOKIE, session_token(runtime.settings), httponly=True, samesite="strict")
        runtime.logger.log("info", "web_login", "Login erfolgreich", {"username": username})
        return response
    runtime.logger.log("warn", "security", "Login fehlgeschlagen", {"username": username})
    return templates.TemplateResponse("login.html", {"request": request, "error": "Login fehlgeschlagen"})


@app.get("/logout")
async def logout():
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE)
    return response


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    checks = run_systemcheck(runtime.settings)
    logs = runtime.memory.logs(limit=60)
    memories = runtime.memory.all(limit=80)
    memory_groups = runtime.memory.grouped(limit_per_group=50)
    memory_stats = runtime.memory.stats()
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "settings": runtime.settings,
            "checks": checks,
            "logs": logs,
            "memories": memories,
            "memory_groups": memory_groups,
            "memory_stats": memory_stats,
            "skills": runtime.skills.list(),
            "jobs": list(runtime.jobs.jobs.values()),
        },
    )


@app.post("/chat")
async def chat(message: str = Form(...)):
    answer = await runtime.agent.handle_message(message, source="web")
    await broadcast({"kind": "chat", "text": answer})
    safe_message = escape(message)
    safe_answer = escape(answer)
    return HTMLResponse(f"<div class='bubble user'>{safe_message}</div><div class='bubble claw'>{safe_answer}</div>")


@app.post("/search")
async def web_search(query: str = Form(...)):
    clean_query = clean_search_query(query)
    context = SkillContext(
        settings=runtime.settings,
        memory=runtime.memory,
        logger=runtime.logger,
        permissions=runtime.permissions,
        jobs=runtime.jobs,
        source="web_search",
    )
    try:
        results = await search_web(clean_query, context, limit=6)
    except Exception as exc:
        runtime.logger.log("warn", "search", "Websuche fehlgeschlagen", {"query": clean_query, "error": type(exc).__name__})
        return HTMLResponse(f"<div class='empty-state compact'><strong>Suche fehlgeschlagen</strong><span>{escape(type(exc).__name__)}</span></div>")
    for item in results:
        runtime.memory.save("search", f"{clean_query}:{item.url}", f"{item.title} - {item.url}", source="web_search", confidence=0.74)
    if not results:
        return HTMLResponse("<div class='empty-state compact'><strong>Keine Treffer</strong><span>Versuch eine andere Suchanfrage.</span></div>")
    cards = [f"<div class='search-summary'><span>{len(results)} Treffer</span><strong>{escape(clean_query)}</strong></div>"]
    for item in results:
        cards.append(
            "<article class='search-card'>"
            f"<div class='search-source'>{escape(item.source)}</div>"
            f"<a href='{escape(item.url)}' target='_blank' rel='noreferrer'>{escape(item.title)}</a>"
            f"<p>{escape(item.description)}</p>"
            f"<small>{escape(item.url)}</small>"
            "</article>"
        )
    await broadcast({"kind": "search", "text": f"{len(results)} Treffer fuer {clean_query}"})
    return HTMLResponse("".join(cards))


@app.post("/memory/delete/{memory_id}")
async def delete_memory(memory_id: int):
    runtime.memory.delete(memory_id)
    runtime.logger.log("info", "memory", "Fakt gelöscht", {"memory_id": memory_id})
    return RedirectResponse("/", status_code=303)


@app.post("/skills/{skill_name}/toggle")
async def toggle_skill(skill_name: str, enabled: str = Form("off")):
    is_enabled = enabled == "on"
    if runtime.skills.set_enabled(skill_name, is_enabled):
        runtime.logger.log("info", "skill", "Skill-Status geändert", {"skill": skill_name, "enabled": is_enabled})
    return RedirectResponse("/", status_code=303)


@app.post("/config")
async def save_config(
    discord_user_id: str = Form(""),
    brave_search_api_key: str = Form(""),
    nvidia_nim_api_key: str = Form(""),
    nvidia_nim_base_url: str = Form("https://integrate.api.nvidia.com/v1"),
    nvidia_nim_model: str = Form("nvidia/llama-3.3-nemotron-super-49b-v1.5"),
    nvidia_nim_max_tokens: int = Form(4096),
    nvidia_nim_context_window: int = Form(0),
    nvidia_nim_temperature: float = Form(0.7),
    nvidia_nim_top_p: float = Form(0.95),
    nvidia_nim_enable_thinking: str = Form("off"),
    nvidia_nim_timeout: int = Form(120),
    nvidia_nim_rpm_limit: int = Form(36),
    allowed_paths: str = Form("/home/pi/redclaw_workspace"),
    personality: str = Form("freundlich, direkt, wachsam"),
):
    paths = [line.strip() for line in allowed_paths.replace(",", "\n").splitlines() if line.strip()]
    data = {
        "paths": {
            "db": str(runtime.settings.db_path),
            "logs": str(runtime.settings.log_dir),
            "workspace": str(runtime.settings.workspace),
            "allowed_paths": paths,
        },
        "discord": {"token": runtime.settings.discord_token, "user_id": discord_user_id},
        "web": {
            "host": runtime.settings.web_host,
            "port": runtime.settings.web_port,
            "username": runtime.settings.admin_username,
            "password": runtime.settings.admin_password,
            "session_secret": runtime.settings.session_secret,
        },
        "agent": {"language": runtime.settings.language, "personality": personality, "log_retention_days": runtime.settings.log_retention_days},
        "api": {
            "brave_search_api_key": brave_search_api_key,
            "nvidia_nim_api_key": nvidia_nim_api_key,
            "nvidia_nim_base_url": nvidia_nim_base_url,
            "nvidia_nim_model": nvidia_nim_model,
            "nvidia_nim_max_tokens": nvidia_nim_max_tokens,
            "nvidia_nim_context_window": nvidia_nim_context_window,
            "nvidia_nim_temperature": nvidia_nim_temperature,
            "nvidia_nim_top_p": nvidia_nim_top_p,
            "nvidia_nim_enable_thinking": nvidia_nim_enable_thinking == "on",
            "nvidia_nim_timeout": nvidia_nim_timeout,
            "nvidia_nim_rpm_limit": nvidia_nim_rpm_limit,
            "codex_command": runtime.settings.codex_command,
        },
    }
    config_path = runtime.settings.project_root / "config" / "redclaw.yaml"
    config_path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    runtime.settings.discord_user_id = discord_user_id
    runtime.settings.brave_search_api_key = brave_search_api_key
    runtime.settings.nvidia_nim_api_key = nvidia_nim_api_key
    runtime.settings.nvidia_nim_base_url = nvidia_nim_base_url
    runtime.settings.nvidia_nim_model = nvidia_nim_model
    runtime.settings.nvidia_nim_max_tokens = nvidia_nim_max_tokens
    runtime.settings.nvidia_nim_context_window = nvidia_nim_context_window
    runtime.settings.nvidia_nim_temperature = nvidia_nim_temperature
    runtime.settings.nvidia_nim_top_p = nvidia_nim_top_p
    runtime.settings.nvidia_nim_enable_thinking = nvidia_nim_enable_thinking == "on"
    runtime.settings.nvidia_nim_timeout = nvidia_nim_timeout
    runtime.settings.nvidia_nim_rpm_limit = nvidia_nim_rpm_limit
    runtime.settings.allowed_paths = [Path(p) for p in paths]
    runtime.settings.personality = personality
    runtime.logger.log("info", "config", "Web-Config gespeichert", {"path": str(config_path)})
    return RedirectResponse("/", status_code=303)


@app.post("/panic")
async def panic():
    count = runtime.jobs.stop_all()
    runtime.logger.log("warn", "security", "Panik-Knopf ausgelöst", {"stopped_jobs": count})
    await broadcast({"kind": "security", "text": f"Panik-Knopf: {count} Jobs gestoppt."})
    return RedirectResponse("/", status_code=303)


@app.post("/voice")
async def voice(message: str = Form(...)):
    answer = await runtime.agent.handle_message(message, source="web_voice")
    audio = await synthesize(answer, BASE_DIR / "static" / "audio")
    return {"answer": answer, "audio": f"/static/audio/{audio.name}"}


@app.websocket("/ws/live")
async def live(ws: WebSocket):
    await ws.accept()
    live_clients.add(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        live_clients.discard(ws)
