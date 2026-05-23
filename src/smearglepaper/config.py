from __future__ import annotations

import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"


def env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def runtime_settings() -> dict[str, object]:
    return {
        "data_dir": str(DATA_DIR),
        "llm": {
            "base_url": env("OPENAI_BASE_URL"),
            "model": env("OPENAI_MODEL", "deepseek-chat"),
            "api_key_configured": bool(env("OPENAI_API_KEY")),
        },
        "wechat": {
            "app_id_configured": bool(env("WECHAT_APP_ID")),
            "app_secret_configured": bool(env("WECHAT_APP_SECRET")),
        },
    }

