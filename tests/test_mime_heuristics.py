from __future__ import annotations

from nexus_agent.agent_loop import _assess_wdfile_quality
from nexus_agent.services.workdrive import WDFile


def test_missing_mime_flagged() -> None:
    f = WDFile(id="1", name="Doc.pdf", mime_type=None)
    issues = _assess_wdfile_quality(f)
    assert any("Missing MIME type" in i for i in issues)


def test_pdf_mismatch_flagged() -> None:
    f = WDFile(id="1", name="Doc.pdf", mime_type="text/plain")
    issues = _assess_wdfile_quality(f)
    assert any(".pdf" in i and "MIME is not application/pdf" in i for i in issues)


def test_docx_mismatch_flagged() -> None:
    f = WDFile(id="1", name="Spec.docx", mime_type="application/pdf")
    issues = _assess_wdfile_quality(f)
    assert any(".docx" in i for i in issues)


def test_txt_mismatch_flagged() -> None:
    f = WDFile(id="1", name="readme.txt", mime_type="application/octet-stream")
    issues = _assess_wdfile_quality(f)
    assert any(".txt" in i and "text/*" in i for i in issues)


def test_matching_mimes_no_extra_flags() -> None:
    # Valid PDF
    f1 = WDFile(id="1", name="Doc.pdf", mime_type="application/pdf")
    # Valid DOCX
    f2 = WDFile(
        id="2",
        name="Spec.docx",
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    # Valid TXT
    f3 = WDFile(id="3", name="readme.txt", mime_type="text/plain")

    assert not any("MIME" in i for i in _assess_wdfile_quality(f1))
    assert not any("MIME" in i for i in _assess_wdfile_quality(f2))
    assert not any("MIME" in i for i in _assess_wdfile_quality(f3))
