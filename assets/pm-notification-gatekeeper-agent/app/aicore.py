"""AI Core initialisation for Cloud Foundry deployment.

Resolves the AI Core configuration from a BTP destination (named by
AICORE_DESTINATION_NAME, default 'aicore') via the bound destination service,
then initialises a LangChain LLM using the sap-ai-sdk-gen package.

Idempotent: the destination lookup is skipped when AICORE_BASE_URL is already
set in the environment (e.g. injected by an operator or a prior call).
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_DEFAULT_AICORE_DESTINATION = os.environ.get("AICORE_DESTINATION_NAME", "aicore")
_initialized = False


def _vcap() -> dict[str, Any]:
    raw = os.environ.get("VCAP_SERVICES")
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        logger.warning("VCAP_SERVICES is set but not valid JSON")
        return {}


def _first_binding(label: str) -> dict[str, Any] | None:
    bindings = _vcap().get(label) or []
    return bindings[0] if bindings else None


async def _fetch_dest_token(creds: dict[str, Any]) -> str:
    """Exchange destination-service client credentials for an OAuth token."""
    token_url = creds.get("url", "").rstrip("/") + "/oauth/token"
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": creds["clientid"],
                "client_secret": creds["clientsecret"],
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15.0,
        )
        resp.raise_for_status()
        return resp.json()["access_token"]


async def _configure_aicore(destination_name: str) -> None:
    """Read AI Core destination from BTP, push env vars for gen_ai_hub."""
    global _initialized

    dest_binding = _first_binding("destination")
    if not dest_binding:
        raise RuntimeError(
            "No 'destination' service binding found in VCAP_SERVICES. "
            "Bind a destination service instance (e.g. 'proj-dest-service') "
            "to this CF app."
        )

    creds = dest_binding.get("credentials", {})
    dest_api_uri = creds.get("uri", "").rstrip("/")
    token = await _fetch_dest_token(creds)

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{dest_api_uri}/destination-configuration/v1/destinations/{destination_name}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15.0,
        )
        resp.raise_for_status()
        cfg: dict[str, Any] = resp.json().get("destinationConfiguration", {})

    url = cfg.get("URL", "")
    client_id = cfg.get("clientId", "")
    client_secret = cfg.get("clientSecret", "")
    token_svc_url = cfg.get("tokenServiceURL", "")
    resource_group = (
        cfg.get("URL.headers.AI-Resource-Group")
        or cfg.get("AI-Resource-Group")
        or "default"
    )

    missing = [k for k, v in [
        ("URL", url), ("clientId", client_id),
        ("clientSecret", client_secret), ("tokenServiceURL", token_svc_url),
    ] if not v]
    if missing:
        raise RuntimeError(
            f"AI Core destination '{destination_name}' is missing fields: {missing}. "
            f"Available keys: {list(cfg.keys())}"
        )

    os.environ["AICORE_BASE_URL"] = url
    os.environ["AICORE_AUTH_URL"] = token_svc_url
    os.environ["AICORE_CLIENT_ID"] = client_id
    os.environ["AICORE_CLIENT_SECRET"] = client_secret
    os.environ["AICORE_RESOURCE_GROUP"] = resource_group

    logger.info(
        "AI Core configured from destination '%s' (resource_group=%s)",
        destination_name,
        resource_group,
    )
    _initialized = True


def _has_direct_aicore_binding() -> bool:
    """Return True when an 'aicore' service is bound directly via VCAP_SERVICES."""
    vcap = _vcap()
    return bool(vcap.get("aicore") or vcap.get("AICORE"))


async def init_llm_from_destination(
    model_name: str,
    *,
    temperature: float = 0.0,
    max_tokens: int | None = None,
    destination_name: str | None = None,
) -> Any:
    """Return a LangChain LLM backed by SAP AI Core.

    When an 'aicore' service is bound directly (VCAP_SERVICES), gen_ai_hub reads
    the credentials automatically — no destination lookup needed.  The lookup only
    runs when neither a direct binding nor AICORE_BASE_URL is present.
    """
    from gen_ai_hub.proxy.langchain.init_models import init_llm  # type: ignore[import]

    if not _initialized and not os.environ.get("AICORE_BASE_URL") and not _has_direct_aicore_binding():
        await _configure_aicore(destination_name or _DEFAULT_AICORE_DESTINATION)
    elif _has_direct_aicore_binding() and not os.environ.get("AICORE_RESOURCE_GROUP"):
        # Direct aicore binding: the VCAP_SERVICES credential doesn't carry the
        # resource group — gen_ai_hub needs it explicitly to set the AI-Resource-Group
        # header on every /deployments and inference call.
        os.environ["AICORE_RESOURCE_GROUP"] = "default"
        logger.info("Direct aicore binding detected — set AICORE_RESOURCE_GROUP=default")

    kwargs: dict[str, Any] = {"temperature": temperature}
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens

    return init_llm(model_name, **kwargs)
