"""Parent-controlled wishlist letters for child profiles."""
from alembic import op
import sqlalchemy as sa
revision = '0a94e27c61bd'
down_revision = 'f73d8b26ae10'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('wishlist_letter',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('household_id', sa.Integer(), sa.ForeignKey('household.id', ondelete='CASCADE'), nullable=False),
        sa.Column('profile_id', sa.Integer(), sa.ForeignKey('person_profile.id', ondelete='CASCADE'), nullable=False),
        sa.Column('wishlist_id', sa.Integer(), sa.ForeignKey('wishlist.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('sender_name', sa.String(120), nullable=False),
        sa.Column('send_on', sa.Date(), nullable=False),
        sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=False))
    op.create_index('ix_wishlist_letter_household_id', 'wishlist_letter', ['household_id'])
    op.create_index('ix_wishlist_letter_profile_id', 'wishlist_letter', ['profile_id'])

def downgrade():
    op.drop_table('wishlist_letter')
