"""Store family relationships within each household."""
from alembic import op
import sqlalchemy as sa
revision = "e2c51480a7d6"
down_revision = "c921b46a830f"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("household_profile_access", sa.Column("relationship", sa.String(30), nullable=False, server_default="family_member"))


def downgrade():
    op.drop_column("household_profile_access", "relationship")
