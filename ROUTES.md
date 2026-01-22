# EventMaster API — Rotas (Resumo para Mobile)

> Documentação gerada automaticamente a partir do código do backend. Use-a como referência rápida para integração do app mobile.

---

## 📌 Visão geral
- Base URL (exemplo): `https://<host>`
- Versão da API: 1.0.0
- Principais módulos:
  - **Admin API**: `/api/admin` (requer autenticação admin)
  - **Bilheteria**: `/api/bilheteria` (requer token de bilheteria)
  - **Portaria**: `/api/portaria` (requer token de portaria)
  - **Coletor de Leads**: `/api/leads` (público)
  - **Inscrição pública / API de inscrição**: `/inscricao` (frontend) e `/api/inscricao` (API pública)
  - **Eventos (render/meta/capture)**: `/api/eventos`

---

## 🔐 Autenticação / Headers
- Admin: `Authorization: Bearer <JWT>` (preferível) ou `X-Admin-Key: <legacy-key>`
- Bilheteria: `X-Token-Bilheteria: <token>` (header obrigatório)
- Portaria: `X-Token-Portaria: <token>` (header obrigatório)
- Upload público (planilha): link com `token` na URL (`/upload/{token}`)

> Observação: endpoints administrativos usam a dependência `verify_admin_access` (aceita Bearer JWT ou X-Admin-Key para compatibilidade).

---

## 🗂️ Endpoints por módulo

### 1) Raiz & Health
- GET `/` — informações gerais (docs, módulos)
- GET `/health` — `{ "status": "healthy" }`

---

### 2) Admin Web UI (HTML) — prefix `/admin`
- GET `/admin/login` — página HTML de login
- POST `/admin/login` — form `username`, `password` (seta cookie `admin_jwt`) — uso UI

> Para mobile, prefira um endpoint JSON de login; atualmente o login via UI retorna cookie. Posso adicionar um endpoint JSON se preferir.

---

### 3) Admin API — prefix `/api/admin` (Requer admin auth)
- GET `/api/admin/eventos` — lista eventos (query: `skip`, `limit`)
- GET `/api/admin/eventos/{evento_id}` — obter evento
- POST `/api/admin/eventos` — criar evento (body `EventoCreate`)
- PUT `/api/admin/eventos/{evento_id}` — atualizar evento (body `EventoUpdate`)
- DELETE `/api/admin/eventos/{evento_id}` — deletar evento

- Ilhas:
  - GET `/api/admin/eventos/{evento_id}/ilhas` — listar ilhas
  - POST `/api/admin/ilhas` — criar ilha (body `IlhaCreate`)
  - PUT `/api/admin/ilhas/{ilha_id}` — atualizar ilha
  - DELETE `/api/admin/ilhas/{ilha_id}` — deletar ilha

- Tipos de ingresso:
  - GET `/api/admin/eventos/{evento_id}/tipos-ingresso` — listar
  - POST `/api/admin/tipos-ingresso` — criar (body `TipoIngressoCreate`)
  - PUT `/api/admin/tipos-ingresso/{tipo_id}` — atualizar
  - DELETE `/api/admin/tipos-ingresso/{tipo_id}` — deletar

- Relatórios & utilitários:
  - GET `/api/admin/eventos/{evento_id}/relatorio-vendas` — json de vendas
  - GET `/api/admin/eventos/{evento_id}/exportar-leads` — XLSX (attachment)
  - GET `/api/admin/eventos/{evento_id}/planilha-modelo` — XLSX modelo
  - POST `/api/admin/emitir` — body `{evento_id, tipo_ingresso_id, participante_id}` (emissão via admin)
  - POST `/api/admin/eventos/{evento_id}/planilha-upload` — upload planilha (auth admin)

---

### 4) Bilheteria — prefix `/api/bilheteria` (Requer `X-Token-Bilheteria`)
- GET `/api/bilheteria/evento` — retorna `EventoInfo` (token no header)
- POST `/api/bilheteria/participantes` — cria participante (body `ParticipanteCreate`) → 201
- POST `/api/bilheteria/emitir` — body `{ tipo_ingresso_id, participante_id }` → 201 (retorna `EmissaoIngressoResponse` with `ingresso` + `layout_preenchido`)
- GET `/api/bilheteria/participante/{participante_id}` — obter participante
- GET `/api/bilheteria/participantes/buscar?nome=&email=&cpf=` — busca (limit 20)
- GET `/api/bilheteria/busca-credenciamento?nome=&email=` — busca otimizada para reimpressão
- POST `/api/bilheteria/reimprimir/{ingresso_id}` — reimprime ingresso (retorna `EmissaoIngressoResponse`)

