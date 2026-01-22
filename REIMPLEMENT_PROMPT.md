# Plano de Reimplementação (Prompt) - Ticket Manager

Objetivo: Reimplementar, de forma simples e fiel ao especificado, as funcionalidades de inscrição, importação de planilhas e modelos de dados. Não introduzir micro-serviços nem filas externas; manter solução leve (BackgroundTasks quando necessário).

---

~~## Fase 1 — Modelos e Validações (Prioridade Alta) — COMPLETED nesta sessão em 2026-01-22T11:54:03Z~~
- Participante
  - Remover campo `cargo`.
  - Adicionar `cpf` (string, obrigatório) e `nacionalidade` (string, opcional).
  - Tornar `nome`, `email`, `cpf` obrigatórios; demais campos opcionais.
  - Validação de CPF (formato e dígito verificador).
  - Regra: CPF único por evento.
- TipoIngresso
  - Adicionar `numero` (int, único por evento, sequencial começando em 1).
  - Adicionar `padrao` (bool, default `false`).
  - Tornar `valor` opcional.
  - Regra: apenas um `padrao` por evento; ao criar primeiro tipo, marcar `padrao=True`.
- Evento
  - Adicionar `campos_obrigatorios_planilha: List[str]` com default `[]`.
  - Adicionar `token_inscricao` (string, token público para inscrição).

**Critério de aceitação:** modelos atualizados, validações unitárias cobrindo CPF e regra de `padrao`.

---

~~## Fase 2 — Índices no MongoDB (Prioridade Alta) — COMPLETED nesta sessão em 2026-01-22T12:09:58.675Z~~
- Criar índices únicos:
  - `eventos.token_inscricao` (unique)
  - `tipos_ingresso` composto: `(evento_id, numero)` unique
  - `tipos_ingresso` parcial: `(evento_id, padrao)` unique when `padrao=True`
  - `ingressos_emitidos` ou `participantes` (escolha a modelagem): `(evento_id, participante_cpf)` unique

**Critério de aceitação:** índices criados durante startup; documentar comandos/origem.

---

~~## Fase 3 — Sequência e Regras de Tipo de Ingresso (Prioridade Média) — COMPLETED nesta sessão em 2026-01-22T15:06:59.527Z~~
- Ao criar `TipoIngresso`:
  - Calcular `numero` como `max(numero)` + 1 dentro do evento (ou `1` se nenhum existir).
  - Se for o primeiro tipo do evento, setar `padrao=True`.
  - Ao marcar `padrao=True`, desmarcar `padrao` de outros tipos do evento.

**Critério de aceitação:** testes cobrindo criação sequencial e enforcement de `padrao`.

---

~~## Fase 4 — Inscrição Pública (Prioridade Alta) — COMPLETED nesta sessão em 2026-01-22T13:40:20.118Z~~
- Endpoint público: `GET /inscricao/{nome_normalizado}` (formulário) e `POST /inscricao/{nome_normalizado}` (envio)
- Fluxo e regras atualizadas:
  - Recupera `evento` pelo campo `nome_normalizado` (adicionado ao modelo de Evento). Ex.: "Show Do Gustavo Lima Limeira 2025" -> `showgustavolimalimeira2025`.
  - Índice único em `eventos.nome_normalizado` garante unicidade do slug usado na URL.
  - Novo campo no modelo Evento: `aceita_inscricoes: bool` (default `false`). O endpoint público só está disponível se `aceita_inscricoes` for `true`.
  - Regra de negócio: o administrador só pode ativar `aceita_inscricoes=True` se `campos_obrigatorios_planilha` incluir obrigatoriamente `Nome`, `Email` e `CPF` — caso contrário, a ativação falha com 400.
  - O formulário público retornado por GET inclui apenas os campos marcados como obrigatórios no evento (mas sempre garante `Nome`, `Email`, `CPF`).
  - POST valida CPF (formato + dígito verificador), normaliza para dígitos e verifica unicidade por evento; retorna 409 em caso de duplicação.
  - Encontra `TipoIngresso` com `padrao=True` para o evento e vincula automaticamente.
  - Cria `Participante` (ou reusa existente) e `IngressoEmitido` com `qrcode_hash`.
  - Ao ativar `aceita_inscricoes`, o sistema gera automaticamente uma planilha modelo estilizada (.xlsx) usando openpyxl e salva em `app/static/planilhas/{nome_normalizado}_modelo.xlsx`.
