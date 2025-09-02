from __future__ import annotations

from typing import Any

import pytest

from nexus_agent.agent_loop import run_once
from nexus_agent.config import ZohoConfig


class _DummyClient:
    def __init__(self) -> None:
        class _T:  # tokens
            token_type = "Bearer"  # pragma: allowlist secret
            access_token = "atk"  # pragma: allowlist secret
            expires_in = 3600
            api_domain = "https://www.zohoapis.com"

        self._tokens = _T()
        self.api_base = "https://www.zohoapis.com"

    def refresh_access_token(self):  # type: ignore[no-untyped-def]
        return self._tokens

    def auth_header(self) -> dict[str, str]:
        return {"Authorization": "Bearer atk", "User-Agent": "UA"}  # pragma: allowlist secret


class _DummyWD:
    def __init__(self, *_: Any, **__: Any) -> None:
        pass

    def list_files(self, folder_id: str, limit: int = 50) -> list[Any]:  # noqa: ARG002
        class _F:
            def __init__(self, name: str) -> None:
                self.id = "1"
                self.name = name
                self.mime_type = "application/pdf"

        return [
            _F("Good Document.pdf"),
            _F("Bad"),  # no extension and short title
        ]


@pytest.fixture()
def cfg() -> ZohoConfig:
    return ZohoConfig(
        client_id="id",
        client_secret="secret",  # pragma: allowlist secret
        refresh_token="refresh",  # pragma: allowlist secret
        accounts_base="https://accounts.zoho.com",
    )


def test_run_once_mock_path(
    monkeypatch: pytest.MonkeyPatch,
    cfg: ZohoConfig,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("NEXUS_USE_LIVE_APIS", raising=False)

    # Stub client to avoid HTTP; only used for token refresh log
    from nexus_agent import agent_loop as loop

    monkeypatch.setattr(loop, "ZohoClient", lambda _cfg: _DummyClient())

    run_once(cfg)
    out = capsys.readouterr().out
    assert "New Email Draft" in out  # at least one issue from mock docs


def test_run_once_live_path(
    monkeypatch: pytest.MonkeyPatch,
    cfg: ZohoConfig,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("NEXUS_USE_LIVE_APIS", "true")
    monkeypatch.setenv("WORKDRIVE_FOLDER_ID", "folder123")

    from nexus_agent import agent_loop as loop

    monkeypatch.setattr(loop, "ZohoClient", lambda _cfg: _DummyClient())
    monkeypatch.setattr(loop, "WorkDriveService", lambda client: _DummyWD())

    run_once(cfg)
    out = capsys.readouterr().out
    assert "New Email Draft" in out  # one bad file should trigger a draft


def test_live_true_without_folder_falls_back_to_mock(
    monkeypatch: pytest.MonkeyPatch, cfg: ZohoConfig, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("NEXUS_USE_LIVE_APIS", "true")
    monkeypatch.delenv("WORKDRIVE_FOLDER_ID", raising=False)

    from nexus_agent import agent_loop as loop

    monkeypatch.setattr(loop, "ZohoClient", lambda _cfg: _DummyClient())
    # Ensure WorkDriveService isn't used due to missing folder
    monkeypatch.setattr(loop, "WorkDriveService", lambda client: _DummyWD())

    run_once(cfg)
    out = capsys.readouterr().out
    assert "New Email Draft" in out


def test_main_invokes_run_once(
    monkeypatch: pytest.MonkeyPatch, cfg: ZohoConfig, capsys: pytest.CaptureFixture[str]
) -> None:
    from nexus_agent import agent_loop as loop

    # Use our cfg from fixture
    monkeypatch.setattr(loop, "load_zoho_config", lambda: cfg)
    monkeypatch.setenv("NEXUS_USE_LIVE_APIS", "false")

    # Stub client
    monkeypatch.setattr(loop, "ZohoClient", lambda _cfg: _DummyClient())

    loop.main()
    out = capsys.readouterr().out
    assert "New Email Draft" in out
