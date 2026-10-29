"""Add personal seasonal themes and private background uploads."""
from alembic import op
import sqlalchemy as sa
revision = 'c60ef1439d25'
down_revision = 'b59de0328c14'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('user', sa.Column('theme_key', sa.String(20), nullable=False, server_default='classic'))
    op.add_column('user', sa.Column('theme_image_path', sa.String(500)))


def downgrade():
    op.drop_column('user', 'theme_image_path')
    op.drop_column('user', 'theme_key')
