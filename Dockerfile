FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

RUN addgroup --system cepio && adduser --system --ingroup cepio cepio

COPY . /app
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir .

RUN mkdir -p /data && chown -R cepio:cepio /app /data
USER cepio

EXPOSE 8000

CMD ["sh", "-c", "uvicorn cepio.public_api:app --host 0.0.0.0 --port ${PORT:-8000}"]
