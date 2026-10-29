"""Explicit personal wish audiences."""
from alembic import op
import sqlalchemy as sa
revision = 'd9366e7064f8'
down_revision = 'c8255d6f53e7'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('personal_wish', sa.Column('visibility', sa.String(20), nullable=False, server_default='custom'))

def downgrade():
    op.drop_column('personal_wish','visibility')
