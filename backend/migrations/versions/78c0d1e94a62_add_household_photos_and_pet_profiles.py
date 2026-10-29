"""Add household photos and pet profiles

Revision ID: 78c0d1e94a62
Revises: a981c5d42e10
Create Date: 2026-10-20 13:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "78c0d1e94a62"
down_revision = "a981c5d42e10"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("household", sa.Column("photo_path", sa.String(length=500), nullable=True))
    op.add_column(
        "person_profile",
        sa.Column("profile_type", sa.String(length=20), server_default="person", nullable=False),
    )
    op.add_column(
        "person_profile",
        sa.Column("avatar_key", sa.String(length=30), server_default="flower", nullable=False),
    )
    op.create_table(
        "notification",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("household_id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("message", sa.String(length=255), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["user.id"],
            name=op.f("fk_notification_user_id_user"), ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["household_id"], ["household.id"],
            name=op.f("fk_notification_household_id_household"), ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["item_id"], ["wishlist_item.id"],
            name=op.f("fk_notification_item_id_wishlist_item"), ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notification")),
    )
    op.create_index(op.f("ix_notification_user_id"), "notification", ["user_id"], unique=False)
    op.create_index(op.f("ix_notification_household_id"), "notification", ["household_id"], unique=False)
    op.create_index(op.f("ix_notification_created_at"), "notification", ["created_at"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_notification_created_at"), table_name="notification")
    op.drop_index(op.f("ix_notification_household_id"), table_name="notification")
    op.drop_index(op.f("ix_notification_user_id"), table_name="notification")
    op.drop_table("notification")
    op.drop_column("person_profile", "avatar_key")
    op.drop_column("person_profile", "profile_type")
    op.drop_column("household", "photo_path")
