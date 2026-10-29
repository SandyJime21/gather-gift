"""Parent-controlled family-only gift visibility."""
from alembic import op
import sqlalchemy as sa
revision = 'f93bc476ca58'
down_revision = 'e82ab365bf47'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('wishlist_item', sa.Column('family_only', sa.Boolean(), nullable=False, server_default=sa.false()))

def downgrade():
    op.drop_column('wishlist_item', 'family_only')
