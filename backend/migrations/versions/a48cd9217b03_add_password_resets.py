"""Add single-use password reset tokens and session revocation."""
from alembic import op
import sqlalchemy as sa
revision = 'a48cd9217b03'
down_revision = 'f72d09c1ab84'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('user', sa.Column('session_version', sa.Integer(), nullable=False, server_default='0'))
    op.create_table('password_reset',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token_hash', sa.String(64), nullable=False, unique=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True)),
        sa.Column('password_version', sa.Integer(), nullable=False))
    op.create_index('ix_password_reset_user_id', 'password_reset', ['user_id'])


def downgrade():
    op.drop_table('password_reset')
    op.drop_column('user', 'session_version')
