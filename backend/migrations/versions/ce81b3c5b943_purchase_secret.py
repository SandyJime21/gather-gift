"""Optional buyer attribution for purchases."""
from alembic import op
import sqlalchemy as sa
revision = 'ce81b3c5b943'
down_revision = 'bd70a2b4a832'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('gift_reservation', sa.Column('purchase_secret', sa.Boolean(), nullable=False, server_default=sa.true()))

def downgrade():
    op.drop_column('gift_reservation', 'purchase_secret')
