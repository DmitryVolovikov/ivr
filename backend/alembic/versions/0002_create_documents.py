"""create documents tables

Revision ID: 0002_create_documents
Revises: 0001_create_users
Create Date: 2024-10-10 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_create_documents"
down_revision = "0001_create_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("original_name", sa.String(length=512), nullable=False),
        sa.Column("stored_filename", sa.String(length=1024), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_reason", sa.String(length=1024), nullable=True),
        sa.Column("reject_reason", sa.String(length=1024), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_documents_id", "documents", ["id"], unique=False)

    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_document_chunks_id", "document_chunks", ["id"], unique=False)
    op.create_index(
        "ix_document_chunks_document_id",
        "document_chunks",
        ["document_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_document_chunks_document_id", table_name="document_chunks")
    op.drop_index("ix_document_chunks_id", table_name="document_chunks")
    op.drop_table("document_chunks")
    op.drop_index("ix_documents_id", table_name="documents")
    op.drop_table("documents")
