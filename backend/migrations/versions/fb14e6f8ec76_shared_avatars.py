"""Shared profile cartoon collection."""
from alembic import op
import sqlalchemy as sa
revision='fb14e6f8ec76'
down_revision='ea03d5e7db65'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('shared_avatar',sa.Column('id',sa.Integer(),primary_key=True),sa.Column('name',sa.String(80),nullable=False),sa.Column('image_path',sa.String(500),nullable=False))

def downgrade():
    op.drop_table('shared_avatar')
