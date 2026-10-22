FROM python:3.12.11-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv
COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock && useradd --create-home liga
COPY . .
USER liga
EXPOSE 8000
CMD ["sh", "-c", "python -m app.wait_db && alembic upgrade head && python -m app.seed && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-access-log"]
