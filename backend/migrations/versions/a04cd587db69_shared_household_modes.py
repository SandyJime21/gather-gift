"""Shared household member profiles and parent PIN."""
from alembic import op
import sqlalchemy as sa
revision = 'a04cd587db69'
down_revision = 'f93bc476ca58'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('user', sa.Column('parent_pin_hash', sa.String(255)))
    op.add_column('person_profile', sa.Column('is_adult', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('person_profile', sa.Column('is_guardian', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('person_profile', sa.Column('member_email', sa.String(255)))

def downgrade():
    op.drop_column('person_profile', 'member_email')
    op.drop_column('person_profile', 'is_guardian')
    op.drop_column('person_profile', 'is_adult')
    op.drop_column('user', 'parent_pin_hash')
