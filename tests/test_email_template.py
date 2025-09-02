"""Tests for EmailDraft and make_email_draft template in agent_loop.

Fast unit tests, no network.
"""

from __future__ import annotations

from nexus_agent.agent_loop import EmailDraft, make_email_draft


def test_make_email_draft_structure() -> None:
    issues = ["Missing file extension", "Document title is too short"]
    draft = make_email_draft("a@x.com", "Doc.pdf", issues)

    assert isinstance(draft, EmailDraft)
    assert draft.to == "a@x.com"
    assert draft.subject == "Review of your document: Doc.pdf"
    # Body should include a header and each issue as a bullet
    assert "Body:\nHello," in draft.body
    assert "- Missing file extension" in draft.body
    assert "- Document title is too short" in draft.body
    # Copy should be preserved in issues field
    assert draft.issues == issues
