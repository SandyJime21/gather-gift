"""Email approval before password and family photo changes."""
from alembic import op
import sqlalchemy as sa
revision = 'd370081a0e92'
down_revision = 'c26ef709fd81'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('account_email_code', sa.Column('pending_data', sa.JSON()))

def downgrade():
    op.drop_column('account_email_code', 'pending_data')
