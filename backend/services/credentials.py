import json
import logging
import os
from pathlib import Path
from threading import Lock
from typing import Literal, Optional

from pydantic import BaseModel

from backend.config import settings

logger = logging.getLogger(__name__)

def _resolve_config_path() -> Path:
    override = os.getenv("LIKHO_CONFIG_PATH")
    if override:
        return Path(override)
    return Path(__file__).resolve().parent.parent.parent / ".likho_config.json"


CONFIG_PATH = _resolve_config_path()
CONFIG_TMP_PATH = CONFIG_PATH.with_suffix(".json.tmp")

Source = Literal["file", "env", "none"]

PROVIDER_FIELDS = ("openai_api_key", "anthropic_api_key", "gemini_api_key")


class Credentials(BaseModel):
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None


class CredentialStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._creds, self._sources = self._load()

    def _load(self) -> tuple[Credentials, dict[str, Source]]:
        file_data: dict = {}
        if CONFIG_PATH.exists():
            try:
                file_data = json.loads(CONFIG_PATH.read_text())
                if not isinstance(file_data, dict):
                    raise ValueError("config file is not a JSON object")
            except Exception as e:
                logger.warning(f"Ignoring corrupt config file {CONFIG_PATH}: {e}")
                file_data = {}

        env_map = {
            "openai_api_key": settings.openai_api_key,
            "anthropic_api_key": settings.anthropic_api_key,
            "gemini_api_key": settings.gemini_api_key,
        }

        creds_data: dict = {}
        sources: dict[str, Source] = {}
        for field in PROVIDER_FIELDS:
            file_val = file_data.get(field)
            if file_val:
                creds_data[field] = file_val
                sources[field] = "file"
            elif env_map[field]:
                creds_data[field] = env_map[field]
                sources[field] = "env"
            else:
                sources[field] = "none"

        return Credentials(**creds_data), sources

    def get(self) -> Credentials:
        with self._lock:
            return self._creds.model_copy()

    def sources(self) -> dict[str, Source]:
        with self._lock:
            return dict(self._sources)

    def has_openai(self) -> bool:
        with self._lock:
            return bool(self._creds.openai_api_key)

    def has_provider(self, provider: str) -> bool:
        field = f"{provider}_api_key"
        if field not in PROVIDER_FIELDS:
            return False
        with self._lock:
            return bool(getattr(self._creds, field, None))

    def get_key(self, provider: str) -> Optional[str]:
        field = f"{provider}_api_key"
        if field not in PROVIDER_FIELDS:
            return None
        with self._lock:
            return getattr(self._creds, field, None)

    def save(self, payload: dict) -> Credentials:
        """Persist non-empty payload fields to the config file. Returns new creds."""
        with self._lock:
            current = self._read_file()
            for field in PROVIDER_FIELDS:
                value = payload.get(field)
                if value is not None and str(value).strip():
                    current[field] = str(value).strip()
            CONFIG_TMP_PATH.write_text(json.dumps(current, indent=2))
            os.replace(CONFIG_TMP_PATH, CONFIG_PATH)
            try:
                CONFIG_PATH.chmod(0o600)
            except OSError:
                pass
            self._creds, self._sources = self._load()
            return self._creds.model_copy()

    @staticmethod
    def _read_file() -> dict:
        if not CONFIG_PATH.exists():
            return {}
        try:
            data = json.loads(CONFIG_PATH.read_text())
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}


store = CredentialStore()