- Observação: o campo `token_inscricao` permanece no modelo mas não é usado pelo endpoint público conforme pedido do cliente.
- Simplicidade: processamento síncrono; não enfileirar.

**Critério de aceitação:** formulário público limitado aos campos obrigatórios do evento, validação de CPF e regra de ativação de inscrições aplicadas; geração automática de planilha modelo estilizada ao ativar inscrições; testes automatizados cobrindo formulário, inscrição e conflito por CPF (implementados).

---

## Fase 5 — Geração de Planilha Modelo (Prioridade Média) — COMPLETED nesta sessão em 2026-01-22T13:43:38.905Z
- Endpoint: `GET /api/admin/eventos/{evento_id}/planilha-modelo`
- Gera `.xlsx` com colunas:
  - Obrigatórias: `Nome`, `Email`, `CPF` (+ quaisquer `campos_obrigatorios_planilha`).
  - Opcionais: `Empresa`, `Telefone`, `Nacionalidade`, `Tipo Ingresso` (número inteiro).
- Aba `Legenda`: relação `numero -> descrição` dos tipos de ingresso (populada a partir de `tipos_ingresso`).
- Inclui uma coluna auxiliar `Tipo Ingresso Descricao` com fórmula VLOOKUP para facilitar o preenchimento a partir da aba `Legenda`.
- Aba `Instrucao`: instruções básicas sobre preenchimento e uso.
- Implementação usando `openpyxl` e retorno como download (StreamingResponse).

**Critério de aceitação:** arquivo `.xlsx` baixável e testado localmente; endpoint criado e integrado ao router administrativo; VLOOKUP incluído para conveniência.


---

~~## Fase 6 — Upload e Validação de Planilha (Prioridade Alta) — COMPLETED nesta sessão em 2026-01-22T15:06:59.527Z~~
- Endpoint: `POST /api/admin/eventos/{evento_id}/planilha-upload`
- Aceita `.xlsx` e `.csv`.
- Validações por linha:
  - Campos obrigatórios preenchidos.
  - CPF válido (formato + dígitos).
  - CPF único por evento (rejeitar/registrar erro se duplicado na planilha ou já existente).
  - Email com formato válido.
  - `Tipo Ingresso` (número) existe e pertence ao evento.
- Após validação:
  - Para cada linha válida: criar `Participante` (ou reusar) e `IngressoEmitido`.
  - Retornar relatório JSON: total linhas, criados, atualizados, erros (lista resumida).
- Implementação simples: processamento em `BackgroundTasks` (opcional) ou síncrono para pequenos arquivos.
- Registrar upload em `PlanilhaImportacao` com `status`, `relatorio`.

**Critério de aceitação:** upload processado, relatório gerado; status armazenado.

---

~~## Fase 7 — Tela Administrativa de Planilhas (Prioridade Média) — COMPLETED nesta sessão em 2026-01-22T15:06:59.527Z~~
- Página: `/admin/eventos/{evento_id}/planilhas`
- Funcionalidades:
  - Botão `Gerar Modelo de Planilha` (download).
  - Área de upload (drag-and-drop ou input file).
  - Histórico das `PlanilhaImportacao` com status e link para relatório/download.
  - Controle de `campos_obrigatorios_planilha` (checkboxes) e botão `Salvar`.

**Critério de aceitação:** UI integrada, sem sistemas externos.

---

~~## Fase 8 — Validações no Fluxo de Emissão (Prioridade Alta) — COMPLETED nesta sessão em 2026-01-22T15:09:29.192Z~~
- Emissão via bilheteria e admin devem validar CPF único por evento antes de criar ingresso.
- Mensagens de erro claras (conflict 409 quando duplicado).

**Critério de aceitação:** rotas `POST /api/bilheteria/emitir` e admin de emissão aplicam validação.

---

## Fase 9 — Testes e Migração (Prioridade Média)
- Testes unitários para validação de CPF, criação sequencial de `numero` e planilha parsing.
- Testes de integração manuais para upload/inscrição pública.
- NOTA: não faremos backfills automáticos — aplicar índices únicos apenas; se conflito existir, operador deverá decidir.

---

