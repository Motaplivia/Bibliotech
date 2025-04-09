from fastapi import APIRouter, Depends, HTTPException, Request, Form, status
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from datetime import date, timedelta
from ..auth import obter_usuario_atual
from sqlalchemy.sql import func, text

router = APIRouter(
    prefix="/leitor",
    tags=["leitor"]
)

templates = Jinja2Templates(directory="templates")

@router.get("/livros-disponiveis")
async def listar_livros_disponiveis(
    request: Request,
    busca: str = None,
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(obter_usuario_atual)
):
    # Verificar se o usuário é um leitor
    if usuario_atual.nivel_acesso != "leitor":
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    
    query = db.query(models.Livro).filter(models.Livro.exemplares_disponiveis > 0)
    
    if busca:
        query = query.filter(models.Livro.titulo.ilike(f"%{busca}%"))
    
    livros = query.all()
    return templates.TemplateResponse(
        "leitor/livros_disponiveis.html",
        {
            "request": request,
            "livros": livros,
            "usuario": usuario_atual
        }
    )

@router.get("/livro/{livro_id}")
async def detalhes_livro(
    livro_id: int,
    request: Request,
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(obter_usuario_atual)
):
    # Verificar se o usuário é um leitor
    if usuario_atual.nivel_acesso != "leitor":
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    
    livro = db.query(models.Livro).filter(models.Livro.id == livro_id).first()
    if not livro:
        raise HTTPException(status_code=404, detail="Livro não encontrado")
    
    # Buscar resenhas do livro
    resenhas = db.query(models.Resenha).filter(models.Resenha.livro_id == livro_id).all()
    
    # Verificar se o usuário já tem este livro emprestado
    emprestimo_atual = db.query(models.Emprestimo).filter(
        models.Emprestimo.livro_id == livro_id,
        models.Emprestimo.usuario_id == usuario_atual.id,
        models.Emprestimo.data_devolucao_efetiva == None
    ).first()
    
    return templates.TemplateResponse(
        "leitor/detalhes_livro.html",
        {
            "request": request,
            "livro": livro,
            "resenhas": resenhas,
            "emprestimo_atual": emprestimo_atual,
            "usuario": usuario_atual
        }
    )

# Rota alternativa para acessar detalhes do livro sem o prefixo /leitor
@router.get("/livros/{livro_id}")
async def detalhes_livro_alternativo(
    livro_id: int,
    request: Request,
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(obter_usuario_atual)
):
    return await detalhes_livro(livro_id, request, db, usuario_atual)

