# EventMaster API

Sistema completo de gerenciamento de eventos com controle de acesso e emissão de ingressos usando FastAPI e MongoDB.

## 📋 Visão Geral

O EventMaster API é uma solução backend para gestão de eventos que oferece:

- **Interface Web Administrativa**: Painel moderno com design glassmorphism
- **Gerenciamento de Eventos**: CRUD completo de eventos com configuração de layout personalizável
- **Upload de Logo**: Sistema de upload com validação e otimização automática de imagens
- **Editor Visual de Ingressos**: Criador drag-and-drop de layouts de ingressos
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

### Método 1: Docker Compose (Recomendado)

1. Clone o repositório:
```bash
git clone https://github.com/SrClauss/ticket_manager.git
cd ticket_manager
```

2. Copie o arquivo de exemplo de variáveis de ambiente (ou use o script de inicialização):
```bash
cp .env.example .env
```

3. Execute o script de inicialização:
```bash
./start.sh
```

OU execute manualmente:
```bash
docker compose up --build -d
```

4. Acesse a aplicação:
- **Admin Web UI**: http://localhost:8000/admin/login
- **API Docs (Swagger)**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

**Chave de acesso padrão**: `admin_key_change_in_production`

### Método 2: Desenvolvimento Local com Hot-Reload

Use o arquivo docker-compose.dev.yml que inclui Mongo Express para visualizar o banco:

```bash
docker compose -f docker-compose.dev.yml up --build
```

Isso iniciará:
- **FastAPI** com hot-reload em http://localhost:8000
- **MongoDB** em localhost:27017
- **Mongo Express** em http://localhost:8081 (usuário: admin, senha: admin)

### Comandos Úteis do Docker Compose

```bash
# Parar serviços
docker compose down

# Ver logs
docker compose logs -f fastapi

# Reconstruir após mudanças
docker compose up --build

# Limpar tudo (incluindo volumes)
docker compose down -v

# Verificar status
docker compose ps
```

## 📚 Documentação da API

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 🔐 Autenticação

O sistema utiliza autenticação moderna com múltiplas camadas de segurança:

### 1. Acesso Administrativo (JWT)
- **Login**: Interface web em `/admin/login`
- **Credenciais padrão (DEV)**:
  - Username: `admin`
  - Password: `admin_key_change_in_production`
- **Tecnologia**: JWT (JSON Web Tokens) com Bearer Authentication
- **Expiração**: 24 horas (configurável)
- **Header API**: `Authorization: Bearer <JWT_TOKEN>`
- **Cookie Web**: `admin_jwt` (HttpOnly, Secure)
- ⚠️ **IMPORTANTE**: Configure JWT_SECRET_KEY forte em produção

### 2. Token de Bilheteria
- Header: `X-Token-Bilheteria`
- Gerado automaticamente ao criar um evento
- Permite: cadastro de participantes, emissão de ingressos
- Acesso via URL: `/bilheteria/credenciamento?token=TOKEN`

### 3. Token de Portaria
- Header: `X-Token-Portaria`
- Gerado automaticamente ao criar um evento
- Permite: validação de QR codes e controle de acesso
- Acesso via URL: `/portaria/controle?token=TOKEN`

## 🔌 Módulos e Endpoints

### 🌐 Interface Web Administrativa (`/admin`)

**Interface Web Moderna com Glassmorphism Design e JWT Authentication**

- `GET /admin/login` - Tela de login administrativa com JWT
- `POST /admin/login` - Autenticação (username/password → JWT)
- `GET /admin/logout` - Encerrar sessão
- `GET /admin/dashboard` - Dashboard com estatísticas em tempo real
- `GET /admin/eventos` - Listagem de eventos com filtros avançados
- `GET /admin/eventos/novo` - Formulário de criação de evento
- `POST /admin/eventos/novo` - Criar evento com upload de logo
- `GET /admin/eventos/{id}` - Detalhes do evento com gestão de ilhas e tipos de ingresso
- `GET /admin/eventos/layout/{id}` - Editor visual de layout de ingressos (drag-and-drop)
- `POST /admin/eventos/layout/{id}` - Salvar layout do ingresso
- `POST /admin/eventos/limpar-passados` - Soft delete de eventos passados (manutenção)
- `GET /admin/financeiro` - Módulo financeiro (em desenvolvimento)
- `GET /admin/configuracoes` - Configurações do sistema

**Recursos da Interface:**
- Design glassmorphism com gradientes vibrantes
- Navegação bottom bar mobile-first com logout
- Upload de logo com validação (200KB max, PNG/JPG, resize 400x400)
- Editor visual drag-and-drop de ingressos com Interact.js
- Sistema de template tags: `{NOME}`, `{CPF}`, `{EMAIL}`, `{TIPO_INGRESSO}`, `{qrcode_hash}`, etc.
- Filtros avançados de eventos (status, período, busca)
- Notificações toast do Bootstrap
- Gestão completa de ilhas/setores e tipos de ingresso
- Links diretos para módulos operacionais

