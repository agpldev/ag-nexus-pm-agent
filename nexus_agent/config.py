"""Configuration utilities for the Nexus Agent.

Loads and validates required environment variables with type hints.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Final

from dotenv import load_dotenv

# Load environment variables once at import time. Do not reload in functions to keep
# behavior predictable for tests that patch environment variables.
load_dotenv()


@dataclass(frozen=True)
class ZohoConfig:
    """Typed configuration for Zoho access.

    Uses environment variables only; do not store secrets in code.
    """

    client_id: str
    client_secret: str
    refresh_token: str
    accounts_base: str
    api_domain_fallback: str = "https://www.zohoapis.com"


def load_zoho_config() -> ZohoConfig:
    """Load and validate Zoho config from environment.

    Returns:
        ZohoConfig: The validated configuration object.
    """
    client_id = os.environ.get("ZOHO_CLIENT_ID")
    client_secret = os.environ.get("ZOHO_CLIENT_SECRET")
    refresh_token = os.environ.get("ZOHO_REFRESH_TOKEN")
    accounts_base = os.environ.get("ZOHO_ACCOUNTS_BASE", "https://accounts.zoho.com")

    missing = [
        name
        for name, val in [
            ("ZOHO_CLIENT_ID", client_id),
            ("ZOHO_CLIENT_SECRET", client_secret),
            ("ZOHO_REFRESH_TOKEN", refresh_token),
        ]
        if not val
    ]
    if missing:
        names = ", ".join(missing)
        raise ValueError(f"Missing required environment variables: {names}")

    return ZohoConfig(
        client_id=client_id,  # type: ignore[arg-type]
        client_secret=client_secret,  # type: ignore[arg-type]
        refresh_token=refresh_token,  # type: ignore[arg-type]
        accounts_base=accounts_base,
    )


# Constants
USER_AGENT: Final[str] = "NexusAgent/0.1 (+https://example.invalid)"
