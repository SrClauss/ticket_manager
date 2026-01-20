# EventMaster API

Sistema completo de gerenciamento de eventos com controle de acesso e emissão de ingressos usando FastAPI e MongoDB.

## 📋 Visão Geral

O EventMaster API é uma solução backend para gestão de eventos que oferece:

- **Gerenciamento de Eventos**: CRUD completo de eventos com configuração de layout personalizável
- **Controle de Acesso por Setores (Ilhas)**: Defina áreas e permissões de acesso
- **Tipos de Ingresso Flexíveis**: Configure diferentes categorias com permissões específicas
- **Bilheteria Digital**: Emissão de ingressos com QR Code único
- **Validação de Acesso**: Sistema de portaria com verificação de permissões
- **Coleta de Leads**: Rastreie interações de participantes durante o evento
- **Relatórios e Exportação**: Análise de vendas e exportação de leads

## 🏗️ Arquitetura de Dados

### Entidades Principais

**Evento**
- id, nome, descrição, data_criacao, data_evento
- token_bilheteria: Hash único para acesso de vendedores
- token_portaria: Hash único para dispositivos de validação
- layout_ingresso: Campo JSON flexível para layout de impressão

**Ilha (Setor)**
- id, nome_setor, capacidade_maxima
- Sub-entidade vinculada a eventos

**Tipo de Ingresso**
- id, evento_id, descricao (ex: VIP, Pista), valor
- permissoes: Lista de IDs das Ilhas com acesso permitido

**Participante/Lead**
- id, nome, email, telefone, empresa, cargo

**Ingresso Emitido**
- id, evento_id, tipo_ingresso_id, participante_id
- status (Ativo/Cancelado), qrcode_hash

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

## 🔐 Autenticação

O sistema utiliza três tipos de autenticação baseada em tokens:

### 1. Acesso Administrativo
- Header: `X-Admin-Key`
- Valor padrão (DEV): `admin_key_change_in_production`
- **⚠️ IMPORTANTE**: Altere para OAuth2/JWT em produção

### 2. Token de Bilheteria
- Header: `X-Token-Bilheteria`
- Gerado automaticamente ao criar um evento
- Permite: cadastro de participantes, emissão de ingressos

### 3. Token de Portaria
- Header: `X-Token-Portaria`
- Gerado automaticamente ao criar um evento
- Permite: validação de QR codes e controle de acesso

## 🔌 Módulos e Endpoints

### 📊 Módulo Administrativo (`/api/admin`)

**Gestão de Eventos**
- `GET /eventos` - Lista todos os eventos
- `GET /eventos/{evento_id}` - Obtém detalhes de um evento
- `POST /eventos` - Cria novo evento (gera tokens automaticamente)
- `PUT /eventos/{evento_id}` - Atualiza evento
- `DELETE /eventos/{evento_id}` - Remove evento

**Gestão de Ilhas/Setores**
- `GET /eventos/{evento_id}/ilhas` - Lista ilhas de um evento
- `POST /ilhas` - Cria nova ilha
- `PUT /ilhas/{ilha_id}` - Atualiza ilha
- `DELETE /ilhas/{ilha_id}` - Remove ilha

**Gestão de Tipos de Ingresso**
- `GET /eventos/{evento_id}/tipos-ingresso` - Lista tipos de ingresso
- `POST /tipos-ingresso` - Cria novo tipo
- `PUT /tipos-ingresso/{tipo_id}` - Atualiza tipo
- `DELETE /tipos-ingresso/{tipo_id}` - Remove tipo

**Relatórios**
- `GET /eventos/{evento_id}/relatorio-vendas` - Relatório de vendas
- `GET /eventos/{evento_id}/exportar-leads` - Exporta leads em XLSX

### 🎫 Módulo Bilheteria (`/api/bilheteria`)

- `POST /participantes` - Cadastro rápido de participantes
- `POST /emitir` - Emite ingresso com QR code e retorna layout preenchido
- `GET /busca-credenciamento` - Busca participantes por nome/email
- `POST /reimprimir/{ingresso_id}` - Reimprime ingresso existente

### 🚪 Módulo Portaria (`/api/portaria`)

- `POST /validar` - Valida QR code e verifica permissões de acesso
  - Retorna 200 (OK) se acesso permitido
  - Retorna 403 (NEGADO) se acesso negado
- `GET /estatisticas` - Estatísticas de validações

### 📈 Módulo Coletor de Leads (`/api/leads`)

- `POST /coletar` - Registra interação de participante
- `GET /interacoes/{evento_id}` - Lista interações
- `GET /estatisticas/{evento_id}` - Estatísticas de coleta

## 🏗️ Estrutura do Projeto

```
ticket_manager/
├── app/
│   ├── __init__.py
│   ├── main.py                    # Aplicação FastAPI principal
│   ├── config/
│   │   ├── __init__.py
│   │   ├── database.py           # Configuração do MongoDB
│   │   ├── auth.py               # Middlewares de autenticação
│   │   └── indexes.py            # Índices do MongoDB
│   ├── models/
│   │   ├── __init__.py
│   │   ├── evento.py             # Modelo de Evento
│   │   ├── ilha.py               # Modelo de Ilha/Setor
│   │   ├── tipo_ingresso.py     # Modelo de Tipo de Ingresso
│   │   ├── participante.py       # Modelo de Participante
│   │   ├── ingresso_emitido.py   # Modelo de Ingresso Emitido
│   │   └── lead_interacao.py     # Modelo de Interação de Lead
│   └── routers/
│       ├── __init__.py
│       ├── admin.py              # Rotas administrativas
│       ├── bilheteria.py         # Rotas de bilheteria
│       ├── portaria.py           # Rotas de portaria
│       └── leads.py              # Rotas de coleta de leads
├── requirements.txt              # Dependências Python
├── Dockerfile                    # Dockerfile da aplicação
├── docker-compose.yml           # Configuração do Docker Compose
└── .env.example                 # Exemplo de variáveis de ambiente
```