Cabeçalho obrigatório: `X-Token-Bilheteria: <token>`

---

### 5) Portaria — prefix `/api/portaria` (Requer `X-Token-Portaria`)
- GET `/api/portaria/evento` — `EventoInfoPortaria`
- GET `/api/portaria/ingresso/{qrcode_hash}` — `IngressoDetalhes` (mostra antes de validar)
- POST `/api/portaria/validar` — body `{ qrcode_hash, ilha_id }` — valida acesso e registra validação (retorna `ValidacaoResponse` ou 403)
- GET `/api/portaria/ilhas` — lista ilhas do evento
- GET `/api/portaria/estatisticas` — estatísticas de validações

Cabeçalho obrigatório: `X-Token-Portaria: <token>`

---

### 6) Coleta de Leads — prefix `/api/leads` (Público)
- POST `/api/leads/coletar` — body `{ qrcode_hash, origem }` → 201 (cria `LeadInteracao`)
- GET `/api/leads/interacoes/{evento_id}?origem=` — lista interações
- GET `/api/leads/estatisticas/{evento_id}` — estatísticas (total, por origem, participantes únicos)

---

### 7) Inscrição pública — prefix `/inscricao` e `/api/inscricao`
- GET `/inscricao/{evento_slug}` — retorna campos e metadados para formulário público (só se `aceita_inscricoes`)
- GET `/inscricao/{evento_slug}/meu-ingresso` — página HTML
- POST `/inscricao/{evento_slug}/buscar-ingresso` — body `{ cpf }` → retorna `{ ingresso_id, evento_id }`
- POST `/inscricao/{evento_slug}` — body `ParticipanteCreate` → cria participante e ingresso padrão → 201

---

### 8) Eventos / Rendering — prefix `/api/eventos`
- GET `/api/eventos/{evento_id}/ingresso/{ingresso_id}/render.jpg?dpi=300` — retorna JPG renderizado do ingresso
  - Suporta cache: retorna `ETag` e `Cache-Control`; respeita `If-None-Match` / `If-Modified-Since` (304 quando não modificado)
- GET `/api/eventos/{evento_id}/ingresso/{ingresso_id}/meta` — meta (nome, tipo, data_emissao)
- POST `/api/eventos/{evento_id}/ingresso/{ingresso_id}/capture` — multipart file (salva foto vinculada ao ingresso)

---

### 9) Planilha upload pública (token) — prefix `/api/admin`
- GET `/api/admin/upload/{token}` — formulário HTML público
- POST `/api/admin/upload/{token}` — upload planilha pública (processa import)

---

## 🔁 Modelos úteis (resumo)
- ParticipanteCreate: `nome, email, cpf, telefone?, empresa?, nacionalidade?`
- EmissaoIngressoRequest: `tipo_ingresso_id, participante_id`
- LeadInteracaoCreate: `qrcode_hash, origem`
- ValidacaoRequest: `qrcode_hash, ilha_id`
- IngressoEmitido: `_id, evento_id, tipo_ingresso_id, participante_id, status, qrcode_hash, data_emissao`

> Para modelos completos, ver `app/models/*.py` (ex.: `participante.py`, `ingresso_emitido.py`, `lead_interacao.py`).

---

## 💡 Dicas para integração mobile
- Use `X-Token-Bilheteria` para ações de bilheteria (emissão, busca, reimpressão).
- Use `X-Token-Portaria` para validação de acesso na portaria.
- Para imagens de ingresso, use `If-None-Match` com o `ETag` retornado para economizar banda.
- Se preferir login JSON para admins, recomendo adicionar um endpoint POST `/api/admin/login` que retorne um JWT (atualmente o login web seta cookie).

---

## ✅ Próximos passos que posso fazer
- Gerar arquivo OpenAPI / swagger JSON ou YAML
- Criar collection Postman
- Implementar endpoint de login JSON para mobile

---

> Arquivo gerado automaticamente a partir do código-fonte. Se quiser, adapto para gerar OpenAPI/Postman.
