"""Zoho Projects service wrappers.

These are thin, typed helpers over Zoho Projects API endpoints.
Currently provide interfaces and simple wiring; implement endpoints incrementally.
"""

from __future__ import annotations

from dataclasses import dataclass

import requests

from ..zoho_client import ZohoClient


@dataclass(frozen=True)
class Project:
    """Minimal project model."""

    id: str
    name: str


class ProjectsService:
    """Service for Zoho Projects operations."""

    def __init__(self, client: ZohoClient):
        self._client = client

    def list_portal_projects(self, portal_id: str, *, limit: int = 50) -> list[Project]:
        """List projects for a given portal.

        Args:
            portal_id: Zoho portal identifier (string subdomain or id).
            limit: Max number of projects to return (server may cap separately).

        Returns:
            A list of Project models.
        """
        headers = self._client.auth_header()
        base = self._client.api_base
        url = f"{base}/projects/v1/portals/{portal_id}/projects/"
        params: dict[str, object] = {"index": 1, "range": limit}
        # NOTE: Enable once we wire in real usage
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("projects") or []
        results: list[Project] = []
        for it in items:
            pid = str(it.get("id"))
            name = str(it.get("name"))
            results.append(Project(id=pid, name=name))
        return results

    def create_task(
        self,
        portal_id: str,
        project_id: str,
        *,
        title: str,
        description: str | None = None,
    ) -> str:
        """Create a task in a Zoho Project and return its ID.

        Args:
            portal_id: Zoho portal identifier.
            project_id: Target project identifier.
            title: Task title.
            description: Optional detailed description/notes.

        Returns:
            The created task ID as a string.
        """
        headers = self._client.auth_header()
        base = self._client.api_base
        url = f"{base}/projects/v1/portals/{portal_id}/projects/{project_id}/tasks/"
        payload: dict[str, object] = {"name": title}
        if description:
            payload["description"] = description
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        task = data.get("task") or {}
        task_id = str(task.get("id"))
        if not task_id or task_id == "None":  # defensive
            raise RuntimeError("Task creation response missing id")
        return task_id
