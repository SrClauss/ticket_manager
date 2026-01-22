# Roadmap e Backlog - Ticket Manager Mobile + Backend

> **Objetivo:** Este documento contém o planejamento detalhado das funcionalidades mobile e backend solicitadas pelo cliente, incluindo épicos, issues, subtarefas, critérios de aceite, endpoints sugeridos, decisões técnicas e estimativas. Serve como backlog pronto para criação manual ou automatizada de issues.

---

## 📋 Sumário Executivo

Este roadmap abrange as seguintes funcionalidades principais:

1. **Epic A** — Reorganizar tela de teste de impressora e alterar menu principal
2. **Epic B** — Tela principal de Token (MainTokenScreen)
3. **Epic C** — Fluxo Bilheteria (busca de participantes + impressão de bilhetes)
4. **Epic D** — Fluxo Portaria (leitor de QR e check-in)
5. **Epic E** — Upload de planilhas por empresas
6. **Epic F** — Inscrições individuais com formulário dinâmico
7. **Epic G** — Infraestrutura, segurança, validação, testes e documentação

---

## 🎯 Epic A — Reorganizar Tela de Teste de Impressora e Alterar Menu Principal

### Descrição
Mover a funcionalidade de teste de impressora do menu principal para um submenu de configurações (Settings) e atualizar o menu principal para apontar para a nova tela principal de tokens.

### Issues/Subtarefas

#### [A1] Mover arquivo/rota da tela de teste de impressora para Settings/TestPrinter
**Descrição:**
- Reorganizar estrutura de arquivos e rotas da aplicação mobile
- Mover tela de teste de impressora para seção de Settings
- Atualizar navegação para refletir nova localização

**Critérios de Aceite:**
- [ ] Arquivo de tela de teste de impressora está em `Settings/TestPrinter` ou estrutura equivalente
- [ ] Navegação para teste de impressora acessível apenas via menu Settings
- [ ] Rota atualizada no sistema de navegação mobile
- [ ] Imports atualizados em todos os arquivos dependentes

**Endpoints Afetados:**
- Nenhum (mudança apenas mobile)

**Estimativa:** 3 pontos

**Labels:** `mobile`, `refactor`, `navigation`

---

#### [A2] Substituir entrada do menu principal para MainTokenScreen
**Descrição:**
- Atualizar menu principal da aplicação mobile
- Remover entrada direta para teste de impressora
- Adicionar entrada para nova MainTokenScreen
- Garantir que fluxo principal aponte para autenticação via token

**Critérios de Aceite:**
- [ ] Menu principal mostra entrada para MainTokenScreen
- [ ] Entrada de teste de impressora removida do menu principal
- [ ] Ícones e labels apropriados para nova entrada
- [ ] Navegação funcional ao clicar na nova entrada

**Endpoints Afetados:**
- Nenhum (mudança apenas mobile)

**Estimativa:** 2 pontos

**Labels:** `mobile`, `ui`, `navigation`

---

#### [A3] Ajustar imports, rotas e permissões de acesso
**Descrição:**
- Revisar todos os imports após reorganização
- Atualizar rotas de navegação
- Verificar e ajustar permissões de acesso se necessário
- Garantir que teste de impressora requer autenticação apropriada

**Critérios de Aceite:**
- [ ] Todos os imports compilam sem erros
- [ ] Rotas de navegação funcionam corretamente
- [ ] Testes de impressora acessíveis apenas para usuários autenticados
- [ ] Sem warnings de imports não utilizados

**Endpoints Afetados:**
- Nenhum (mudança apenas mobile)

**Estimativa:** 2 pontos

**Labels:** `mobile`, `refactor`, `security`

---

**Estimativa Total Epic A:** 7 pontos
**Prioridade:** Alta
**Dependências:** Nenhuma

---

## 🔐 Epic B — Tela Principal de Token (MainTokenScreen)

### Descrição
Criar tela principal para inserção de tokens de bilheteria ou portaria, com validação no backend e armazenamento seguro no dispositivo móvel.

### Issues/Subtarefas

#### [B1] Criar interface mobile MainTokenScreen
**Descrição:**
- Desenvolver tela de entrada de token
- Incluir campo de input para token
- Botões de ação (validar/entrar)
- Seletor de tipo de token (Bilheteria/Portaria)
- Design responsivo e consistente com app

**Critérios de Aceite:**
- [ ] Tela renderiza corretamente em iOS e Android
- [ ] Campo de input aceita texto/código
- [ ] Validação básica de formato (não vazio, length mínimo)
- [ ] Feedback visual durante validação (loading)
- [ ] Mensagens de erro amigáveis

**Endpoints Utilizados:**
- `POST /api/v1/tokens/validate`

**Estimativa:** 5 pontos

**Labels:** `mobile`, `ui`, `feature`

---

#### [B2] Implementar endpoint POST /api/v1/tokens/validate (Backend)
**Descrição:**
- Criar endpoint para validação de tokens
- Verificar se token existe e está ativo
- Retornar tipo de token (bilheteria/portaria) e dados do evento
- Incluir informações de permissões/scopes

**Critérios de Aceite:**
- [ ] Endpoint responde em `/api/v1/tokens/validate`
- [ ] Aceita token no body: `{ "token": "abc123", "type": "bilheteria" }`
- [ ] Retorna 200 com dados do evento se válido
- [ ] Retorna 401 se token inválido/expirado
- [ ] Retorna dados: `{ "valid": true, "event_id": "...", "event_name": "...", "type": "bilheteria", "scopes": [...] }`
- [ ] Token validado contra banco de dados (eventos.token_bilheteria ou eventos.token_portaria)

**Request Example:**
```json
POST /api/v1/tokens/validate
{
  "token": "a1b2c3d4e5f6",
  "type": "bilheteria"
}
```

