"""Persist per-template email block designs."""
from alembic import op
import sqlalchemy as sa
revision = '51a8c29e7b10'
down_revision = '3f8a12c6d904'
branch_labels = None
depends_on = None


def upgrade():
    if sa.inspect(op.get_bind()).has_table('email_template_design'):
        return
    op.create_table('email_template_design',sa.Column('template_id',sa.String(60),primary_key=True),sa.Column('blocks',sa.JSON(),nullable=False))


def downgrade():
    op.drop_table('email_template_design')
