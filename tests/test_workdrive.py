from __future__ import annotations

from typing import Any

import pytest

from nexus_agent.config import ZohoConfig
from nexus_agent.services.workdrive import WDFile, WorkDriveService
from nexus_agent.zoho_client import ZohoClient


class _Resp:
    def __init__(self, *, status: int, ok: bool, payload: dict[str, Any] | None = None):
        self.status_code = status
        self.ok = ok
        self._payload = payload or {}

    def raise_for_status(self) -> None:
        if not self.ok:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self) -> dict[str, Any]:
        return self._payload


class _DummyClient(ZohoClient):
    def __init__(self) -> None:  # type: ignore[no-untyped-def]
        cfg = ZohoConfig(
            client_id="id",
            client_secret="secret",  # pragma: allowlist secret
            refresh_token="refresh",  # pragma: allowlist secret
            accounts_base="https://accounts.zoho.com",
        )
        super().__init__(cfg)
        # seed tokens so auth_header() works without refresh
        type(
            "T",
            (),
            {
                "token_type": "Bearer",
                "access_token": "atk",
                "expires_in": 3600,
                "api_domain": "https://www.zohoapis.com",
            },
        )
        self._tokens = type(
            "T",
            (),
            {
                "token_type": "Bearer",
                "access_token": "atk",
                "expires_in": 3600,
                "api_domain": "https://www.zohoapis.com",
            },
        )()

    @property
    def api_base(self) -> str:  # override to avoid depending on tokens
        return "https://www.zohoapis.com"


def test_list_files_success(monkeypatch: pytest.MonkeyPatch) -> None:
    import requests

    payload = {
        "data": [
            {"id": "1", "name": "Doc.pdf", "mime_type": "application/pdf"},
            {"id": "2", "name": "Notes", "mime_type": None},
        ]
    }

    def fake_get(url: str, headers: dict[str, str], params: dict[str, object], timeout: int):  # type: ignore[no-untyped-def]
        assert url.endswith("/workdrive/api/v1/folders/f123/files")
        assert params["limit"] == 3
        return _Resp(status=200, ok=True, payload=payload)

    monkeypatch.setattr(requests, "get", fake_get)

    svc = WorkDriveService(_DummyClient())
    files = svc.list_files("f123", limit=3)
    assert [f.id for f in files] == ["1", "2"]
    assert isinstance(files[0], WDFile)


def test_list_files_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    import requests  # noqa: WPS433

    def fake_get(*_: Any, **__: Any):  # type: ignore[no-untyped-def]
        return _Resp(status=200, ok=True, payload={"data": []})

    monkeypatch.setattr(requests, "get", fake_get)

    svc = WorkDriveService(_DummyClient())
    files = svc.list_files("f123", limit=1)
    assert files == []


def test_list_files_error(monkeypatch: pytest.MonkeyPatch) -> None:
    import requests  # noqa: WPS433

    def fake_get(*_: Any, **__: Any):  # type: ignore[no-untyped-def]
        return _Resp(status=500, ok=False)

    monkeypatch.setattr(requests, "get", fake_get)

    svc = WorkDriveService(_DummyClient())
    with pytest.raises(RuntimeError):
        svc.list_files("f123")
