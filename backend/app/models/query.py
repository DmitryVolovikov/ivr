from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class Query(Base):
    __tablename__ = "queries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    versions = relationship(
        "QueryVersion",
        back_populates="query",
        cascade="all, delete-orphan",
        order_by="QueryVersion.version_no",
    )


class QueryVersion(Base):
    __tablename__ = "query_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    query_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("queries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    query = relationship("Query", back_populates="versions")
    citations = relationship(
        "Citation",
        back_populates="query_version",
        cascade="all, delete-orphan",
        order_by="Citation.source_no",
    )


class Citation(Base):
    __tablename__ = "citations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    query_version_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("query_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_no: Mapped[int] = mapped_column(Integer, nullable=False)
    document_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("document_chunks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    snippet: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    query_version = relationship("QueryVersion", back_populates="citations")
