# SafeTodo

Uma RestAPI desenvolvida com Django e Django REST Framework para gerenciar uma todo list segura.

## Tecnologias

- Django 4.2.8
- Django REST Framework 3.14.0
- Python 3.9+
- SQLite (padrão) ou PostgreSQL

## Instalação

### 1. Clonar o repositório
```bash
git clone <seu-repositorio>
cd safetodo
```

### 2. Criar ambiente virtual
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar dependências
```bash
pip install -r requirements.txt
```

### 4. Configurar variáveis de ambiente
```bash
# Copiar arquivo de exemplo
cp .env.example .env

# Editar .env com suas configurações
```

### 5. Executar migrações
```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Criar superusuário (opcional)
```bash
python manage.py createsuperuser
```

## Executar o servidor

```bash
python manage.py runserver
```

O servidor será iniciado em `http://localhost:8000`

## Estrutura do Projeto

```
safetodo/
├── safetodo/              # Configurações principais do projeto
│   ├── __init__.py
│   ├── settings.py          # Configurações do Django
│   ├── urls.py              # URLs principais
│   ├── asgi.py
│   ├── wsgi.py
├── api/                     # App principal (será criado)
├── manage.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## API Endpoints

A documentação dos endpoints será adicionada conforme as apps forem criadas.

## Desenvolvimento

Para adicionar novas apps:

```bash
python manage.py startapp nome_da_app
```

## Licença

MIT
