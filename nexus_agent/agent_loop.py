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
import random
import time
from dataclasses import dataclass
from functools import partial
from typing import Protocol

from loguru import logger

from .config import ZohoConfig, load_zoho_config
from .errors import is_retryable
from .metrics import (
    add_rate_limit_sleep,
    inc_retries,
    inc_retry_exhausted,
    inc_tasks_created,
    inc_tasks_skipped_dedupe,
)
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


def _env_retry_attempts() -> int:
    """Read max retry attempts from env with sane defaults."""
    raw = os.environ.get("NEXUS_RETRY_ATTEMPTS", "3")
    try:
        val = int(raw)
        return max(1, min(val, 10))
    except ValueError:
        return 3


def _env_retry_base_delay() -> float:
    """Base delay in seconds derived from ms env var (default 500ms)."""
    raw = os.environ.get("NEXUS_RETRY_BASE_DELAY_MS", "500")
    try:
        ms = float(raw)
        return max(0.01, ms / 1000.0)
    except ValueError:
        return 0.5


def _env_tasks_rps() -> float:
    """Read task creation rate limit in requests per second.

    Defaults to 2.0 rps. Minimum 0.1 rps.
    """
    try:
        rps = float(os.environ.get("NEXUS_TASKS_RPS", "2.0"))
    except ValueError:
        rps = 2.0
    return max(0.1, rps)


class TokenBucket:
    """Simple token-bucket rate limiter.

    Fills at `rate` tokens/sec up to `capacity` tokens. `consume(1)` will block
    (sleep) until a token is available.
    """

    def __init__(self, rate: float, capacity: int | None = None) -> None:
        self.rate = max(0.1, rate)
        cap = int(capacity if capacity is not None else max(1, int(rate)))
        self.capacity = max(1, cap)
        self.tokens = float(self.capacity)
        self.last = time.monotonic()

    def consume(self, amount: float = 1.0) -> None:
        while True:
            now = time.monotonic()
            elapsed = now - self.last
            self.last = now
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            if self.tokens >= amount:
                self.tokens -= amount
                return
            # need to wait; compute time to next token
            needed = amount - self.tokens
            sleep_for = needed / self.rate
            logger.info("Rate limit: sleeping {:.3f}s", sleep_for)
            add_rate_limit_sleep(sleep_for)
            time.sleep(sleep_for)


