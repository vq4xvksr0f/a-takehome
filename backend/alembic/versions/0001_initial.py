"""initial schema: leads, attorneys, email_outbox

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-14 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "leads",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("first_name", sa.Text(), nullable=False),
        sa.Column("last_name", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column(
            "state",
            sa.Text(),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("resume_object_key", sa.Text(), nullable=False),
        sa.Column("resume_filename", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "state IN ('PENDING', 'REACHED_OUT')", name="ck_leads_state"
        ),
    )
    op.create_index(
        "idx_leads_created_at", "leads", [sa.text("created_at DESC")]
    )
    op.create_index("idx_leads_state", "leads", ["state"])

    op.create_table(
        "attorneys",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("email", sa.Text(), nullable=False, unique=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
    )

    op.create_table(
        "email_outbox",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "lead_id", sa.Text(), sa.ForeignKey("leads.id"), nullable=False
        ),
        sa.Column("recipient", sa.Text(), nullable=False),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("html", sa.Text(), nullable=False),
        sa.Column(
            "status", sa.Text(), nullable=False, server_default="pending"
        ),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'sent', 'failed')", name="ck_outbox_status"
        ),
    )


def downgrade() -> None:
    op.drop_table("email_outbox")
    op.drop_table("attorneys")
    op.drop_index("idx_leads_state", table_name="leads")
    op.drop_index("idx_leads_created_at", table_name="leads")
    op.drop_table("leads")
