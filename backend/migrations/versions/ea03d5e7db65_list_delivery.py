"""Optional shared list delivery addresses and gift handover plans."""
from alembic import op
import sqlalchemy as sa
revision='ea03d5e7db65'
down_revision='df92c4d6ca54'
branch_labels=None
depends_on=None

def upgrade():
    op.add_column('wishlist',sa.Column('delivery_address',sa.Text(),nullable=True))
    op.add_column('wishlist',sa.Column('share_delivery_address',sa.Boolean(),nullable=False,server_default=sa.false()))
    op.add_column('gift_reservation',sa.Column('delivery_method',sa.String(20),nullable=False,server_default='undecided'))

def downgrade():
    op.drop_column('gift_reservation','delivery_method')
    op.drop_column('wishlist','share_delivery_address')
    op.drop_column('wishlist','delivery_address')
