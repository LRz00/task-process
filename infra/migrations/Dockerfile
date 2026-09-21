FROM python:3.12-slim

WORKDIR /workspace

COPY infra/migrations/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY infra/migrations /workspace/infra/migrations

CMD ["alembic", "-c", "/workspace/infra/migrations/alembic.ini", "upgrade", "head"]
