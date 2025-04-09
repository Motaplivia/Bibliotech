from pydantic import BaseModel, Field, validator, EmailStr, constr
from typing import List, Optional
from datetime import date, datetime
from .models import NivelAcesso
from enum import Enum

# Pydantic Models para Livro
class LivroBase(BaseModel):
    titulo: str = Field(..., min_length=1, max_length=100, description="Título do livro")
    autor: str = Field(..., min_length=1, max_length=100, description="Nome do autor")
    ano_publicacao: int = Field(..., ge=1000, le=date.today().year, description="Ano de publicação")
    isbn: str = Field(..., min_length=10, description="ISBN do livro")
    quantidade: int = Field(default=1, ge=1, description="Quantidade total")
    categoria_id: int = Field(..., gt=0, description="ID da categoria")
    descricao: Optional[str] = None
    numero_paginas: Optional[int] = Field(None, gt=0)
    editora: Optional[str] = None
    idioma: Optional[str] = None
    palavras_chave: Optional[str] = None
    
    @validator('titulo')
    def titulo_nao_vazio(cls, v):
        v = v.strip()
        if not v:
            raise ValueError('Título não pode estar vazio')
        return v
    
    @validator('autor')
    def autor_nao_vazio(cls, v):
        v = v.strip()
        if not v:
            raise ValueError('Nome do autor não pode estar vazio')
        return v

class LivroCreate(LivroBase):
    pass

class Livro(LivroBase):
    id: int
    exemplares_disponiveis: int
    data_cadastro: datetime
    imagem_url: Optional[str] = None
    
    class Config:
        from_attributes = True

class LivroFull(Livro):
    categoria: Optional['CategoriaSimples'] = None

# Pydantic Models para Categoria
class CategoriaBase(BaseModel):
    nome: str = Field(..., min_length=1, max_length=50)
    descricao: Optional[str] = None

class CategoriaCreate(CategoriaBase):
    pass

class Categoria(CategoriaBase):
    id: int
    livros: List[Livro] = []

    class Config:
        from_attributes = True

class CategoriaSimples(CategoriaBase):
    id: int

    class Config:
        from_attributes = True

# Pydantic Models para Emprestimo
class EmprestimoBase(BaseModel):
    livro_id: int = Field(..., gt=0, description="ID do livro")
    usuario_id: int = Field(..., gt=0, description="ID do usuário")
    data_emprestimo: date = Field(default_factory=date.today, description="Data do empréstimo")
    data_devolucao_prevista: date = Field(..., description="Data prevista para devolução")
    data_devolucao_efetiva: Optional[date] = Field(None, description="Data efetiva da devolução")
    status: str = Field(default="Ativo", description="Status do empréstimo")
    renovacoes_feitas: int = Field(default=0, description="Número de renovações feitas")
    multa: float = Field(default=0.0, description="Valor da multa")

class EmprestimoCreate(EmprestimoBase):
    pass

class EmprestimoUpdate(EmprestimoBase):
    pass

class Emprestimo(EmprestimoBase):
    id: int
    livro: Livro
    usuario: 'Usuario'

    class Config:
        from_attributes = True

# Pydantic Models para Usuario
class NivelAcesso(str, Enum):
    ADMIN = "admin"
    BIBLIOTECARIO = "bibliotecario"
    USUARIO = "usuario"

class UsuarioBase(BaseModel):
    nome: str = Field(..., description="Nome completo do usuário")
    email: EmailStr = Field(..., description="Email do usuário")
    cpf: Optional[str] = Field(None, description="CPF do usuário (apenas números)")
    telefone: Optional[str] = Field(None, description="Telefone do usuário")
    data_nascimento: Optional[date] = Field(None, description="Data de nascimento do usuário")
    endereco: Optional[str] = Field(None, description="Endereço completo do usuário")
    nivel_acesso: NivelAcesso = Field(default=NivelAcesso.USUARIO, description="Nível de acesso do usuário")
    limite_emprestimos: int = Field(default=3, ge=0, le=10, description="Limite de empréstimos simultâneos")
    ativo: bool = Field(default=True, description="Status do usuário")

class UsuarioCreate(UsuarioBase):
    senha: str = Field(..., min_length=6, description="Senha do usuário")

class UsuarioUpdate(UsuarioBase):
    senha: Optional[str] = Field(None, min_length=6, description="Nova senha do usuário")

class Usuario(UsuarioBase):
    id: int
    data_registro: datetime
    multa: float = Field(default=0.0, description="Valor da multa atual")
    multas_pendentes: float = Field(default=0.0, description="Valor total de multas pendentes")
    emprestimos: List[Emprestimo] = []

    class Config:
        from_attributes = True

# Pydantic Models para Resenha
class ResenhaBase(BaseModel):
    livro_id: int = Field(..., gt=0)
    texto: str = Field(..., min_length=1)
    avaliacao: int = Field(..., ge=1, le=5)

class ResenhaCreate(ResenhaBase):
    pass

class Resenha(ResenhaBase):
    id: int
    usuario_id: int
    data_criacao: datetime
    livro: Livro
    usuario: Usuario

    class Config:
        from_attributes = True

# Atualizar referências circulares
Livro.model_rebuild()
Categoria.model_rebuild()
Emprestimo.model_rebuild()
Usuario.model_rebuild()

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None