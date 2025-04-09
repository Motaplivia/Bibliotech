from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from . import models
from .database import get_db

async def obter_usuario_atual(request: Request, db: Session = Depends(get_db)):
    try:
        usuario_id = request.cookies.get("usuario_id")
        if not usuario_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Não autorizado"
            )
        
        usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuário não encontrado"
            )
        
        if not usuario.ativo:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuário inativo"
            )
        
        return usuario
    except HTTPException:
        raise
    except Exception as e:
        print(f"Erro ao obter usuário atual: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao obter usuário"
        )

async def verificar_permissao(request: Request, db: Session = Depends(get_db), nivel_minimo: str = "admin"):
    try:
        usuario = await obter_usuario_atual(request, db)
        
        # Definir hierarquia de níveis de acesso
        niveis = {
            "leitor": 0,
            "bibliotecario": 1,
            "admin": 2
        }
        
        # Verificar se o nível do usuário é suficiente
        if niveis.get(usuario.nivel_acesso, -1) < niveis.get(nivel_minimo, 999):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissão insuficiente"
            )
        
        return usuario
    except HTTPException:
        raise
    except Exception as e:
        print(f"Erro ao verificar permissão: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao verificar permissão"
        ) 