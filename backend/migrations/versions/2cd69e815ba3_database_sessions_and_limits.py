"""Shared login sessions and request limits without Redis."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import MEDIUMBLOB

revision = '2cd69e815ba3'
down_revision = '1bc58d704a92'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('app_session',
        sa.Column('key_hash', sa.String(64), primary_key=True),
        sa.Column('data', sa.LargeBinary().with_variant(MEDIUMBLOB(), 'mysql'), nullable=False),
        sa.Column('expires_at', sa.BigInteger(), nullable=False))
    op.create_index('ix_app_session_expires_at', 'app_session', ['expires_at'])
    op.create_table('request_limit',
        sa.Column('key_hash', sa.String(64), primary_key=True),
        sa.Column('value', sa.BigInteger(), nullable=False),
        sa.Column('expires_at', sa.BigInteger(), nullable=False))
    op.create_index('ix_request_limit_expires_at', 'request_limit', ['expires_at'])


def downgrade():
    op.drop_table('request_limit')
    op.drop_table('app_session')
