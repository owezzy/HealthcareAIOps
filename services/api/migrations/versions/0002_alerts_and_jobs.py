"""alerts and jobs: Alertmanager alerts and the Postgres job queue (ADR-0003).

Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "alerts",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("alertname", sa.String(200), nullable=False),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("component", sa.String(200), nullable=True),
        sa.Column("severity", sa.String(20), nullable=True),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("labels", JSONB, nullable=False),
        sa.Column(
            "received_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("fingerprint", "starts_at", name="uq_alerts_occurrence"),
        sa.CheckConstraint("status IN ('firing', 'resolved')", name="alerts_status_valid"),
    )
    op.create_index("ix_alerts_component_starts_at", "alerts", ["component", "starts_at"])

    op.create_table(
        "jobs",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("kind", sa.String(50), nullable=False),
        sa.Column("dedupe_key", sa.String(300), nullable=False),
        sa.Column("payload", JSONB, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "available_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("kind", "dedupe_key", name="uq_jobs_kind_dedupe"),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'done', 'dead')", name="jobs_status_valid"
        ),
    )
    # The consumer's SKIP LOCKED query scans pending jobs in order.
    op.create_index(
        "ix_jobs_pending",
        "jobs",
        ["kind", "available_at"],
        postgresql_where=sa.text("status = 'pending'"),
    )


def downgrade() -> None:
    op.drop_index("ix_jobs_pending", table_name="jobs")
    op.drop_table("jobs")
    op.drop_index("ix_alerts_component_starts_at", table_name="alerts")
    op.drop_table("alerts")
