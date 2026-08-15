"""lead_activities: state-transition audit trail

Revision ID: 0002_lead_activities
Revises: 0001_initial
Create Date: 2026-08-15 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "0002_lead_activities"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lead_activities",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("lead_id", sa.Text(), sa.ForeignKey("leads.id"), nullable=False),
        sa.Column(
            "attorney_id",
            sa.Text(),
            sa.ForeignKey("attorneys.id"),
            nullable=False,
        ),
        sa.Column("from_state", sa.Text(), nullable=False),
        sa.Column("to_state", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "from_state IN ('PENDING', 'REACHED_OUT')",
            name="ck_activity_from_state",
        ),
        sa.CheckConstraint(
            "to_state IN ('PENDING', 'REACHED_OUT')",
            name="ck_activity_to_state",
        ),
    )
    op.create_index("idx_activity_lead_id", "lead_activities", ["lead_id"])


def downgrade() -> None:
    op.drop_index("idx_activity_lead_id", table_name="lead_activities")
    op.drop_table("lead_activities")
