"""Zoho WorkDrive service wrappers.

Minimal helpers around WorkDrive files listing. Designed for incremental build-out.
"""

from __future__ import annotations

from dataclasses import dataclass

import requests

from ..zoho_client import ZohoClient


@dataclass(frozen=True)
class WDFile:
    """Minimal WorkDrive file model."""

    id: str
    name: str
    mime_type: str | None


class WorkDriveService:
    """Service for Zoho WorkDrive operations."""

    def __init__(self, client: ZohoClient):
        self._client = client

    def list_files(self, folder_id: str, *, limit: int = 50) -> list[WDFile]:
        """List files inside a WorkDrive folder.

        Args:
            folder_id: WorkDrive folder identifier.
            limit: Max number of items to request per page (best-effort).
        """
        headers = self._client.auth_header()
        base = self._client.api_base
        # WorkDrive v1 list contents endpoint
        url = f"{base}/workdrive/api/v1/folders/{folder_id}/files"
        params: dict[str, object] = {"limit": limit}
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("data") or []
        results: list[WDFile] = []
        for it in items:
            fid = str(it.get("id"))
            name = str(it.get("name"))
            mime = it.get("mime_type")
            results.append(WDFile(id=fid, name=name, mime_type=mime))
        return results
