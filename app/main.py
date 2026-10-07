import asyncio
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import create_db_and_tables, get_db
from app.models import Certificate, Job
from app.schemas import CertificateResponse, JobCreateRequest, JobCreateResponse, JobStatusResponse
from app.services import generate_certificate_pdf

app = FastAPI(title="Bulk Certificate Generator")
create_db_and_tables()


@app.on_event("startup")
def startup() -> None:
    create_db_and_tables()


async def process_job(job_id: str) -> None:
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if job is None:
            return

        job.status = "processing"
        db.commit()

        for certificate in job.certificates:
            if certificate.status == "generated":
                continue

            try:
                certificate.file_path = generate_certificate_pdf(
                    certificate.recipient_name,
                    job.course_name,
                    job.issued_by,
                )
                certificate.status = "generated"
                job.succeeded_count += 1
            except Exception as exc:  # pragma: no cover - defensive fallback
                certificate.status = "failed"
                certificate.error_message = str(exc)
                job.failed_count += 1

        if job.failed_count == 0:
            job.status = "completed"
        elif job.succeeded_count == 0:
            job.status = "failed"
        else:
            job.status = "completed_with_failures"

        db.commit()
    finally:
        db.close()


@app.post("/jobs", response_model=JobCreateResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_job(request: JobCreateRequest, db: Session = Depends(get_db)) -> JobCreateResponse:
    job = Job(
        course_name=request.course_name,
        issued_by=request.issued_by,
        total_recipients=len(request.recipients),
        status="queued",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    for recipient in request.recipients:
        certificate = Certificate(
            job_id=job.id,
            recipient_name=recipient.name,
            recipient_email=recipient.email,
            status="queued",
        )
        db.add(certificate)
    db.commit()

    asyncio.create_task(process_job(job.id))

    return JobCreateResponse(
        job_id=job.id,
        status=job.status,
        total_recipients=job.total_recipients,
        message="Certificate generation queued.",
    )


@app.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str, db: Session = Depends(get_db)) -> JobStatusResponse:
    job = db.query(Job).filter(Job.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobStatusResponse(
        job_id=job.id,
        course_name=job.course_name,
        issued_by=job.issued_by,
        status=job.status,
        total_recipients=job.total_recipients,
        succeeded_count=job.succeeded_count,
        failed_count=job.failed_count,
        created_at=job.created_at,
    )


@app.get("/jobs/{job_id}/certificates", response_model=list[CertificateResponse])
def list_job_certificates(job_id: str, db: Session = Depends(get_db)) -> list[CertificateResponse]:
    certificates = db.query(Certificate).filter(Certificate.job_id == job_id).all()

    response = []
    for certificate in certificates:
        response.append(
            CertificateResponse(
                id=certificate.id,
                job_id=certificate.job_id,
                recipient_name=certificate.recipient_name,
                recipient_email=certificate.recipient_email,
                status=certificate.status,
                file_path=certificate.file_path,
                error_message=certificate.error_message,
                download_url=f"/certificates/{certificate.id}/download" if certificate.file_path else None,
                created_at=certificate.created_at,
            )
        )

    return response


@app.get("/certificates/{certificate_id}/download")
def download_certificate(certificate_id: str, db: Session = Depends(get_db)) -> FileResponse:
    certificate = db.query(Certificate).filter(Certificate.id == certificate_id).first()
    if certificate is None:
        raise HTTPException(status_code=404, detail="Certificate not found")
    if certificate.file_path is None:
        raise HTTPException(status_code=404, detail="Certificate has not been generated")

    path = Path(certificate.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Certificate file not found")

    return FileResponse(path=path, media_type="application/pdf", filename=path.name)
