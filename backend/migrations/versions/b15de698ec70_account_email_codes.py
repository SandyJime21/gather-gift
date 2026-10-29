"""One-time codes for main-email account recovery."""
from alembic import op
import sqlalchemy as sa
revision = 'b15de698ec70'
down_revision = 'a04cd587db69'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('account_email_code', sa.Column('id', sa.String(64), primary_key=True), sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=False), sa.Column('purpose', sa.String(30), nullable=False), sa.Column('target_email', sa.String(255)), sa.Column('code_hash', sa.String(255), nullable=False), sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False), sa.Column('used_at', sa.DateTime(timezone=True)), sa.Column('attempts', sa.Integer(), nullable=False), sa.Column('session_version', sa.Integer(), nullable=False))
    op.create_index('ix_account_email_code_user_id', 'account_email_code', ['user_id'])

def downgrade():
    op.drop_table('account_email_code')
