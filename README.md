# SafeTodo - Backend

API em Django + Django REST Framework para tarefas, usuários e equipes.

## Tecnologias
- Python 3.12 (imagem Docker)
- Django 4.2.8
- Django REST Framework
- PostgreSQL (via Docker)
- SimpleJWT (JWT)

## Executar com Docker (recomendado)
```bash
cd api-fiscal
docker compose up -d --build
```

Aplicará:
- Banco PostgreSQL em `localhost:5432`
- API em `http://localhost:8000`

### Migrar e seed
```bash
docker compose exec web python manage.py migrate
docker compose exec web python manage.py seed_users
```

### Logs
```bash
docker compose logs -f web
```

### Resetar banco
```bash
docker compose down -v
docker compose up -d --build
docker compose exec web python manage.py migrate
docker compose exec web python manage.py seed_users
```

## Executar local (sem Docker)
```bash
cd api-fiscal
python -m venv .venv
.venv\Scripts\Activate.ps1   # Windows
# source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_users
python manage.py runserver
```

## Variáveis de ambiente
Arquivo `.env` (veja `.env.example`):
- `DEBUG`
- `SECRET_KEY`
- `DB_ENGINE`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `DB_HOST`
- `DB_PORT`
- `ALLOWED_HOSTS`
- `CORS_ALLOWED_ORIGINS`

## Endpoints principais
- `POST /api/users/login/` (JWT)
- `GET /api/users/me/`
- `GET /api/users/choices/` (opções simples de usuários)
- `GET /api/tasks/`
- `GET /api/teams/`
- `GET /api/teams/{id}/tasks/`

## Observações
- As rotas de tarefas são protegidas por autenticação.
- A lógica de permissões usa groups e managers por equipe.
