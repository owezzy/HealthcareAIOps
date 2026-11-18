"""llm_usage: one row per LLM call reported by the agent (ADR-0008).

Revision ID: 0001
Revises:
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "llm_usage",
        sa.Column("call_id", sa.String(200), primary_key=True),
        sa.Column("thread_id", sa.String(200), nullable=True),
        sa.Column("provider", sa.String(100), nullable=True),
        sa.Column("model", sa.String(200), nullable=False),
        sa.Column("metered", sa.Boolean, nullable=False),
        sa.Column("input_tokens", sa.Integer, nullable=True),
        sa.Column("output_tokens", sa.Integer, nullable=True),
        sa.Column("total_tokens", sa.Integer, nullable=True),
        sa.Column("cost_usd", sa.Numeric(14, 6), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(metered AND input_tokens IS NOT NULL AND output_tokens IS NOT NULL"
            " AND total_tokens IS NOT NULL)"
            " OR (NOT metered AND input_tokens IS NULL AND output_tokens IS NULL"
            " AND total_tokens IS NULL AND cost_usd IS NULL)",
            name="llm_usage_metered_consistent",
        ),
    )
    op.create_index("ix_llm_usage_recorded_at", "llm_usage", ["recorded_at"])
    op.create_index("ix_llm_usage_thread_id", "llm_usage", ["thread_id"])


def downgrade() -> None:
    op.drop_index("ix_llm_usage_thread_id", table_name="llm_usage")
    op.drop_index("ix_llm_usage_recorded_at", table_name="llm_usage")
    op.drop_table("llm_usage")
