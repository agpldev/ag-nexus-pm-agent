from __future__ import annotations

from typing import Any

import pytest

from nexus_agent.config import ZohoConfig
from nexus_agent.services.projects import Project, ProjectsService
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


def test_list_portal_projects_success(monkeypatch: pytest.MonkeyPatch) -> None:
    import requests  # noqa: WPS433

    payload = {
        "projects": [
            {"id": "p1", "name": "Alpha"},
            {"id": "p2", "name": "Beta"},
        ]
    }

    def fake_get(url: str, headers: dict[str, str], params: dict[str, object], timeout: int):  # type: ignore[no-untyped-def]
        assert url.endswith("/projects/v1/portals/portal123/projects/")
        assert params["range"] == 10
        return _Resp(status=200, ok=True, payload=payload)

    monkeypatch.setattr(requests, "get", fake_get)

    svc = ProjectsService(_DummyClient())
    projects = svc.list_portal_projects("portal123", limit=10)
    assert [p.id for p in projects] == ["p1", "p2"]
    assert isinstance(projects[0], Project)


def test_list_portal_projects_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    import requests  # noqa: WPS433

    def fake_get(*_: Any, **__: Any):  # type: ignore[no-untyped-def]
        return _Resp(status=200, ok=True, payload={"projects": []})

    monkeypatch.setattr(requests, "get", fake_get)

    svc = ProjectsService(_DummyClient())
    projects = svc.list_portal_projects("portal123", limit=5)
    assert projects == []


def test_list_portal_projects_error(monkeypatch: pytest.MonkeyPatch) -> None:
    import requests  # noqa: WPS433

    def fake_get(*_: Any, **__: Any):  # type: ignore[no-untyped-def]
        return _Resp(status=502, ok=False)

    monkeypatch.setattr(requests, "get", fake_get)

    svc = ProjectsService(_DummyClient())
    with pytest.raises(RuntimeError):
        svc.list_portal_projects("portal123")
