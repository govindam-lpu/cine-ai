"""Both backends satisfy the protocol and return the same shape; 429 and unreachable are typed."""

import json

import pytest

import app.services.writer as wr
from app.services.writer import GroqWriter, OllamaWriter, Writer, WriterRateLimited, WriterUnavailable
from tests.helpers import (
    FakeHTTPResponse,
    WRITER_EVIDENCE,
    WRITER_FILM,
    WRITER_SIGNALS,
    groq_payload,
    ollama_payload,
)


def test_both_backends_satisfy_the_protocol():
    assert isinstance(GroqWriter(api_key="x"), Writer)
    assert isinstance(OllamaWriter(), Writer)


def test_groq_and_ollama_return_the_same_shape(monkeypatch):
    monkeypatch.setattr(
        wr.requests, "post",
        lambda *a, **k: FakeHTTPResponse(200, groq_payload(json.dumps({"reason": "A Groq reason, two sentences."}))),
    )
    groq_out = GroqWriter(api_key="x").write_reason(WRITER_EVIDENCE, WRITER_FILM, WRITER_SIGNALS)

    monkeypatch.setattr(
        wr.requests, "post",
        lambda *a, **k: FakeHTTPResponse(200, ollama_payload(json.dumps({"reason": "An Ollama reason, two sentences."}))),
    )
    ollama_out = OllamaWriter().write_reason(WRITER_EVIDENCE, WRITER_FILM, WRITER_SIGNALS)

    assert isinstance(groq_out, str) and isinstance(ollama_out, str)
    assert groq_out and ollama_out


def test_groq_429_raises_rate_limited(monkeypatch):
    monkeypatch.setattr(wr.requests, "post", lambda *a, **k: FakeHTTPResponse(429, {}))
    with pytest.raises(WriterRateLimited):
        GroqWriter(api_key="x").write_reason(WRITER_EVIDENCE, WRITER_FILM, WRITER_SIGNALS)


def test_groq_missing_key_raises_unavailable():
    with pytest.raises(WriterUnavailable):
        GroqWriter(api_key="").write_reason(WRITER_EVIDENCE, WRITER_FILM, WRITER_SIGNALS)


def test_ollama_connection_refused_raises_unavailable(monkeypatch):
    def refuse(*a, **k):
        raise wr.requests.ConnectionError("connection refused")

    monkeypatch.setattr(wr.requests, "post", refuse)
    with pytest.raises(WriterUnavailable):
        OllamaWriter().write_reason(WRITER_EVIDENCE, WRITER_FILM, WRITER_SIGNALS)


def test_transient_groq_5xx_degrades_to_template(monkeypatch):
    # A 500 (not 429, not a connection refusal) should retry then fall back — never a 500 to the user.
    monkeypatch.setattr(wr.requests, "post", lambda *a, **k: FakeHTTPResponse(500, {}))
    out = GroqWriter(api_key="x").write_reason(WRITER_EVIDENCE, WRITER_FILM, WRITER_SIGNALS)
    from app.services.writer import template_reason

    assert out == template_reason(WRITER_FILM, WRITER_SIGNALS)


def test_get_writer_selects_backend(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "writer_backend", "groq")
    assert isinstance(wr.get_writer(), GroqWriter)
    monkeypatch.setattr(settings, "writer_backend", "ollama")
    assert isinstance(wr.get_writer(), OllamaWriter)
