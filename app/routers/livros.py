from fastapi import APIRouter, HTTPException, status, Depends, Request, Form, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from .. import models, schemas
from ..database import get_db
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from datetime import datetime, date
import os
import shutil
from ..main import obter_usuario_atual

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# Configuração para upload de imagens
UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# rotas livros
@router.get("/livros")
async def listar_livros(
    request: Request,
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(obter_usuario_atual)
):
    if not usuario_atual.tem_permissao("gerenciar_livros"):
        raise HTTPException(status_code=403, detail="Sem permissão para acessar esta página")
    
    livros = db.query(models.Livro).all()
    return templates.TemplateResponse(
        "livros.html",
        {
            "request": request,
            "livros": livros,
            "usuario": usuario_atual
        }
    )

# Rota para adicionar livro (deve vir antes da rota com parâmetro)
@router.get("/livros/adicionar")
async def adicionar_livro_form(
    request: Request,
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(obter_usuario_atual)
):
    if not usuario_atual.tem_permissao("gerenciar_livros"):
        raise HTTPException(status_code=403, detail="Sem permissão para acessar esta página")
    
    categorias = db.query(models.Categoria).all()
    return templates.TemplateResponse(
        "adicionar_livro.html",
        {
            "request": request,
            "categorias": categorias,
            "usuario": usuario_atual,
            "error": None,
            "ano_atual": date.today().year
        }
    )

@router.post("/livros/adicionar")
async def adicionar_livro(
    request: Request,
    titulo: str = Form(...),
    autor: str = Form(...),
    ano_publicacao: int = Form(...),
    isbn: str = Form(...),
    quantidade: int = Form(...),
    categoria_id: int = Form(...),
    descricao: str = Form(...),
    numero_paginas: int = Form(...),
    imagem: UploadFile = File(None),
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(obter_usuario_atual)
):
    if not usuario_atual.tem_permissao("gerenciar_livros"):
        raise HTTPException(status_code=403, detail="Sem permissão para realizar esta ação")
    
    try:
        # Validar ISBN único
        livro_existente = db.query(models.Livro).filter(models.Livro.isbn == isbn).first()
        if livro_existente:
            categorias = db.query(models.Categoria).all()
            return templates.TemplateResponse(
                "adicionar_livro.html",
                {
                    "request": request,
                    "error": "Já existe um livro cadastrado com este ISBN",
                    "categorias": categorias,
                    "usuario": usuario_atual
                }
            )

        # Processar imagem se fornecida
        imagem_url = None
        if imagem and imagem.filename:
            try:
                # Validar tipo de arquivo
                content_type = imagem.content_type
                if not content_type.startswith('image/'):
                    raise ValueError("O arquivo deve ser uma imagem")

                # Gerar nome único para o arquivo
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{timestamp}_{imagem.filename}"
                filepath = os.path.join(UPLOAD_DIR, filename)
                
                # Garantir que o diretório existe
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                
                # Salvar arquivo
                with open(filepath, "wb") as buffer:
                    shutil.copyfileobj(imagem.file, buffer)
                
                imagem_url = f"/static/uploads/{filename}"
            except Exception as e:
                print(f"Erro ao processar imagem: {str(e)}")
                # Continuar sem a imagem em caso de erro
                pass
        
        # Criar novo livro
        novo_livro = models.Livro(
            titulo=titulo,
            autor=autor,
            ano_publicacao=ano_publicacao,
            isbn=isbn,
            quantidade=quantidade,
            exemplares_disponiveis=quantidade,
            categoria_id=categoria_id,
            descricao=descricao,
            numero_paginas=numero_paginas,
            imagem_url=imagem_url,
            data_cadastro=datetime.now()
        )
        
        db.add(novo_livro)
        db.commit()
        db.refresh(novo_livro)
        
        return RedirectResponse(url="/livros", status_code=status.HTTP_303_SEE_OTHER)
    except ValueError as e:
        categorias = db.query(models.Categoria).all()
        return templates.TemplateResponse(
            "adicionar_livro.html",
            {
                "request": request,
                "error": str(e),
                "categorias": categorias,
                "usuario": usuario_atual
            }
        )
    except Exception as e:
        print(f"Erro ao criar livro: {str(e)}")
        categorias = db.query(models.Categoria).all()
        return templates.TemplateResponse(
            "adicionar_livro.html",
            {
                "request": request,
                "error": "Erro ao criar livro. Por favor, tente novamente.",
                "categorias": categorias,
                "usuario": usuario_atual
            }
        )

# Rotas com parâmetros devem vir depois das rotas específicas
@router.get("/livros/{livro_id}")
async def detalhes_livro(
    livro_id: int,
    request: Request,
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(obter_usuario_atual)
):
    if not usuario_atual.tem_permissao("gerenciar_livros"):
        raise HTTPException(status_code=403, detail="Sem permissão para acessar esta página")
    
    livro = db.query(models.Livro).filter(models.Livro.id == livro_id).first()
    if livro is None:
        raise HTTPException(status_code=404, detail="Livro não encontrado")
    
    return templates.TemplateResponse(
        "detalhes_livro.html",
        {
            "request": request,
            "livro": livro,
            "usuario": usuario_atual
        }
    )

