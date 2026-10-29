"""Household Secret Santa and White Elephant games."""
from alembic import op
import sqlalchemy as sa
revision = 'e481192b1fa3'
down_revision = 'd370081a0e92'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('gift_exchange_game', sa.Column('id',sa.Integer(),primary_key=True), sa.Column('household_id',sa.Integer(),sa.ForeignKey('household.id',ondelete='CASCADE'),nullable=False), sa.Column('created_by_id',sa.Integer(),sa.ForeignKey('user.id',ondelete='SET NULL')), sa.Column('kind',sa.String(30),nullable=False), sa.Column('title',sa.String(160),nullable=False), sa.Column('budget',sa.Numeric(10,2)), sa.Column('event_date',sa.Date()), sa.Column('status',sa.String(30),nullable=False), sa.Column('state',sa.JSON(),nullable=False), sa.Column('version',sa.Integer(),nullable=False), sa.Column('created_at',sa.DateTime(timezone=True),nullable=False))
    op.create_index('ix_gift_exchange_game_household_id','gift_exchange_game',['household_id'])

def downgrade():
    op.drop_table('gift_exchange_game')