def _retry(func, *, attempts: int, base_delay: float, factor: float = 2.0, retry_if=None):  # type: ignore[no-untyped-def]
    """Simple exponential backoff retry for transient failures.

    Args:
        func: Zero-arg callable to execute.
        attempts: Max attempts including the first try.
        base_delay: Initial delay in seconds between retries.
        factor: Backoff multiplier.
    """
    last_exc: Exception | None = None
    delay = base_delay
    for i in range(attempts):
        try:
            return func()
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            # stop if last attempt, or predicate says not retryable
            if i == attempts - 1 or (retry_if is not None and not retry_if(exc)):
                inc_retry_exhausted()
                raise
            # jittered backoff
            jitter = random.uniform(0.5, 1.5)
            sleep_for = delay * jitter
            logger.warning(
                "Attempt {}/{} failed: {}. Retrying in {:.2f}s",
                i + 1,
                attempts,
                exc,
                sleep_for,
            )
            inc_retries()
            time.sleep(sleep_for)
            delay *= factor
    assert last_exc is not None
    raise last_exc


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
        created_task_keys: set[tuple[str, str, str]] = set()
        task_bucket = TokenBucket(_env_tasks_rps())

        folder_id: str | None = os.environ.get("WORKDRIVE_FOLDER_ID")
        if not folder_id:
            logger.warning(
                "NEXUS_USE_LIVE_APIS=true but WORKDRIVE_FOLDER_ID not set; falling back to mock"
            )
        else:
            logger.info("Listing WorkDrive files from folder {}", folder_id)
            files = _retry(
                partial(workdrive.list_files, folder_id, limit=50),
                attempts=_env_retry_attempts(),
                base_delay=_env_retry_base_delay(),
                retry_if=is_retryable,
            )
            for f in files:
                issues = _assess_wdfile_quality(f)
                if issues:
                    draft = make_email_draft("project-docs@example.com", f.name, issues)
                    logger.info(
                        "Drafting email for {}: {} issues (file_id={})",
                        f.name,
                        len(issues),
                        f.id,
                    )
                    print("--- New Email Draft ---")
                    print(f"To: {draft.to}")
                    print(f"Subject: {draft.subject}")
                    print(draft.body)
                    print("-----------------------")
                    if os.environ.get("NEXUS_CREATE_TASKS", "false").lower() in [
                        "1",
                        "true",
                        "yes",
                    ]:
                        portal_id = os.environ.get("ZOHO_PORTAL_ID")
                        project_id = os.environ.get("ZOHO_PROJECT_ID")
                        if portal_id and project_id:
                            try:
                                proj_svc = ProjectsService(client)
                                title = f"Doc issues: {f.name}"
                                desc = draft.body
                                key = (portal_id, project_id, title)
                                if key in created_task_keys:
                                    logger.info(
                                        "Skipping duplicate task creation for {} "
                                        "(portal={}, project={})",
                                        f.name,
                                        portal_id,
                                        project_id,
                                    )
                                    inc_tasks_skipped_dedupe()
                                    continue
                                # rate limit task creation
                                task_bucket.consume()
                                task_id = _retry(
                                    partial(
                                        proj_svc.create_task,
                                        portal_id,
                                        project_id,
                                        title=title,
                                        description=desc,
                                    ),
                                    attempts=_env_retry_attempts(),
                                    base_delay=_env_retry_base_delay(),
                                    retry_if=is_retryable,
                                )
                                logger.info(
                                    "Created Zoho task {} for {} (portal={}, project={})",
                                    task_id,
                                    f.name,
                                    portal_id,
                                    project_id,
                                )
                                inc_tasks_created()
                                created_task_keys.add(key)
                            except Exception as exc:  # noqa: BLE001
                                logger.error("Failed to create task: {}", exc)
                        else:
                            logger.warning(
                                "NEXUS_CREATE_TASKS=true but ZOHO_PORTAL_ID/ZOHO_PROJECT_ID not set"
                            )
                else:
                    logger.info("No issues found for {}", f.name)
            return

    # Mock fallback path (no live APIs)
    docs = _mock_list_documents()
    created_task_keys: set[tuple[str, str, str]] = set()
    for doc in docs:
        issues = _assess_document_quality(doc)
        if issues:
            draft = make_email_draft(doc.author, doc.name, issues)
            logger.info(
                "Drafting email for {}: {} issues (doc_id={})",
                doc.name,
                len(issues),
                doc.id,
            )
            print("--- New Email Draft ---")
            print(f"To: {draft.to}")
            print(f"Subject: {draft.subject}")
            print(draft.body)
            print("-----------------------")
            if os.environ.get("NEXUS_CREATE_TASKS", "false").lower() in {
                "1",
                "true",
                "yes",
            }:
                portal_id = os.environ.get("ZOHO_PORTAL_ID")
                project_id = os.environ.get("ZOHO_PROJECT_ID")
                if portal_id and project_id:
                    try:
                        proj_svc = ProjectsService(ZohoClient(cfg))
                        title = f"Doc issues: {doc.name}"
                        desc = draft.body
                        key = (portal_id, project_id, title)
                        if key in created_task_keys:
                            logger.info(
                                "Skipping duplicate task creation for {} (portal={}, project={})",
                                doc.name,
                                portal_id,
                                project_id,
                            )
                            inc_tasks_skipped_dedupe()
                            continue
                        # rate limit task creation
                        task_bucket.consume()
                        task_id = _retry(
                            partial(
                                proj_svc.create_task,
                                portal_id,
                                project_id,
                                title=title,
                                description=desc,
                            ),
                            attempts=_env_retry_attempts(),
                            base_delay=_env_retry_base_delay(),
                            retry_if=is_retryable,
                        )
                        logger.info(
                            "Created Zoho task {} for {} (portal={}, project={})",
                            task_id,
                            doc.name,
                            portal_id,
                            project_id,
                        )
                        inc_tasks_created()
                        created_task_keys.add(key)
                    except Exception as exc:  # noqa: BLE001
                        logger.error("Failed to create task: {}", exc)
                else:
                    logger.warning(
                        "NEXUS_CREATE_TASKS=true but ZOHO_PORTAL_ID/ZOHO_PROJECT_ID not set"
                    )
        else:
            logger.info("No issues found for {}", doc.name)


def main() -> None:
    """CLI entrypoint for a single agent iteration."""
    cfg = load_zoho_config()
    run_once(cfg)


if __name__ == "__main__":
    main()
