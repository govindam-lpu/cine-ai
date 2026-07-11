"""Valid model output parses; malformed triggers a retry then the template."""

import json

from app.services.writer import GroqWriter, template_reason
from tests.helpers import WRITER_EVIDENCE, WRITER_FILM, WRITER_SIGNALS


def test_valid_json_is_returned(monkeypatch):
    w = GroqWriter(api_key="test")
    monkeypatch.setattr(w, "_complete", lambda s, u, m: json.dumps({"reason": "You love slow cinema, and this fits."}))
    assert w.write_reason(WRITER_EVIDENCE, WRITER_FILM, WRITER_SIGNALS) == "You love slow cinema, and this fits."


def test_retry_recovers_after_one_bad_response(monkeypatch):
    calls = {"n": 0}

    def flaky(s, u, m):
        calls["n"] += 1
        return "garbage" if calls["n"] == 1 else json.dumps({"reason": "Valid on the second try, two sentences."})

    w = GroqWriter(api_key="test")
    monkeypatch.setattr(w, "_complete", flaky)
    assert w.write_reason(WRITER_EVIDENCE, WRITER_FILM, WRITER_SIGNALS) == "Valid on the second try, two sentences."
    assert calls["n"] == 2


def test_malformed_twice_falls_back_to_template(monkeypatch):
    calls = {"n": 0}

    def bad(s, u, m):
        calls["n"] += 1
        return "still not json"

    w = GroqWriter(api_key="test")
    monkeypatch.setattr(w, "_complete", bad)
    out = w.write_reason(WRITER_EVIDENCE, WRITER_FILM, WRITER_SIGNALS)
    assert calls["n"] == 2                                   # tried twice before giving up
    assert out == template_reason(WRITER_FILM, WRITER_SIGNALS)


def test_valid_json_wrong_shape_falls_back(monkeypatch):
    w = GroqWriter(api_key="test")
    # Valid JSON, but "reason" too short to pass the schema's min_length.
    monkeypatch.setattr(w, "_complete", lambda s, u, m: json.dumps({"reason": "x"}))
    assert w.write_reason(WRITER_EVIDENCE, WRITER_FILM, WRITER_SIGNALS) == template_reason(WRITER_FILM, WRITER_SIGNALS)


def test_reason_facts_carry_the_right_signals():
    import app.services.writer as wr

    facts = wr._reason_facts(WRITER_EVIDENCE, WRITER_FILM, WRITER_SIGNALS)
    assert facts["film"]["title"] == "Doctor Zhivago"
    assert any("David Lean" in d for d in facts["why_it_scored"])


def test_summary_facts_translate_correlations_to_words():
    import app.services.writer as wr

    facts = wr._summary_facts(WRITER_EVIDENCE)
    assert "Drama" in facts["genres_you_rate_up"]
    assert "David Lean" in facts["directors_you_rate_up"]
    # obscurity -0.5 → drawn to lesser-known; patience 0.4 → rewards longer/slower.
    assert any("lesser-known" in t for t in facts["tendencies"])
    assert any("longer" in t for t in facts["tendencies"])
