"""Zoho client with typed auth refresh and request helpers.

This client focuses on auth/token handling. Data APIs can be added incrementally.
"""

from __future__ import annotations

from dataclasses import dataclass

import requests
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import USER_AGENT, ZohoConfig


@dataclass(frozen=True)
class ZohoTokens:
    """Holds short-lived access token info.

    Attributes:
        access_token: OAuth access token used in API calls.
        token_type: Token type (usually "Bearer").
        expires_in: Seconds until expiry.
        api_domain: API base domain returned by Zoho (fallback if missing in config).
    """

    access_token: str
    token_type: str
    expires_in: int
    api_domain: str


class ZohoAuthError(Exception):
    """Raised when Zoho authentication/refresh fails."""


class ZohoClient:
    """Minimal Zoho client providing token refresh and headers.

    Extend this with product-specific API helpers (Projects, Bugtracker, WorkDrive).
    """

    def __init__(self, cfg: ZohoConfig):
        self._cfg = cfg
        self._tokens: ZohoTokens | None = None

    @retry(
        wait=wait_exponential(multiplier=0.5, min=1, max=6),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def refresh_access_token(self) -> ZohoTokens:
        """Refresh the access token using the configured refresh token.

        Returns:
            ZohoTokens: The refreshed token payload.

        Raises:
            ZohoAuthError: If the token endpoint returns a non-2xx response.
        """
        url = f"{self._cfg.accounts_base}/oauth/v2/token"
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self._cfg.refresh_token,
            "client_id": self._cfg.client_id,
            "client_secret": self._cfg.client_secret,
        }
        logger.info("Refreshing Zoho access token via {}", url)
        resp = requests.post(url, data=data, headers={"User-Agent": USER_AGENT}, timeout=30)
        if not resp.ok:
            raise ZohoAuthError(f"Zoho token endpoint error {resp.status_code}: {resp.text}")
        payload: dict[str, object] = resp.json()
        access_token = str(payload.get("access_token", ""))
        token_type = str(payload.get("token_type", "Bearer"))
        expires_in = int(payload.get("expires_in", 3600))
        api_domain = str(payload.get("api_domain", self._cfg.api_domain_fallback))
        tokens = ZohoTokens(
            access_token=access_token,
            token_type=token_type,
            expires_in=expires_in,
            api_domain=api_domain,
        )
        self._tokens = tokens
        logger.info("Access token refreshed (expires in {}s)", tokens.expires_in)
        return tokens

    def auth_header(self) -> dict[str, str]:
        """Build Authorization header from cached tokens.

        Returns:
            dict[str, str]: Headers to use in API calls.

        Raises:
            ZohoAuthError: If tokens are missing; call refresh_access_token first.
        """
        if not self._tokens:
            raise ZohoAuthError("No tokens present; call refresh_access_token() first")
        return {
            "Authorization": f"{self._tokens.token_type} {self._tokens.access_token}",
            "User-Agent": USER_AGENT,
        }

    @property
    def api_base(self) -> str:
        """Return the API base domain for subsequent calls."""
        if not self._tokens:
            return self._cfg.api_domain_fallback
        return self._tokens.api_domain
