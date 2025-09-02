from __future__ import annotations

import pytest

from nexus_agent.config import load_zoho_config


def test_load_zoho_config_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ZOHO_CLIENT_ID", "id")
    monkeypatch.setenv("ZOHO_CLIENT_SECRET", "secret")  # pragma: allowlist secret
    monkeypatch.setenv("ZOHO_REFRESH_TOKEN", "refresh")  # pragma: allowlist secret
    cfg = load_zoho_config()
    assert cfg.client_id == "id"
    assert cfg.client_secret == "secret"  # pragma: allowlist secret
    assert cfg.refresh_token == "refresh"  # pragma: allowlist secret
    assert cfg.accounts_base.startswith("https://")


def test_load_zoho_config_missing_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    for k in ["ZOHO_CLIENT_ID", "ZOHO_CLIENT_SECRET", "ZOHO_REFRESH_TOKEN"]:
        monkeypatch.delenv(k, raising=False)
    with pytest.raises(ValueError) as ei:
        load_zoho_config()
    msg = str(ei.value)
    assert "Missing required environment variables" in msg
