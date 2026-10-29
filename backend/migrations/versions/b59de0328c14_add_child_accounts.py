"""Parent-managed child logins with approved add-only wishlists."""
from alembic import op
import sqlalchemy as sa
revision = 'b59de0328c14'
down_revision = 'a48cd9217b03'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('user', sa.Column('is_child', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('user', sa.Column('child_username', sa.String(80)))
    op.add_column('user', sa.Column('parent_user_id', sa.Integer()))
    op.add_column('user', sa.Column('child_enabled', sa.Boolean(), nullable=False, server_default='1'))
    with op.batch_alter_table('user') as batch:
        batch.create_unique_constraint('uq_user_child_username', ['child_username'])
        batch.create_foreign_key('fk_user_parent_user_id_user', 'user', ['parent_user_id'], ['id'], ondelete='CASCADE')
    op.create_table('child_wishlist_access',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=False),
        sa.Column('wishlist_id', sa.Integer(), sa.ForeignKey('wishlist.id', ondelete='CASCADE'), nullable=False),
        sa.UniqueConstraint('user_id', 'wishlist_id'))
    op.create_index('ix_child_wishlist_access_user_id', 'child_wishlist_access', ['user_id'])
    op.create_index('ix_child_wishlist_access_wishlist_id', 'child_wishlist_access', ['wishlist_id'])


def downgrade():
    op.drop_table('child_wishlist_access')
    with op.batch_alter_table('user') as batch:
        batch.drop_constraint('fk_user_parent_user_id_user', type_='foreignkey')
        batch.drop_constraint('uq_user_child_username', type_='unique')
        for name in ('child_enabled', 'parent_user_id', 'child_username', 'is_child'):
            batch.drop_column(name)
