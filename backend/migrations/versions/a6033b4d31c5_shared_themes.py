"""Shared seasonal artwork and palettes."""
from alembic import op
import sqlalchemy as sa
revision = 'a6033b4d31c5'
down_revision = 'f5922a3c20b4'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('shared_theme', sa.Column('id', sa.Integer(), primary_key=True), sa.Column('data', sa.JSON(), nullable=False))

def downgrade():
    op.drop_table('shared_theme')