**Response Example (Success):**
```json
{
  "valid": true,
  "event_id": "event_123",
  "event_name": "Tech Conference 2024",
  "type": "bilheteria",
  "scopes": ["read:participants", "write:tickets"]
}
```

**Response Example (Error):**
```json
{
  "valid": false,
  "error": "Token inválido ou expirado"
}
```

**Estimativa:** 5 pontos

**Labels:** `backend`, `api`, `authentication`

---

#### [B3] Implementar armazenamento seguro de token (Secure Storage)
**Descrição:**
- Integrar biblioteca de secure storage (Keychain/Keystore)
- Armazenar token validado de forma segura
- Incluir timestamp de validação
- Implementar função de logout (limpar token)

**Critérios de Aceite:**
- [ ] Token armazenado usando secure storage nativo
- [ ] Token não acessível por outras apps
- [ ] Token persiste entre sessões
- [ ] Função de logout limpa token corretamente
- [ ] App verifica token ao iniciar

**Bibliotecas Sugeridas:**
- React Native: `react-native-keychain` ou `@react-native-async-storage/async-storage` (com criptografia)
- Flutter: `flutter_secure_storage`

**Estimativa:** 3 pontos

**Labels:** `mobile`, `security`, `storage`

---

#### [B4] Implementar navegação condicional baseada em tipo de token
**Descrição:**
- Após validação bem-sucedida, redirecionar para tela apropriada
- Se token de bilheteria → navegar para tela de busca de participantes
- Se token de portaria → navegar para tela de scanner QR
- Manter estado de autenticação durante sessão

**Critérios de Aceite:**
- [ ] Navegação automática após validação de token
- [ ] Redirecionamento correto baseado em tipo
- [ ] Estado mantido durante navegação
- [ ] Botão de logout acessível em todas as telas autenticadas

**Estimativa:** 3 pontos

**Labels:** `mobile`, `navigation`, `feature`

---

**Estimativa Total Epic B:** 16 pontos
**Prioridade:** Alta
**Dependências:** Epic A concluído

---

## 🎫 Epic C — Fluxo Bilheteria

### Descrição
Implementar fluxo completo de bilheteria incluindo busca de participantes, visualização de bilhete e impressão com QR code.

### Issues/Subtarefas

#### [C1] Criar tela de busca de participantes (Mobile)
**Descrição:**
- Tela com campo de busca (nome, CPF, email)
- Lista de resultados com informações básicas
- Indicação visual de status (já possui ingresso ou não)
- Botão de ação para cada participante

**Critérios de Aceite:**
- [ ] Campo de busca com debounce (300ms)
- [ ] Busca funciona para nome parcial, CPF e email
- [ ] Resultados mostram: nome, CPF mascarado, email
- [ ] Indicador visual de status de ingresso
- [ ] Mensagem quando nenhum resultado encontrado
- [ ] Loading state durante busca

**Endpoints Utilizados:**
- `GET /api/v1/events/{eventId}/participants?query={q}`

**Estimativa:** 5 pontos

**Labels:** `mobile`, `ui`, `feature`

---

#### [C2] Implementar endpoint GET /api/v1/events/{eventId}/participants (Backend)
**Descrição:**
- Criar endpoint de busca de participantes
- Suportar busca por nome parcial, CPF e email
- Retornar lista paginada
- Incluir informação se participante já possui ingresso

**Critérios de Aceite:**
- [ ] Endpoint responde em `/api/v1/events/{eventId}/participants`
- [ ] Suporta query parameter: `?query={searchTerm}`
- [ ] Busca case-insensitive
- [ ] Busca em campos: nome, CPF, email
- [ ] Retorna até 20 resultados por página
- [ ] Inclui flag `has_ticket` no response
- [ ] Requer autenticação via token de bilheteria

**Request Example:**
```
GET /api/v1/events/event_123/participants?query=João
Authorization: Bearer {token_bilheteria}
```

**Response Example:**
```json
{
  "total": 2,
  "results": [
    {
      "id": "participant_1",
      "name": "João Silva",
      "cpf": "***.***.123-45",
      "email": "joao@example.com",
      "has_ticket": true,
      "ticket_id": "ticket_1"
    },
    {
      "id": "participant_2",
      "name": "João Santos",
      "cpf": "***.***.678-90",
      "email": "joao.santos@example.com",
      "has_ticket": false,
      "ticket_id": null
    }
  ]
}
```

**Estimativa:** 5 pontos

**Labels:** `backend`, `api`, `feature`

---

#### [C3] Implementar endpoint GET /api/v1/events/{eventId}/participants/{participantId}/ticket-image (Backend)
**Descrição:**
- Criar endpoint para gerar/retornar imagem do bilhete
- Retornar imagem PNG com QR code embutido
- Cachear imagens geradas para performance
- Incluir dados do participante no bilhete

**Critérios de Aceite:**
- [ ] Endpoint retorna imagem PNG (Content-Type: image/png)
- [ ] Imagem contém QR code válido
- [ ] Imagem inclui: nome participante, evento, tipo de ingresso
- [ ] QR code contém: ticketId + assinatura HMAC/JWT
- [ ] Imagens cacheadas por 24h
- [ ] Retorna 404 se participante não tem ingresso
- [ ] Requer autenticação via token de bilheteria

**Request Example:**
```
GET /api/v1/events/event_123/participants/participant_1/ticket-image
Authorization: Bearer {token_bilheteria}
```

**Response:**
- Content-Type: `image/png`
- Binary image data

**Decisões Técnicas:**
- Usar biblioteca Pillow para geração de imagem
- QR code gerado com biblioteca qrcode
- Cache implementado com Redis ou filesystem
- Dimensões padrão: 800x600px ou configurável por evento

**Estimativa:** 8 pontos

