"""Agentic AI loop for Project Nexus (Healthcare).

This is a minimal runnable skeleton that:
- Loads Zoho config from environment
- Refreshes an access token via Zoho
- Executes a placeholder step simulating a document QA/check flow

Extend this module to orchestrate multi-step tasks across:
- Zoho Projects / Bugtracker (task intake, status updates)
- WorkDrive (document listing / metadata)
- Future services (WSO2 gateway, PostgreSQL, Redis, etc.) per PRD
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

from loguru import logger

from .config import ZohoConfig, load_zoho_config
from .services.projects import ProjectsService
from .services.workdrive import WDFile, WorkDriveService
from .zoho_client import ZohoClient


@dataclass(frozen=True)
class Document:
    """Domain model for a project document."""

    id: str
    name: str
    author: str


@dataclass(frozen=True)
class EmailDraft:
    """Structured email draft produced from analyzer findings."""

    to: str
    subject: str
    body: str
    issues: list[str]


def make_email_draft(recipient: str, doc_name: str, issues: list[str]) -> EmailDraft:
    """Create a templated `EmailDraft` for the given document and issues."""
    subject = f"Review of your document: {doc_name}"
    bullets = "\n- ".join(issues)
    body = (
        "Body:\nHello,\n\nI reviewed your document and found:\n- "
        + bullets
        + "\n\nThanks,\nNexus Agent"
    )
    return EmailDraft(to=recipient, subject=subject, body=body, issues=list(issues))


def _mock_list_documents() -> list[Document]:
    """Temporary stub for WorkDrive/Projects documents."""
    return [
        Document(id="doc1", name="Requirement Specification.docx", author="author1@example.com"),
        Document(id="doc2", name="Design Document.pdf", author="author2@example.com"),
        Document(id="doc3", name="Notes", author="author3@example.com"),  # missing extension
    ]


class NameAnalyzer(Protocol):
    """Protocol for analyzing names (file/document) and returning issue strings.

    Implementations should be fast, deterministic, and side-effect free.
    """

    def assess(self, name: str) -> list[str]:
        """Return a list of human-readable issues for the given name."""


class SimpleNameAnalyzer:
    """Baseline analyzer replicating prior heuristic checks for names."""

    def assess(self, name: str) -> list[str]:
        issues: list[str] = []
        if "." not in name:
            issues.append("Missing file extension")
        if len(name.split(".")[0]) < 5:
            issues.append("Document title is too short")
        return issues


def get_default_analyzer() -> NameAnalyzer:
    """Factory for the default analyzer implementation.

    This indirection enables future injection or configuration without API churn.
    """
    return SimpleNameAnalyzer()


def _assess_document_quality(doc: Document) -> list[str]:
    """Assess quality of a `Document` using the default analyzer.

    Kept for backward compatibility with existing tests.
    """
    analyzer = get_default_analyzer()
    return analyzer.assess(doc.name)


def _assess_wdfile_quality(file: WDFile) -> list[str]:
    """Assess quality of a WorkDrive file using the default analyzer."""
    analyzer = get_default_analyzer()
    issues = analyzer.assess(file.name)

    # MIME-based heuristics (best-effort based on metadata only)
    mime = file.mime_type or None
    if mime is None:
        issues.append("Missing MIME type")
    else:
        lower = file.name.lower()
        if lower.endswith(".pdf") and not mime.startswith("application/pdf"):
            issues.append("Extension .pdf but MIME is not application/pdf")
        if lower.endswith(".docx") and not mime.startswith(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ):
            issues.append(
                "Extension .docx but MIME is not "
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        if lower.endswith(".txt") and not mime.startswith("text/"):
            issues.append("Extension .txt but MIME is not text/*")

    return issues


def run_once(cfg: ZohoConfig) -> None:
    """Run a single agent iteration.

    Steps:
    1) Refresh Zoho access token (validates auth path)
    2) List project documents (stub)
    3) Assess quality and emit email drafts (stdout for now)
    """
    client = ZohoClient(cfg)
    tokens = client.refresh_access_token()
    logger.info("Zoho API base resolved to {}", tokens.api_domain)

    use_live = os.environ.get("NEXUS_USE_LIVE_APIS", "false").lower() in {"1", "true", "yes"}

    # Optional: list projects for visibility/debugging using Zoho Projects
    if os.environ.get("NEXUS_LIST_PROJECTS", "false").lower() in {"1", "true", "yes"}:
        portal_id = os.environ.get("ZOHO_PORTAL_ID")
        if not portal_id:
            logger.warning(
                "NEXUS_LIST_PROJECTS=true but ZOHO_PORTAL_ID not set; skipping projects list",
            )
        else:
            try:
                proj_svc = ProjectsService(client)
                projs = proj_svc.list_portal_projects(portal_id, limit=10)
                logger.info("Projects in portal {}: {}", portal_id, len(projs))
                for p in projs:
                    print(f"- Project: {p.name} (id={p.id})")
            except Exception as exc:  # noqa: BLE001
                logger.error("Failed to list projects: {}", exc)

    if use_live:
        # Live path: list files via WorkDrive for a configured folder
        workdrive = WorkDriveService(client)

        folder_id: str | None = os.environ.get("WORKDRIVE_FOLDER_ID")
        if not folder_id:
            logger.warning(
                "NEXUS_USE_LIVE_APIS=true but WORKDRIVE_FOLDER_ID not set; falling back to mock"
            )
        else:
            logger.info("Listing WorkDrive files from folder {}", folder_id)
            files = workdrive.list_files(folder_id, limit=50)
            for f in files:
                issues = _assess_wdfile_quality(f)
                if issues:
                    draft = make_email_draft("project-docs@example.com", f.name, issues)
                    logger.info("Drafting email for {}: {} issues", f.name, len(issues))
                    print("--- New Email Draft ---")
                    print(f"To: {draft.to}")
                    print(f"Subject: {draft.subject}")
                    print(draft.body)
                    print("-----------------------")
                else:
                    logger.info("No issues found for {}", f.name)
            return

    # Mock fallback path (no live APIs)
    docs = _mock_list_documents()
    for doc in docs:
        issues = _assess_document_quality(doc)
        if issues:
            draft = make_email_draft(doc.author, doc.name, issues)
            logger.info("Drafting email for {}: {} issues", doc.name, len(issues))
            print("--- New Email Draft ---")
            print(f"To: {draft.to}")
            print(f"Subject: {draft.subject}")
            print(draft.body)
            print("-----------------------")
        else:
            logger.info("No issues found for {}", doc.name)


def main() -> None:
    """CLI entrypoint for a single agent iteration."""
    cfg = load_zoho_config()
    run_once(cfg)


if __name__ == "__main__":
    main()
