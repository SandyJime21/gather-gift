"""Adult family accounts and approved gift suggestions."""
from alembic import op
import sqlalchemy as sa
revision='bd70a2b4a832'
down_revision='ac6991a39721'
branch_labels=None
depends_on=None

def upgrade():
    op.add_column('household_membership',sa.Column('is_family_member',sa.Boolean(),nullable=False,server_default=sa.false()))
    op.add_column('household_membership',sa.Column('inherited_from_household_id',sa.Integer(),nullable=True))
    op.add_column('household_invitation',sa.Column('linked_profile_id',sa.Integer(),nullable=True))
    op.create_foreign_key('fk_invitation_linked_profile','household_invitation','person_profile',['linked_profile_id'],['id'],ondelete='CASCADE')
    op.create_table('gift_suggestion',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('sender_id',sa.Integer(),sa.ForeignKey('user.id',ondelete='CASCADE'),nullable=False),
        sa.Column('recipient_id',sa.Integer(),sa.ForeignKey('user.id',ondelete='CASCADE'),nullable=False,index=True),
        sa.Column('profile_id',sa.Integer(),sa.ForeignKey('person_profile.id',ondelete='CASCADE'),nullable=False),
        sa.Column('data',sa.JSON(),nullable=False),sa.Column('status',sa.String(20),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False))

def downgrade():
    op.drop_table('gift_suggestion')
    op.drop_constraint('fk_invitation_linked_profile','household_invitation',type_='foreignkey')
    op.drop_column('household_invitation','linked_profile_id')
    op.drop_column('household_membership','inherited_from_household_id')
    op.drop_column('household_membership','is_family_member')