**Labels:** `backend`, `api`, `imaging`, `feature`

---

#### [C4] Criar tela de preview e impressão do bilhete (Mobile)
**Descrição:**
- Tela para visualizar imagem do bilhete antes de imprimir
- Botão de impressão
- Integração com impressora térmica ou impressora padrão do dispositivo
- Opção de salvar/compartilhar bilhete

**Critérios de Aceite:**
- [ ] Imagem do bilhete carrega e exibe corretamente
- [ ] Preview mostra imagem em tamanho adequado
- [ ] Botão de imprimir funciona
- [ ] Integração com impressora térmica (se disponível)
- [ ] Fallback para impressora padrão do sistema
- [ ] Opção de salvar imagem na galeria
- [ ] Feedback de sucesso/erro após impressão

**Bibliotecas Sugeridas:**
- React Native: `react-native-print`, `react-native-thermal-receipt-printer`
- Flutter: `printing`, `esc_pos_printer`

**Estimativa:** 8 pontos

**Labels:** `mobile`, `printing`, `feature`

---

#### [C5] Implementar segurança do QR code com assinatura
**Descrição:**
- Implementar geração de QR code com assinatura HMAC ou JWT
- Incluir ticketId + eventId + timestamp
- Adicionar expiração (opcional, configurável)
- Documentar formato do QR code

**Critérios de Aceite:**
- [ ] QR code contém: `{"ticket_id": "...", "event_id": "...", "timestamp": "...", "signature": "..."}`
- [ ] Assinatura HMAC-SHA256 ou JWT com secret key
- [ ] Secret key armazenado em variável de ambiente
- [ ] Formato documentado para integração com portaria
- [ ] Validação de assinatura implementada

**Formato Sugerido (JWT):**
```json
{
  "ticket_id": "ticket_123",
  "event_id": "event_123",
  "participant_id": "participant_1",
  "iat": 1234567890,
  "exp": 1234567890
}
```

**Estimativa:** 5 pontos

**Labels:** `backend`, `security`, `qrcode`

---

**Estimativa Total Epic C:** 31 pontos
**Prioridade:** Alta
**Dependências:** Epic B concluído

---

## 🚪 Epic D — Fluxo Portaria (Leitor de QR)

### Descrição
Implementar sistema de leitura de QR code para check-in de participantes na portaria, com validação de permissões e registro de entrada.

### Issues/Subtarefas

#### [D1] Criar tela de scanner QR (Mobile)
**Descrição:**
- Implementar tela com câmera para leitura de QR code
- Interface intuitiva com visualização da câmera
- Feedback visual ao detectar QR code
- Seletor de ilha/setor para validação

**Critérios de Aceite:**
- [ ] Câmera abre automaticamente ao entrar na tela
- [ ] QR code detectado automaticamente
- [ ] Feedback visual ao escanear (borda verde/vermelha)
- [ ] Seletor de ilha/setor visível e funcional
- [ ] Botão para alternar câmera (frontal/traseira)
- [ ] Permissões de câmera solicitadas corretamente

**Bibliotecas Sugeridas:**
- React Native: `react-native-camera`, `react-native-qrcode-scanner`
- Flutter: `qr_code_scanner`, `mobile_scanner`

**Estimativa:** 8 pontos

**Labels:** `mobile`, `camera`, `qrcode`, `feature`

---

#### [D2] Implementar endpoint POST /api/v1/validate/qr (Backend)
**Descrição:**
- Criar endpoint para validar QR code escaneado
- Verificar assinatura do QR code
- Validar se ingresso existe e está ativo
- Verificar permissões de acesso para ilha selecionada
- Retornar informações do participante

**Critérios de Aceite:**
- [ ] Endpoint responde em `/api/v1/validate/qr`
- [ ] Aceita: `{ "qr_data": "...", "ilha_id": "..." }`
- [ ] Valida assinatura HMAC/JWT do QR code
- [ ] Verifica se ingresso não foi cancelado
- [ ] Verifica se tipo de ingresso tem permissão para ilha
- [ ] Retorna 200 se válido com dados do participante
- [ ] Retorna 403 se acesso negado
- [ ] Retorna 404 se ingresso não encontrado
- [ ] Requer autenticação via token de portaria

**Request Example:**
```json
POST /api/v1/validate/qr
Authorization: Bearer {token_portaria}
{
  "qr_data": "eyJhbGc...",
  "ilha_id": "ilha_vip"
}
```

**Response Example (Success):**
```json
{
  "valid": true,
  "access_granted": true,
  "participant": {
    "name": "João Silva",
    "ticket_type": "VIP All Access",
    "ticket_id": "ticket_123"
  },
  "message": "Acesso permitido"
}
```

**Response Example (Denied):**
```json
{
  "valid": true,
  "access_granted": false,
  "participant": {
    "name": "João Silva",
    "ticket_type": "Pista",
    "ticket_id": "ticket_123"
  },
  "message": "Ingresso não tem permissão para esta área"
}
```

**Estimativa:** 8 pontos

**Labels:** `backend`, `api`, `validation`, `security`

---

#### [D3] Implementar endpoint POST /api/v1/tickets/{ticketId}/checkin (Backend)
**Descrição:**
- Criar endpoint para registrar check-in do participante
- Registrar timestamp, ilha e dispositivo usado
- Prevenir check-ins duplicados (opcional: permitir múltiplos check-ins)
- Manter histórico de acessos

**Critérios de Aceite:**
- [ ] Endpoint responde em `/api/v1/tickets/{ticketId}/checkin`
- [ ] Registra: timestamp, ilha_id, token_device
- [ ] Retorna 200 se check-in registrado
- [ ] Retorna 400 se ingresso já teve check-in (se configurado para único)
- [ ] Mantém histórico de todos os check-ins
- [ ] Requer autenticação via token de portaria

