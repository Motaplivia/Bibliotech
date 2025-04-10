from fastapi import FastAPI, Request, Depends, HTTPException, status, Form
from app import models
from .database import engine, get_db
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from fastapi.responses import RedirectResponse
from . import schemas
from fastapi.middleware.cors import CORSMiddleware
from datetime import date, datetime, timedelta
from passlib.context import CryptContext
from sqlalchemy.sql import func, text
from fastapi.staticfiles import StaticFiles
from .auth import obter_usuario_atual

from .routers.livros import router as routerLivros
from .routers.categorias import router as routerCategorias
from .routers.emprestimos import router as routerEmprestimos
from .routers.usuarios import router as routerUsuarios
from .routers.leitor import router as routerLeitor

# Configuração de segurança
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Criar as tabelas no banco de dados
models.Base.metadata.create_all(bind=engine)

# Criar usuário administrador inicial
def criar_admin_inicial():
    db = next(get_db())
    try:
        # Verificar se já existe algum usuário admin
        admin = db.query(models.Usuario).filter(models.Usuario.nivel_acesso == "admin").first()
        if not admin:
            admin = models.Usuario(
                nome="Administrador",
                email="admin@biblioteca.com",
                senha_hash=pwd_context.hash("admin123"),
                nivel_acesso="admin",
                ativo=True
            )
            db.add(admin)
            db.commit()
            print("Usuário administrador criado com sucesso!")
    except Exception as e:
        print(f"Erro ao criar usuário administrador: {str(e)}")
    finally:
        db.close()

criar_admin_inicial()

templates = Jinja2Templates(directory="templates")

app = FastAPI(title="Sistema de Biblioteca")

# Configuração CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montar diretório de arquivos estáticos
app.mount("/static", StaticFiles(directory="static"), name="static")

# Incluir routers
app.include_router(routerLivros)
app.include_router(routerCategorias)
app.include_router(routerEmprestimos)
app.include_router(routerUsuarios)
app.include_router(routerLeitor)

@app.get("/")
async def index(request: Request):
    try:
        # Tentar obter o usuário atual
        db = next(get_db())
        usuario = await obter_usuario_atual(request, db)
        # Se conseguir obter o usuário, redirecionar para o dashboard
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    except:
        # Se não conseguir obter o usuário, redirecionar para a landing page
        return RedirectResponse(url="/landing", status_code=status.HTTP_302_FOUND)

@app.get("/landing")
async def landing_page(request: Request):
    return templates.TemplateResponse("landing.html", {"request": request})

