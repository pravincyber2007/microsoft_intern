import time
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.services import generate_certificate_pdf as real_generate_certificate_pdf

client = TestClient(app)


def test_create_generation_job():
    payload = {
        "course_name": "Python Fundamentals",
        "issued_by": "Acme Academy",
        "recipients": [
            {"name": "Alice Example", "email": "alice@example.com"},
            {"name": "Bob Example", "email": "bob@example.com"},
        ],
    }

    response = client.post("/jobs", json=payload)

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "queued"
    assert "job_id" in body
    assert body["total_recipients"] == 2


def test_input_validation_rejects_invalid_recipient():
    payload = {
        "course_name": "Python Fundamentals",
        "issued_by": "Acme Academy",
        "recipients": [
            {"name": "", "email": "invalid-email"},
        ],
    }

    response = client.post("/jobs", json=payload)

    assert response.status_code == 422


def test_retrieve_job_status_and_certificates():
    payload = {
        "course_name": "Data Analysis",
        "issued_by": "Acme Academy",
        "recipients": [
            {"name": "Carol Example", "email": "carol@example.com"},
        ],
    }

    create_response = client.post("/jobs", json=payload)
    job_id = create_response.json()["job_id"]

    status_response = client.get(f"/jobs/{job_id}")
    assert status_response.status_code == 200
    status_body = status_response.json()
    assert status_body["job_id"] == job_id
    assert status_body["total_recipients"] == 1

    certificate_response = client.get(f"/jobs/{job_id}/certificates")
    assert certificate_response.status_code == 200
    assert isinstance(certificate_response.json(), list)


def test_individual_certificate_failure_does_not_block_other_valid_certificates():
    payload = {
        "course_name": "Advanced Analytics",
        "issued_by": "Acme Academy",
        "recipients": [
            {"name": "Dana Example", "email": "dana@example.com"},
            {"name": "Evan Example", "email": "evan@example.com"},
        ],
    }

    def fake_generate_certificate_pdf(recipient_name, course_name, issued_by):
        if recipient_name == "Evan Example":
            raise RuntimeError("Simulated generation issue")
        return real_generate_certificate_pdf(recipient_name, course_name, issued_by)

    with patch("app.main.generate_certificate_pdf", side_effect=fake_generate_certificate_pdf):
        create_response = client.post("/jobs", json=payload)
        assert create_response.status_code == 202
        job_id = create_response.json()["job_id"]

        deadline = time.time() + 5
        while time.time() < deadline:
            status_response = client.get(f"/jobs/{job_id}")
            if status_response.json()["status"] in {"completed", "completed_with_failures", "failed"}:
                break
            time.sleep(0.1)

        status_response = client.get(f"/jobs/{job_id}")
        status_body = status_response.json()
        assert status_body["succeeded_count"] == 1
        assert status_body["failed_count"] == 1

        certificates_response = client.get(f"/jobs/{job_id}/certificates")
        certificates = certificates_response.json()
        assert len(certificates) == 2
        assert any(item["status"] == "generated" for item in certificates)
        assert any(item["status"] == "failed" for item in certificates)
