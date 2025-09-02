from __future__ import annotations

from typing import Any

import pytest

from nexus_agent.config import ZohoConfig
from nexus_agent.zoho_client import ZohoAuthError, ZohoClient


class _Resp:
    def __init__(self, ok: bool, status: int, payload: dict[str, Any]):
        self.ok = ok
        self.status_code = status
        self._payload = payload
        self.text = str(payload)

    def json(self) -> dict[str, Any]:
        return self._payload


def test_refresh_access_token_success(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_post(url: str, data: dict[str, Any], headers: dict[str, str], timeout: int):  # type: ignore[no-untyped-def]
        return _Resp(
            ok=True,
            status=200,
            payload={
                "access_token": "atk",
                "token_type": "Bearer",
                "expires_in": 3600,
                "api_domain": "https://www.zohoapis.com",
            },
        )

    import requests  # noqa: WPS433

    monkeypatch.setattr(requests, "post", fake_post)

    cfg = ZohoConfig(
        client_id="id",
        client_secret="secret",  # pragma: allowlist secret
        refresh_token="refresh",  # pragma: allowlist secret
        accounts_base="https://accounts.zoho.com",
    )
    client = ZohoClient(cfg)
    tokens = client.refresh_access_token()
    assert tokens.access_token == "atk"
    assert tokens.api_domain.startswith("https://")
    # api_base should use tokens.api_domain when tokens are present
    assert client.api_base == tokens.api_domain


def test_refresh_access_token_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_post(url: str, data: dict[str, Any], headers: dict[str, str], timeout: int):  # type: ignore[no-untyped-def]
        return _Resp(ok=False, status=400, payload={"error": "bad_request"})

    import requests  # noqa: WPS433

    monkeypatch.setattr(requests, "post", fake_post)

    cfg = ZohoConfig(
        client_id="id",
        client_secret="secret",  # pragma: allowlist secret
        refresh_token="refresh",  # pragma: allowlist secret
        accounts_base="https://accounts.zoho.com",
    )
    client = ZohoClient(cfg)
    with pytest.raises(ZohoAuthError):
        client.refresh_access_token()


def test_auth_header_raises_without_tokens() -> None:
    cfg = ZohoConfig(
        client_id="id",
        client_secret="secret",  # pragma: allowlist secret
        refresh_token="refresh",  # pragma: allowlist secret
        accounts_base="https://accounts.zoho.com",
    )
    client = ZohoClient(cfg)
    with pytest.raises(ZohoAuthError):
        client.auth_header()


def test_api_base_fallback_without_tokens() -> None:
    cfg = ZohoConfig(
        client_id="id",
        client_secret="secret",  # pragma: allowlist secret
        refresh_token="refresh",  # pragma: allowlist secret
        accounts_base="https://accounts.zoho.com",
    )
    client = ZohoClient(cfg)
    assert client.api_base == cfg.api_domain_fallback
