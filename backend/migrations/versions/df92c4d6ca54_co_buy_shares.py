"""Co-buy requested contributions and decline status."""
from alembic import op
import sqlalchemy as sa
revision='df92c4d6ca54'
down_revision='ce81b3c5b943'
branch_labels=None
depends_on=None

def upgrade():
    op.add_column('co_buy_invitation',sa.Column('share_percent',sa.Numeric(5,2),nullable=False,server_default='50'))
    op.add_column('co_buy_invitation',sa.Column('declined',sa.Boolean(),nullable=False,server_default=sa.false()))

def downgrade():
    op.drop_column('co_buy_invitation','declined')
    op.drop_column('co_buy_invitation','share_percent')