**Request Example:**
```json
POST /api/v1/tickets/ticket_123/checkin
Authorization: Bearer {token_portaria}
{
  "ilha_id": "ilha_vip",
  "device_id": "tablet_portaria_1"
}
```

**Response Example:**
```json
{
  "success": true,
  "checkin_id": "checkin_456",
  "timestamp": "2024-06-15T10:30:00Z",
  "message": "Check-in registrado com sucesso"
}
```

**Estimativa:** 5 pontos

**Labels:** `backend`, `api`, `feature`

---

#### [D4] Implementar feedback visual de acesso permitido/negado (Mobile)
**Descrição:**
- Tela de feedback full-screen após validação
- Verde com ✓ para acesso permitido
- Vermelho com ✗ para acesso negado
- Mostrar informações do participante
- Retornar automaticamente para scanner após 3 segundos

**Critérios de Aceite:**
- [ ] Feedback visual claro e imediato
- [ ] Tela verde para acesso permitido
- [ ] Tela vermelha para acesso negado
- [ ] Mostra nome do participante e tipo de ingresso
- [ ] Feedback sonoro (bip de sucesso/erro)
- [ ] Retorna automaticamente para scanner
- [ ] Contador de acessos permitidos/negados

**Estimativa:** 5 pontos

**Labels:** `mobile`, `ui`, `ux`

---

#### [D5] Implementar modo offline com sincronização (Opcional/Futuro)
**Descrição:**
- Permitir validação de QR codes sem conexão
- Armazenar validações localmente
- Sincronizar com servidor quando conexão retornar
- Cache de lista de ingressos válidos

**Critérios de Aceite:**
- [ ] App funciona sem conexão
- [ ] Validações armazenadas localmente
- [ ] Sincronização automática quando online
- [ ] Indicador visual de modo offline
- [ ] Lista de ingressos válidos sincronizada periodicamente

**Estimativa:** 13 pontos

**Labels:** `mobile`, `offline`, `sync`, `enhancement`

**Prioridade:** Média (pode ser implementado em fase futura)

---

**Estimativa Total Epic D:** 39 pontos (26 pontos sem item opcional)
**Prioridade:** Alta
**Dependências:** Epic B e C concluídos (para validação de QR)

---

## 📊 Epic E — Upload de Planilhas por Empresas

### Descrição
Permitir que empresas façam upload de planilhas (Excel/CSV) com lista de participantes via interface web, com validação, processamento em background e feedback de resultados.

### Issues/Subtarefas

#### [E1] Adicionar seção de upload de planilhas em Event Details (Frontend Web)
**Descrição:**
- Adicionar seção na página de detalhes do evento
- Seletor de empresa (dropdown)
- Componente de upload de arquivo (.xlsx, .csv)
- Instruções e template de planilha para download
- Lista de uploads anteriores com status

**Critérios de Aceite:**
- [ ] Seção visível na página de detalhes do evento
- [ ] Dropdown de seleção de empresa (cadastradas previamente)
- [ ] Aceita apenas arquivos .xlsx e .csv
- [ ] Tamanho máximo: 5MB
- [ ] Link para download de template de planilha
- [ ] Lista de uploads anteriores (últimos 10)
- [ ] Indicação de status: processando, concluído, erro

**Template de Planilha (colunas):**
- Nome (obrigatório)
- CPF (obrigatório)
- Email (obrigatório)
- Telefone (opcional)
- Cargo (opcional)
- Tipo de Ingresso (obrigatório)

**Estimativa:** 5 pontos

**Labels:** `frontend`, `ui`, `upload`

---

#### [E2] Implementar endpoint POST /api/v1/events/{eventId}/company-uploads (Backend)
**Descrição:**
- Criar endpoint para receber upload de planilha
- Aceitar multipart/form-data
- Validar formato de arquivo
- Criar job de processamento em background
- Retornar job_id para acompanhamento

**Critérios de Aceite:**
- [ ] Endpoint aceita upload multipart
- [ ] Valida extensão (.xlsx, .csv)
- [ ] Valida tamanho (max 5MB)
- [ ] Armazena arquivo temporariamente
- [ ] Cria job de processamento em fila
- [ ] Retorna job_id e status inicial
- [ ] Requer autenticação administrativa

**Request Example:**
```
POST /api/v1/events/event_123/company-uploads
Authorization: Bearer {admin_token}
Content-Type: multipart/form-data

company_id: company_1
file: [binary data]
```

**Response Example:**
```json
{
  "success": true,
  "job_id": "job_789",
  "status": "queued",
  "message": "Upload recebido. Processamento iniciado."
}
```

**Estimativa:** 8 pontos

**Labels:** `backend`, `api`, `upload`, `jobs`

---

#### [E3] Implementar job de validação e processamento de planilha (Backend)
**Descrição:**
- Criar worker/job para processar planilha
- Validar cada linha (campos obrigatórios, formato CPF, email)
- Verificar duplicatas
- Criar/atualizar participantes
- Emitir ingressos automaticamente
- Registrar erros por linha

**Critérios de Aceite:**
- [ ] Job processa planilha linha por linha
- [ ] Valida campos obrigatórios
- [ ] Valida formato de CPF (11 dígitos)
- [ ] Valida formato de email
- [ ] Verifica duplicatas de CPF no evento
- [ ] Cria participantes se não existirem
- [ ] Emite ingressos automaticamente
- [ ] Registra erros com número da linha e descrição
- [ ] Atualiza status do job (processing, completed, failed)
- [ ] Gera relatório de sucesso/erro

**Bibliotecas Sugeridas:**
- Celery ou RQ para jobs assíncronos
- pandas ou openpyxl para processar Excel
- csv para processar CSV

**Estimativa:** 13 pontos

