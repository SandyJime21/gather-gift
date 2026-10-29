"""Shared allergy notes for authorized gift profile viewers."""
from alembic import op
import sqlalchemy as sa
revision = "e82c4b9510fa"
down_revision = "d71e82a940cb"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("person_profile", sa.Column("allergies", sa.Text(), nullable=True))
    op.add_column("person_profile", sa.Column("favorite_snacks", sa.JSON(), nullable=True))

def downgrade():
    op.drop_column("person_profile", "favorite_snacks")
    op.drop_column("person_profile", "allergies")
