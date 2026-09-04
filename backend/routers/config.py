import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Response
from openai import APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI
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
    mistral_configured: bool
    mistral_preview: Optional[str] = None
    mistral_source: str
    local_configured: bool
    local_preview: Optional[str] = None
    local_source: str
    # Raw values (not secrets) so the modal can prefill its inputs.
    local_base_url: Optional[str] = None
    local_model: Optional[str] = None


class ConfigUpdate(BaseModel):
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    mistral_api_key: Optional[str] = None
    local_base_url: Optional[str] = None
    local_model: Optional[str] = None
    local_api_key: Optional[str] = None


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
        mistral_configured=bool(creds.mistral_api_key),
        mistral_preview=_mask(creds.mistral_api_key),
        mistral_source=sources["mistral_api_key"],
        local_configured=bool(creds.local_base_url and creds.local_model),
        local_preview=(
            f"{creds.local_model} @ {creds.local_base_url}"
            if creds.local_base_url and creds.local_model
            else None
        ),
        local_source=sources["local_base_url"],
        local_base_url=creds.local_base_url,
        local_model=creds.local_model,
    )


def _normalize_base_url(base_url: str) -> str:
    """Strip whitespace/trailing slash and require an http(s) scheme."""
    normalized = base_url.strip().rstrip("/")
    if not normalized.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=400,
            detail={
                "code": "invalid_base_url",
                "message": "Base URL must start with http:// or https://",
            },
        )
    return normalized


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
    if payload_dict.get("local_base_url"):
        payload_dict["local_base_url"] = _normalize_base_url(payload_dict["local_base_url"])
    store.save(payload_dict)

    return _build_status()


class LocalModelsRequest(BaseModel):
    base_url: str
    api_key: Optional[str] = None


class LocalModelsResponse(BaseModel):
    models: list[str]


@router.post("/local/models", response_model=LocalModelsResponse)
async def list_local_models(payload: LocalModelsRequest) -> LocalModelsResponse:
    """List models served by a local OpenAI-compatible server.

    Fetched server-side to avoid browser CORS restrictions on Ollama/LM Studio,
    and doubles as the modal's connection test. This proxies a user-supplied URL,
    which is acceptable for a localhost dev tool whose config API is unauthenticated
    anyway; the scheme check above is the only guard.
    """
    base_url = _normalize_base_url(payload.base_url)
    client = AsyncOpenAI(
        base_url=base_url,
        api_key=payload.api_key or "not-needed",
        timeout=5.0,
        max_retries=0,
    )
    try:
        models = [model.id async for model in client.models.list()]
    except (APITimeoutError, APIConnectionError):
        raise HTTPException(
            status_code=502,
            detail={
                "code": "local_unreachable",
                "message": f"Could not reach your local model server at {base_url} — is it running?",
            },
        )
    except APIStatusError as e:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "local_error",
                "message": (
                    f"Server at {base_url} responded with an error ({e.status_code}). "
                    "If it requires an API key, add one."
                ),
            },
        )
    return LocalModelsResponse(models=sorted(models))