**Labels:** `backend`, `jobs`, `validation`, `feature`

---

#### [E4] Implementar endpoint GET /api/v1/uploads/{job_id}/status (Backend)
**Descrição:**
- Criar endpoint para consultar status do job
- Retornar progresso (linhas processadas/total)
- Retornar lista de erros se houver
- Informar quando job está completo

**Critérios de Aceite:**
- [ ] Endpoint retorna status atual do job
- [ ] Inclui progresso: `{ "processed": 45, "total": 100 }`
- [ ] Lista erros encontrados
- [ ] Retorna 404 se job_id não existe
- [ ] Requer autenticação administrativa

**Response Example (Processing):**
```json
{
  "job_id": "job_789",
  "status": "processing",
  "progress": {
    "processed": 45,
    "total": 100,
    "percentage": 45
  },
  "errors": [],
  "created_at": "2024-06-15T10:00:00Z"
}
```

**Response Example (Completed with Errors):**
```json
{
  "job_id": "job_789",
  "status": "completed",
  "progress": {
    "processed": 100,
    "total": 100,
    "percentage": 100
  },
  "summary": {
    "success": 95,
    "errors": 5
  },
  "errors": [
    {
      "line": 15,
      "field": "CPF",
      "value": "123",
      "error": "CPF inválido"
    },
    {
      "line": 27,
      "field": "Email",
      "value": "invalido",
      "error": "Email em formato inválido"
    }
  ],
  "completed_at": "2024-06-15T10:05:00Z"
}
```

**Estimativa:** 5 pontos

**Labels:** `backend`, `api`, `jobs`

---

#### [E5] Criar página de feedback com erros e opção de download de relatório (Frontend Web)
**Descrição:**
- Página para visualizar resultados do upload
- Tabela com erros por linha
- Estatísticas de sucesso/erro
- Botão para download de relatório (CSV/Excel)
- Opção de corrigir e fazer novo upload

**Critérios de Aceite:**
- [ ] Página mostra progresso em tempo real
- [ ] Atualiza automaticamente (polling ou websocket)
- [ ] Tabela de erros com: linha, campo, valor, erro
- [ ] Card de estatísticas (total, sucesso, erro)
- [ ] Botão para download de relatório completo
- [ ] Link para fazer novo upload

**Estimativa:** 5 pontos

**Labels:** `frontend`, `ui`, `reporting`

---

**Estimativa Total Epic E:** 36 pontos
**Prioridade:** Média
**Dependências:** Sistema de eventos e participantes já existente

---

## 📝 Epic F — Inscrições Individuais (Formulário Dinâmico)

### Descrição
Permitir que participantes se inscrevam individualmente em eventos através de formulário web dinâmico com campos configuráveis.

### Issues/Subtarefas

#### [F1] Implementar endpoint GET /api/v1/events/{eventId}/registration-fields (Backend)
**Descrição:**
- Criar endpoint para retornar configuração de campos do formulário
- Campos podem ser configurados administrativamente
- Incluir informações de tipo, obrigatoriedade, validações
- Suportar diferentes tipos de campo (text, email, select, etc.)

**Critérios de Aceite:**
- [ ] Endpoint retorna lista de campos configurados
- [ ] Cada campo inclui: name, label, type, required, options (se select)
- [ ] Campos padrão: nome, email, CPF (sempre obrigatórios)
- [ ] Campos customizados configuráveis por evento
- [ ] Endpoint público (não requer autenticação)

**Response Example:**
```json
{
  "event_id": "event_123",
  "event_name": "Tech Conference 2024",
  "fields": [
    {
      "name": "nome",
      "label": "Nome Completo",
      "type": "text",
      "required": true,
      "validation": {
        "min_length": 3
      }
    },
    {
      "name": "email",
      "label": "E-mail",
      "type": "email",
      "required": true
    },
    {
      "name": "cpf",
      "label": "CPF",
      "type": "text",
      "required": true,
      "validation": {
        "pattern": "\\d{11}"
      }
    },
    {
      "name": "empresa",
      "label": "Empresa",
      "type": "text",
      "required": false
    },
    {
      "name": "tipo_ingresso",
      "label": "Tipo de Ingresso",
      "type": "select",
      "required": true,
      "options": [
        {"value": "vip", "label": "VIP"},
        {"value": "pista", "label": "Pista"}
      ]
    }
  ]
}
```

**Estimativa:** 5 pontos

**Labels:** `backend`, `api`, `configuration`

---

#### [F2] Criar modelo de configuração de campos dinâmicos (Backend)
**Descrição:**
- Criar modelo de dados para armazenar configuração de campos
- Permitir CRUD de campos customizados via interface administrativa
- Validar tipos de campo suportados
- Armazenar validações customizadas

**Critérios de Aceite:**
- [ ] Modelo permite definir campos por evento
- [ ] Suporta tipos: text, email, tel, number, select, textarea
- [ ] Permite definir obrigatoriedade
- [ ] Permite definir validações (regex, min/max length)
- [ ] Campos administrativos (nome, email, CPF) não podem ser removidos

**Estimativa:** 5 pontos

**Labels:** `backend`, `models`, `configuration`

---

#### [F3] Implementar endpoint POST /api/v1/events/{eventId}/registrations (Backend)
**Descrição:**
- Criar endpoint para receber submissão de formulário de inscrição
- Validar campos obrigatórios
- Validar formatos (email, CPF)
- Verificar duplicatas de CPF
- Criar participante e emitir ingresso automaticamente
- Enviar email de confirmação (opcional)

**Critérios de Aceite:**
- [ ] Endpoint aceita dados do formulário
- [ ] Valida todos os campos obrigatórios
- [ ] Valida formatos (CPF, email, telefone)
- [ ] Verifica duplicata de CPF no evento
- [ ] Cria participante se não existe
- [ ] Emite ingresso automaticamente
- [ ] Retorna 201 com dados do ingresso
- [ ] Retorna 400 se validação falhar
- [ ] Endpoint público (não requer autenticação)

