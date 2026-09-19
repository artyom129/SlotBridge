FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN groupadd --system slotbridge \
    && useradd --system --gid slotbridge --home-dir /app slotbridge \
    && mkdir -p /app/data \
    && chown -R slotbridge:slotbridge /app

USER slotbridge
EXPOSE 8000
CMD ["sh", "scripts/entrypoint.sh"]
