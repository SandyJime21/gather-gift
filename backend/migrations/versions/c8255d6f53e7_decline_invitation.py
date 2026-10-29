"""Remember declined family invitations."""
from alembic import op
import sqlalchemy as sa
revision = 'c8255d6f53e7'
down_revision = 'b7144c5e42d6'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('household_invitation', sa.Column('declined_at', sa.DateTime(timezone=True), nullable=True))

def downgrade():
    op.drop_column('household_invitation', 'declined_at')
