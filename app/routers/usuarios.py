from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from sqlalchemy.orm import Session
from typing import List
from .. import models, schemas
from ..database import get_db
from passlib.context import CryptContext
from ..auth import verificar_permissao, obter_usuario_atual
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from datetime import datetime

router = APIRouter()
templates = Jinja2Templates(directory="templates")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str):
    return pwd_context.hash(password)

@router.get("/usuarios")
async def listar_usuarios(
    request: Request,
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(obter_usuario_atual)
):
    if not usuario_atual.tem_permissao("gerenciar_usuarios"):
        raise HTTPException(status_code=403, detail="Sem permissão para acessar esta página")
    
    usuarios = db.query(models.Usuario).all()
    
    # Atualizar multas de todos os usuários
    for usuario in usuarios:
        usuario.atualizar_multas()
    db.commit()
    
    return templates.TemplateResponse(
        "usuarios.html",
        {
            "request": request,
            "usuarios": usuarios,
            "usuario": usuario_atual
        }
    )

@router.get("/usuarios/adicionar")
async def adicionar_usuario_form(
    request: Request,
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(obter_usuario_atual)
):
    if not usuario_atual.tem_permissao("gerenciar_usuarios"):
        raise HTTPException(status_code=403, detail="Sem permissão para acessar esta página")
    
    return templates.TemplateResponse(
        "adicionar_usuario.html",
        {
            "request": request,
            "usuario": usuario_atual
        }
    )

