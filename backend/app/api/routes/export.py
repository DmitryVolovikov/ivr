from io import BytesIO
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Response, status
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont, TTFError
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.document import Document
from app.models.query import Citation, Query, QueryVersion
from app.models.user import User

router = APIRouter(tags=["export"])

logger = logging.getLogger(__name__)

FONT_NAME = "DejaVuSans"
FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
)


def _register_font():
    for candidate in FONT_CANDIDATES:
        path = Path(candidate)
        if path.exists():
            try:
                pdfmetrics.registerFont(TTFont(FONT_NAME, str(path)))
                return FONT_NAME
            except (OSError, TTFError, ValueError) as exc:
                logger.warning("Failed to register DejaVu font from %s", candidate, exc_info=exc)
    logger.warning("DejaVu font not found, falling back to Helvetica.")
    return "Helvetica"


DEFAULT_FONT = _register_font()


def _draw_lines(
    pdf,
    text,
    x,
    y,
    max_width,
    font_name,
    leading=14,
):
    lines = simpleSplit(text, font_name, 11, max_width)
    for line in lines:
        if y < 72:
            pdf.showPage()
            pdf.setFont(font_name, 11)
            y = 720
        pdf.drawString(x, y, line)
        y -= leading
    return y


def _build_pdf(question, answer, sources):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    pdf.setFont(DEFAULT_FONT, 11)
    y = 720
    y = _draw_lines(pdf, f"Вопрос: {question}", 72, y, 468, DEFAULT_FONT)
    y -= 12
    y = _draw_lines(pdf, "Ответ:", 72, y, 468, DEFAULT_FONT)
    y = _draw_lines(pdf, answer, 72, y, 468, DEFAULT_FONT)
    y -= 12
    y = _draw_lines(pdf, "Источники:", 72, y, 468, DEFAULT_FONT)
    for source_no, title, snippet in sources:
        y = _draw_lines(pdf, f"[S{source_no}] {title}", 72, y, 468, DEFAULT_FONT)
        y = _draw_lines(pdf, snippet, 90, y, 450, DEFAULT_FONT)
        y -= 6
    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer.getvalue()


def _load_sources(db, version_id):
    citations = (
        db.query(Citation)
        .filter(Citation.query_version_id == version_id)
        .order_by(Citation.source_no.asc())
        .all()
    )
    if not citations:
        return []
    doc_titles = {
        doc.id: doc.title or f"Документ {doc.id}"
        for doc in db.query(Document)
        .filter(Document.id.in_({c.document_id for c in citations}))
        .all()
    }
    return [
        (citation.source_no, doc_titles.get(citation.document_id, "Документ"), citation.snippet)
        for citation in citations
    ]


@router.get("/export/{version_id}")
@router.get("/export/{version_id}.pdf")
def export_version(
    version_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user()),
) -> Response:
    version = db.query(QueryVersion).filter(QueryVersion.id == version_id).first()
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")
    query = db.query(Query).filter(Query.id == version.query_id).first()
    if query is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Query not found")
    if query.user_id != user.id and not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    sources = _load_sources(db, version.id)
    pdf_bytes = _build_pdf(query.question, version.answer, sources)
    return Response(
        pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=export-{version.id}.pdf"},
    )
