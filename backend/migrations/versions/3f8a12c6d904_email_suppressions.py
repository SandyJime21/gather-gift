"""Address-wide email opt-out, including non-account recipients."""
from alembic import op
import sqlalchemy as sa

revision = '3f8a12c6d904'
down_revision = '2cd69e815ba3'
branch_labels = None
depends_on = None


def upgrade():
    # The additive table may already exist when local work shares production DB.
    if sa.inspect(op.get_bind()).has_table('email_suppression'):
        return
    op.create_table('email_suppression',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('source', sa.String(30), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False))
    op.create_index('ix_email_suppression_email', 'email_suppression', ['email'], unique=True)


def downgrade():
    op.drop_index('ix_email_suppression_email', table_name='email_suppression')
    op.drop_table('email_suppression')