## Restrições e Decisões Arquiteturais (Regras do Cliente)
- Nada de micro-serviços, filas externas ou infra adicional.
- Solução simples: `BackgroundTasks` para processamento assíncrono leve; processamento síncrono para arquivos pequenos.
- Persistir `PlanilhaImportacao` na mesma base Mongo.

---

## Comandos úteis (para desenvolvedor)
```bash
cd /home/claus/src/ticket_manager
# Reset local to remoto
git fetch --all
git reset --hard origin/HEAD
# Criar ambiente e instalar deps
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# Rodar testes unitários
PYTHONPATH=$(pwd) venv/bin/pytest -q
```

---

## Fase Final — Exibição de Ingresso e Captura (Prioridade Baixa)
- Objetivo: permitir que participantes recuperem um ingresso já emitido via CPF, vejam o ingresso na tela (renderizado a partir do layout do tipo de ingresso / layout do evento) e capturem uma imagem (screenshot/foto) do ingresso para validar/mostrar no dia do evento.

- Requisitos funcionais:
  - Página pública: `/inscricao/{nome_normalizado}/meu-ingresso` que aceita CPF e, se um ingresso existir, redireciona para `GET /ingresso/{ingresso_id}` (página de visualização do ingresso).
  - Página de visualização do ingresso (`/ingresso/{ingresso_id}`) deve mostrar o ingresso renderizado em alta qualidade e oferecer um botão `Baixar JPG` e um botão `Capturar imagem` que ativa a câmera do dispositivo (via API Web) para tirar/registrar uma foto do ingresso em exibição.
  - Endpoint backend para gerar imagem a partir do layout: `GET /api/eventos/{evento_id}/ingresso/{ingresso_id}/render.jpg` — recebe o layout (do tipo de ingresso ou evento), aplica os dados do ingresso (nome, tipo, qrcode, data) nas posições definidas e retorna um JPG com as dimensões corretas (ex.: mm convertidos para px com DPI configurável).
  - O endpoint deve garantir que apenas ingressos realmente emitidos para o participante/ID sejam renderizados (validação de evento/ingresso).
  - O JPG deve incluir QR code embutido (renderizado) para validação rápida na portaria.
  - A página deve permitir ao usuário salvar/baixar o JPG; o botão `Capturar imagem` deve permitir salvar a cópia feita pelo usuário (ex.: upload opcional para armazenamento se desejado no futuro).

- Requisitos não funcionais/operacionais:
  - A renderização pode ser feita usando PIL/Pillow e uma biblioteca de QR code (já presente). Converter medidas mm->px assumindo 300 DPI por padrão.
  - Garantir cacheamento (HTTP cache headers) para evitar regeneração excessiva.
  - Logs de acesso/visualização podem ser registrados para auditoria.

- Prompt estruturado para implementação futura (para o dev/AI):
  """
  Implementar página pública de recuperação de ingresso e endpoint de renderização JPG:
  1. Criar rota GET /inscricao/{nome_normalizado}/meu-ingresso com formulário que pede CPF; ao submeter, chama API POST /api/inscricao/{nome_normalizado}/buscar-ingresso que retorna ingresso_id se encontrado, ou 404/409 conforme o caso.
  2. Criar página /ingresso/{ingresso_id} que consome /api/eventos/{evento_id}/ingresso/{ingresso_id}/render.jpg na tag <img> e mostra metadados (nome, tipo, data). Incluir botões: "Baixar JPG" (link direto) e "Capturar imagem" (JS que ativa câmera e permite salvar imagem localmente ou enviar para /api/ingresso/{ingresso_id}/capture).
  3. Backend: implementar GET /api/eventos/{evento_id}/ingresso/{ingresso_id}/render.jpg que:
     - Verifica existência do ingresso e carrega tipo_ingresso e evento.
     - Calcula dimensões a partir do layout (mm->px) e cria imagem PIL RGB com fundo branco.
     - Renderiza textos, QR code (usar qrcode lib) e quaisquer elementos do layout, seguindo posições e fontes básicas.
     - Retorna imagem em formato JPEG com qualidade configurável.
  4. Escrever testes unitários que mockem DB e verifiquem que o endpoint retorna um bytes object com header image/jpeg e que erros 404/403 são respeitados.
  """

- Observação: não será implementado nesta iteração; planejar como fase final no roadmap.

## Próximo passo sugerido
- Prosseguir com Fase 5 (Geração de planilha modelo) e validar download e conteúdo gerado. 
