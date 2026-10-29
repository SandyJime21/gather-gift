"""Add master support account and staff invitations

Revision ID: a981c5d42e10
Revises: b2a1fa57d7f7
Create Date: 2026-10-19 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "a981c5d42e10"
down_revision = "b2a1fa57d7f7"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "user",
        sa.Column("is_superuser", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.create_table(
        "support_invitation",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("invited_by_id", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["invited_by_id"],
            ["user.id"],
            name=op.f("fk_support_invitation_invited_by_id_user"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_support_invitation")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_support_invitation_token_hash")),
    )
    op.create_index(
        op.f("ix_support_invitation_email"),
        "support_invitation",
        ["email"],
        unique=False,
    )
    op.create_index(
        op.f("ix_support_invitation_expires_at"),
        "support_invitation",
        ["expires_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_support_invitation_invited_by_id"),
        "support_invitation",
        ["invited_by_id"],
        unique=False,
    )


def downgrade():
    op.drop_index(op.f("ix_support_invitation_invited_by_id"), table_name="support_invitation")
    op.drop_index(op.f("ix_support_invitation_expires_at"), table_name="support_invitation")
    op.drop_index(op.f("ix_support_invitation_email"), table_name="support_invitation")
    op.drop_table("support_invitation")
    op.drop_column("user", "is_superuser")
