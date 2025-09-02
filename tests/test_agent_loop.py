"""Unit tests for minimal agent loop utilities.

Fast tests (<100ms) without network.
"""

from __future__ import annotations

from nexus_agent.agent_loop import Document, _assess_document_quality


def test_assess_document_quality_flags_missing_extension():
    doc = Document(id="1", name="Notes", author="a@x.com")
    issues = _assess_document_quality(doc)
    assert any("Missing file extension" in i for i in issues)


def test_assess_document_quality_flags_short_title():
    doc = Document(id="1", name="Doc.pdf", author="a@x.com")
    issues = _assess_document_quality(doc)
    assert any("too short" in i for i in issues)


def test_assess_document_quality_ok():
    doc = Document(id="1", name="Design Document.pdf", author="a@x.com")
    issues = _assess_document_quality(doc)
    assert issues == []