@app.get("/dashboard")
async def dashboard(request: Request, db: Session = Depends(get_db)):
    try:
        usuario = await obter_usuario_atual(request, db)
        
        # Redirecionar para a dashboard apropriada baseado no nível de acesso
        if usuario.nivel_acesso == "leitor":
            return RedirectResponse(url="/leitor/dashboard", status_code=status.HTTP_302_FOUND)
        
        # Se não for leitor, mostrar dashboard do admin
        # Estatísticas
        total_livros = db.query(func.count(models.Livro.id)).scalar()
        total_categorias = db.query(func.count(models.Categoria.id)).scalar()
        emprestimos_ativos = db.query(func.count(models.Emprestimo.id)).filter(models.Emprestimo.data_devolucao_efetiva == None).scalar()
        emprestimos_atrasados = db.query(func.count(models.Emprestimo.id)).filter(
            models.Emprestimo.data_devolucao_efetiva == None,
            models.Emprestimo.data_devolucao_prevista < func.current_date()
        ).scalar()

        # Livros mais emprestados
        livros_mais_emprestados = db.query(
            models.Livro.titulo,
            func.count(models.Emprestimo.id).label('total_emprestimos')
        ).join(models.Emprestimo).group_by(models.Livro.id).order_by(text('total_emprestimos DESC')).limit(5).all()

        # Categorias populares
        categorias_populares = db.query(
            models.Categoria.nome,
            func.count(models.Emprestimo.id).label('total_emprestimos')
        ).join(
            models.Livro, models.Livro.categoria_id == models.Categoria.id
        ).join(
            models.Emprestimo, models.Emprestimo.livro_id == models.Livro.id
        ).group_by(
            models.Categoria.id, models.Categoria.nome
        ).order_by(text('total_emprestimos DESC')).limit(5).all()
        
        # Empréstimos recentes (últimos 5)
        emprestimos_recentes = db.query(models.Emprestimo).order_by(models.Emprestimo.data_emprestimo.desc()).limit(5).all()
        
        # Marcar empréstimos atrasados
        for emprestimo in emprestimos_recentes:
            if emprestimo.data_devolucao_efetiva is None and emprestimo.data_devolucao_prevista < date.today():
                emprestimo.atrasado = True
            else:
                emprestimo.atrasado = False

        # Obter dados de empréstimos por mês (últimos 6 meses)
        hoje = date.today()
        seis_meses_atras = hoje - timedelta(days=180)
        
        # Consulta para empréstimos
        emprestimos_por_mes = db.query(
            func.date_trunc('month', models.Emprestimo.data_emprestimo).label('mes'),
            func.count(models.Emprestimo.id).label('total')
        ).filter(
            models.Emprestimo.data_emprestimo >= seis_meses_atras
        ).group_by(
            func.date_trunc('month', models.Emprestimo.data_emprestimo)
        ).order_by('mes').all()

        # Consulta para devoluções
        devolucoes_por_mes = db.query(
            func.date_trunc('month', models.Emprestimo.data_devolucao_efetiva).label('mes'),
            func.count(models.Emprestimo.id).label('total')
        ).filter(
            models.Emprestimo.data_devolucao_efetiva >= seis_meses_atras,
            models.Emprestimo.data_devolucao_efetiva.isnot(None)
        ).group_by(
            func.date_trunc('month', models.Emprestimo.data_devolucao_efetiva)
        ).order_by('mes').all()

        # Preparar dados para o gráfico
        meses = []
        emprestimos = []
        devolucoes = []

        # Preencher os últimos 6 meses
        for i in range(6):
            data = hoje - timedelta(days=30*i)
            mes = data.replace(day=1)
            meses.insert(0, mes.strftime('%b/%Y'))
            
            # Buscar total de empréstimos para este mês
            total_emp = next((item[1] for item in emprestimos_por_mes if item[0].month == mes.month and item[0].year == mes.year), 0)
            emprestimos.insert(0, total_emp)
            
            # Buscar total de devoluções para este mês
            total_dev = next((item[1] for item in devolucoes_por_mes if item[0].month == mes.month and item[0].year == mes.year), 0)
            devolucoes.insert(0, total_dev)

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "usuario": usuario,
                "total_livros": total_livros,
                "total_categorias": total_categorias,
                "emprestimos_ativos": emprestimos_ativos,
                "emprestimos_atrasados": emprestimos_atrasados,
                "livros_mais_emprestados": {
                    "labels": [livro[0] for livro in livros_mais_emprestados],
                    "data": [livro[1] for livro in livros_mais_emprestados]
                },
                "categorias_populares": {
                    "labels": [categoria[0] for categoria in categorias_populares],
                    "data": [categoria[1] for categoria in categorias_populares]
                },
                "emprestimos_recentes": emprestimos_recentes,
                "grafico_emprestimos": {
                    "meses": meses,
                    "emprestimos": emprestimos,
                    "devolucoes": devolucoes
                }
            }
        )
    except HTTPException:
        # Se houver erro de autenticação, redirecionar para o login
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    except Exception as e:
        print(f"Erro no dashboard: {str(e)}")
        # Se houver outro erro, redirecionar para o login
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

@app.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    senha: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        print(f"Tentativa de login para o email: {email}")  # Log do email
        
        # Buscar usuário no banco
        usuario = db.query(models.Usuario).filter(models.Usuario.email == email).first()
        
        if not usuario:
            print("Usuário não encontrado")  # Log de erro
            return templates.TemplateResponse(
                "login.html",
                {
                    "request": request,
                    "error": "Email ou senha incorretos"
                }
            )
        
        print(f"Usuário encontrado: {usuario.nome}, Nível: {usuario.nivel_acesso}")  # Log do usuário
        
        if not pwd_context.verify(senha, usuario.senha_hash):
            print("Senha incorreta")  # Log de erro
            return templates.TemplateResponse(
                "login.html",
                {
                    "request": request,
                    "error": "Email ou senha incorretos"
                }
            )
        
        # Verificar se o usuário está ativo
        if not usuario.ativo:
            print("Usuário inativo")  # Log de erro
            return templates.TemplateResponse(
                "login.html",
                {
                    "request": request,
                    "error": "Usuário inativo. Entre em contato com o administrador."
                }
            )
        
        # Criar resposta com redirecionamento
        response = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
        
        # Definir cookie com o ID do usuário
        response.set_cookie(
            key="usuario_id",
            value=str(usuario.id),
            httponly=True,
            samesite="lax",
            max_age=3600  # 1 hora
        )
        print("Cookie definido com sucesso")  # Log de sucesso
        
        return response
        
    except Exception as e:
        print(f"Erro no login: {str(e)}")  # Log detalhado do erro
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error": "Erro ao fazer login. Tente novamente."
            }
        )

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/landing", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(key="usuario_id")
    return response

