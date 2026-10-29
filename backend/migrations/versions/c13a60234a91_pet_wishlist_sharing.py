"""Pet wishlist sharing.

Revision ID: c13a60234a91
Revises: fb14e6f8ec76
"""
from alembic import op
import sqlalchemy as sa


revision = "c13a60234a91"
down_revision = "fb14e6f8ec76"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "person_profile",
        sa.Column(
            "share_wishlist",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade():
    op.drop_column("person_profile", "share_wishlist")
