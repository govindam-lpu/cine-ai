"""The writer — the only component that touches a language model, and it does no reasoning.

The ranker already decided what and why; the writer just phrases the facts as prose. Two backends
behind one protocol, chosen by WRITER_BACKEND: GroqWriter (llama-3.3-70b-versatile, production) and
OllamaWriter (llama3.2:3b, local dev). Both request JSON-object mode and we validate the result with
Pydantic — llama-3.3-70b doesn't support Groq's strict json_schema, so validate-in-code + retry +
template fallback is the portable path, and it makes both backends return the identical shape.

Failure policy:
- Model responded but with malformed/invalid JSON → retry once → templated sentence from the same
  signals (degraded, never broken, never a stack trace).
- 429 → WriterRateLimited, propagated so Phase 5 can show "at capacity", never a 500.
- Backend unreachable (e.g. Ollama not running) → WriterUnavailable with an actionable message.
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Protocol, runtime_checkable

import requests
from pydantic import BaseModel, Field, ValidationError

from app.core.config import settings

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


class WriterRateLimited(Exception):
    """The backend's rate/daily limit was hit (HTTP 429). Surfaced for capacity handling."""


class WriterUnavailable(Exception):
    """The backend couldn't be reached or is misconfigured. Message is actionable."""


class ReasonOut(BaseModel):
    reason: str = Field(min_length=8, max_length=800)


class SummaryOut(BaseModel):
    summary: str = Field(min_length=15, max_length=1500)


@runtime_checkable
class Writer(Protocol):
    def write_taste_summary(self, evidence: dict) -> str: ...
    def write_reason(self, evidence: dict, film: dict, signals: list[dict]) -> str: ...


@lru_cache(maxsize=None)
def _load_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


# --- fact assembly (what the model is handed) --------------------------------


def _interpret(signal: dict | None, pos: str, neg: str, threshold: float = 0.25) -> str | None:
    if not signal or signal.get("value") is None:
        return None
    value = signal["value"]
    if value >= threshold:
        return pos
    if value <= -threshold:
        return neg
    return None


def _reason_facts(evidence: dict, film: dict, signals: list[dict]) -> dict:
    return {
        "film": {
            "title": film.get("title"),
            "year": film.get("year"),
            "overview": (film.get("overview") or "")[:300],
        },
        "why_it_scored": [s["detail"] for s in signals if s.get("detail")][:4],
        "your_taste": {
            "higher_rated_genres": [
                g["genre"] for g in evidence.get("genre_affinity", []) if (g.get("delta") or 0) > 0
            ][:3],
        },
    }


def _summary_facts(evidence: dict) -> dict:
    genre_aff = evidence.get("genre_affinity", [])
    liked = [g["genre"] for g in genre_aff if (g.get("delta") or 0) > 0][:3]
    cooler = [g["genre"] for g in genre_aff if (g.get("delta") or 0) < -0.2][:2]
    eras = [e["decade"] for e in evidence.get("era_affinity", []) if (e.get("delta") or 0) > 0][:2]
    directors = [d["name"] for d in evidence.get("crew_affinity", {}).get("director", [])][:3]
    counts = evidence.get("counts", {})

    facts = {
        "films_rated": counts.get("rated"),
        "average_rating_out_of_5": evidence.get("baseline_rating"),
        "genres_you_rate_up": liked,
        "genres_you_rate_down": cooler,
        "favorite_decades": eras,
        "directors_you_rate_up": directors,
        "rewatched_count": counts.get("rewatched"),
    }
    tendencies = [
        _interpret(evidence.get("contrarianism"), "you tend to agree with critical consensus",
                   "you often disagree with the critical consensus"),
        _interpret(evidence.get("obscurity_preference"), "you're comfortable with popular, widely-seen films",
                   "you're drawn to lesser-known, under-the-radar films"),
        _interpret(evidence.get("patience"), "you reward longer, slower films",
                   "you prefer tighter, shorter films"),
    ]
    facts["tendencies"] = [t for t in tendencies if t]
    return facts


# --- template fallbacks (no LLM; built from the same signals) ----------------


def _ensure_period(text: str) -> str:
    text = text.strip()
    return text if text.endswith((".", "!", "?")) else text + "."


def template_reason(film: dict, signals: list[dict]) -> str:
    # Lead with a specific signal (director/genre/era/…), keep the generic similarity line last, so
    # the fallback doesn't open every card with the same sentence.
    specific = [s["detail"] for s in signals if s.get("factor") != "similarity" and s.get("detail")]
    generic = [s["detail"] for s in signals if s.get("factor") == "similarity" and s.get("detail")]
    details = specific + generic
    if not details:
        return f"{film.get('title') or 'This film'} sits close to the films you rate most highly."
    return " ".join(_ensure_period(d) for d in details[:2])


