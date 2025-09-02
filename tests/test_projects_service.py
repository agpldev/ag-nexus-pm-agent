from __future__ import annotations

from typing import Any

import pytest

from nexus_agent.config import ZohoConfig
from nexus_agent.services.projects import ProjectsService
from nexus_agent.zoho_client import ZohoClient


class _DummyClient(ZohoClient):
    def __init__(self) -> None:  # type: ignore[no-untyped-def]
        cfg = ZohoConfig(
            client_id="id",
            client_secret="secret",  # pragma: allowlist secret
            refresh_token="refresh",  # pragma: allowlist secret
            accounts_base="https://accounts.zoho.com",
        )
        super().__init__(cfg)
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


def test_create_task_success(monkeypatch: pytest.MonkeyPatch) -> None:
    import requests

    captured: dict[str, Any] = {}

    class _Resp:
        ok = True
        status_code = 200

        def raise_for_status(self) -> None:  # noqa: D401
            return None

        def json(self) -> dict[str, Any]:  # noqa: D401
            return {"task": {"id": "999"}}

    def fake_post(url: str, headers: dict[str, str], json: dict[str, Any], timeout: int):  # type: ignore[no-untyped-def]
        captured["url"] = url
        captured["json"] = json
        assert url.endswith("/projects/v1/portals/p1/projects/proj1/tasks/")
        assert json["name"] == "My Task"
        assert "description" in json
        return _Resp()

    monkeypatch.setattr(requests, "post", fake_post)

    svc = ProjectsService(_DummyClient())
    tid = svc.create_task("p1", "proj1", title="My Task", description="desc")
    assert tid == "999"


def test_create_task_missing_id_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    import requests

    class _Resp:
        ok = True
        status_code = 200

        def raise_for_status(self) -> None:  # noqa: D401
            return None

        def json(self) -> dict[str, Any]:  # noqa: D401
            return {"task": {}}

    monkeypatch.setattr(requests, "post", lambda *a, **k: _Resp())  # type: ignore[misc]

    svc = ProjectsService(_DummyClient())
    with pytest.raises(RuntimeError):
        svc.create_task("p1", "proj1", title="x")
