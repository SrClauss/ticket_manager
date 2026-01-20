# Ticket Manager

Sistema de gerenciamento de tickets usando FastAPI e MongoDB.

## 📋 Pré-requisitos

- Docker
- Docker Compose

## 🚀 Como executar

1. Clone o repositório:
```bash
git clone https://github.com/SrClauss/ticket_manager.git
cd ticket_manager
```

2. Copie o arquivo de exemplo de variáveis de ambiente:
```bash
cp .env.example .env
```

3. Execute o projeto com Docker Compose:
```bash
docker-compose up --build
```

A API estará disponível em: `http://localhost:8000`

## 📚 Documentação da API

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 🏗️ Estrutura do Projeto

```
ticket_manager/
├── app/
│   ├── __init__.py
│   ├── main.py              # Aplicação FastAPI principal
│   ├── config/
│   │   ├── __init__.py
│   │   └── database.py      # Configuração do MongoDB
│   ├── models/
│   │   ├── __init__.py
│   │   └── ticket.py        # Modelo de dados do Ticket
│   └── routers/
│       ├── __init__.py
│       └── tickets.py       # Rotas da API de tickets
├── requirements.txt         # Dependências Python
├── Dockerfile              # Dockerfile da aplicação
├── docker-compose.yml      # Configuração do Docker Compose
└── .env.example           # Exemplo de variáveis de ambiente
```

## 🔌 Endpoints da API

### Tickets

- `GET /api/tickets/` - Lista todos os tickets
- `GET /api/tickets/{ticket_id}` - Obtém um ticket específico
- `POST /api/tickets/` - Cria um novo ticket
- `PUT /api/tickets/{ticket_id}` - Atualiza um ticket
- `DELETE /api/tickets/{ticket_id}` - Deleta um ticket

### Health Check

- `GET /health` - Verifica o status da API

## 🛠️ Tecnologias Utilizadas

- **FastAPI**: Framework web moderno e rápido para construção de APIs
- **MongoDB**: Banco de dados NoSQL
- **Motor**: Driver assíncrono do MongoDB para Python
- **Pydantic**: Validação de dados
- **Docker**: Containerização da aplicação
- **Uvicorn**: Servidor ASGI

## 📝 Modelo de Dados

### Ticket

```json
{
  "title": "string",
  "description": "string",
  "priority": "low | medium | high | urgent",
  "status": "open | in_progress | resolved | closed",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

## 🔧 Desenvolvimento Local

### Sem Docker

1. Crie um ambiente virtual:
```bash
python -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate
```

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

3. Configure as variáveis de ambiente no arquivo `.env`

4. Execute a aplicação:
```bash
uvicorn app.main:app --reload
```

## 🌐 Variáveis de Ambiente

- `MONGO_USERNAME`: Usuário do MongoDB (padrão: admin)
- `MONGO_PASSWORD`: Senha do MongoDB (padrão: password)
- `MONGO_DATABASE`: Nome do banco de dados (padrão: ticket_manager)
- `MONGODB_URL`: URL de conexão do MongoDB
- `DATABASE_NAME`: Nome do banco de dados

## 📄 Licença

Este projeto é um scaffolding básico para desenvolvimento de aplicações com FastAPI e MongoDB.