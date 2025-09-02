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

from loguru import logger

from .config import ZohoConfig, load_zoho_config
from .services.workdrive import WDFile, WorkDriveService
from .zoho_client import ZohoClient


@dataclass(frozen=True)
class Document:
    """Domain model for a project document."""

    id: str
    name: str
    author: str


def _mock_list_documents() -> list[Document]:
    """Temporary stub for WorkDrive/Projects documents."""
    return [
        Document(id="doc1", name="Requirement Specification.docx", author="author1@example.com"),
        Document(id="doc2", name="Design Document.pdf", author="author2@example.com"),
        Document(id="doc3", name="Notes", author="author3@example.com"),  # missing extension
    ]


def _assess_document_quality(doc: Document) -> list[str]:
    """Toy quality checks until real analyzers are integrated."""
    issues: list[str] = []
    if "." not in doc.name:
        issues.append("Missing file extension")
    if len(doc.name.split(".")[0]) < 5:
        issues.append("Document title is too short")
    return issues


def _assess_wdfile_quality(file: WDFile) -> list[str]:
    """Quality checks adapted for WorkDrive file objects."""
    issues: list[str] = []
    name = file.name
    if "." not in name:
        issues.append("Missing file extension")
    if len(name.split(".")[0]) < 5:
        issues.append("Document title is too short")
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
                    logger.info("Drafting email for {}: {} issues", f.name, len(issues))
                    print("--- New Email Draft ---")
                    # Author unknown from WorkDrive list; placeholder address
                    print("To: project-docs@example.com")
                    print(f"Subject: Review of your document: {f.name}")
                    bullets = "\n- ".join(issues)
                    print(
                        "Body:\nHello,\n\nI reviewed your document and found:\n- "
                        + bullets
                        + "\n\nThanks,\nNexus Agent"
                    )
                    print("-----------------------")
                else:
                    logger.info("No issues found for {}", f.name)
            return

    # Mock fallback path (no live APIs)
    docs = _mock_list_documents()
    for doc in docs:
        issues = _assess_document_quality(doc)
        if issues:
            logger.info("Drafting email for {}: {} issues", doc.name, len(issues))
            print("--- New Email Draft ---")
            print(f"To: {doc.author}")
            print(f"Subject: Review of your document: {doc.name}")
            bullets = "\n- ".join(issues)
            print(
                "Body:\nHello,\n\nI reviewed your document and found:\n- "
                + bullets
                + "\n\nThanks,\nNexus Agent"
            )
            print("-----------------------")
        else:
            logger.info("No issues found for {}", doc.name)


def main() -> None:
    """CLI entrypoint for a single agent iteration."""
    cfg = load_zoho_config()
    run_once(cfg)


if __name__ == "__main__":
    main()
