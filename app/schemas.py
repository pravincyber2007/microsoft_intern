from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RecipientCreate(BaseModel):
    name: str = Field(..., min_length=1)
    email: EmailStr


class JobCreateRequest(BaseModel):
    course_name: str = Field(..., min_length=1)
    issued_by: str = Field(..., min_length=1)
    recipients: list[RecipientCreate] = Field(..., min_length=1)


class JobCreateResponse(BaseModel):
    job_id: str
    status: str
    total_recipients: int
    message: str


class JobStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: str
    course_name: str
    issued_by: str
    status: str
    total_recipients: int
    succeeded_count: int
    failed_count: int
    created_at: datetime


class CertificateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    job_id: str
    recipient_name: str
    recipient_email: str
    status: str
    file_path: str | None = None
    error_message: str | None = None
    download_url: str | None = None
    created_at: datetime
