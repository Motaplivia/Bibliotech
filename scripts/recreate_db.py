from app.database import recreate_database
from app.models import Base
from app.database import engine

if __name__ == "__main__":
    print("Recriando banco de dados...")
    recreate_database()
    print("Banco de dados recriado com sucesso!") 