@router.post("/livro/{livro_id}/emprestar")
async def emprestar_livro(
    livro_id: int,
    request: Request,
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(obter_usuario_atual)
):
    # Verificar se o usuário é um leitor
    if usuario_atual.nivel_acesso != "leitor":
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    
    livro = db.query(models.Livro).filter(models.Livro.id == livro_id).first()
    if not livro:
        raise HTTPException(status_code=404, detail="Livro não encontrado")
    
    if livro.exemplares_disponiveis <= 0:
        return templates.TemplateResponse(
            "leitor/detalhes_livro.html",
            {
                "request": request,
                "livro": livro,
                "error": "Livro não disponível para empréstimo",
                "usuario": usuario_atual
            }
        )
    
    # Verificar se o usuário pode fazer empréstimos
    if not usuario_atual.pode_fazer_emprestimo():
        return templates.TemplateResponse(
            "leitor/detalhes_livro.html",
            {
                "request": request,
                "livro": livro,
                "error": "Você não pode fazer empréstimos no momento. Verifique se você tem multas pendentes ou atingiu o limite de empréstimos.",
                "usuario": usuario_atual
            }
        )
    
    # Criar novo empréstimo
    novo_emprestimo = models.Emprestimo(
        livro_id=livro_id,
        usuario_id=usuario_atual.id,
        data_emprestimo=date.today(),
        data_devolucao_prevista=date.today() + timedelta(days=14),
        status="Ativo"
    )
    
    # Atualizar quantidade de exemplares disponíveis
    livro.exemplares_disponiveis -= 1
    
    db.add(novo_emprestimo)
    db.commit()
    
    return RedirectResponse(url="/leitor/meus-emprestimos", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/meus-emprestimos")
async def meus_emprestimos(
    request: Request,
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(obter_usuario_atual)
):
    # Verificar se o usuário é um leitor
    if usuario_atual.nivel_acesso != "leitor":
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    
    emprestimos = db.query(models.Emprestimo).filter(
        models.Emprestimo.usuario_id == usuario_atual.id
    ).all()
    
    return templates.TemplateResponse(
        "leitor/meus_emprestimos.html",
        {
            "request": request,
            "emprestimos": emprestimos,
            "usuario": usuario_atual
        }
    )

@router.post("/emprestimo/{emprestimo_id}/renovar")
async def renovar_emprestimo(
    emprestimo_id: int,
    request: Request,
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(obter_usuario_atual)
):
    # Verificar se o usuário é um leitor
    if usuario_atual.nivel_acesso != "leitor":
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    
    emprestimo = db.query(models.Emprestimo).filter(
        models.Emprestimo.id == emprestimo_id,
        models.Emprestimo.usuario_id == usuario_atual.id,
        models.Emprestimo.data_devolucao_efetiva == None
    ).first()
    
    if not emprestimo:
        raise HTTPException(status_code=404, detail="Empréstimo não encontrado")
    
    # Renovar por mais 14 dias
    emprestimo.data_devolucao_prevista = date.today() + timedelta(days=14)
    db.commit()
    
    return RedirectResponse(url="/leitor/meus-emprestimos", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/livro/{livro_id}/resenha")
async def adicionar_resenha(
    livro_id: int,
    request: Request,
    texto: str = Form(...),
    avaliacao: int = Form(...),
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(obter_usuario_atual)
):
    # Verificar se o usuário é um leitor
    if usuario_atual.nivel_acesso != "leitor":
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    
    livro = db.query(models.Livro).filter(models.Livro.id == livro_id).first()
    if not livro:
        raise HTTPException(status_code=404, detail="Livro não encontrado")
    
    # Verificar se o usuário já fez uma resenha para este livro
    resenha_existente = db.query(models.Resenha).filter(
        models.Resenha.livro_id == livro_id,
        models.Resenha.usuario_id == usuario_atual.id
    ).first()
    
    if resenha_existente:
        return templates.TemplateResponse(
            "leitor/detalhes_livro.html",
            {
                "request": request,
                "livro": livro,
                "error": "Você já fez uma resenha para este livro",
                "usuario": usuario_atual
            }
        )
    
    # Criar nova resenha
    nova_resenha = models.Resenha(
        livro_id=livro_id,
        usuario_id=usuario_atual.id,
        texto=texto,
        avaliacao=avaliacao,
        data_criacao=date.today()
    )
    
    db.add(nova_resenha)
    db.commit()
    
    return RedirectResponse(url=f"/leitor/livro/{livro_id}", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/dashboard")
async def dashboard_leitor(
    request: Request,
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(obter_usuario_atual)
):
    # Verificar se o usuário é um leitor
    if usuario_atual.nivel_acesso != "leitor":
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    
    # Obter empréstimos ativos
    emprestimos_ativos = db.query(models.Emprestimo).filter(
        models.Emprestimo.usuario_id == usuario_atual.id,
        models.Emprestimo.data_devolucao_efetiva == None
    ).all()
    
    # Obter empréstimos próximos a vencer (3 dias)
    hoje = date.today()
    emprestimos_proximos_vencer = db.query(models.Emprestimo).filter(
        models.Emprestimo.usuario_id == usuario_atual.id,
        models.Emprestimo.data_devolucao_efetiva == None,
        models.Emprestimo.data_devolucao_prevista <= hoje + timedelta(days=3)
    ).all()
    
    # Obter empréstimos concluídos
    emprestimos_concluidos = db.query(models.Emprestimo).filter(
        models.Emprestimo.usuario_id == usuario_atual.id,
        models.Emprestimo.data_devolucao_efetiva != None
    ).order_by(models.Emprestimo.data_devolucao_efetiva.desc()).all()
    
    # Calcular multa total
    multa_total = sum(emprestimo.calcular_multa() for emprestimo in emprestimos_ativos)
    
    # Obter livros lidos (últimos 5)
    livros_lidos = db.query(
        models.Livro,
        models.Emprestimo.data_devolucao_efetiva
    ).select_from(models.Livro).join(
        models.Emprestimo, models.Emprestimo.livro_id == models.Livro.id
    ).filter(
        models.Emprestimo.usuario_id == usuario_atual.id,
        models.Emprestimo.data_devolucao_efetiva != None
    ).distinct().order_by(models.Emprestimo.data_devolucao_efetiva.desc()).limit(5).all()
    
    # Extrair apenas os livros da consulta
    livros_lidos = [item[0] for item in livros_lidos]
    
    # Obter recomendações baseadas nas categorias favoritas
    categorias_favoritas = db.query(
        models.Categoria.nome,
        func.count(models.Emprestimo.id).label('count')
    ).select_from(models.Categoria).join(
        models.Livro, models.Livro.categoria_id == models.Categoria.id
    ).join(
        models.Emprestimo, models.Emprestimo.livro_id == models.Livro.id
    ).filter(
        models.Emprestimo.usuario_id == usuario_atual.id,
        models.Emprestimo.data_devolucao_efetiva != None
    ).group_by(models.Categoria.id, models.Categoria.nome).order_by(text('count DESC')).limit(3).all()
    
    # Buscar livros recomendados
    recomendacoes = []
    if categorias_favoritas:
        categoria_ids = [cat[0] for cat in categorias_favoritas]
        recomendacoes = db.query(models.Livro).select_from(models.Livro).join(
            models.Categoria, models.Livro.categoria_id == models.Categoria.id
        ).filter(
            models.Categoria.nome.in_(categoria_ids),
            models.Livro.exemplares_disponiveis > 0
        ).distinct().limit(4).all()
    
    return templates.TemplateResponse(
        "leitor/dashboard.html",
        {
            "request": request,
            "usuario": usuario_atual,
            "emprestimos_ativos": emprestimos_ativos,
            "emprestimos_proximos_vencer": emprestimos_proximos_vencer,
            "emprestimos_concluidos": emprestimos_concluidos,
            "multa_total": multa_total,
            "livros_lidos": livros_lidos,
            "recomendacoes": recomendacoes,
            "categorias_favoritas": categorias_favoritas,
            "hoje": hoje
        }
    ) 