from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base, Usuario, NivelAcesso
from app.database import SQLALCHEMY_DATABASE_URL, SessionLocal
from passlib.context import CryptContext

# Configuração de segurança
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def criar_admin():
    db = SessionLocal()
    try:
        # Verificar se já existe um admin
        admin = db.query(Usuario).filter(Usuario.email == "admin@biblioteca.com").first()
        if admin:
            print("Usuário administrador já existe!")
            return

        # Criar novo admin
        admin = Usuario(
            nome="Administrador",
            email="admin@biblioteca.com",
            senha_hash=pwd_context.hash("admin123"),
            nivel_acesso=NivelAcesso.ADMIN.value,
            ativo=True
        )
        
        db.add(admin)
        db.commit()
        print("Usuário administrador criado com sucesso!")
        print("Email: admin@biblioteca.com")
        print("Senha: admin123")
        
    except Exception as e:
        print(f"Erro ao criar usuário administrador: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    criar_admin() 