"""Family list collections, without merging members' gifts."""
from alembic import op
import sqlalchemy as sa
revision='7c83a92db461'
down_revision='6ab4e1d092f3'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('family_list_collection',sa.Column('id',sa.Integer(),primary_key=True),sa.Column('household_id',sa.Integer(),sa.ForeignKey('household.id',ondelete='CASCADE'),nullable=False),sa.Column('title',sa.String(160),nullable=False),sa.Column('cover_url',sa.String(2000)),sa.Column('use_family_photo',sa.Boolean(),nullable=False),sa.Column('wishlist_ids',sa.JSON(),nullable=False),sa.UniqueConstraint('household_id','title'))
    op.create_index('ix_family_list_collection_household_id','family_list_collection',['household_id'])

def downgrade():
    op.drop_table('family_list_collection')
