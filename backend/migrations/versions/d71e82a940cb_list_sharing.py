"""List-level sharing for managed family wishlists."""
from alembic import op
import sqlalchemy as sa
revision = "d71e82a940cb"
down_revision = "7fe12c6a9d34"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("wishlist", sa.Column("share_publicly", sa.Boolean(), nullable=True))

def downgrade():
    op.drop_column("wishlist", "share_publicly")
