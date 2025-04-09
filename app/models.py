from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime, Date, func, Enum, Text, Float
from sqlalchemy.orm import relationship
from .database import Base  
import enum
from datetime import datetime

class NivelAcesso(str, enum.Enum):
    ADMIN = "admin"
    LEITOR = "leitor"

    @classmethod
    def get_permissions(cls, nivel):
        try:
            if isinstance(nivel, str):
                nivel = cls(nivel)
            return {
                cls.ADMIN: {
                    "gerenciar_usuarios": True,
                    "gerenciar_livros": True,
                    "gerenciar_categorias": True,
                    "gerenciar_emprestimos": True,
                    "visualizar_relatorios": True,
                    "fazer_emprestimo": False  # Admin não pode fazer empréstimos
                },
                cls.LEITOR: {
                    "gerenciar_usuarios": False,
                    "gerenciar_livros": False,
                    "gerenciar_categorias": False,
                    "gerenciar_emprestimos": False,
                    "visualizar_relatorios": False,
                    "fazer_emprestimo": True  # Leitor pode fazer empréstimos
                }
            }.get(nivel, {})
        except ValueError:
            print(f"Nível de acesso inválido: {nivel}")
            return {}

class Livro(Base):
    __tablename__ = 'livros'

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String, index=True)
    autor = Column(String)
    ano_publicacao = Column(Integer)
    isbn = Column(String, unique=True)
    quantidade = Column(Integer)
    exemplares_disponiveis = Column(Integer)
    categoria_id = Column(Integer, ForeignKey("categorias.id"))
    data_cadastro = Column(DateTime, default=datetime.now)
    descricao = Column(Text)
    numero_paginas = Column(Integer)
    imagem_url = Column(String)
    editora = Column(String)
    idioma = Column(String)
    palavras_chave = Column(String)

    categoria = relationship("Categoria", back_populates="livros")
    emprestimos = relationship("Emprestimo", back_populates="livro")
    resenhas = relationship("Resenha", back_populates="livro")

    def __init__(self, **kwargs):
        if 'quantidade' in kwargs:
            kwargs['exemplares_disponiveis'] = kwargs['quantidade']
        super().__init__(**kwargs)

    @property
    def disponivel(self):
        return self.exemplares_disponiveis > 0

    __table_args__ = {
        'extend_existing': True
    }

# Modelo para a tabela Categoria
class Categoria(Base):
    __tablename__ = 'categorias'

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, unique=True, index=True)
    descricao = Column(String)

    # Relacionamento com a tabela Livro
    livros = relationship("Livro", back_populates="categoria")

# Modelo para a tabela Emprestimo
class Emprestimo(Base):
    __tablename__ = 'emprestimos'

    id = Column(Integer, primary_key=True, index=True)
    livro_id = Column(Integer, ForeignKey('livros.id'))
    usuario_id = Column(Integer, ForeignKey('usuarios.id'))
    data_emprestimo = Column(Date, default=func.current_date())
    data_devolucao_prevista = Column(Date)
    data_devolucao_efetiva = Column(Date, nullable=True)
    status = Column(String, default="Ativo")
    renovacoes_feitas = Column(Integer, default=0)
    multa = Column(Float, default=0.0)

    livro = relationship("Livro", back_populates="emprestimos")
    usuario = relationship("Usuario", back_populates="emprestimos")

    def calcular_multa(self):
        if self.status == "Ativo" and datetime.now().date() > self.data_devolucao_prevista:
            dias_atraso = (datetime.now().date() - self.data_devolucao_prevista).days
            self.multa = dias_atraso * 1.0  # R$ 1,00 por dia de atraso
        elif self.status == "Devolvido" and self.data_devolucao_efetiva > self.data_devolucao_prevista:
            dias_atraso = (self.data_devolucao_efetiva - self.data_devolucao_prevista).days
            self.multa = dias_atraso * 1.0
        return self.multa

class Resenha(Base):
    __tablename__ = "resenhas"

    id = Column(Integer, primary_key=True, index=True)
    livro_id = Column(Integer, ForeignKey("livros.id"))
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    texto = Column(Text)
    avaliacao = Column(Integer)
    data_criacao = Column(DateTime, default=datetime.now)

    livro = relationship("Livro", back_populates="resenhas")
    usuario = relationship("Usuario", back_populates="resenhas")

class Usuario(Base):
    __tablename__ = 'usuarios'

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String)
    email = Column(String, unique=True, index=True)
    senha_hash = Column(String)
    nivel_acesso = Column(String, default="leitor")
    ativo = Column(Boolean, default=True)
    data_registro = Column(DateTime, default=datetime.now)
    telefone = Column(String)
    cpf = Column(String, unique=True)
    data_nascimento = Column(Date)
    endereco = Column(String)
    limite_emprestimos = Column(Integer, default=3)
    multas_pendentes = Column(Float, default=0.0)

    emprestimos = relationship("Emprestimo", back_populates="usuario")
    resenhas = relationship("Resenha", back_populates="usuario")

    def tem_permissao(self, permissao):
        try:
            nivel = NivelAcesso(self.nivel_acesso)
            return NivelAcesso.get_permissions(nivel).get(permissao, False)
        except ValueError:
            print(f"Erro ao verificar permissão: nível de acesso inválido ({self.nivel_acesso})")
            return False
        except Exception as e:
            print(f"Erro ao verificar permissão: {str(e)}")
            return False

    def pode_fazer_emprestimo(self):
        if self.nivel_acesso == NivelAcesso.ADMIN:
            return False
        
        emprestimos_ativos = sum(1 for e in self.emprestimos if e.status == "Ativo")
        return (
            self.ativo and
            emprestimos_ativos < self.limite_emprestimos and
            self.multas_pendentes == 0
        )

    def atualizar_multas(self):
        total_multas = 0
        for emprestimo in self.emprestimos:
            if emprestimo.status == "Ativo":
                total_multas += emprestimo.calcular_multa()
        self.multas_pendentes = total_multas