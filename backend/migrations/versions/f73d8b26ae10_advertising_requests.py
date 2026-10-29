"""Advertising requests and portal delivery status."""
from alembic import op
import sqlalchemy as sa
revision = 'f73d8b26ae10'
down_revision = 'b8d4f02e6c31'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('advertising_request',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(120), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('business_name', sa.String(160), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('campaign_id', sa.Integer(), sa.ForeignKey('ad_campaign.id', ondelete='SET NULL'), nullable=True),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('email_delivery', sa.String(30), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index('ix_advertising_request_status', 'advertising_request', ['status'])

def downgrade():
    op.drop_table('advertising_request')
