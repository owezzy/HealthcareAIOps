"""incidents and incident_alerts: correlated alert groups (ADR-0005).

Minimal for the correlator; the incidents context (plan §7.5 state machine,
problems, changes, timeline) extends it in a later revision.

Revision ID: 0003
Revises: 0002
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "incidents",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("root_component", sa.String(200), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_alert_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("merged_into", sa.BigInteger, sa.ForeignKey("incidents.id"), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("status IN ('open', 'merged')", name="incidents_status_valid"),
        sa.CheckConstraint(
            "(status = 'merged') = (merged_into IS NOT NULL)", name="incidents_merged_has_target"
        ),
    )
    op.create_index(
        "ix_incidents_open",
        "incidents",
        ["last_alert_at"],
        postgresql_where=sa.text("status = 'open'"),
    )
    op.create_table(
        "incident_alerts",
        sa.Column("alert_id", sa.BigInteger, sa.ForeignKey("alerts.id"), primary_key=True),
        sa.Column("incident_id", sa.BigInteger, sa.ForeignKey("incidents.id"), nullable=False),
    )
    op.create_index("ix_incident_alerts_incident", "incident_alerts", ["incident_id"])
    op.add_column("jobs", sa.Column("last_error", sa.Text, nullable=True))


def downgrade() -> None:
    op.drop_column("jobs", "last_error")
    op.drop_index("ix_incident_alerts_incident", table_name="incident_alerts")
    op.drop_table("incident_alerts")
    op.drop_index("ix_incidents_open", table_name="incidents")
    op.drop_table("incidents")