**Request Example:**
```json
POST /api/v1/events/event_123/registrations
{
  "nome": "Maria Santos",
  "email": "maria@example.com",
  "cpf": "12345678901",
  "empresa": "Tech Corp",
  "tipo_ingresso": "vip"
}
```

**Response Example (Success):**
```json
{
  "success": true,
  "participant_id": "participant_456",
  "ticket_id": "ticket_789",
  "message": "Inscrição realizada com sucesso! Verifique seu email para mais detalhes.",
  "ticket_url": "https://app.com/ticket/ticket_789"
}
```

**Response Example (Error):**
```json
{
  "success": false,
  "error": "CPF já cadastrado neste evento",
  "field": "cpf"
}
```

**Estimativa:** 8 pontos

**Labels:** `backend`, `api`, `validation`, `feature`

---

#### [F4] Criar página web de formulário dinâmico (Frontend Web)
**Descrição:**
- Criar página de inscrição pública
- Renderizar formulário dinamicamente baseado em configuração
- Validação client-side
- Feedback de sucesso/erro
- Design responsivo

**Critérios de Aceite:**
- [ ] Página pública acessível via URL: `/events/{eventId}/register`
- [ ] Formulário renderizado dinamicamente
- [ ] Validação client-side antes de submit
- [ ] Máscaras para CPF e telefone
- [ ] Feedback visual de validação (campo a campo)
- [ ] Mensagem de sucesso após submissão
- [ ] Mensagens de erro claras
- [ ] Design responsivo (mobile-friendly)

**Estimativa:** 8 pontos

**Labels:** `frontend`, `ui`, `forms`, `feature`

---

#### [F5] Implementar regras de imutabilidade de campos obrigatórios
**Descrição:**
- Garantir que campos administrativos (nome, email, CPF) não possam ser removidos
- Interface administrativa deve indicar campos imutáveis
- Validação backend para prevenir remoção de campos obrigatórios

**Critérios de Aceite:**
- [ ] Campos nome, email, CPF sempre presentes
- [ ] Interface administrativa marca campos imutáveis
- [ ] Tentativa de remover campo obrigatório retorna erro
- [ ] Campos imutáveis podem ter label personalizado
- [ ] Validações de campos imutáveis podem ser ajustadas (com limites)

**Estimativa:** 3 pontos

**Labels:** `backend`, `frontend`, `validation`, `security`

---

#### [F6] Implementar envio de email de confirmação (Opcional)
**Descrição:**
- Enviar email após inscrição bem-sucedida
- Incluir link para download do ingresso
- Template de email customizável

**Critérios de Aceite:**
- [ ] Email enviado após inscrição
- [ ] Contém: dados do evento, nome do participante
- [ ] Link para visualizar/baixar ingresso
- [ ] Template de email configurável
- [ ] Logs de emails enviados

**Bibliotecas Sugeridas:**
- SendGrid, Mailgun, ou SMTP direto

**Estimativa:** 5 pontos

**Labels:** `backend`, `email`, `feature`, `enhancement`

**Prioridade:** Baixa (opcional)

---

**Estimativa Total Epic F:** 34 pontos (29 pontos sem email)
**Prioridade:** Média
**Dependências:** Sistema de eventos e participantes já existente

---

## 🔐 Epic G — Infraestrutura, Segurança, Validação, Testes e Documentação

### Descrição
Estabelecer infraestrutura robusta, segurança adequada, validações, testes automatizados e documentação completa para todos os novos recursos.

### Issues/Subtarefas

#### [G1] Definir esquema de tokens e scopes
**Descrição:**
- Documentar estrutura de tokens (bilheteria, portaria, admin)
- Definir scopes/permissões para cada tipo de token
- Implementar middleware de autorização baseado em scopes
- Documentar fluxos de autenticação

**Critérios de Aceite:**
- [ ] Documentação de tipos de token e scopes
- [ ] Middleware de autorização implementado
- [ ] Endpoints protegidos com scopes apropriados
- [ ] Testes de autorização
- [ ] Documentação de fluxos de autenticação

**Scopes Sugeridos:**
- Bilheteria: `read:participants`, `write:tickets`, `read:events`
- Portaria: `read:tickets`, `write:checkins`, `validate:qr`
- Admin: `*:*` (acesso completo)

**Estimativa:** 5 pontos

**Labels:** `backend`, `security`, `authentication`, `docs`

---

#### [G2] Implementar assinatura de QR code (HMAC/JWT)
**Descrição:**
- Implementar geração de assinatura para QR codes
- Usar HMAC-SHA256 ou JWT
- Configurar secret key em variável de ambiente
- Implementar validação de assinatura
- Adicionar expiração opcional

**Critérios de Aceite:**
- [ ] QR code assinado com HMAC-SHA256 ou JWT
- [ ] Secret key em variável de ambiente
- [ ] Validação de assinatura funcional
- [ ] Suporte a expiração de QR code (configurável)
- [ ] Documentação do formato

**Estimativa:** 5 pontos

**Labels:** `backend`, `security`, `qrcode`

---

#### [G3] Implementar sistema de filas para jobs de background
**Descrição:**
- Configurar sistema de filas (Celery, RQ, ou similar)
- Implementar workers para processar jobs
- Configurar Redis ou RabbitMQ como broker
- Monitoramento de jobs
- Retry logic para jobs falhados

**Critérios de Aceite:**
- [ ] Sistema de filas configurado (Celery/RQ)
- [ ] Workers funcionando
- [ ] Redis/RabbitMQ configurado
- [ ] Jobs de processamento de planilha usando filas
- [ ] Jobs de geração de imagens usando filas
- [ ] Retry automático para jobs falhados (max 3x)
- [ ] Logs de jobs

