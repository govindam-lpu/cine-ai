"""The Groq daily budget produces a graceful 'at capacity' state — template reasons, never a 500."""

from app.core.budget import GenerationBudget
from tests.helpers import parse_sse, seed_ready_profile


def test_budget_unmetered_for_ollama(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "writer_backend", "ollama")
    b = GenerationBudget(daily_limit=1)
    b.consume()
    b.consume()
    assert b.exhausted() is False       # local Ollama is unlimited


def test_budget_metered_for_groq(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "writer_backend", "groq")
    b = GenerationBudget(daily_limit=2)
    assert b.exhausted() is False
    b.consume()
    b.consume()
    assert b.exhausted() is True
    assert b.remaining() == 0


def test_recommendations_at_capacity_uses_templates(client, monkeypatch):
    handle = seed_ready_profile(client, monkeypatch, handle="capped")

    # Simulate the daily Groq budget being spent.
    from app.core.config import settings
    from app.core import budget as budget_mod

    monkeypatch.setattr(settings, "writer_backend", "groq")
    monkeypatch.setattr(budget_mod.budget, "daily_limit", 0)
    budget_mod.budget.reset()

    resp = client.get(f"/api/profiles/{handle}/recommendations")
    assert resp.status_code == 200                       # never a 500
    recs = parse_sse(resp.text)
    assert len(recs) == 8
    assert all(r["at_capacity"] for r in recs)           # flagged for the UI
    # Reasons are the template (built from signals), not the FakeWriter's canned line.
    assert all("Recommended for you because it fits your taste" not in r["reason"] for r in recs)
    assert all(r["reason"] for r in recs)                # still real prose, never blank
