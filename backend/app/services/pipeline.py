"""End-to-end orchestration: upload → enrich → analyze, and profile → rank → reasons.

Ties Phases 1–4 together. `make_tmdb` / `make_writer` are the seams tests monkeypatch to inject
fakes; the endpoints use the real ones. The ingest job runs inside the single-worker queue.
"""

import logging

from sqlalchemy.orm import Session

from app.core.budget import GenerationBudget
from app.core.budget import budget as default_budget
from app.db.session import SessionLocal
from app.models.entities import IngestJob, TasteProfile
from app.services.enrich import EnrichmentService, enrich_into
from app.services.evidence import build_evidence, check_gate, load_watches, store_evidence
from app.services.ingest import ParsedFilm
from app.services.ranker import recommend
from app.services.tmdb import TMDBService
from app.services.writer import (
    Writer,
    WriterRateLimited,
    WriterUnavailable,
    get_writer,
    template_reason,
    template_summary,
)

logger = logging.getLogger(__name__)


def make_tmdb() -> TMDBService:
    return TMDBService()


def make_writer() -> Writer:
    return get_writer()


def run_full_ingest(job_id: str, handle: str, films: list[ParsedFilm], source: str = "upload") -> None:
    """The full ingest: enrich films, then analyze (evidence + written summary), then complete.

    Owns its own session (runs in the queue's worker thread). Never raises to the caller — a failure
    marks the job failed; a below-gate profile completes with a friendly BELOW_GATE marker; a writer
    outage degrades the summary to a template rather than failing the whole ingest.
    """
    svc = EnrichmentService(make_tmdb())
    db = SessionLocal()
    try:
        job = db.get(IngestJob, job_id)
        if job is None:
            return

        enrich_into(db, job, handle, films, source, svc)

        job.status = "analyzing"
        job.step = "Reading your taste"
        db.commit()

        watches = load_watches(db, handle)
        gate = check_gate(watches)
        if not gate.ok:
            job.status = "complete"
            job.step = "Needs more films"
            job.error_code = "BELOW_GATE"
            job.error_message = gate.message
            db.commit()
            return

        evidence = build_evidence(watches)
        try:
            summary = make_writer().write_taste_summary(evidence)
        except (WriterRateLimited, WriterUnavailable) as exc:
            logger.info("taste summary degraded to template: %s", exc)
            summary = template_summary(evidence)

        store_evidence(db, handle, evidence, summary)
        job.status = "complete"
        job.step = "Done"
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        job = db.get(IngestJob, job_id)
        if job:
            job.status = "failed"
            job.error_code = "INGEST_FAILED"
            job.error_message = str(exc)
            db.commit()
    finally:
        db.close()


def generate_recommendations(
    db: Session,
    handle: str,
    mood: str | None = None,
    limit: int = 8,
    budget: GenerationBudget | None = None,
    prompt: str | None = None,
):
    """Yield (recommendation, reason, at_capacity) tuples — ranked fresh, reasons written per film.

    Reasons stream one film at a time. When the Groq daily budget is spent (or the writer rate-limits
    mid-stream), fall back to the templated reason and flag at_capacity so the caller can tell the
    user prose generation is paused — never a 500, never an empty list.
    """
    budget = budget or default_budget
    tp = db.query(TasteProfile).filter_by(profile_handle=handle).first()
    if tp is None or tp.evidence_json is None:
        return
    evidence = tp.evidence_json

    writer = make_writer()
    recs = recommend(db, handle, evidence, tmdb=make_tmdb(), mood=mood, prompt=prompt, limit=limit)

    for rec in recs:
        film = {"title": rec.title, "year": rec.vector.release_year, "overview": rec.vector.overview}
        at_capacity = False
        if budget.exhausted():
            reason = template_reason(film, rec.signals)
            at_capacity = True
        else:
            try:
                reason = writer.write_reason(evidence, film, rec.signals)
                budget.consume()
            except WriterRateLimited:
                reason = template_reason(film, rec.signals)
                at_capacity = True
            except WriterUnavailable:
                reason = template_reason(film, rec.signals)
        yield rec, reason, at_capacity