**Estimativa:** 8 pontos

**Labels:** `backend`, `infra`, `jobs`, `performance`

---

#### [G4] Implementar geração de imagens de bilhete em background
**Descrição:**
- Mover geração de imagens para job assíncrono
- Cachear imagens geradas
- Implementar regeneração de cache quando necessário
- Otimizar performance

**Critérios de Aceite:**
- [ ] Imagens geradas em background quando ingresso emitido
- [ ] Cache de imagens implementado (Redis ou filesystem)
- [ ] Endpoint retorna imagem do cache se disponível
- [ ] Fallback para geração síncrona se cache não existe
- [ ] Purge de cache antigo (configurável)

**Estimativa:** 8 pontos

**Labels:** `backend`, `performance`, `imaging`, `jobs`

---

#### [G5] Implementar testes unitários para novos endpoints
**Descrição:**
- Criar testes unitários para todos os novos endpoints
- Cobertura mínima de 80%
- Testes de casos de sucesso e erro
- Mocks apropriados

**Critérios de Aceite:**
- [ ] Testes para endpoints de validação de token
- [ ] Testes para busca de participantes
- [ ] Testes para validação de QR
- [ ] Testes para upload de planilhas
- [ ] Testes para inscrições individuais
- [ ] Cobertura ≥ 80% nos novos módulos
- [ ] Testes passam em CI/CD

**Framework:** pytest (já utilizado no projeto)

**Estimativa:** 13 pontos

**Labels:** `backend`, `tests`, `quality`

---

#### [G6] Implementar testes E2E para fluxos principais (Mobile)
**Descrição:**
- Criar testes E2E para fluxos críticos mobile
- Testes de login com token
- Testes de busca e impressão
- Testes de scanner QR

**Critérios de Aceite:**
- [ ] Teste E2E: login com token válido/inválido
- [ ] Teste E2E: fluxo de busca e impressão de bilhete
- [ ] Teste E2E: fluxo de scanner QR e check-in
- [ ] Testes executam em ambiente de staging
- [ ] CI/CD configurado para rodar testes E2E

**Frameworks Sugeridos:**
- React Native: Detox
- Flutter: integration_test

**Estimativa:** 13 pontos

**Labels:** `mobile`, `tests`, `e2e`, `quality`

---

#### [G7] Documentar APIs com OpenAPI/Swagger
**Descrição:**
- Atualizar documentação Swagger com novos endpoints
- Incluir exemplos de request/response
- Documentar códigos de erro
- Incluir informações de autenticação/autorização

**Critérios de Aceite:**
- [ ] Todos os novos endpoints documentados no Swagger
- [ ] Exemplos de request/response incluídos
- [ ] Códigos de status HTTP documentados
- [ ] Modelos de dados documentados
- [ ] Esquemas de autenticação atualizados
- [ ] Documentação acessível via /docs

**Estimativa:** 5 pontos

**Labels:** `backend`, `docs`, `api`

---

#### [G8] Criar guia de configuração e deployment
**Descrição:**
- Documentar variáveis de ambiente necessárias
- Guia de instalação e configuração
- Instruções de deployment (Docker, cloud)
- Troubleshooting comum

**Critérios de Aceite:**
- [ ] README atualizado com novas funcionalidades
- [ ] Variáveis de ambiente documentadas
- [ ] Guia de instalação passo a passo
- [ ] Instruções de deployment para produção
- [ ] Seção de troubleshooting
- [ ] Exemplos de configuração

**Estimativa:** 3 pontos

**Labels:** `docs`, `deployment`

---

#### [G9] Implementar logging e monitoramento
**Descrição:**
- Adicionar logs estruturados para operações críticas
- Implementar rastreamento de erros (Sentry/similar)
- Métricas de performance
- Alertas para falhas

**Critérios de Aceite:**
- [ ] Logs estruturados (JSON) para todas operações
- [ ] Integração com Sentry ou similar para erros
- [ ] Logs incluem: timestamp, level, user_id, action, resultado
- [ ] Métricas de API (response time, error rate)
- [ ] Dashboard básico de monitoramento

**Estimativa:** 8 pontos

**Labels:** `backend`, `infra`, `monitoring`, `observability`

---

#### [G10] Implementar rate limiting e proteção contra abuso
**Descrição:**
- Adicionar rate limiting em endpoints públicos
- Proteção contra force brute em login
- Validação de uploads (anti-malware básico)
- Throttling de requests

**Critérios de Aceite:**
- [ ] Rate limiting em endpoints públicos (ex: 100 req/min por IP)
- [ ] Rate limiting em upload de planilhas (5 uploads/hora)
- [ ] Rate limiting em inscrições (10 inscrições/hora por IP)
- [ ] Validação de tipo de arquivo (magic bytes)
- [ ] Retorna 429 quando limite excedido

**Bibliotecas Sugeridas:**
- slowapi para FastAPI
- Redis para armazenar contadores

**Estimativa:** 5 pontos

**Labels:** `backend`, `security`, `rate-limiting`

---

**Estimativa Total Epic G:** 73 pontos
**Prioridade:** Alta (segurança e testes) / Média (docs e monitoring)
**Dependências:** Todos os epics anteriores para testes completos

---

## 📐 Modelos de API - Referência Rápida

### Autenticação e Tokens
```
POST /api/v1/tokens/validate
Body: { "token": "abc123", "type": "bilheteria" }
Response: { "valid": true, "event_id": "...", "scopes": [...] }
```

### Bilheteria
```
GET /api/v1/events/{eventId}/participants?query={q}
Authorization: Bearer {token_bilheteria}
Response: { "total": 10, "results": [...] }

GET /api/v1/events/{eventId}/participants/{participantId}/ticket-image
Authorization: Bearer {token_bilheteria}
Response: image/png
```

