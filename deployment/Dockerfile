# Poetry Vision (final) container. NOT built or tested yet (building pulls a base image, which needs the owner's approval).
# CLIP weights are not baked in: mount a Hugging Face cache and set PV_HF_CACHE (see deployment/DEPLOYMENT.md).
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY contracts/ contracts/
COPY retrieval/ retrieval/
COPY vision_model/ vision_model/
COPY backend/ backend/
COPY artifacts/heads/ artifacts/heads/
COPY artifacts/model_card_v1.json artifacts/model_card_v1.json
COPY poetry_corpus/__init__.py poetry_corpus/__init__.py
COPY poetry_corpus/exports/corpus_all_v2.jsonl poetry_corpus/exports/corpus_all_v2.jsonl
COPY frontend/dist/ frontend/dist/
ENV PV_DEVICE=cpu PV_HF_CACHE=/hf HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
EXPOSE 8010
CMD ["python", "-B", "-m", "uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8010"]
