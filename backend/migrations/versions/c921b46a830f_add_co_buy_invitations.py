"""Add private co-buy invitations."""
from alembic import op
import sqlalchemy as sa
revision = "c921b46a830f"
down_revision = "0b7f21a4d9ce"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("co_buy_invitation",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("reservation_id", sa.Integer(), sa.ForeignKey("gift_reservation.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("accepted", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("reservation_id", "email"))
    op.create_index("ix_co_buy_invitation_reservation_id", "co_buy_invitation", ["reservation_id"])


def downgrade():
    op.drop_table("co_buy_invitation")
