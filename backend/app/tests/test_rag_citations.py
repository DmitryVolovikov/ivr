from app.api.routes import rag as rag_routes
from app.models.document import Document, DocumentChunk
from app.models.query import Citation, Query, QueryVersion
from app.models.user import User
from app.schemas.rag import RagSource


def test_store_citations_skips_missing_chunks(db_session):
    user = User(
        email="user@example.com",
        display_name="User",
        password_hash="hashed",
    )
    document = Document(
        original_name="doc.txt",
        stored_filename="doc.txt",
        mime_type="text/plain",
        title="Doc",
        status="published",
    )
    chunk = DocumentChunk(document=document, chunk_index=0, text="Example text")
    db_session.add_all([user, document, chunk])
    db_session.commit()

    query = Query(user_id=user.id, question="What is this?")
    db_session.add(query)
    db_session.commit()

    version = QueryVersion(query_id=query.id, version_no=1, answer="Answer")
    db_session.add(version)
    db_session.commit()

    sources = [
        RagSource(
            source_no=1,
            doc_id=document.id,
            title=document.title,
            chunk_id=chunk.id,
            snippet="Example text",
        ),
        RagSource(
            source_no=2,
            doc_id=document.id,
            title=document.title,
            chunk_id=chunk.id + 999,
            snippet="Missing chunk",
        ),
    ]

    skipped_count = rag_routes._store_citations(db_session, version, sources)
    db_session.commit()

    citations = db_session.query(Citation).order_by(Citation.source_no).all()
    assert skipped_count == 1
    assert len(citations) == 1
    assert citations[0].chunk_id == chunk.id
