"""Occasions on personal private wishes."""
from alembic import op
import sqlalchemy as sa
revision = 'b7144c5e42d6'
down_revision = 'a6033b4d31c5'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('personal_wish', sa.Column('occasion', sa.String(80), nullable=False, server_default=''))

def downgrade():
    op.drop_column('personal_wish','occasion')
