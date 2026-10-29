"""Help assistant chat history."""
from alembic import op
import sqlalchemy as sa

revision = 'a7c3e91d5b20'
down_revision = 'e82c4b9510fa'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'help_chat_message',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('sender', sa.String(length=10), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("sender IN ('user','bot')", name='ck_help_chat_message_help_chat_sender'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], name=op.f('fk_help_chat_message_user_id_user'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_help_chat_message')),
    )
    with op.batch_alter_table('help_chat_message', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_help_chat_message_user_id'), ['user_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_help_chat_message_created_at'), ['created_at'], unique=False)


def downgrade():
    with op.batch_alter_table('help_chat_message', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_help_chat_message_created_at'))
        batch_op.drop_index(batch_op.f('ix_help_chat_message_user_id'))
    op.drop_table('help_chat_message')
