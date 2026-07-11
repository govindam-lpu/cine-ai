"""Seed a deterministic, offline backend for the Playwright e2e.

Creates ./e2e.db with a ready "demo" profile (28 rated watched films → clears the gate → evidence +
a template summary) plus 12 unwatched candidate films, all embedded. Uses the test FakeTMDB catalog,
so it needs no network. The e2e backend runs with blank TMDB keys and no Ollama, so discovery falls
back to these cached candidates and reasons come out as real template prose.

Run from backend/ with PYTHONPATH=backend:  python scripts/seed_e2e.py
"""

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./e2e.db")
os.environ["TMDB_API_KEY"] = ""
os.environ["TMDB_BEARER_TOKEN"] = ""


def main() -> None:
    from app.db.init_db import init_db
    from app.db.session import Base, SessionLocal, engine
    from app.models.entities import Film, IngestJob, Profile
    from app.services.enrich import EnrichmentService, enrich_into
    from app.services.evidence import build_evidence, load_watches, store_evidence
    from app.services.ingest import parse_export
    from app.services.ranker import ensure_film_embeddings
    from app.services.writer import template_summary
    from tests.helpers import make_e2e_fixture

    # Fresh DB every seed.
    Base.metadata.drop_all(bind=engine)
    init_db()

    csv_bytes, fake = make_e2e_fixture()
    films = parse_export(csv_bytes, "ratings.csv")

    db = SessionLocal()
    try:
        db.merge(Profile(handle="demo", display_name="Demo Viewer"))
        job = IngestJob(profile_handle="demo", source="upload", status="queued")
        db.add(job)
        db.commit()
        db.refresh(job)

        svc = EnrichmentService(fake)
        enrich_into(db, job, "demo", films, "upload", svc)

        # Candidate pool (unwatched) for the recommender's cache fallback.
        for result in fake.discover:
            svc.get_or_create_by_tmdb_id(db, result["id"])

        watches = load_watches(db, "demo")
        evidence = build_evidence(watches)
        store_evidence(db, "demo", evidence, template_summary(evidence))

        ensure_film_embeddings(db, db.query(Film).all())
        job.status = "complete"
        job.step = "Done"
        db.commit()

        print(f"seeded: {db.query(Film).count()} films, profile 'demo' ready")
    finally:
        db.close()


if __name__ == "__main__":
    main()
