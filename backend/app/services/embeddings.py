"""Local, CPU-only embeddings via fastembed (ONNX, no PyTorch).

Model: sentence-transformers/all-MiniLM-L6-v2 (384-dim). fastembed returns L2-normalized vectors,
so cosine similarity is just a dot product. Verified sane at build time (semantically-close texts
score higher than distant ones), so the sentence-transformers fallback the plan hedged on is not
needed. The model loads lazily and once — first use eats the load (part of the cold-start budget).
"""

import threading

import numpy as np

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBED_DIM = 384

_model = None
_lock = threading.Lock()


def get_model():
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                from fastembed import TextEmbedding

                _model = TextEmbedding(MODEL_NAME)
    return _model


def embed_texts(texts: list[str]) -> list[np.ndarray]:
    """Embed a batch of texts into unit-norm 384-dim float32 vectors."""
    if not texts:
        return []
    model = get_model()
    return [np.asarray(vec, dtype=np.float32) for vec in model.embed(list(texts))]


def film_embedding_text(overview: str | None, genres, keywords) -> str | None:
    """The text a film is embedded from: overview + genres + keywords (per PLAN.md §1c).

    Returns None for a cold film with nothing to embed, so the caller can skip it rather than
    embed an empty string.
    """
    parts: list[str] = []
    if overview and overview.strip():
        parts.append(overview.strip())
    if genres:
        parts.append("Genres: " + ", ".join(genres))
    if keywords:
        parts.append("Themes: " + ", ".join(list(keywords)[:20]))
    text = ". ".join(parts)
    return text or None