## 💡 Exemplo de Uso

### 1. Criar um Evento

```bash
curl -X POST "http://localhost:8000/api/admin/eventos" \
  -H "X-Admin-Key: admin_key_change_in_production" \
  -H "Content-Type: application/json" \
  -d '{
    "nome": "Tech Conference 2024",
    "descricao": "Conferência anual de tecnologia",
    "data_evento": "2024-06-15T09:00:00"
  }'
```

Resposta incluirá `token_bilheteria` e `token_portaria`.

### 2. Criar Ilhas (Setores)

```bash
curl -X POST "http://localhost:8000/api/admin/ilhas" \
  -H "X-Admin-Key: admin_key_change_in_production" \
  -H "Content-Type: application/json" \
  -d '{
    "evento_id": "EVENT_ID",
    "nome_setor": "VIP",
    "capacidade_maxima": 100
  }'
```

### 3. Criar Tipo de Ingresso com Permissões

```bash
curl -X POST "http://localhost:8000/api/admin/tipos-ingresso" \
  -H "X-Admin-Key: admin_key_change_in_production" \
  -H "Content-Type: application/json" \
  -d '{
    "evento_id": "EVENT_ID",
    "descricao": "VIP All Access",
    "valor": 150.00,
    "permissoes": ["ILHA_ID_1", "ILHA_ID_2"]
  }'
```

### 4. Emitir Ingresso (Bilheteria)

```bash
curl -X POST "http://localhost:8000/api/bilheteria/emitir" \
  -H "X-Token-Bilheteria: TOKEN_FROM_EVENT" \
  -H "Content-Type: application/json" \
  -d '{
    "tipo_ingresso_id": "TIPO_ID",
    "participante_id": "PARTICIPANTE_ID"
  }'
```

### 5. Validar Acesso (Portaria)

```bash
curl -X POST "http://localhost:8000/api/portaria/validar" \
  -H "X-Token-Portaria: TOKEN_FROM_EVENT" \
  -H "Content-Type: application/json" \
  -d '{
    "qrcode_hash": "HASH_DO_QRCODE",
    "ilha_id": "ILHA_ID"
  }'
```

## 📐 Layout de Ingresso (JSON)

O campo `layout_ingresso` permite personalização completa do layout de impressão:

```json
{
  "canvas": { 
    "width": 80, 
    "unit": "mm" 
  },
  "elements": [
    { 
      "type": "text", 
      "value": "{participante_nome}", 
      "x": 10, 
      "y": 5, 
      "size": 12 
    },
    { 
      "type": "qrcode", 
      "value": "{qrcode_hash}", 
      "x": 10, 
      "y": 20, 
      "size": 40 
    },
    { 
      "type": "text", 
      "value": "{tipo_ingresso}", 
      "x": 10, 
      "y": 65, 
      "size": 10 
    }
  ]
}
```

**Variáveis disponíveis:**
- `{participante_nome}` - Nome do participante
- `{qrcode_hash}` - Hash do QR code
- `{tipo_ingresso}` - Descrição do tipo de ingresso
- `{evento_nome}` - Nome do evento
- `{data_evento}` - Data do evento

## 🛠️ Tecnologias Utilizadas

- **FastAPI**: Framework web moderno para APIs
- **MongoDB**: Banco de dados NoSQL com Motor (driver assíncrono)
- **Pydantic v2**: Validação de dados
- **Docker**: Containerização
- **QRCode**: Geração de códigos QR
- **OpenPyXL**: Exportação de planilhas Excel

## 🔒 Segurança

### Recursos Implementados
- Tokens únicos por evento para bilheteria e portaria
- Validação de permissões baseada em ilhas
- Índices únicos para QR codes e emails
- CORS configurável

### Recomendações para Produção
- ⚠️ Implementar OAuth2/JWT para autenticação administrativa
- Configurar CORS com domínios específicos
- Usar HTTPS
- Implementar rate limiting
- Adicionar logs de auditoria
- Configurar variáveis de ambiente seguras

## 🌐 Variáveis de Ambiente

```env
MONGO_USERNAME=admin
MONGO_PASSWORD=password
MONGO_DATABASE=ticket_manager
MONGODB_URL=mongodb://admin:password@localhost:27017
DATABASE_NAME=ticket_manager
```

## 🔧 Desenvolvimento Local

### Sem Docker

1. Crie um ambiente virtual:
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

3. Configure o `.env`

4. Inicie o MongoDB localmente

5. Execute:
```bash
uvicorn app.main:app --reload
```

## 📊 Índices do MongoDB

O sistema cria automaticamente os seguintes índices para performance:

- `eventos.token_bilheteria` (único)
- `eventos.token_portaria` (único)
- `ingressos_emitidos.qrcode_hash` (único)
- `participantes.email` (único)
- `participantes.nome`
- `tipos_ingresso.evento_id + descricao`
- `ilhas.evento_id`
- `lead_interacoes.evento_id + data_interacao`

## 📄 Licença

Este projeto é um scaffolding para desenvolvimento de sistemas de gestão de eventos.