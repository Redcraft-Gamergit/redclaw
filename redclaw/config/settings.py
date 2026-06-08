from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _split_paths(raw: str | list[str]) -> list[Path]:
    if isinstance(raw, list):
        return [Path(p).expanduser() for p in raw]
    return [Path(p.strip()).expanduser() for p in raw.split(",") if p.strip()]


@dataclass
class Settings:
    project_root: Path = PROJECT_ROOT
    db_path: Path = PROJECT_ROOT / "data" / "redclaw.db"
    log_dir: Path = PROJECT_ROOT / "logs"
    workspace: Path = Path("/home/pi/redclaw_workspace")
    allowed_paths: list[Path] = field(default_factory=lambda: [Path("/home/pi/redclaw_workspace")])
    discord_user_id: str = ""
    discord_test_user_id: str = ""
    discord_allow_test_bots: bool = False
    discord_token: str = ""
    brave_search_api_key: str = ""
    nvidia_nim_api_key: str = ""
    nvidia_nim_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_nim_model: str = "nvidia/llama-3.3-nemotron-super-49b-v1.5"
    nvidia_nim_max_tokens: int = 4096
    nvidia_nim_temperature: float = 0.7
    nvidia_nim_top_p: float = 0.95
    nvidia_nim_enable_thinking: bool = False
    nvidia_nim_timeout: int = 120
    codex_command: str = "codex"
    language: str = "de"
    personality: str = "freundlich, direkt, wachsam"
    admin_username: str = "redcrafter"
    admin_password: str = "redclaw"
    session_secret: str = "change-me"
    log_retention_days: int = 50
    web_host: str = "0.0.0.0"
    web_port: int = 8080

    @classmethod
    def load(cls) -> "Settings":
        load_dotenv(PROJECT_ROOT / ".env")
        default_config = PROJECT_ROOT / "config" / "redclaw.yaml"
        if not default_config.exists():
            default_config = PROJECT_ROOT / "config" / "config.example.yaml"
        config_path = Path(os.getenv("REDCLAW_CONFIG", default_config))
        data: dict[str, Any] = {}
        if config_path.exists():
            with config_path.open("r", encoding="utf-8") as handle:
                loaded = yaml.safe_load(handle) or {}
                if isinstance(loaded, dict):
                    data = loaded

        paths = data.get("paths", {})
        discord = data.get("discord", {})
        web = data.get("web", {})
        agent = data.get("agent", {})
        api = data.get("api", {})

        workspace = Path(os.getenv("REDCLAW_WORKSPACE", paths.get("workspace", "/home/pi/redclaw_workspace"))).expanduser()
        allowed_raw = os.getenv("REDCLAW_ALLOWED_PATHS", paths.get("allowed_paths", [str(workspace)]))

        return cls(
            db_path=Path(os.getenv("REDCLAW_DB", paths.get("db", PROJECT_ROOT / "data" / "redclaw.db"))),
            log_dir=Path(os.getenv("REDCLAW_LOG_DIR", paths.get("logs", PROJECT_ROOT / "logs"))),
            workspace=workspace,
            allowed_paths=_split_paths(allowed_raw),
            discord_user_id=str(os.getenv("REDSCRAFTER_DISCORD_ID", discord.get("user_id", ""))),
            discord_test_user_id=str(os.getenv("DISCORD_TEST_USER_ID", discord.get("test_user_id", ""))),
            discord_allow_test_bots=str(os.getenv("DISCORD_ALLOW_TEST_BOTS", discord.get("allow_test_bots", False))).lower() in {"1", "true", "yes", "on"},
            discord_token=os.getenv("DISCORD_TOKEN", discord.get("token", "")),
            brave_search_api_key=os.getenv("BRAVE_SEARCH_API_KEY", api.get("brave_search_api_key", "")),
            nvidia_nim_api_key=os.getenv("NVIDIA_NIM_API_KEY", api.get("nvidia_nim_api_key", "")),
            nvidia_nim_base_url=os.getenv("NVIDIA_NIM_BASE_URL", api.get("nvidia_nim_base_url", "https://integrate.api.nvidia.com/v1")),
            nvidia_nim_model=os.getenv("NVIDIA_NIM_MODEL", api.get("nvidia_nim_model", "nvidia/llama-3.3-nemotron-super-49b-v1.5")),
            nvidia_nim_max_tokens=int(os.getenv("NVIDIA_NIM_MAX_TOKENS", api.get("nvidia_nim_max_tokens", 4096))),
            nvidia_nim_temperature=float(os.getenv("NVIDIA_NIM_TEMPERATURE", api.get("nvidia_nim_temperature", 0.7))),
            nvidia_nim_top_p=float(os.getenv("NVIDIA_NIM_TOP_P", api.get("nvidia_nim_top_p", 0.95))),
            nvidia_nim_enable_thinking=str(os.getenv("NVIDIA_NIM_ENABLE_THINKING", api.get("nvidia_nim_enable_thinking", False))).lower() in {"1", "true", "yes", "on"},
            nvidia_nim_timeout=int(os.getenv("NVIDIA_NIM_TIMEOUT", api.get("nvidia_nim_timeout", 120))),
            codex_command=os.getenv("CODEX_COMMAND", api.get("codex_command", "codex")),
            language=str(agent.get("language", "de")),
            personality=str(agent.get("personality", "freundlich, direkt, wachsam")),
            admin_username=str(web.get("username", "redcrafter")),
            admin_password=os.getenv("REDCLAW_ADMIN_PASSWORD", str(web.get("password", "redclaw"))),
            session_secret=os.getenv("REDCLAW_SESSION_SECRET", str(web.get("session_secret", "change-me"))),
            log_retention_days=int(agent.get("log_retention_days", 50)),
            web_host=os.getenv("REDCLAW_WEB_HOST", str(web.get("host", "0.0.0.0"))),
            web_port=int(os.getenv("REDCLAW_WEB_PORT", web.get("port", 8080))),
        )

    def ensure_dirs(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        for path in self.allowed_paths:
            path.mkdir(parents=True, exist_ok=True)


_SETTINGS: Settings | None = None


def get_settings() -> Settings:
    global _SETTINGS
    if _SETTINGS is None:
        _SETTINGS = Settings.load()
    return _SETTINGS
