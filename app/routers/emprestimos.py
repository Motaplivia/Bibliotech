from fastapi import APIRouter, HTTPException, status, Depends, Request, Form
from sqlalchemy.orm import Session
from typing import List
from .. import models, schemas
from ..database import get_db
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from datetime import date, timedelta
from ..main import obter_usuario_atual

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# rotas empréstimos
@router.get("/emprestimos")
async def listar_emprestimos(
    request: Request,
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(obter_usuario_atual)
):
    if not usuario_atual.tem_permissao("gerenciar_emprestimos"):
        raise HTTPException(status_code=403, detail="Sem permissão para acessar esta página")
    
    emprestimos = db.query(models.Emprestimo).all()
    return templates.TemplateResponse(
        "emprestimos.html",
        {
            "request": request,
            "emprestimos": emprestimos,
            "usuario": usuario_atual
        }
    )

@router.get("/emprestimos/adicionar")
async def adicionar_emprestimo_form(
    request: Request,
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(obter_usuario_atual)
):
    if not usuario_atual.tem_permissao("gerenciar_emprestimos"):
        raise HTTPException(status_code=403, detail="Sem permissão para acessar esta página")
    
    livros = db.query(models.Livro).filter(models.Livro.exemplares_disponiveis > 0).all()
    usuarios = db.query(models.Usuario).filter(models.Usuario.ativo == True).all()
    
    return templates.TemplateResponse(
        "adicionar_emprestimo.html",
        {
            "request": request,
            "livros": livros,
            "usuarios": usuarios,
            "usuario": usuario_atual,
            "data_minima": date.today().strftime('%Y-%m-%d'),
            "data_maxima": (date.today() + timedelta(days=30)).strftime('%Y-%m-%d')
        }
    )

@router.post("/emprestimos/adicionar")
async def adicionar_emprestimo(
    request: Request,
    livro_id: int = Form(...),
    usuario_id: int = Form(...),
    data_devolucao_prevista: str = Form(...),
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(obter_usuario_atual)
):
    if not usuario_atual.tem_permissao("gerenciar_emprestimos"):
        raise HTTPException(status_code=403, detail="Sem permissão para realizar esta ação")
    
    try:
        # Verificar se o livro existe e está disponível
        livro = db.query(models.Livro).filter(models.Livro.id == livro_id).first()
        if not livro or livro.exemplares_disponiveis <= 0:
            raise HTTPException(status_code=400, detail="Livro não disponível para empréstimo")
        
        # Verificar se o usuário existe e está ativo
        usuario = db.query(models.Usuario).filter(
            models.Usuario.id == usuario_id,
            models.Usuario.ativo == True
        ).first()
        if not usuario:
            raise HTTPException(status_code=400, detail="Usuário não encontrado ou inativo")
        
        # Verificar se o usuário pode fazer empréstimos
        if not usuario.pode_fazer_emprestimo():
            return templates.TemplateResponse(
                "adicionar_emprestimo.html",
                {
                    "request": request,
                    "error": "Usuário não pode fazer empréstimos. Verifique se tem multas pendentes ou atingiu o limite de empréstimos.",
                    "usuario": usuario_atual,
                    "livros": db.query(models.Livro).filter(models.Livro.exemplares_disponiveis > 0).all(),
                    "usuarios": db.query(models.Usuario).filter(models.Usuario.ativo == True).all(),
                    "data_minima": date.today().strftime('%Y-%m-%d'),
                    "data_maxima": (date.today() + timedelta(days=30)).strftime('%Y-%m-%d')
                }
            )
        
        # Criar novo empréstimo
        novo_emprestimo = models.Emprestimo(
            livro_id=livro_id,
            usuario_id=usuario_id,
            data_emprestimo=date.today(),
            data_devolucao_prevista=date.fromisoformat(data_devolucao_prevista),
            status="Ativo",
            renovacoes_feitas=0
        )
        
        # Atualizar quantidade de exemplares disponíveis
        livro.exemplares_disponiveis -= 1
        
        db.add(novo_emprestimo)
        db.commit()
        
        return RedirectResponse(url="/emprestimos", status_code=status.HTTP_303_SEE_OTHER)
    except ValueError as e:
        return templates.TemplateResponse(
            "adicionar_emprestimo.html",
            {
                "request": request,
                "error": "Data de devolução inválida",
                "usuario": usuario_atual,
                "livros": db.query(models.Livro).filter(models.Livro.exemplares_disponiveis > 0).all(),
                "usuarios": db.query(models.Usuario).filter(models.Usuario.ativo == True).all(),
                "data_minima": date.today().strftime('%Y-%m-%d'),
                "data_maxima": (date.today() + timedelta(days=30)).strftime('%Y-%m-%d')
            }
        )
    except Exception as e:
        return templates.TemplateResponse(
            "adicionar_emprestimo.html",
            {
                "request": request,
                "error": f"Erro ao criar empréstimo: {str(e)}",
                "usuario": usuario_atual,
                "livros": db.query(models.Livro).filter(models.Livro.exemplares_disponiveis > 0).all(),
                "usuarios": db.query(models.Usuario).filter(models.Usuario.ativo == True).all(),
                "data_minima": date.today().strftime('%Y-%m-%d'),
                "data_maxima": (date.today() + timedelta(days=30)).strftime('%Y-%m-%d')
            }
        )

