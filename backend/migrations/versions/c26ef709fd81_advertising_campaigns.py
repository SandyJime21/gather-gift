"""Reviewed scheduled advertising campaigns and Stripe payment state."""
from alembic import op
import sqlalchemy as sa
revision = 'c26ef709fd81'
down_revision = 'b15de698ec70'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('ad_campaign', sa.Column('id', sa.Integer(), primary_key=True), sa.Column('token_hash', sa.String(64), nullable=False, unique=True), sa.Column('data', sa.JSON(), nullable=False), sa.Column('status', sa.String(30), nullable=False), sa.Column('amount_cents', sa.Integer(), nullable=False), sa.Column('stripe_session_id', sa.String(255), unique=True), sa.Column('payment_intent', sa.String(255)), sa.Column('paid', sa.Boolean(), nullable=False), sa.Column('created_at', sa.DateTime(timezone=True), nullable=False))

def downgrade():
    op.drop_table('ad_campaign')
