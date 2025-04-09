from sqlalchemy import create_engine
from app.models import Base
from app.database import SQLALCHEMY_DATABASE_URL

def update_database():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    update_database()
    print("Banco de dados atualizado com sucesso!") 