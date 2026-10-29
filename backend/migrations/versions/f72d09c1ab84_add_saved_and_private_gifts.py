"""Add private saved gifts and personal gift plans."""
from alembic import op
import sqlalchemy as sa
revision = 'f72d09c1ab84'
down_revision = 'e2c51480a7d6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('saved_gift',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=False),
        sa.Column('item_id', sa.Integer(), sa.ForeignKey('wishlist_item.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('user_id', 'item_id'))
    op.create_index('ix_saved_gift_user_id', 'saved_gift', ['user_id'])
    op.create_index('ix_saved_gift_item_id', 'saved_gift', ['item_id'])
    op.create_table('private_gift',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('recipient', sa.String(120), nullable=False),
        sa.Column('household_name', sa.String(160)),
        sa.Column('occasion', sa.String(160)),
        sa.Column('store_name', sa.String(120)),
        sa.Column('product_url', sa.String(2000)),
        sa.Column('image_url', sa.String(2000)),
        sa.Column('estimated_price', sa.Numeric(10, 2)),
        sa.Column('currency', sa.String(3), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('planned','purchased')", name='private_gift_status'))
    op.create_index('ix_private_gift_user_id', 'private_gift', ['user_id'])


def downgrade():
    op.drop_table('private_gift')
    op.drop_table('saved_gift')
