"""Assign support tickets to staff."""
from alembic import op
import sqlalchemy as sa

revision = 'b8d4f02e6c31'
down_revision = 'a7c3e91d5b20'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('support_ticket', schema=None) as batch_op:
        batch_op.add_column(sa.Column('assigned_to_id', sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f('ix_support_ticket_assigned_to_id'), ['assigned_to_id'], unique=False)
        batch_op.create_foreign_key(batch_op.f('fk_support_ticket_assigned_to_id_user'), 'user', ['assigned_to_id'], ['id'], ondelete='SET NULL')


def downgrade():
    with op.batch_alter_table('support_ticket', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_support_ticket_assigned_to_id_user'), type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_support_ticket_assigned_to_id'))
        batch_op.drop_column('assigned_to_id')
