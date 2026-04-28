import json
import logging
import os
from pathlib import Path
from threading import Lock
from typing import Literal, Optional

import weave
from pydantic import BaseModel

from backend.config import settings

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / ".likho_config.json"
CONFIG_TMP_PATH = CONFIG_PATH.with_suffix(".json.tmp")

Source = Literal["file", "env", "none"]


class Credentials(BaseModel):
    openai_api_key: Optional[str] = None
    wandb_api_key: Optional[str] = None
    weave_entity: Optional[str] = None
    weave_project: Optional[str] = None


class CredentialStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._weave_initialized_for: Optional[tuple[str, str, str]] = None
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
            "wandb_api_key": settings.wandb_api_key,
            "weave_entity": settings.weave_entity,
            "weave_project": settings.weave_project,
        }

        creds_data: dict = {}
        sources: dict[str, Source] = {}
        for field in ("openai_api_key", "wandb_api_key", "weave_entity", "weave_project"):
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

    def has_weave(self) -> bool:
        with self._lock:
            c = self._creds
            return bool(c.wandb_api_key and c.weave_entity and c.weave_project)

    def save(self, payload: dict) -> Credentials:
        """Persist non-empty payload fields to the config file. Returns new creds."""
        with self._lock:
            current = self._read_file()
            for field in ("openai_api_key", "wandb_api_key", "weave_entity", "weave_project"):
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

    def try_init_weave(self) -> Optional[str]:
        """Initialize Weave if all four creds present. Returns error string on failure, None on success/skip."""
        with self._lock:
            c = self._creds
            if not (c.wandb_api_key and c.weave_entity and c.weave_project):
                return None
            target = (c.wandb_api_key, c.weave_entity, c.weave_project)
            if self._weave_initialized_for == target:
                return None

        try:
            os.environ["WANDB_API_KEY"] = c.wandb_api_key
            weave.init(f"{c.weave_entity}/{c.weave_project}")
            with self._lock:
                self._weave_initialized_for = target
            return None
        except Exception as e:
            logger.warning(f"Weave init failed: {e}")
            return str(e)


store = CredentialStore()
