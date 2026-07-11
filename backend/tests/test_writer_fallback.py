"""Forced failure yields the templated sentence built from the same signals — never an exception."""

from app.services.writer import GroqWriter, template_reason, template_summary
from tests.helpers import WRITER_EVIDENCE, WRITER_FILM, WRITER_SIGNALS


def test_reason_falls_back_to_template_on_bad_json(monkeypatch):
    w = GroqWriter(api_key="test")
    monkeypatch.setattr(w, "_complete", lambda s, u, m: "not json at all")
    out = w.write_reason(WRITER_EVIDENCE, WRITER_FILM, WRITER_SIGNALS)
    assert out == template_reason(WRITER_FILM, WRITER_SIGNALS)
    # The fallback is real and specific — it reuses the actual fired signals.
    assert "close to the center" in out or "David Lean" in out


def test_summary_falls_back_to_template_on_bad_json(monkeypatch):
    w = GroqWriter(api_key="test")
    monkeypatch.setattr(w, "_complete", lambda s, u, m: "{ broken")
    out = w.write_taste_summary(WRITER_EVIDENCE)
    assert out == template_summary(WRITER_EVIDENCE)
    assert "Drama" in out and "3.8" in out


def test_template_reason_is_specific_not_generic():
    out = template_reason(WRITER_FILM, WRITER_SIGNALS)
    assert "David Lean" in out          # references the real director signal
    assert out.endswith(".")


def test_template_reason_handles_empty_signals():
    out = template_reason(WRITER_FILM, [])
    assert "Doctor Zhivago" in out      # degrades to an honest similarity line, no crash
