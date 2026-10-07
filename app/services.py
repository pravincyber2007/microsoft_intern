import re
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

CERTIFICATE_DIR = Path(__file__).resolve().parent / "generated_certificates"
CERTIFICATE_DIR.mkdir(exist_ok=True, parents=True)


def sanitize_name(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return safe or "certificate"


def generate_certificate_pdf(recipient_name: str, course_name: str, issued_by: str) -> str:
    safe_name = sanitize_name(recipient_name)
    filename = f"{safe_name}.pdf"
    output_path = CERTIFICATE_DIR / filename

    drawing = canvas.Canvas(str(output_path), pagesize=letter)
    width, height = letter

    drawing.setTitle(f"Certificate for {recipient_name}")
    drawing.setFont("Helvetica-Bold", 28)
    drawing.drawCentredString(width / 2, height - 80, "Certificate of Completion")

    drawing.setFont("Helvetica", 18)
    drawing.drawCentredString(width / 2, height - 150, "This is to certify that")

    drawing.setFont("Helvetica-Bold", 24)
    drawing.drawCentredString(width / 2, height - 220, recipient_name)

    drawing.setFont("Helvetica", 18)
    drawing.drawCentredString(width / 2, height - 285, f"has successfully completed the course: {course_name}")
    drawing.drawCentredString(width / 2, height - 330, f"issued by {issued_by}")

    drawing.line(120, 380, width - 120, 380)
    drawing.setFont("Helvetica-Oblique", 12)
    drawing.drawCentredString(width / 2, 340, "Awarded for active participation and completion")

    drawing.save()
    return str(output_path)
