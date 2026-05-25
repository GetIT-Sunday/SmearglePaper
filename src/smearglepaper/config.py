from __future__ import annotations

import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"


def load_dotenv(path: Path | None = None) -> None:
    dotenv_path = path or ROOT_DIR / ".env"
    if not dotenv_path.exists():
        return
    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


load_dotenv()


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
