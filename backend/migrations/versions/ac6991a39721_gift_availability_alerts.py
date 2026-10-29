"""Gift availability alerts."""
from alembic import op
import sqlalchemy as sa
revision='ac6991a39721'
down_revision='fb5880928610'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('gift_availability_alert',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('user_id',sa.Integer(),sa.ForeignKey('user.id',ondelete='CASCADE'),nullable=False,index=True),
        sa.Column('item_id',sa.Integer(),sa.ForeignKey('wishlist_item.id',ondelete='CASCADE'),nullable=False,index=True),
        sa.Column('ready',sa.Boolean(),nullable=False),
        sa.Column('read_at',sa.DateTime(timezone=True)),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint('user_id','item_id'))

def downgrade():
    op.drop_table('gift_availability_alert')
