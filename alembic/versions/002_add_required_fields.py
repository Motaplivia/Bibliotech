"""add required fields

Revision ID: 002
Revises: 001
Create Date: 2024-03-19 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Adicionar campos ao modelo Usuario
    op.add_column('usuarios', sa.Column('telefone', sa.String(), nullable=True))
    op.add_column('usuarios', sa.Column('cpf', sa.String(11), nullable=True))
    op.add_column('usuarios', sa.Column('data_nascimento', sa.Date(), nullable=True))
    op.add_column('usuarios', sa.Column('endereco', sa.String(), nullable=True))
    op.add_column('usuarios', sa.Column('limite_emprestimos', sa.Integer(), server_default='3', nullable=False))
    op.add_column('usuarios', sa.Column('multas_pendentes', sa.Float(), server_default='0', nullable=False))
    
    # Adicionar campos ao modelo Emprestimo
    op.add_column('emprestimos', sa.Column('renovacoes_feitas', sa.Integer(), server_default='0', nullable=False))
    op.add_column('emprestimos', sa.Column('multa', sa.Float(), server_default='0', nullable=False))
    
    # Adicionar campos ao modelo Livro
    op.add_column('livros', sa.Column('editora', sa.String(), nullable=True))
    op.add_column('livros', sa.Column('idioma', sa.String(), nullable=True))
    op.add_column('livros', sa.Column('palavras_chave', sa.String(), nullable=True))


def downgrade() -> None:
    # Remover campos do modelo Usuario
    op.drop_column('usuarios', 'telefone')
    op.drop_column('usuarios', 'cpf')
    op.drop_column('usuarios', 'data_nascimento')
    op.drop_column('usuarios', 'endereco')
    op.drop_column('usuarios', 'limite_emprestimos')
    op.drop_column('usuarios', 'multas_pendentes')
    
    # Remover campos do modelo Emprestimo
    op.drop_column('emprestimos', 'renovacoes_feitas')
    op.drop_column('emprestimos', 'multa')
    
    # Remover campos do modelo Livro
    op.drop_column('livros', 'editora')
    op.drop_column('livros', 'idioma')
    op.drop_column('livros', 'palavras_chave') 