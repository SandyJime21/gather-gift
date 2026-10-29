"""Support-created family setup invitations."""
from alembic import op
import sqlalchemy as sa


revision = "7fe12c6a9d34"
down_revision = "c13a60234a91"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "household_invitation",
        sa.Column(
            "transfer_owner_on_accept",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "household_invitation",
        sa.Column("setup_created_by_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_household_invitation_setup_created_by_id",
        "household_invitation",
        ["setup_created_by_id"],
    )
    op.create_foreign_key(
        "fk_household_invitation_setup_created_by_id_user",
        "household_invitation",
        "user",
        ["setup_created_by_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade():
    op.drop_constraint(
        "fk_household_invitation_setup_created_by_id_user",
        "household_invitation",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_household_invitation_setup_created_by_id",
        table_name="household_invitation",
    )
    op.drop_column("household_invitation", "setup_created_by_id")
    op.drop_column("household_invitation", "transfer_owner_on_accept")
