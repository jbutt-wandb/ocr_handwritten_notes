import logging
from typing import Optional

from fastapi import APIRouter, Response
from pydantic import BaseModel

from backend.services.credentials import store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/config", tags=["Config"])


class ConfigStatus(BaseModel):
    openai_configured: bool
    openai_preview: Optional[str] = None
    openai_source: str
    anthropic_configured: bool
    anthropic_preview: Optional[str] = None
    anthropic_source: str
    gemini_configured: bool
    gemini_preview: Optional[str] = None
    gemini_source: str


class ConfigUpdate(BaseModel):
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None


def _mask(secret: Optional[str]) -> Optional[str]:
    if not secret:
        return None
    if len(secret) <= 4:
        return "..." + secret
    if secret.startswith("sk-ant-"):
        return f"sk-ant-...{secret[-4:]}"
    if secret.startswith("sk-"):
        return f"sk-...{secret[-4:]}"
    return f"...{secret[-4:]}"


def _build_status() -> ConfigStatus:
    creds = store.get()
    sources = store.sources()
    return ConfigStatus(
        openai_configured=bool(creds.openai_api_key),
        openai_preview=_mask(creds.openai_api_key),
        openai_source=sources["openai_api_key"],
        anthropic_configured=bool(creds.anthropic_api_key),
        anthropic_preview=_mask(creds.anthropic_api_key),
        anthropic_source=sources["anthropic_api_key"],
        gemini_configured=bool(creds.gemini_api_key),
        gemini_preview=_mask(creds.gemini_api_key),
        gemini_source=sources["gemini_api_key"],
    )


@router.get("/status", response_model=ConfigStatus)
async def get_status(response: Response) -> ConfigStatus:
    response.headers["Cache-Control"] = "no-store"
    return _build_status()


@router.post("", response_model=ConfigStatus)
@router.post("/", response_model=ConfigStatus, include_in_schema=False)
async def save_config(payload: ConfigUpdate, response: Response) -> ConfigStatus:
    response.headers["Cache-Control"] = "no-store"

    # No upfront key validation — OCR calls surface provider errors directly.
    payload_dict = payload.model_dump(exclude_none=True)
    store.save(payload_dict)

    return _build_status()
