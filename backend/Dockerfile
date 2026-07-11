# Cinerex backend — Hugging Face Space (Docker, CPU). fastembed (ONNX) + FastAPI, no PyTorch.
# HF Spaces serve on port 7860 and run as uid 1000, so we build under a non-root user.
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1

WORKDIR /home/user/app

# sqlalchemy-libsql installs here (Linux) via the platform marker in requirements.txt.
COPY --chown=user requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

COPY --chown=user . .

# Bake the embedding model into the image so the first request doesn't wait on a download.
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('sentence-transformers/all-MiniLM-L6-v2')"

EXPOSE 7860
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
