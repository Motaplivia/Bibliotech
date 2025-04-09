from fastapi import APIRouter, HTTPException, status, Depends, Request, Form
from sqlalchemy.orm import Session
from typing import List
from .. import models, schemas
from ..database import get_db
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from ..main import obter_usuario_atual

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# rotas categorias
@router.get("/categorias")
async def listar_categorias(
    request: Request,
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(obter_usuario_atual)
):
    if not usuario_atual.tem_permissao("gerenciar_categorias"):
        raise HTTPException(status_code=403, detail="Sem permissão para acessar esta página")
    
    categorias = db.query(models.Categoria).all()
    return templates.TemplateResponse(
        "categorias.html",
        {
            "request": request,
            "categorias": categorias,
            "usuario": usuario_atual
        }
    )

@router.get("/categorias/adicionar")
async def adicionar_categoria_form(
    request: Request,
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(obter_usuario_atual)
):
    if not usuario_atual.tem_permissao("gerenciar_categorias"):
        raise HTTPException(status_code=403, detail="Sem permissão para acessar esta página")
    
    return templates.TemplateResponse(
        "adicionar_categoria.html",
        {
            "request": request,
            "usuario": usuario_atual
        }
    )

@router.post("/categorias/adicionar")
async def adicionar_categoria(
    request: Request,
    nome: str = Form(...),
    descricao: str = Form(...),
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(obter_usuario_atual)
):
    if not usuario_atual.tem_permissao("gerenciar_categorias"):
        raise HTTPException(status_code=403, detail="Sem permissão para realizar esta ação")
    
    try:
        # Verificar se já existe uma categoria com este nome
        if db.query(models.Categoria).filter(models.Categoria.nome == nome).first():
            return templates.TemplateResponse(
                "adicionar_categoria.html",
                {
                    "request": request,
                    "error": "Já existe uma categoria com este nome",
                    "usuario": usuario_atual
                }
            )
        
        # Criar nova categoria
        nova_categoria = models.Categoria(
            nome=nome,
            descricao=descricao
        )
        
        db.add(nova_categoria)
        db.commit()
        
        return RedirectResponse(url="/categorias", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        return templates.TemplateResponse(
            "adicionar_categoria.html",
            {
                "request": request,
                "error": f"Erro ao criar categoria: {str(e)}",
                "usuario": usuario_atual
            }
        )

@router.get("/categorias/editar/{categoria_id}")
async def editar_categoria_form(
    categoria_id: int,
    request: Request,
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(obter_usuario_atual)
):
    if not usuario_atual.tem_permissao("gerenciar_categorias"):
        raise HTTPException(status_code=403, detail="Sem permissão para acessar esta página")
    
    categoria = db.query(models.Categoria).filter(models.Categoria.id == categoria_id).first()
    if not categoria:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    
    return templates.TemplateResponse(
        "editar_categoria.html",
        {
            "request": request,
            "categoria": categoria,
            "usuario": usuario_atual
        }
    )

@router.post("/categorias/editar/{categoria_id}")
async def editar_categoria(
    categoria_id: int,
    request: Request,
    nome: str = Form(...),
    descricao: str = Form(...),
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(obter_usuario_atual)
):
    if not usuario_atual.tem_permissao("gerenciar_categorias"):
        raise HTTPException(status_code=403, detail="Sem permissão para realizar esta ação")
    
    try:
        categoria = db.query(models.Categoria).filter(models.Categoria.id == categoria_id).first()
        if not categoria:
            raise HTTPException(status_code=404, detail="Categoria não encontrada")
        
        # Verificar se já existe outra categoria com este nome
        if nome != categoria.nome:
            if db.query(models.Categoria).filter(models.Categoria.nome == nome).first():
                return templates.TemplateResponse(
                    "editar_categoria.html",
                    {
                        "request": request,
                        "categoria": categoria,
                        "error": "Já existe uma categoria com este nome",
                        "usuario": usuario_atual
                    }
                )
        
        # Atualizar dados da categoria
        categoria.nome = nome
        categoria.descricao = descricao
        
        db.commit()
        
        return RedirectResponse(url="/categorias", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        return templates.TemplateResponse(
            "editar_categoria.html",
            {
                "request": request,
                "categoria": categoria,
                "error": f"Erro ao atualizar categoria: {str(e)}",
                "usuario": usuario_atual
            }
        )

@router.get("/categorias/deletar/{categoria_id}")
async def deletar_categoria_form(
    categoria_id: int,
    request: Request,
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(obter_usuario_atual)
):
    if not usuario_atual.tem_permissao("gerenciar_categorias"):
        raise HTTPException(status_code=403, detail="Sem permissão para acessar esta página")
    
    categoria = db.query(models.Categoria).filter(models.Categoria.id == categoria_id).first()
    if not categoria:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    
    # Verificar se existem livros nesta categoria
    livros = db.query(models.Livro).filter(models.Livro.categoria_id == categoria_id).first()
    if livros:
        return templates.TemplateResponse(
            "categorias.html",
            {
                "request": request,
                "error": "Não é possível deletar uma categoria que possui livros",
                "usuario": usuario_atual
            }
        )
    
    return templates.TemplateResponse(
        "deletar_categoria.html",
        {
            "request": request,
            "categoria": categoria,
            "usuario": usuario_atual
        }
    )

@router.post("/categorias/deletar/{categoria_id}")
async def deletar_categoria(
    categoria_id: int,
    request: Request,
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(obter_usuario_atual)
):
    if not usuario_atual.tem_permissao("gerenciar_categorias"):
        raise HTTPException(status_code=403, detail="Sem permissão para realizar esta ação")
    
    try:
        categoria = db.query(models.Categoria).filter(models.Categoria.id == categoria_id).first()
        if not categoria:
            raise HTTPException(status_code=404, detail="Categoria não encontrada")
        
        # Verificar se existem livros nesta categoria
        livros = db.query(models.Livro).filter(models.Livro.categoria_id == categoria_id).first()
        if livros:
            return templates.TemplateResponse(
                "categorias.html",
                {
                    "request": request,
                    "error": "Não é possível deletar uma categoria que possui livros",
                    "usuario": usuario_atual
                }
            )
        
        db.delete(categoria)
        db.commit()
        
        return RedirectResponse(url="/categorias", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        return templates.TemplateResponse(
            "categorias.html",
            {
                "request": request,
                "error": f"Erro ao deletar categoria: {str(e)}",
                "usuario": usuario_atual
            }
        )