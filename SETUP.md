# Guia de Instalação e Setup da API Fiscal

## ✅ Projeto criado com sucesso!

A estrutura da aplicação Django RestAPI foi criada em:
```
c:\Users\Lucas\Documents\Projetos\api-fiscal
```

## 📋 Próximos Passos

### 1. Instalar Python (se não tiver)
- Baixe de: https://www.python.org/downloads/
- **IMPORTANTE**: Marque a opção "Add Python to PATH" durante a instalação

### 2. Criar Ambiente Virtual
```powershell
cd c:\Users\Lucas\Documents\Projetos\api-fiscal
python -m venv venv
```

### 3. Ativar Ambiente Virtual
```powershell
# Windows
venv\Scripts\activate

# Você deve ver (venv) no início da linha
```

### 4. Instalar Dependências
```powershell
pip install -r requirements.txt
```

### 5. Aplicar Migrações
```powershell
python manage.py migrate
```

### 6. Criar Superusuário (opcional)
```powershell
python manage.py createsuperuser
```

### 7. Iniciar o Servidor
```powershell
python manage.py runserver
```

Acesse em: http://localhost:8000

## 📁 Estrutura do Projeto

```
api-fiscal/
├── api_fiscal/              # Configurações do projeto
│   ├── settings.py          # Configurações Django
│   ├── urls.py              # URLs principais
│   ├── wsgi.py
│   └── asgi.py
├── api/                     # App principal
│   ├── models.py            # Modelos de dados
│   ├── serializers.py       # Serializadores REST
│   ├── views.py             # Views e ViewSets
│   ├── urls.py              # URLs da app
│   └── migrations/
├── manage.py
├── requirements.txt
├── .env.example             # Variáveis de ambiente
├── .gitignore
└── README.md
```

## 🔑 Configuração de Variáveis de Ambiente

1. Copie `.env.example` para `.env`:
```powershell
copy .env.example .env
```

2. Edite `.env` com suas configurações específicas

## 🚀 Endpoint de Teste

Após iniciar o servidor, teste em:
```
GET http://localhost:8000/api/health/
```

Esperado:
```json
{
  "status": "API Fiscal funcionando!"
}
```

## 📚 Documentação Adicional

- Django: https://docs.djangoproject.com/
- Django REST Framework: https://www.django-rest-framework.org/
- Decouple: https://github.com/henriquebastos/python-decouple

## ✨ Próximos Passos Recomendados

1. Criar apps específicas para suas funcionalidades
2. Definir modelos de dados
3. Criar serializers
4. Implementar viewsets
5. Documentar endpoints

Qualquer dúvida, é só chamar!
