"""Tests for the pluggable name analyzer used in agent_loop.

Fast unit tests (<100ms), no network.
"""

from __future__ import annotations

from nexus_agent.agent_loop import SimpleNameAnalyzer


def test_simple_name_analyzer_missing_extension() -> None:
    analyzer = SimpleNameAnalyzer()
    issues = analyzer.assess("Notes")
    assert any("Missing file extension" in i for i in issues)


def test_simple_name_analyzer_short_title() -> None:
    analyzer = SimpleNameAnalyzer()
    issues = analyzer.assess("Doc.pdf")
    assert any("too short" in i for i in issues)


def test_simple_name_analyzer_ok() -> None:
    analyzer = SimpleNameAnalyzer()
    issues = analyzer.assess("Design Document.pdf")
    assert issues == []
