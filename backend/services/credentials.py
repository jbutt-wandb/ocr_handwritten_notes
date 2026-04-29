import logging
import os
from pathlib import Path
from threading import Lock
from typing import Literal, Optional

import weave
from dotenv import set_key
from pydantic import BaseModel

from backend.config import Settings

logger = logging.getLogger(__name__)

ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"

# Internal field name -> env var name written into .env
ENV_KEYS: dict[str, str] = {
    "wandb_api_key": "WANDB_API_KEY",
    "weave_entity": "ENTITY",
    "weave_project": "PROJECT",
    "model": "MODEL",
}

Source = Literal["env", "none"]


class Credentials(BaseModel):
    wandb_api_key: Optional[str] = None
    weave_entity: Optional[str] = None
    weave_project: Optional[str] = None
    model: Optional[str] = None


class CredentialStore:
    """Thin wrapper around `.env`. Reads via Pydantic Settings, writes via dotenv.set_key."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._weave_initialized_for: Optional[tuple[str, str, str]] = None
        self._refresh()

    def _refresh(self) -> None:
        s = Settings()
        self._creds = Credentials(
            wandb_api_key=s.wandb_api_key,
            weave_entity=s.weave_entity,
            weave_project=s.weave_project,
            model=s.model,
        )

    def get(self) -> Credentials:
        with self._lock:
            return self._creds.model_copy()

    def sources(self) -> dict[str, Source]:
        """Each field is either 'env' (set somewhere — .env or shell) or 'none'."""
        with self._lock:
            return {
                field: ("env" if getattr(self._creds, field) else "none")
                for field in ENV_KEYS
            }

    def has_inference(self) -> bool:
        with self._lock:
            c = self._creds
            return bool(c.wandb_api_key and c.weave_entity and c.weave_project)

    has_weave = has_inference

    def save(self, payload: dict) -> Credentials:
        """Write non-empty payload fields to .env, update os.environ, refresh state."""
        with self._lock:
            ENV_PATH.touch(exist_ok=True)
            try:
                ENV_PATH.chmod(0o600)
            except OSError:
                pass

            for field, env_name in ENV_KEYS.items():
                value = payload.get(field)
                if value is None:
                    continue
                v = str(value).strip()
                if not v:
                    continue
                set_key(str(ENV_PATH), env_name, v, quote_mode="never")
                os.environ[env_name] = v

            self._refresh()
            return self._creds.model_copy()

    def try_init_weave(self) -> Optional[str]:
        """Initialize Weave if all three creds present. Returns error string on failure, None on success/skip."""
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