### Portaria
```
POST /api/v1/validate/qr
Authorization: Bearer {token_portaria}
Body: { "qr_data": "...", "ilha_id": "..." }
Response: { "valid": true, "access_granted": true, "participant": {...} }

POST /api/v1/tickets/{ticketId}/checkin
Authorization: Bearer {token_portaria}
Body: { "ilha_id": "...", "device_id": "..." }
Response: { "success": true, "checkin_id": "..." }
```

### Upload de Planilhas
```
POST /api/v1/events/{eventId}/company-uploads
Authorization: Bearer {admin_token}
Content-Type: multipart/form-data
Response: { "job_id": "...", "status": "queued" }

GET /api/v1/uploads/{job_id}/status
Authorization: Bearer {admin_token}
Response: { "status": "completed", "progress": {...}, "errors": [...] }
```

### Inscrições Individuais
```
GET /api/v1/events/{eventId}/registration-fields
Response: { "fields": [...] }

POST /api/v1/events/{eventId}/registrations
Body: { "nome": "...", "email": "...", "cpf": "...", ... }
Response: { "success": true, "ticket_id": "..." }
```

---

## 🛠️ Decisões Técnicas Consolidadas

### Backend
- **Framework:** FastAPI (já em uso)
- **Banco de Dados:** MongoDB (já em uso)
- **Jobs Assíncronos:** Celery ou RQ com Redis
- **QR Code:** Biblioteca qrcode + assinatura JWT/HMAC
- **Geração de Imagens:** Pillow
- **Processamento de Planilhas:** pandas/openpyxl
- **Autenticação:** JWT (Bearer tokens) + tokens específicos por evento

### Mobile
- **Stack:** A confirmar (React Native ou Flutter)
- **Armazenamento Seguro:** 
  - React Native: `react-native-keychain`
  - Flutter: `flutter_secure_storage`
- **Scanner QR:**
  - React Native: `react-native-camera` ou `react-native-qrcode-scanner`
  - Flutter: `qr_code_scanner` ou `mobile_scanner`
- **Impressão:**
  - React Native: `react-native-print` + `react-native-thermal-receipt-printer`
  - Flutter: `printing` + `esc_pos_printer`

### Segurança
- **QR Code:** JWT com expiração ou HMAC-SHA256
- **Tokens API:** Bearer tokens com scopes
- **Secrets:** Armazenados em variáveis de ambiente
- **Rate Limiting:** slowapi (FastAPI)
- **Validação de Upload:** Validação de magic bytes e extensão

### Infraestrutura
- **Cache:** Redis (para jobs, rate limiting, cache de imagens)
- **Storage de Arquivos:** Filesystem local ou S3-compatible
- **Logging:** Logs estruturados (JSON) + Sentry
- **CI/CD:** Executar testes unitários e E2E automaticamente
- **Deployment:** Docker + Docker Compose (produção: Kubernetes ou similar)

---

## 📊 Resumo de Estimativas

| Epic | Descrição | Pontos | Prioridade |
|------|-----------|--------|------------|
| **A** | Reorganizar tela de teste de impressora | 7 | Alta |
| **B** | Tela principal de Token | 16 | Alta |
| **C** | Fluxo Bilheteria | 31 | Alta |
| **D** | Fluxo Portaria | 26-39* | Alta |
| **E** | Upload de planilhas | 36 | Média |
| **F** | Inscrições individuais | 29-34* | Média |
| **G** | Infra, segurança, testes, docs | 73 | Alta/Média |
| **TOTAL** | | **218-236** | |

*\* Varia com itens opcionais*

---

## 🎯 Roadmap de Implementação Sugerido

### Fase 1 - Fundação Mobile (Sprints 1-2)
- Epic A: Reorganização de telas
- Epic B: Sistema de tokens
- Início de Epic G: Segurança básica e autenticação

### Fase 2 - Bilheteria (Sprints 3-4)
- Epic C: Fluxo completo de bilheteria
- Continuação Epic G: Testes para bilheteria

### Fase 3 - Portaria (Sprints 5-6)
- Epic D: Fluxo de portaria com QR
- Continuação Epic G: Testes para portaria

### Fase 4 - Gestão de Participantes (Sprints 7-9)
- Epic E: Upload de planilhas
- Epic F: Inscrições individuais
- Continuação Epic G: Jobs, validações, testes

### Fase 5 - Finalização (Sprint 10)
- Epic G: Documentação, monitoring, deployment
- Refinamentos e ajustes finais
- Testes E2E completos

---

## 📝 Próximos Passos

1. **Validar stack mobile** — Confirmar se será React Native ou Flutter
2. **Revisar e priorizar épicos** — Ajustar prioridades conforme necessidades de negócio
3. **Criar issues no GitHub** — Converter cada subtarefa deste documento em issue
4. **Configurar projeto mobile** — Scaffold inicial do app mobile
5. **Setup de infraestrutura** — Redis, Celery/RQ, ambiente de desenvolvimento
6. **Iniciar Sprint 1** — Épicos A e B

---

## 📌 Observações Finais

- Este documento é um **backlog vivo** e deve ser atualizado conforme o projeto evolui
- Estimativas são baseadas em pontos (Fibonacci) e devem ser refinadas pela equipe
- Prioridades podem ser ajustadas conforme necessidades de negócio
- Dependências entre épicos devem ser respeitadas para evitar retrabalho
- Testes e documentação são parte integral de cada epic, não devem ser deixados para depois
- Segurança deve ser considerada desde o início, não como add-on posterior

---

**Documento criado em:** 2026-01-22  
**Versão:** 1.0  
**Responsável:** Equipe de Desenvolvimento Ticket Manager