@router.get("/livros/editar/{livro_id}")
async def editar_livro_form(
    livro_id: int,
    request: Request,
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(obter_usuario_atual)
):
    if not usuario_atual.tem_permissao("gerenciar_livros"):
        raise HTTPException(status_code=403, detail="Sem permissão para acessar esta página")
    
    livro = db.query(models.Livro).filter(models.Livro.id == livro_id).first()
    if livro is None:
        raise HTTPException(status_code=404, detail="Livro não encontrado")
    
    categorias = db.query(models.Categoria).all()
    return templates.TemplateResponse(
        "editar_livro.html",
        {
            "request": request,
            "livro": livro,
            "categorias": categorias,
            "usuario": usuario_atual
        }
    )

@router.post("/livros/editar/{livro_id}")
async def editar_livro(
    livro_id: int,
    request: Request,
    titulo: str = Form(...),
    autor: str = Form(...),
    ano_publicacao: int = Form(...),
    isbn: str = Form(...),
    quantidade: int = Form(...),
    categoria_id: int = Form(...),
    descricao: str = Form(...),
    numero_paginas: int = Form(...),
    imagem: UploadFile = File(None),
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(obter_usuario_atual)
):
    if not usuario_atual.tem_permissao("gerenciar_livros"):
        raise HTTPException(status_code=403, detail="Sem permissão para realizar esta ação")
    
    try:
        livro = db.query(models.Livro).filter(models.Livro.id == livro_id).first()
        if livro is None:
            raise HTTPException(status_code=404, detail="Livro não encontrado")
        
        # Processar nova imagem se fornecida
        if imagem:
            # Gerar nome único para o arquivo
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{imagem.filename}"
            filepath = os.path.join(UPLOAD_DIR, filename)
            
            # Salvar novo arquivo
            with open(filepath, "wb") as buffer:
                shutil.copyfileobj(imagem.file, buffer)
            
            # Remover imagem antiga se existir
            if livro.imagem_url:
                old_filepath = os.path.join("static", livro.imagem_url.lstrip("/"))
                if os.path.exists(old_filepath):
                    os.remove(old_filepath)
            
            livro.imagem_url = f"/static/uploads/{filename}"
        
        # Atualizar dados do livro
        livro.titulo = titulo
        livro.autor = autor
        livro.ano_publicacao = ano_publicacao
        livro.isbn = isbn
        livro.quantidade = quantidade
        livro.exemplares_disponiveis = max(0, quantidade - (livro.quantidade - livro.exemplares_disponiveis))
        livro.categoria_id = categoria_id
        livro.descricao = descricao
        livro.numero_paginas = numero_paginas
        
        db.commit()
        db.refresh(livro)
        
        return RedirectResponse(url="/livros", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        print(f"Erro ao atualizar livro: {str(e)}")
        return templates.TemplateResponse(
            "editar_livro.html",
            {
                "request": request,
                "livro": livro,
                "error": "Erro ao atualizar livro",
                "usuario": usuario_atual
            }
        )

@router.get("/livros/deletar/{livro_id}")
async def deletar_livro_form(
    livro_id: int,
    request: Request,
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(obter_usuario_atual)
):
    if not usuario_atual.tem_permissao("gerenciar_livros"):
        raise HTTPException(status_code=403, detail="Sem permissão para acessar esta página")
    
    livro = db.query(models.Livro).filter(models.Livro.id == livro_id).first()
    if livro is None:
        raise HTTPException(status_code=404, detail="Livro não encontrado")
    
    return templates.TemplateResponse(
        "deletar_livro.html",
        {
            "request": request,
            "livro": livro,
            "usuario": usuario_atual
        }
    )

@router.post("/livros/deletar/{livro_id}")
async def deletar_livro(
    livro_id: int,
    request: Request,
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(obter_usuario_atual)
):
    if not usuario_atual.tem_permissao("gerenciar_livros"):
        raise HTTPException(status_code=403, detail="Sem permissão para realizar esta ação")
    
    try:
        livro = db.query(models.Livro).filter(models.Livro.id == livro_id).first()
        if livro is None:
            raise HTTPException(status_code=404, detail="Livro não encontrado")
        
        # Remover imagem se existir
        if livro.imagem_url:
            filepath = os.path.join("static", livro.imagem_url.lstrip("/"))
            if os.path.exists(filepath):
                os.remove(filepath)
        
        db.delete(livro)
        db.commit()
        
        return RedirectResponse(url="/livros", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        print(f"Erro ao deletar livro: {str(e)}")
        return templates.TemplateResponse(
            "deletar_livro.html",
            {
                "request": request,
                "livro": livro,
                "error": "Erro ao deletar livro",
                "usuario": usuario_atual
            }
        )