def template_summary(evidence: dict) -> str:
    counts = evidence.get("counts", {})
    rated = counts.get("rated") or 0
    avg = evidence.get("baseline_rating")
    genre_aff = evidence.get("genre_affinity", [])
    liked = [g["genre"] for g in genre_aff if (g.get("delta") or 0) > 0][:2]
    eras = [e["decade"] for e in evidence.get("era_affinity", []) if (e.get("delta") or 0) > 0][:1]

    parts: list[str] = []
    if avg is not None:
        parts.append(f"Across {rated} rated films, you average about {avg:.1f} out of 5.")
    else:
        parts.append(f"You've logged {rated} rated films.")
    if liked:
        parts.append(f"You rate {' and '.join(liked)} above your own baseline.")
    if eras:
        parts.append(f"The {eras[0]} is a decade you keep returning to.")
    for phrase in _summary_facts(evidence).get("tendencies", [])[:1]:
        parts.append(_ensure_period(phrase[0].upper() + phrase[1:]))
    return " ".join(parts)


# --- base + backends ---------------------------------------------------------


class _LLMWriter:
    """Shared generate-validate-retry-fallback logic. Subclasses implement `_complete`."""

    temperature = 0.7

    def _complete(self, system: str, user: str, max_tokens: int) -> str:  # pragma: no cover - abstract
        raise NotImplementedError

    def _generate(self, system: str, user: str, model_cls, key: str, max_tokens: int) -> str | None:
        for _ in range(2):  # initial attempt + one retry
            try:
                raw = self._complete(system, user, max_tokens)
            except (WriterRateLimited, WriterUnavailable):
                raise
            except Exception:  # transient HTTP/5xx/timeout → retry, then fall back
                continue
            try:
                payload = json.loads(raw)
                return getattr(model_cls(**payload), key)
            except (json.JSONDecodeError, ValidationError, TypeError):
                continue
        return None  # both attempts produced unusable output → caller uses the template

    def write_taste_summary(self, evidence: dict) -> str:
        system = _load_prompt("taste_summary.md")
        user = json.dumps(_summary_facts(evidence), ensure_ascii=False)
        result = self._generate(system, user, SummaryOut, "summary", max_tokens=400)
        return result if result is not None else template_summary(evidence)

    def write_reason(self, evidence: dict, film: dict, signals: list[dict]) -> str:
        system = _load_prompt("reason.md")
        user = json.dumps(_reason_facts(evidence, film, signals), ensure_ascii=False)
        result = self._generate(system, user, ReasonOut, "reason", max_tokens=220)
        return result if result is not None else template_reason(film, signals)


class GroqWriter(_LLMWriter):
    def __init__(self, api_key: str | None = None, model: str | None = None, base_url: str = GROQ_URL) -> None:
        self.api_key = api_key if api_key is not None else settings.groq_api_key
        self.model = model or settings.groq_model
        self.base_url = base_url

    def _complete(self, system: str, user: str, max_tokens: int) -> str:
        if not self.api_key:
            raise WriterUnavailable("GROQ_API_KEY is not set; cannot use the Groq writer.")
        resp = requests.post(
            self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={
                "model": self.model,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "response_format": {"type": "json_object"},
                "temperature": self.temperature,
                "max_tokens": max_tokens,
            },
            timeout=45,
        )
        if resp.status_code == 429:
            raise WriterRateLimited("Groq rate/daily limit reached.")
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


class OllamaWriter(_LLMWriter):
    def __init__(self, host: str | None = None, model: str | None = None) -> None:
        self.host = (host or settings.ollama_host).rstrip("/")
        self.model = model or settings.ollama_model

    def _complete(self, system: str, user: str, max_tokens: int) -> str:
        try:
            resp = requests.post(
                f"{self.host}/api/chat",
                json={
                    "model": self.model,
                    "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                    "format": "json",
                    "stream": False,
                    "options": {"temperature": self.temperature, "num_predict": max_tokens},
                },
                timeout=120,
            )
        except requests.ConnectionError as exc:
            raise WriterUnavailable(
                f"Ollama isn't reachable at {self.host}. Start Ollama and run "
                f"`ollama pull {self.model}`."
            ) from exc
        if resp.status_code == 429:
            raise WriterRateLimited("Ollama is busy.")
        resp.raise_for_status()
        return resp.json()["message"]["content"]


def get_writer() -> Writer:
    """Select the backend by WRITER_BACKEND (ollama = local dev, groq = production)."""
    if settings.writer_backend == "groq":
        return GroqWriter()
    return OllamaWriter()
