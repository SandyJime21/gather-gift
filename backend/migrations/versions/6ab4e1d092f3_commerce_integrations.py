"""Approved commerce integrations and anonymous outbound events."""
from alembic import op
import sqlalchemy as sa
revision='6ab4e1d092f3'
down_revision='51a8c29e7b10'
branch_labels=None
depends_on=None


def upgrade():
    op.create_table('commerce_integration',sa.Column('provider',sa.String(30),primary_key=True),sa.Column('enabled',sa.Boolean(),nullable=False),sa.Column('approved',sa.Boolean(),nullable=False),sa.Column('merchant_rules',sa.JSON(),nullable=False),sa.Column('last_error',sa.String(120)),sa.Column('last_error_at',sa.DateTime(timezone=True)),sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False))
    op.create_table('commerce_product_metadata',sa.Column('item_id',sa.Integer(),sa.ForeignKey('wishlist_item.id',ondelete='CASCADE'),primary_key=True),sa.Column('retailer_domain',sa.String(253),nullable=False),sa.Column('source_provider',sa.String(30),nullable=False),sa.Column('external_product_id',sa.String(200)),sa.Column('last_verified_at',sa.DateTime(timezone=True)))
    op.create_table('commerce_outbound_event',sa.Column('id',sa.Integer(),primary_key=True),sa.Column('item_id',sa.Integer(),sa.ForeignKey('wishlist_item.id',ondelete='SET NULL')),sa.Column('provider',sa.String(30),nullable=False),sa.Column('merchant',sa.String(253),nullable=False),sa.Column('attribution_id',sa.String(32),nullable=False,unique=True),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False))
    op.create_index('ix_commerce_outbound_event_created_at','commerce_outbound_event',['created_at'])


def downgrade():
    op.drop_index('ix_commerce_outbound_event_created_at',table_name='commerce_outbound_event')
    op.drop_table('commerce_outbound_event')
    op.drop_table('commerce_product_metadata')
    op.drop_table('commerce_integration')