@router.post("/emprestimos/{emprestimo_id}/devolver")
async def devolver_emprestimo(
    emprestimo_id: int,
    request: Request,
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(obter_usuario_atual)
):
    if not usuario_atual.tem_permissao("gerenciar_emprestimos"):
        raise HTTPException(status_code=403, detail="Sem permissão para realizar esta ação")
    
    emprestimo = db.query(models.Emprestimo).filter(models.Emprestimo.id == emprestimo_id).first()
    if not emprestimo:
        raise HTTPException(status_code=404, detail="Empréstimo não encontrado")
    
    if emprestimo.status != "Ativo":
        return templates.TemplateResponse(
            "emprestimos.html",
            {
                "request": request,
                "error": "Este empréstimo já foi devolvido",
                "emprestimos": db.query(models.Emprestimo).all(),
                "usuario": usuario_atual
            }
        )
    
    # Calcular multa se houver atraso
    emprestimo.calcular_multa()
    if emprestimo.multa > 0:
        emprestimo.usuario.multas_pendentes += emprestimo.multa
    
    # Realizar a devolução
    emprestimo.devolver()
    db.commit()
    
    return RedirectResponse(url="/emprestimos", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/leitor/emprestimo/{emprestimo_id}/renovar")
async def renovar_emprestimo(
    emprestimo_id: int,
    request: Request,
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(obter_usuario_atual)
):
    if usuario_atual.nivel_acesso != "leitor":
        raise HTTPException(status_code=403, detail="Apenas leitores podem renovar empréstimos")
    
    emprestimo = db.query(models.Emprestimo).filter(
        models.Emprestimo.id == emprestimo_id,
        models.Emprestimo.usuario_id == usuario_atual.id
    ).first()
    
    if not emprestimo:
        raise HTTPException(status_code=404, detail="Empréstimo não encontrado")
    
    if not emprestimo.pode_renovar():
        return templates.TemplateResponse(
            "leitor/meus_emprestimos.html",
            {
                "request": request,
                "error": "Não é possível renovar este empréstimo",
                "emprestimos": db.query(models.Emprestimo).filter(
                    models.Emprestimo.usuario_id == usuario_atual.id
                ).all(),
                "usuario": usuario_atual
            }
        )
    
    emprestimo.renovar()
    db.commit()
    
    return RedirectResponse(url="/leitor/meus-emprestimos", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/emprestimos/{emprestimo_id}")
async def detalhes_emprestimo(
    emprestimo_id: int,
    request: Request,
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(obter_usuario_atual)
):
    if not usuario_atual.tem_permissao("gerenciar_emprestimos"):
        raise HTTPException(status_code=403, detail="Sem permissão para acessar esta página")
    
    emprestimo = db.query(models.Emprestimo).filter(models.Emprestimo.id == emprestimo_id).first()
    if emprestimo is None:
        raise HTTPException(status_code=404, detail="Empréstimo não encontrado")
    
    return templates.TemplateResponse(
        "detalhes_emprestimo.html",
        {
            "request": request,
            "emprestimo": emprestimo,
            "usuario": usuario_atual
        }
    )

@router.get("/emprestimos/{emprestimo_id}", response_model=schemas.Emprestimo)
def get_emprestimo(emprestimo_id: int, db: Session = Depends(get_db)):
    emprestimo = db.query(models.Emprestimo).filter(models.Emprestimo.id == emprestimo_id).first()
    if emprestimo is None:
        raise HTTPException(status_code=404, detail="Empréstimo não encontrado.")
    return emprestimo

@router.put("/emprestimos/{emprestimo_id}", response_model=schemas.Emprestimo)
def update_emprestimo(emprestimo_id: int, updated_emprestimo: schemas.EmprestimoCreate, db: Session = Depends(get_db)):
    emprestimo = db.query(models.Emprestimo).filter(models.Emprestimo.id == emprestimo_id).first()
    if emprestimo is None:
        raise HTTPException(status_code=404, detail="Empréstimo não encontrado.")
    
    # Se o status está mudando para "Devolvido", atualizar exemplares disponíveis
    if updated_emprestimo.status == "Devolvido" and emprestimo.status != "Devolvido":
        livro = db.query(models.Livro).filter(models.Livro.id == emprestimo.livro_id).first()
        livro.exemplares_disponiveis = min(livro.quantidade, livro.exemplares_disponiveis + 1)
    
    for key, value in updated_emprestimo.dict(exclude_unset=True).items():
        setattr(emprestimo, key, value)
    
    db.commit()
    db.refresh(emprestimo)
    return emprestimo

@router.delete("/emprestimos/{emprestimo_id}", response_model=dict, status_code=status.HTTP_200_OK)
def delete_emprestimo(emprestimo_id: int, db: Session = Depends(get_db)):
    emprestimo = db.query(models.Emprestimo).filter(models.Emprestimo.id == emprestimo_id).first()
    if emprestimo is None:
        raise HTTPException(status_code=404, detail="Empréstimo não encontrado.")
    db.delete(emprestimo)
    db.commit()
    return {"message": f"Empréstimo com ID {emprestimo_id} deletado com sucesso."}
