"""Family letter art selections and one-time design purchases."""
from alembic import op
import sqlalchemy as sa
revision='1bc58d704a92'
down_revision='0a94e27c61bd'
branch_labels=None
depends_on=None

def upgrade():
    with op.batch_alter_table('wishlist_letter') as batch:
        batch.add_column(sa.Column('theme_id',sa.Integer(),nullable=True))
        batch.create_foreign_key('fk_wishlist_letter_theme_id_shared_theme','shared_theme',['theme_id'],['id'],ondelete='SET NULL')
    op.create_table('letter_art_purchase',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('household_id',sa.Integer(),sa.ForeignKey('household.id',ondelete='CASCADE'),nullable=False),
        sa.Column('theme_id',sa.Integer(),sa.ForeignKey('shared_theme.id',ondelete='CASCADE'),nullable=False),
        sa.Column('buyer_user_id',sa.Integer(),sa.ForeignKey('user.id',ondelete='SET NULL')),
        sa.Column('art_name',sa.String(80),nullable=False),
        sa.Column('amount_cents',sa.Integer(),nullable=False),
        sa.Column('currency',sa.String(3),nullable=False),
        sa.Column('stripe_session_id',sa.String(255),unique=True),
        sa.Column('checkout_url',sa.String(2000)),
        sa.Column('expires_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('payment_intent',sa.String(255)),
        sa.Column('paid',sa.Boolean(),nullable=False),
        sa.Column('revoked',sa.Boolean(),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False))
    for column in ['household_id','theme_id','payment_intent']:
        op.create_index('ix_letter_art_purchase_'+column,'letter_art_purchase',[column])

def downgrade():
    op.drop_table('letter_art_purchase')
    with op.batch_alter_table('wishlist_letter') as batch:
        batch.drop_constraint('fk_wishlist_letter_theme_id_shared_theme',type_='foreignkey')
        batch.drop_column('theme_id')
