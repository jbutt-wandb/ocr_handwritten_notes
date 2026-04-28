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
    wandb_configured: bool
    wandb_preview: Optional[str] = None
    wandb_source: str
    weave_entity: Optional[str] = None
    weave_entity_source: str
    weave_project: Optional[str] = None
    weave_project_source: str


class ConfigUpdate(BaseModel):
    openai_api_key: Optional[str] = None
    wandb_api_key: Optional[str] = None
    weave_entity: Optional[str] = None
    weave_project: Optional[str] = None


class ConfigSaveResponse(BaseModel):
    status: ConfigStatus
    weave_warning: Optional[str] = None


def _mask(secret: Optional[str]) -> Optional[str]:
    if not secret:
        return None
    if len(secret) <= 4:
        return "..." + secret
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
        wandb_configured=bool(creds.wandb_api_key),
        wandb_preview=_mask(creds.wandb_api_key),
        wandb_source=sources["wandb_api_key"],
        weave_entity=creds.weave_entity,
        weave_entity_source=sources["weave_entity"],
        weave_project=creds.weave_project,
        weave_project_source=sources["weave_project"],
    )


@router.get("/status", response_model=ConfigStatus)
async def get_status(response: Response) -> ConfigStatus:
    response.headers["Cache-Control"] = "no-store"
    return _build_status()


@router.post("", response_model=ConfigSaveResponse)
@router.post("/", response_model=ConfigSaveResponse, include_in_schema=False)
async def save_config(payload: ConfigUpdate, response: Response) -> ConfigSaveResponse:
    response.headers["Cache-Control"] = "no-store"

    # No upfront key validation — OCR calls surface OpenAI's error directly.
    payload_dict = payload.model_dump(exclude_none=True)
    store.save(payload_dict)

    weave_warning: Optional[str] = None
    if store.has_weave():
        weave_warning = store.try_init_weave()

    return ConfigSaveResponse(status=_build_status(), weave_warning=weave_warning)
