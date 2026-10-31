# Works on Hugging Face Spaces (Docker SDK) and on Render.
FROM python:3.11-slim

RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    DEMANDRANGE_CACHE=/tmp/demandrange_cache
WORKDIR /home/user/app

COPY --chown=user requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

COPY --chown=user . .

# The API needs a trained model. Priority:
# 1) a model you trained on real data and committed (models/demandrange.joblib)
# 2) a CSV at data/real_training.csv   3) the simulated demo data
RUN if [ -f models/demandrange.joblib ]; then echo "Using the committed model"; \
    elif [ -f data/real_training.csv ]; then python run_pipeline.py --data data/real_training.csv; \
    else python run_pipeline.py; fi

EXPOSE 7860
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
