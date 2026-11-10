FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && useradd --create-home --uid 10001 app

COPY main.py ./
COPY api/ ./api/
COPY schemas/ ./schemas/
COPY services/ ./services/
COPY repositories/ ./repositories/

USER app
EXPOSE 8080
CMD ["sh", "-c", "exec python -m uvicorn main:app --host 0.0.0.0 --port \"${PORT:-8080}\""]
