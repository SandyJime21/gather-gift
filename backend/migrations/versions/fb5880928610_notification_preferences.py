"""Account notification preferences."""
from alembic import op
import sqlalchemy as sa
revision = 'fb5880928610'
down_revision = 'ea477f817509'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('user', sa.Column('notification_preferences', sa.JSON(), nullable=True))

def downgrade():
    op.drop_column('user', 'notification_preferences')
