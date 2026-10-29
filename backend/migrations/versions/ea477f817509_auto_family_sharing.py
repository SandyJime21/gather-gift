"""Automatic non-private family sharing for new invitations."""
from alembic import op
import sqlalchemy as sa
revision = 'ea477f817509'
down_revision = 'd9366e7064f8'
branch_labels = None
depends_on = None

def upgrade():
    for table in ('household_membership','household_invitation'):
        op.add_column(table,sa.Column('share_all_profiles',sa.Boolean(),nullable=False,server_default=sa.false()))

def downgrade():
    for table in ('household_invitation','household_membership'):
        op.drop_column(table,'share_all_profiles')
