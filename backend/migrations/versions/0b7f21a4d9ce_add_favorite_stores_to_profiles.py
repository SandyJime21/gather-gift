"""Add favorite stores to profiles

Revision ID: 0b7f21a4d9ce
Revises: 78c0d1e94a62
Create Date: 2026-10-20 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "0b7f21a4d9ce"
down_revision = "78c0d1e94a62"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("person_profile", sa.Column("favorite_stores", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("person_profile", "favorite_stores")
