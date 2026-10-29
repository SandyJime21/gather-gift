"""Add private company registries alongside family households."""
from alembic import op
import sqlalchemy as sa
revision = 'd71fa254ae36'
down_revision = 'c60ef1439d25'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('household', sa.Column('registry_type', sa.String(20), nullable=False, server_default='family'))


def downgrade():
    op.drop_column('household', 'registry_type')
