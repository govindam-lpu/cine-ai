"""Search-intent parser: valid JSON becomes filters; any failure → None so the ranker falls back.

The LLM only translates the request into filters (a language task) — it never sees or ranks films.
"""

import json

import app.services.writer as wr
from app.services.writer import GroqWriter, WriterUnavailable, parse_search_intent

GENRES = ["Comedy", "Romance", "Horror", "Thriller", "Drama", "Science Fiction"]

VALID = {
    "genres": ["Romance", "Comedy"],
    "exclude_genres": ["Horror", "Thriller"],
    "keywords": ["feel-good"],
    "exclude_terms": ["stand-up", "concert"],
    "era": None,
    "min_rating": 7.0,
    "query": "a warm, feel-good romantic comedy",
}


def test_valid_intent_parses(monkeypatch):
    w = GroqWriter(api_key="test")
    monkeypatch.setattr(w, "_complete", lambda s, u, m: json.dumps(VALID))
    intent = w.parse_search_intent("romantic comedy, feel good", GENRES)
    assert intent["genres"] == ["Romance", "Comedy"]
    assert intent["exclude_genres"] == ["Horror", "Thriller"]
    assert "stand-up" in intent["exclude_terms"]
    assert intent["min_rating"] == 7.0


def test_malformed_output_returns_none(monkeypatch):
    w = GroqWriter(api_key="test")
    monkeypatch.setattr(w, "_complete", lambda s, u, m: "not json at all")
    assert w.parse_search_intent("anything", GENRES) is None


def test_module_parser_falls_back_and_caches():
    wr._intent_cache.clear()

    class BoomWriter:
        calls = 0

        def parse_search_intent(self, prompt, genres):
            BoomWriter.calls += 1
            raise WriterUnavailable("backend down")

    # A backend outage → None (the ranker then uses its embedding plan), and the result is cached.
    assert parse_search_intent("cache me", GENRES, writer=BoomWriter()) is None
    assert parse_search_intent("cache me", GENRES, writer=BoomWriter()) is None
    assert BoomWriter.calls == 1


def test_empty_parse_is_treated_as_none():
    wr._intent_cache.clear()

    class EmptyWriter:
        def parse_search_intent(self, prompt, genres):
            return {"genres": [], "query": ""}

    assert parse_search_intent("blah blah blah", GENRES, writer=EmptyWriter()) is None
