"""Personal wishlists shared with selected family accounts."""
from alembic import op
import sqlalchemy as sa
revision = 'e82ab365bf47'
down_revision = 'd71fa254ae36'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('personal_wish',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('owner_id', sa.Integer(), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=False),
        sa.Column('item_id', sa.Integer(), sa.ForeignKey('wishlist_item.id', ondelete='CASCADE'), nullable=False, unique=True))
    op.create_index('ix_personal_wish_owner_id', 'personal_wish', ['owner_id'])
    op.create_table('personal_wish_viewer',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('wish_id', sa.Integer(), sa.ForeignKey('personal_wish.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=False),
        sa.UniqueConstraint('wish_id', 'user_id'))
    op.create_index('ix_personal_wish_viewer_wish_id', 'personal_wish_viewer', ['wish_id'])
    op.create_index('ix_personal_wish_viewer_user_id', 'personal_wish_viewer', ['user_id'])


def downgrade():
    op.drop_table('personal_wish_viewer')
    op.drop_table('personal_wish')
