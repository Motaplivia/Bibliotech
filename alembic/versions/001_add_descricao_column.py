"""add descricao column

Revision ID: 001
Revises: 
Create Date: 2024-03-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('livros', sa.Column('descricao', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('livros', 'descricao') 