@router.post("/usuarios/adicionar")
async def adicionar_usuario(
    request: Request,
    nome: str = Form(...),
    email: str = Form(...),
    senha: str = Form(...),
    cpf: str = Form(...),
    telefone: str = Form(...),
    data_nascimento: str = Form(...),
    endereco: str = Form(...),
    nivel_acesso: str = Form(...),
    limite_emprestimos: int = Form(...),
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(obter_usuario_atual)
):
    if not usuario_atual.tem_permissao("gerenciar_usuarios"):
        raise HTTPException(status_code=403, detail="Sem permissão para realizar esta ação")
    
    try:
        # Verificar se já existe um usuário com este email
        if db.query(models.Usuario).filter(models.Usuario.email == email).first():
            return templates.TemplateResponse(
                "adicionar_usuario.html",
                {
                    "request": request,
                    "error": "Já existe um usuário com este email",
                    "usuario": usuario_atual
                }
            )
        
        # Criar novo usuário
        novo_usuario = models.Usuario(
            nome=nome,
            email=email,
            senha_hash=pwd_context.hash(senha),
            cpf=cpf,
            telefone=telefone,
            data_nascimento=data_nascimento,
            endereco=endereco,
            nivel_acesso=nivel_acesso,
            limite_emprestimos=limite_emprestimos,
            ativo=True
        )
        
        db.add(novo_usuario)
        db.commit()
        
        return RedirectResponse(url="/usuarios", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        return templates.TemplateResponse(
            "adicionar_usuario.html",
            {
                "request": request,
                "error": f"Erro ao criar usuário: {str(e)}",
                "usuario": usuario_atual
            }
        )

@router.get("/usuarios/{usuario_id}")
async def detalhes_usuario(
    usuario_id: int,
    request: Request,
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(obter_usuario_atual)
):
    if not usuario_atual.tem_permissao("gerenciar_usuarios") and usuario_atual.id != usuario_id:
        raise HTTPException(status_code=403, detail="Sem permissão para acessar esta página")
    
    usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    # Atualizar multas do usuário
    usuario.atualizar_multas()
    db.commit()
    
    return templates.TemplateResponse(
        "detalhes_usuario.html",
        {
            "request": request,
            "usuario_detalhes": usuario,
            "usuario": usuario_atual
        }
    )

@router.get("/usuarios/editar/{usuario_id}")
async def editar_usuario_form(
    usuario_id: int,
    request: Request,
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(obter_usuario_atual)
):
    if not usuario_atual.tem_permissao("gerenciar_usuarios"):
        raise HTTPException(status_code=403, detail="Sem permissão para acessar esta página")
    
    usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    return templates.TemplateResponse(
        "editar_usuario.html",
        {
            "request": request,
            "usuario": usuario,
            "usuario_atual": usuario_atual
        }
    )

@router.post("/usuarios/editar/{usuario_id}")
async def editar_usuario(
    usuario_id: int,
    request: Request,
    nome: str = Form(...),
    email: str = Form(...),
    senha: str = Form(None),
    cpf: str = Form(...),
    telefone: str = Form(...),
    data_nascimento: str = Form(...),
    endereco: str = Form(...),
    nivel_acesso: str = Form(...),
    limite_emprestimos: int = Form(...),
    ativo: bool = Form(...),
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(obter_usuario_atual)
):
    if not usuario_atual.tem_permissao("gerenciar_usuarios"):
        raise HTTPException(status_code=403, detail="Sem permissão para realizar esta ação")
    
    try:
        usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
        if not usuario:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        
        # Verificar se já existe outro usuário com este email
        if email != usuario.email:
            if db.query(models.Usuario).filter(models.Usuario.email == email).first():
                return templates.TemplateResponse(
                    "editar_usuario.html",
                    {
                        "request": request,
                        "usuario": usuario,
                        "error": "Já existe um usuário com este email",
                        "usuario_atual": usuario_atual
                    }
                )
        
        # Atualizar dados do usuário
        usuario.nome = nome
        usuario.email = email
        if senha:
            usuario.senha_hash = pwd_context.hash(senha)
        usuario.cpf = cpf
        usuario.telefone = telefone
        usuario.data_nascimento = data_nascimento
        usuario.endereco = endereco
        usuario.nivel_acesso = nivel_acesso
        usuario.limite_emprestimos = limite_emprestimos
        usuario.ativo = ativo
        
        db.commit()
        
        return RedirectResponse(url="/usuarios", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        return templates.TemplateResponse(
            "editar_usuario.html",
            {
                "request": request,
                "usuario": usuario,
                "error": f"Erro ao atualizar usuário: {str(e)}",
                "usuario_atual": usuario_atual
            }
        )

@router.get("/usuarios/deletar/{usuario_id}")
async def deletar_usuario_form(
    usuario_id: int,
    request: Request,
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(obter_usuario_atual)
):
    if not usuario_atual.tem_permissao("gerenciar_usuarios"):
        raise HTTPException(status_code=403, detail="Sem permissão para acessar esta página")
    
    usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    # Verificar se existem empréstimos ativos
    emprestimos = db.query(models.Emprestimo).filter(
        models.Emprestimo.usuario_id == usuario_id,
        models.Emprestimo.status == "Ativo"
    ).first()
    if emprestimos:
        return templates.TemplateResponse(
            "usuarios.html",
            {
                "request": request,
                "error": "Não é possível deletar um usuário com empréstimos ativos",
                "usuario": usuario_atual
            }
        )
    
    return templates.TemplateResponse(
        "deletar_usuario.html",
        {
            "request": request,
            "usuario": usuario,
            "usuario_atual": usuario_atual
        }
    )

@router.post("/usuarios/deletar/{usuario_id}")
async def deletar_usuario(
    usuario_id: int,
    request: Request,
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(obter_usuario_atual)
):
    if not usuario_atual.tem_permissao("gerenciar_usuarios"):
        raise HTTPException(status_code=403, detail="Sem permissão para realizar esta ação")
    
    try:
        usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
        if not usuario:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        
        # Verificar se existem empréstimos ativos
        emprestimos = db.query(models.Emprestimo).filter(
            models.Emprestimo.usuario_id == usuario_id,
            models.Emprestimo.status == "Ativo"
        ).first()
        if emprestimos:
            return templates.TemplateResponse(
                "usuarios.html",
                {
                    "request": request,
                    "error": "Não é possível deletar um usuário com empréstimos ativos",
                    "usuario": usuario_atual
                }
            )
        
        # Verificar se o usuário está deletando a si mesmo
        deletando_proprio_usuario = usuario_id == usuario_atual.id
        
        db.delete(usuario)
        db.commit()
        
        # Se o usuário deletou a si mesmo, redirecionar para o logout
        if deletando_proprio_usuario:
            return RedirectResponse(url="/logout", status_code=status.HTTP_303_SEE_OTHER)
        
        return RedirectResponse(url="/usuarios", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        return templates.TemplateResponse(
            "usuarios.html",
            {
                "request": request,
                "error": f"Erro ao deletar usuário: {str(e)}",
                "usuario": usuario_atual
            }
        ) 