### 🎫 Módulos Operacionais (Web UI)

**Box Office/Credenciamento** (`/bilheteria/credenciamento?token=TOKEN`)
- Interface responsiva para tablets/desktops
- Busca de participantes por nome, email ou CPF
- Botão "Adicionar Participante" com formulário completo
- Emissão de ingressos com QR code
- Design glassmorphism consistente

**Gate/Access Control** (`/portaria/controle?token=TOKEN`)
- Scanner QR code com Html5-qrcode
- Suporte a câmera frontal para dispositivos móveis
- Seleção de setor/ilha para validação
- Feedback visual full-screen:
  - ✓ Verde para acesso PERMITIDO
  - ✗ Vermelho para acesso NEGADO
- Contadores em tempo real (permitidos/negados)
- Informações da última validação

**Lead Collector** (`/leads/coletor`)
- Scanner QR code para captura de leads
- Armazenamento local com localStorage
- Contador de leads coletados (total e hoje)
- Exportação para CSV
- Feedback sonoro em captura bem-sucedida
- Sem necessidade de autenticação

**Self-Credentialing** (`/auto-credenciamento?evento_id=ID`)
- Interface de auto-atendimento
- Scanner QR code com câmera frontal
- Simulação de impressão automática de crachá
- Tela de boas-vindas personalizada
- Redirecionamento para Help Desk em caso de erro
- Design intuitivo para público geral

### 📊 Módulo Administrativo API (`/api/admin`)

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
- `GET /participantes/buscar` - Busca participantes por filtros (nome, email, CPF)
- `POST /emitir` - Emite ingresso com QR code e retorna layout preenchido
- `GET /busca-credenciamento` - Busca participantes com ingressos para reimpressão
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

- **FastAPI**: Framework web moderno e rápido para APIs
- **MongoDB**: Banco de dados NoSQL com Motor (driver assíncrono)
- **Pydantic v2**: Validação de dados e serialização
- **PyJWT & python-jose**: Autenticação JWT
- **Docker & Docker Compose**: Containerização e orquestração
- **QRCode & Pillow**: Geração de QR codes e processamento de imagens
- **OpenPyXL**: Exportação de planilhas Excel
- **Jinja2**: Template engine para renderização de páginas
- **Bootstrap 5**: Framework CSS para UI responsiva
- **Html5-qrcode**: Biblioteca JavaScript para leitura de QR codes
- **Interact.js**: Biblioteca para drag-and-drop no editor visual
- **Lucide Icons**: Ícones modernos e consistentes

## 🔒 Segurança

### Recursos Implementados
- ✅ **JWT Authentication**: Autenticação segura com tokens JWT para administradores
- ✅ **Tokens únicos por evento**: Para bilheteria e portaria
- ✅ **Validação de permissões**: Baseada em ilhas/setores
- ✅ **Índices únicos**: Para QR codes e emails (previne duplicatas)
- ✅ **CORS configurável**: Controle de origens permitidas
- ✅ **Secure cookies**: HttpOnly cookies para JWT
- ✅ **Timezone-aware datetime**: Compatibilidade com Python 3.12+
- ✅ **Environment validation**: Validação de JWT secret em produção
- ✅ **Image validation**: Validação de tipo, tamanho e resize automático para logos

### CodeQL Security Scan
- ✅ **0 vulnerabilities encontradas** - Código verificado e aprovado

### Recomendações para Produção
- ⚠️ Configure JWT_SECRET_KEY forte (use `openssl rand -hex 32`)
- ⚠️ Configure ENVIRONMENT=production no .env
- ⚠️ Configure ADMIN_USERNAME e ADMIN_PASSWORD seguros
- ⚠️ Restrinja CORS com domínios específicos
- ⚠️ Use HTTPS em produção
- ⚠️ Implemente rate limiting (ex: slowapi)
- ⚠️ Adicione logs de auditoria
- ⚠️ Configure backup automático do MongoDB
- ⚠️ Use secrets manager (AWS Secrets Manager, Azure Key Vault, etc.)

## 🌐 Variáveis de Ambiente

```env
# Environment Configuration
ENVIRONMENT=development  # or production

# MongoDB Configuration
MONGO_USERNAME=admin
MONGO_PASSWORD=password
MONGO_DATABASE=ticket_manager
MONGODB_URL=mongodb://admin:password@localhost:27017
DATABASE_NAME=ticket_manager

# JWT Configuration (CRITICAL FOR PRODUCTION)
JWT_SECRET_KEY=your-secret-key-change-in-production-use-openssl-rand-hex-32
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Admin Configuration (CHANGE IN PRODUCTION)
ADMIN_USERNAME=admin
ADMIN_PASSWORD=change-this-password-in-production
```

**Gerando JWT_SECRET_KEY seguro:**
```bash
openssl rand -hex 32
# or
python -c "import secrets; print(secrets.token_urlsafe(32))"
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