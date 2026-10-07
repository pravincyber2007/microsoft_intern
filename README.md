# Bulk Certificate Generator

A FastAPI-based backend for generating certificates in bulk for a list of recipients. It validates input, tracks job status, processes each certificate independently, and exposes generated PDFs for retrieval.

## Stack

- Python 3.11+
- FastAPI
- SQLAlchemy
- SQLite (default relational DB)
- ReportLab for PDF generation

## Project structure

- `app/main.py` – FastAPI application and API routes
- `app/models.py` – SQLAlchemy database models
- `app/schemas.py` – request/response validation models
- `app/services.py` – certificate generation logic
- `app/database.py` – DB engine and session setup
- `tests/test_api.py` – API and regression tests

## Setup

From the project root:

```bash
cd D:\micro
python -m pip install -r requirements.txt
```

The app creates the SQLite database automatically at startup in the project root as `certificates.db`.

## Run the application

```bash
cd D:\micro
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API docs are available at:

- http://127.0.0.1:8000/docs
- http://127.0.0.1:8000/redoc

## Run tests

```bash
cd D:\micro
python -m pytest -q
```

## Submit a certificate generation request

Example request body:

```json
{
  "course_name": "Python Fundamentals",
  "issued_by": "Acme Academy",
  "recipients": [
    {"name": "Alice Example", "email": "alice@example.com"},
    {"name": "Bob Example", "email": "bob@example.com"}
  ]
}
```

Call the API:

```bash
curl -X POST "http://127.0.0.1:8000/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "course_name": "Python Fundamentals",
    "issued_by": "Acme Academy",
    "recipients": [
      {"name": "Alice Example", "email": "alice@example.com"},
      {"name": "Bob Example", "email": "bob@example.com"}
    ]
  }'
```

Response:

```json
{
  "job_id": "<uuid>",
  "status": "queued",
  "total_recipients": 2,
  "message": "Certificate generation queued."
}
```

## Check job status and progress

```bash
curl http://127.0.0.1:8000/jobs/<job_id>
```

Example response:

```json
{
  "job_id": "<uuid>",
  "course_name": "Python Fundamentals",
  "issued_by": "Acme Academy",
  "status": "completed_with_failures",
  "total_recipients": 2,
  "succeeded_count": 1,
  "failed_count": 1,
  "created_at": "2026-10-07T12:00:00Z"
}
```

## Retrieve generated certificates

List certificate metadata for a job:

```bash
curl http://127.0.0.1:8000/jobs/<job_id>/certificates
```

Download an individual certificate PDF:

```bash
curl -L -o certificate.pdf http://127.0.0.1:8000/certificates/<certificate_id>/download
```

## Implementation decisions

- Bulk processing is modeled as a single generation job with many recipients, which keeps the client contract efficient and avoids one request per certificate.
- Validation happens up front with Pydantic so malformed recipient data is rejected before generation begins.
- Each certificate is generated independently. A failure in one recipient does not block the rest of the job; the job status and per-certificate records capture success or failure.
- A lightweight SQLite database stores job metadata and certificate records, making the system simple to run locally without additional infrastructure.
- ReportLab is used to generate a single predefined certificate layout that uses the request-specific values (name, course, issuer).
- The generation is scheduled asynchronously with FastAPI/asyncio so the API returns quickly while the certificates are created in the background.
