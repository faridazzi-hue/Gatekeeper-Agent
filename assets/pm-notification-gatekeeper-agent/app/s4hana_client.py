"""SAP backend OData/REST client backed by a BTP destination.

Required CF service bindings (provided via VCAP_SERVICES):

* destination   — exposes the destination-configuration REST API. Its service
                  key already embeds an OAuth client (clientid, clientsecret,
                  token endpoint url) used to fetch access tokens via the
                  client_credentials grant.
* connectivity  — on-premise destinations only; provides onpremise_proxy_host /
                  onpremise_proxy_http_port and its own embedded OAuth client
                  for the proxy authorization token.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DEFAULT_DESTINATION_NAME = os.environ.get("S4HANA_DESTINATION_NAME", "S4HANA_QUALITY")
DEFAULT_TIMEOUT_SECONDS = float(os.environ.get("S4HANA_TIMEOUT_SECONDS", "20.0"))
TOKEN_TTL = float(os.environ.get("DESTINATION_TOKEN_TTL", "600"))
DEST_CACHE_TTL = float(os.environ.get("DESTINATION_CACHE_TTL", "300"))

RESPONSE_ENVELOPE = "odata_v2"
CSRF_REQUIRED = True


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
    if not bindings:
        return None
    return (bindings[0] or {}).get("credentials") or {}


@dataclass
class Destination:
    url: str
    auth_type: str
    username: str | None = None
    password: str | None = None
    sap_client: str | None = None
    proxy_type: str = "Internet"
    additional: dict[str, str] = field(default_factory=dict)


@dataclass
class _CachedToken:
    value: str
    expires_at: float

    def expired(self) -> bool:
        return time.monotonic() >= self.expires_at


class _DestinationResolver:
    def __init__(self, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> None:
        self._timeout = timeout
        self._xsuaa_token: _CachedToken | None = None
        self._proxy_token: _CachedToken | None = None
        self._dest_cache: dict[str, tuple[Destination, float]] = {}

    async def _client_credentials_token(
        self, token_url: str, client_id: str, client_secret: str
    ) -> str:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            r = await client.post(
                token_url.rstrip("/") + "/oauth/token",
                data={"grant_type": "client_credentials"},
                auth=(client_id, client_secret),
                headers={"Accept": "application/json"},
            )
        r.raise_for_status()
        return r.json()["access_token"]

    async def _xsuaa_access_token(self) -> str:
        if self._xsuaa_token and not self._xsuaa_token.expired():
            return self._xsuaa_token.value
        creds = _first_binding("destination") or {}
        if not creds:
            raise RuntimeError(
                "No 'destination' service binding found in VCAP_SERVICES. "
                "Bind a destination service instance to the app."
            )
        token = await self._client_credentials_token(
            creds["url"], creds["clientid"], creds["clientsecret"]
        )
        self._xsuaa_token = _CachedToken(token, time.monotonic() + TOKEN_TTL)
        return token

    async def _connectivity_proxy_token(self) -> str:
        if self._proxy_token and not self._proxy_token.expired():
            return self._proxy_token.value
        creds = _first_binding("connectivity") or {}
        if not creds:
            raise RuntimeError(
                "Destination is OnPremise but no 'connectivity' service "
                "binding was found in VCAP_SERVICES."
            )
        token = await self._client_credentials_token(
            creds["token_service_url"], creds["clientid"], creds["clientsecret"]
        )
        self._proxy_token = _CachedToken(token, time.monotonic() + TOKEN_TTL)
        return token

    async def resolve(self, name: str) -> Destination:
        cached = self._dest_cache.get(name)
        if cached and time.monotonic() < cached[1]:
            return cached[0]

        creds = _first_binding("destination") or {}
        if not creds:
            raise RuntimeError("No 'destination' service binding found in VCAP_SERVICES.")
        access_token = await self._xsuaa_access_token()
        uri = creds["uri"].rstrip("/")
        url = f"{uri}/destination-configuration/v1/destinations/{name}"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            r = await client.get(
                url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                },
            )
        if r.status_code >= 400:
            raise RuntimeError(
                f"Destination service returned {r.status_code} for '{name}': {r.text}"
            )
        body = r.json()
        cfg = body.get("destinationConfiguration") or {}
        d_url = (cfg.get("URL") or "").rstrip("/")
        if not d_url:
            raise RuntimeError(f"Destination '{name}' has no URL configured.")
        sap_client = (
            cfg.get("sap-client") or cfg.get("SAP-Client") or cfg.get("sap_client")
        )
        well_known = {
            "URL", "Name", "Type", "Authentication", "ProxyType",
            "User", "Password", "sap-client", "SAP-Client", "sap_client",
        }
        additional = {k: v for k, v in cfg.items() if k not in well_known}
        dest = Destination(
            url=d_url,
            auth_type=cfg.get("Authentication", "NoAuthentication"),
            username=cfg.get("User"),
            password=cfg.get("Password"),
            sap_client=sap_client,
            proxy_type=cfg.get("ProxyType", "Internet"),
            additional=additional,
        )
        self._dest_cache[name] = (dest, time.monotonic() + DEST_CACHE_TTL)
        return dest

    async def proxy_settings(self) -> tuple[str, dict[str, str]]:
        creds = _first_binding("connectivity") or {}
        if not creds:
            raise RuntimeError(
                "Destination is OnPremise but no 'connectivity' binding found."
            )
        host = creds["onpremise_proxy_host"]
        port = creds["onpremise_proxy_http_port"]
        proxy_url = f"http://{host}:{port}"
        token = await self._connectivity_proxy_token()
        return proxy_url, {"Proxy-Authorization": f"Bearer {token}"}


class Client:
    """Async HTTP client backed by a BTP destination."""

    def __init__(
        self,
        destination: Destination | None = None,
        destination_name: str = DEFAULT_DESTINATION_NAME,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        resolver: _DestinationResolver | None = None,
    ) -> None:
        self._destination = destination
        self._destination_name = destination_name
        self._timeout = timeout
        self._resolver = resolver or _DestinationResolver(timeout=timeout)

    async def destination(self) -> Destination:
        if self._destination is None:
            self._destination = await self._resolver.resolve(self._destination_name)
        return self._destination

    def _build_url(self, base_url: str, service_path: str) -> str:
        if not service_path.startswith("/"):
            service_path = "/" + service_path
        return f"{base_url}{service_path}"

    def _auth(self, dest: Destination) -> httpx.BasicAuth | None:
        if dest.auth_type == "BasicAuthentication" and dest.username and dest.password:
            return httpx.BasicAuth(dest.username, dest.password)
        return None

    def _base_headers(self) -> dict[str, str]:
        return {"Accept": "application/json"}

    async def _client_kwargs(self, dest: Destination) -> tuple[dict[str, Any], dict[str, str]]:
        kwargs: dict[str, Any] = {"timeout": self._timeout}
        extra: dict[str, str] = {}
        if dest.proxy_type.lower() == "onpremise":
            proxy_url, hdr = await self._resolver.proxy_settings()
            kwargs["proxy"] = proxy_url
            extra.update(hdr)
            location_id = dest.additional.get("CloudConnectorLocationId", "")
            if location_id:
                extra["SAP-Connectivity-SCC-Location_ID"] = location_id
        return kwargs, extra

    def _inject_mandatory_params(self, dest: Destination, params: dict[str, Any]) -> dict[str, Any]:
        if dest.sap_client and "sap-client" not in params:
            params["sap-client"] = dest.sap_client
        return params

    def _unwrap_response(self, body: Any) -> Any:
        if RESPONSE_ENVELOPE == "odata_v2" and isinstance(body, dict) and "d" in body:
            return body["d"]
        return body

    async def _fetch_csrf(
        self,
        client: httpx.AsyncClient,
        dest: Destination,
        service_root: str,
        extra_headers: dict[str, str],
    ) -> str:
        params: dict[str, Any] = {}
        self._inject_mandatory_params(dest, params)
        headers = {"x-csrf-token": "fetch", "Accept": "application/json"}
        headers.update(extra_headers)
        r = await client.get(
            self._build_url(dest.url, service_root),
            auth=self._auth(dest),
            headers=headers,
            params=params,
        )
        return r.headers.get("x-csrf-token") or r.headers.get("X-CSRF-Token") or ""

    async def get(
        self,
        service_path: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        dest = await self.destination()
        merged: dict[str, Any] = dict(params or {})
        self._inject_mandatory_params(dest, merged)
        client_kwargs, extra = await self._client_kwargs(dest)
        headers = self._base_headers()
        headers.update(extra)
        async with httpx.AsyncClient(**client_kwargs) as client:
            r = await client.get(
                self._build_url(dest.url, service_path),
                auth=self._auth(dest),
                headers=headers,
                params=merged,
            )
        if r.status_code >= 400:
            return {
                "error": True,
                "status_code": r.status_code,
                "message": r.text,
                "url": self._build_url(dest.url, service_path),
            }
        try:
            body = r.json()
        except Exception:
            return {"error": True, "status_code": r.status_code, "message": r.text}
        return self._unwrap_response(body)

    async def post(
        self,
        service_path: str,
        body: dict[str, Any],
        service_root: str,
    ) -> dict[str, Any]:
        dest = await self.destination()
        client_kwargs, extra = await self._client_kwargs(dest)
        async with httpx.AsyncClient(**client_kwargs) as client:
            csrf = ""
            if CSRF_REQUIRED:
                csrf = await self._fetch_csrf(client, dest, service_root, extra)
            headers = self._base_headers()
            headers["Content-Type"] = "application/json"
            if CSRF_REQUIRED:
                headers["x-csrf-token"] = csrf
            headers.update(extra)
            params: dict[str, Any] = {}
            self._inject_mandatory_params(dest, params)
            r = await client.post(
                self._build_url(dest.url, service_path),
                json=body,
                auth=self._auth(dest),
                headers=headers,
                params=params,
            )
        if r.status_code >= 400:
            return {"error": True, "status_code": r.status_code, "message": r.text}
        try:
            return r.json()
        except Exception:
            return {"status_code": r.status_code, "raw": r.text}

    async def patch(
        self,
        service_path: str,
        body: dict[str, Any],
        service_root: str,
    ) -> dict[str, Any]:
        dest = await self.destination()
        client_kwargs, extra = await self._client_kwargs(dest)
        async with httpx.AsyncClient(**client_kwargs) as client:
            csrf = ""
            if CSRF_REQUIRED:
                csrf = await self._fetch_csrf(client, dest, service_root, extra)
            headers = self._base_headers()
            headers["Content-Type"] = "application/json"
            headers["X-Http-Method"] = "MERGE"
            if CSRF_REQUIRED:
                headers["x-csrf-token"] = csrf
            headers.update(extra)
            params: dict[str, Any] = {}
            self._inject_mandatory_params(dest, params)
            r = await client.patch(
                self._build_url(dest.url, service_path),
                json=body,
                auth=self._auth(dest),
                headers=headers,
                params=params,
            )
        if r.status_code == 204:
            return {"success": True, "status_code": 204}
        if r.status_code >= 400:
            return {"error": True, "status_code": r.status_code, "message": r.text}
        try:
            return r.json()
        except Exception:
            return {"status_code": r.status_code, "raw": r.text}

    async def function_import(
        self,
        service_root: str,
        function_name: str,
        params: dict[str, Any] | None = None,
        method: str = "GET",
    ) -> dict[str, Any]:
        """Call an OData V2 function import (GET or POST)."""
        dest = await self.destination()
        merged: dict[str, Any] = dict(params or {})
        self._inject_mandatory_params(dest, merged)
        merged["$format"] = "json"
        client_kwargs, extra = await self._client_kwargs(dest)
        headers = self._base_headers()
        headers.update(extra)
        path = f"{service_root}/{function_name}"
        async with httpx.AsyncClient(**client_kwargs) as client:
            if method.upper() == "POST":
                if CSRF_REQUIRED:
                    csrf = await self._fetch_csrf(client, dest, service_root, extra)
                    headers["x-csrf-token"] = csrf
                headers["Content-Type"] = "application/json"
                # Fetch real ETag — SAP rejects If-Match: * for action function imports
                notif_id = str((params or {}).get("MaintenanceNotification", "")).strip("'")
                if notif_id:
                    etag_params: dict[str, Any] = {}
                    self._inject_mandatory_params(dest, etag_params)
                    etag_params["$format"] = "json"
                    etag_r = await client.get(
                        self._build_url(dest.url, f"{service_root}/MaintenanceNotification('{notif_id}')"),
                        auth=self._auth(dest),
                        headers=self._base_headers(),
                        params=etag_params,
                    )
                    etag = etag_r.headers.get("ETag") or etag_r.headers.get("etag") or "*"
                else:
                    etag = "*"
                headers["If-Match"] = etag
                r = await client.post(
                    self._build_url(dest.url, path),
                    auth=self._auth(dest),
                    headers=headers,
                    params=merged,
                    json={},
                )
            else:
                r = await client.get(
                    self._build_url(dest.url, path),
                    auth=self._auth(dest),
                    headers=headers,
                    params=merged,
                )
        if r.status_code >= 400:
            return {"error": True, "status_code": r.status_code, "message": r.text}
        try:
            body = r.json()
        except Exception:
            return {"status_code": r.status_code, "raw": r.text}
        return self._unwrap_response(body)


__all__ = ["Client", "Destination", "DEFAULT_DESTINATION_NAME"]
