# Interface Gráfica Biblioteca API

---

## Como Clonar

1. **Clone o Repositório**:
   - No terminal, execute o comando abaixo para clonar o projeto:   
   ```
   https://github.com/Motaplivia/biblioteca.git
   ```

2. **Crie e Ative um Ambiente Virtual**:
   - Com o diretório do projeto aberto crie o ambiente virtual com o comando abaixo:
    ```bash
      python -m venv venv
     ```
      - Para ativar
          - No windows:
            ```bash
              venv\Scripts\activate
             ```
          - No Linux/macOS:
            ```bash
              source venv/bin/activate
             ```

4. **Instale as Dependências**:
    ```bash
    pip install -r requirements.txt
    ```
     
5. **Execute a API**:
     ```bash
     uvicorn app.main:app --reload
     ```

---

