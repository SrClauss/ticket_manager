# Plano de Reimplementação (Prompt) - Ticket Manager

Objetivo: Reimplementar, de forma simples e fiel ao especificado, as funcionalidades de inscrição, importação de planilhas e modelos de dados. Não introduzir micro-serviços nem filas externas; manter solução leve (BackgroundTasks quando necessário).

---

## Fase 1 — Modelos e Validações (Prioridade Alta)
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

## Fase 2 — Índices no MongoDB (Prioridade Alta)
- Criar índices únicos:
  - `eventos.token_inscricao` (unique)
  - `tipos_ingresso` composto: `(evento_id, numero)` unique
  - `tipos_ingresso` parcial: `(evento_id, padrao)` unique when `padrao=True`
  - `ingressos_emitidos` ou `participantes` (escolha a modelagem): `(evento_id, participante_cpf)` unique

**Critério de aceitação:** índices criados durante startup; documentar comandos/origem.

---

## Fase 3 — Sequência e Regras de Tipo de Ingresso (Prioridade Média)
- Ao criar `TipoIngresso`:
  - Calcular `numero` como `max(numero)` + 1 dentro do evento (ou `1` se nenhum existir).
  - Se for o primeiro tipo do evento, setar `padrao=True`.
  - Ao marcar `padrao=True`, desmarcar `padrao` de outros tipos do evento.

**Critério de aceitação:** testes cobrindo criação sequencial e enforcement de `padrao`.

---

## Fase 4 — Inscrição Pública (Prioridade Alta)
- Endpoint público: `GET /inscricao/{token_inscricao}` (formulário) e `POST /inscricao/{token_inscricao}` (envio)
- Fluxo:
  - Recupera `evento` pelo `token_inscricao`.
  - Formulário exige `nome`, `email`, `cpf` (outros campos conforme `campos_obrigatorios_planilha`).
  - Valida CPF único no evento.
  - Encontra `TipoIngresso` com `padrao=True` naquele evento; vincula automaticamente.
  - Cria `Participante` (ou reusa existente) e cria `IngressoEmitido`.
- Simplicidade: processamento síncrono; não enfileirar.

**Critério de aceitação:** página funcional e API que retorna sucesso + ingresso gerado.

---

## Fase 5 — Geração de Planilha Modelo (Prioridade Média)
- Endpoint: `GET /api/admin/eventos/{evento_id}/planilha-modelo`
- Gera `.xlsx` com colunas:
  - Obrigatórias: `Nome`, `Email`, `CPF` (+ quaisquer `campos_obrigatorios_planilha`).
  - Opcionais: `Empresa`, `Telefone`, `Nacionalidade`, `Tipo Ingresso` (número inteiro).
- Aba `Legenda`: relação `numero -> descrição` dos tipos de ingresso.
- Incluir instruções e fórmula VLOOKUP para conveniência.
- Implementação usando `openpyxl`.

**Critério de aceitação:** arquivo `.xlsx` baixável e testado localmente.

---

## Fase 6 — Upload e Validação de Planilha (Prioridade Alta)
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

## Fase 7 — Tela Administrativa de Planilhas (Prioridade Média)
- Página: `/admin/eventos/{evento_id}/planilhas`
- Funcionalidades:
  - Botão `Gerar Modelo de Planilha` (download).
  - Área de upload (drag-and-drop ou input file).
  - Histórico das `PlanilhaImportacao` com status e link para relatório/download.
  - Controle de `campos_obrigatorios_planilha` (checkboxes) e botão `Salvar`.

**Critério de aceitação:** UI integrada, sem sistemas externos.

---

## Fase 8 — Validações no Fluxo de Emissão (Prioridade Alta)
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

## Próximo passo sugerido
- Confirmar se aceita este plano faseado; após sua confirmação eu implemento Fase 1 (modelos e validações) e atualizo o `todo list`. 

