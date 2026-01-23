# Arquitetura Refatorada

## Estrutura do Projeto

O projeto foi refatorado para seguir melhor as práticas de Django com múltiplos apps:

```
safetodo/
├── safetodo/           # Configuração do projeto Django
├── users/                # App de Usuários (compartilhado)
├── tasks/                # App de Tarefas (TODO list)
├── manage.py
├── db.sqlite3
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env
└── README.md
```

## Apps

### users/
App responsável por **gerenciar usuários** que podem acessar todos os demais apps.

**Endpoints:**
- `GET /api/users/` - Listar todos os usuários
- `POST /api/users/register/` - Registrar novo usuário (sem autenticação)
- `GET /api/users/me/` - Dados do usuário autenticado
- `GET /api/users/{id}/` - Detalhes de um usuário específico
- `PUT /api/users/{id}/` - Atualizar usuário
- `DELETE /api/users/{id}/` - Deletar usuário

**Models:**
- `User` - Modelo customizado que estende AbstractUser
  - username, email, first_name, last_name
  - bio, phone (campos adicionais)

### tasks/
App responsável por gerenciar **tarefas (TODO list)** do usuário.

**Endpoints:**
- `GET /api/tasks/` - Listar tarefas do usuário autenticado
- `POST /api/tasks/` - Criar nova tarefa
- `GET /api/tasks/{id}/` - Detalhes da tarefa
- `PUT /api/tasks/{id}/` - Atualizar tarefa
- `DELETE /api/tasks/{id}/` - Deletar tarefa
- `GET /api/tasks/pending/` - Listar tarefas pendentes
- `GET /api/tasks/completed/` - Listar tarefas concluídas

**Models:**
- `Task` - Modelo de tarefa
  - title, description, status, due_date, priority
  - user (ForeignKey para User - cada tarefa pertence a um usuário)

## Autenticação

O projeto usa autenticação baseada em token do Django REST Framework.

### Para registrar um novo usuário:
```bash
POST /api/users/register/
{
  "username": "lucas",
  "email": "lucas@example.com",
  "first_name": "Lucas",
  "last_name": "Silva",
  "password": "senha123",
  "password2": "senha123"
}
```

### Para obter token de autenticação:
```bash
POST /api-auth/login/
{
  "username": "lucas",
  "password": "senha123"
}
```

## Fluxo de Uso

1. **Registrar usuário** → `POST /api/users/register/`
2. **Fazer login** → Obter token de autenticação
3. **Criar tarefas** → `POST /api/tasks/` (com token de autenticação)
4. **Listar tarefas** → `GET /api/tasks/` (apenas do usuário autenticado)
5. **Atualizar/Deletar tarefas** → `PUT/DELETE /api/tasks/{id}/`

## Próximos Passos

O app `tasks` começou como uma TODO list simples, mas pode evoluir para:
- Contas a pagar / Contas a receber
- Transações financeiras
- Relatórios
- Outros módulos financeiros

Cada novo módulo será um app separado dentro do projeto Django.

## Segurança

- Cada usuário só pode ver/modificar suas próprias tarefas
- Autenticação é obrigatória para acessar `/api/users/` e `/api/tasks/`
- O registro de novo usuário é a única operação permitida sem autenticação

## Configurações

As credenciais do banco de dados PostgreSQL devem ser configuradas no arquivo `.env`:
```env
DB_ENGINE=django.db.backends.postgresql
DB_NAME=safetodo_db
DB_USER=postgres
DB_PASSWORD=your_db_password_here
DB_HOST=db
DB_PORT=5432
```
