"""Mutual family follows after accepted invitations."""
from alembic import op
import sqlalchemy as sa
revision = 'f5922a3c20b4'
down_revision = 'e481192b1fa3'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('family_follow',sa.Column('id',sa.Integer(),primary_key=True),sa.Column('follower_id',sa.Integer(),sa.ForeignKey('user.id',ondelete='CASCADE'),nullable=False),sa.Column('followed_id',sa.Integer(),sa.ForeignKey('user.id',ondelete='CASCADE'),nullable=False),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),sa.UniqueConstraint('follower_id','followed_id'))
    op.create_index('ix_family_follow_follower_id','family_follow',['follower_id'])
    op.create_index('ix_family_follow_followed_id','family_follow',['followed_id'])

def downgrade():
    op.drop_table('family_follow')
