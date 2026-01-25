"""create queries tables

Revision ID: 0003_create_queries
Revises: 0002_create_documents
Create Date: 2024-10-10 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_create_queries"
down_revision = "0002_create_documents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "queries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_queries_id", "queries", ["id"], unique=False)
    op.create_index("ix_queries_user_id", "queries", ["user_id"], unique=False)

    op.create_table(
        "query_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("query_id", sa.Integer(), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["query_id"], ["queries.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_query_versions_id", "query_versions", ["id"], unique=False)
    op.create_index("ix_query_versions_query_id", "query_versions", ["query_id"], unique=False)

    op.create_table(
        "citations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("query_version_id", sa.Integer(), nullable=False),
        sa.Column("source_no", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("chunk_id", sa.Integer(), nullable=False),
        sa.Column("snippet", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["query_version_id"], ["query_versions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["chunk_id"], ["document_chunks.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_citations_id", "citations", ["id"], unique=False)
    op.create_index(
        "ix_citations_query_version_id",
        "citations",
        ["query_version_id"],
        unique=False,
    )
    op.create_index("ix_citations_document_id", "citations", ["document_id"], unique=False)
    op.create_index("ix_citations_chunk_id", "citations", ["chunk_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_citations_chunk_id", table_name="citations")
    op.drop_index("ix_citations_document_id", table_name="citations")
    op.drop_index("ix_citations_query_version_id", table_name="citations")
    op.drop_index("ix_citations_id", table_name="citations")
    op.drop_table("citations")
    op.drop_index("ix_query_versions_query_id", table_name="query_versions")
    op.drop_index("ix_query_versions_id", table_name="query_versions")
    op.drop_table("query_versions")
    op.drop_index("ix_queries_user_id", table_name="queries")
    op.drop_index("ix_queries_id", table_name="queries")
    op.drop_table("queries")
