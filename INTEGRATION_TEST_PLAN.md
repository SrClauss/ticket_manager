# Plano de Implementação — Testes de Integração Robustos

Data: 2026-01-22T17:21:34.438Z

Objetivo
- Definir e implementar uma suíte de testes de integração abrangente para validar todos os fluxos críticos do sistema (inscrições públicas, upload/processamento de planilhas por empresas, emissão de ingressos, renderização de ingressos, bilheteria, portaria, administração de eventos e geração de planilhas modelo).

Escopo
- Cobrir as rotas HTTP públicas e administrativas (UI endpoints server-rendered e API endpoints).
- Cobrir processamento de arquivos (.xlsx/.csv) e regras de negócio (validação de CPF, unicidade por evento, regra de `padrao` em tipos de ingresso, geração de tokens, geração e download de planilha modelo).
- Testar renderização de ingresso (endpoint que retorna JPG) e fluxo "meu ingresso" (busca por CPF -> redirecionamento para página do ingresso).
- Incluir testes de concorrência para garantir a consistência da regra "CPF único por evento".

Ferramentas e dependências propostas
- pytest + pytest-asyncio
- httpx AsyncClient / FastAPI TestClient para chamadas HTTP
- motor (ou a mesma camada de acesso usada em produção) apontando para um MongoDB de teste em Docker (preferível) ou Testcontainers para testes isolados
- openpyxl para gerar .xlsx de teste
- faker para dados sintéticos
- freezegun para congelar tempo quando necessário
- pytest-xdist (execução paralela) opcional

Estratégia de Infraestrutura de Teste
1. Usar um serviço MongoDB isolado por pipeline/runner (docker-compose.test.yml ou Testcontainers) com banco nomeado por job/ID para evitar cross-talk.
2. Armazenamento de arquivos em diretório temporário (tmpdir fixture) durante testes; apontar app static/uploads/tests para esse diretório.
3. Variáveis de ambiente de testes: MONGO_URI_TEST, TEST_STATIC_DIR, SKIP_EXTERNAL_CALLS=1.
4. Scripts/compose para levantar dependências no CI (mongodb) e rodar pytest.

Organização dos testes
- tests/integration/
  - conftest.py (fixtures compartilhadas)
  - test_eventos_api.py (criação/atualização/get de eventos, nome_normalizado automático)
  - test_tipos_ingresso_sequence.py (sequenciamento e regra padrao)
  - test_inscricao_publica.py (GET formulário, POST inscrição, conflitos 409)
  - test_planilha_modelo.py (download do modelo, conteúdo e fórmulas)
  - test_planilha_upload_public.py (fluxo via token: gerar link, upload por empresa, relatório, registro)
  - test_admin_planilhas_ui.py (rotas/snapshots de UI relevantes)
  - test_emissao_bilheteria.py (validação de CPF único na emissão)
  - test_evento_ingresso_render.py (render.jpg retorna image/jpeg, ETag e conteúdo esperado)
  - test_capture_endpoint.py (upload de imagem capturada)
  - test_concurrency_cpf_unique.py (cenários concorrentes para mesma CPF)
  - test_security_tokens.py (verificar acesso com/sem tokens corretos)

Fixtures recomendadas (em tests/integration/conftest.py)
- event_loop (pytest-asyncio)
- mongodb (setup/teardown): cria banco temporário, aplica índices (chamar create_indexes()) e, após cada teste, limpa coleções relevantes.
- app_client: TestClient apontando para app.main.app com as variáveis de ambiente de teste aplicadas.
- async_client: httpx AsyncClient ligado ao app para testes async diretos.
- temp_upload_dir: tmp_path fixture para isolar uploads.
- seeded_event: cria um evento com tipos de ingresso e ilhas pré-populados, retorna ids e documentos úteis.
- upload_xlsx_generator: helper que gera arquivos .xlsx válidos/inválidos rapidamente usando openpyxl.
- monkeypatch_auth: fixture para gerar e aplicar tokens JWT de admin (ou usar real create_initial_admin + login em testes integrados).

Detalhamento de casos de teste críticos
1. Modelos e índices
   - Verificar criação de índices únicos (nome_normalizado, (evento_id, numero), parcial padrao, (evento_id, participante_cpf)).
   - Testar que tentativas de duplicação geram erros esperados.

2. Sequência TipoIngresso
   - Criar N tipos sequenciais e verificar numeros 1..N e comportamento do campo padrao.
   - Marcar um tipo como padrao e verificar que os demais são desmarcados.

3. Inscrição pública
   - GET /inscricao/{slug} retorna campos obrigatórios corretos.
   - POST válido cria participante e ingresso; retorno 201 e dados esperados.
   - POST com CPF duplicado retorna 409.
   - Testar submissão com nome_normalizado faltando (usar ID fallback) — link copiado na UI deve funcionar.

4. Geração de Planilha Modelo
   - GET admin/eventos/{id}/planilha-modelo retorna .xlsx com abas Modelo, Legenda, Instrucao.
   - Verificar que colunas obrigatórias e fórmulas VLOOKUP estão presentes.

5. Upload por empresas (token)
   - Gerar token via admin UI (POST /admin/eventos/{id}/planilhas/empresas/generate) — verificar armazenamento do token.
   - GET /upload/{token} exibe form; POST /upload/{token} processa planilha.
   - Validar relatório resultante, status registrado em planilha_importacoes e resposta HTML de sucesso/partial/fail.

6. Emissão e validações na bilheteria/admin
   - POST /api/bilheteria/emitir e endpoint admin_emitir validam CPF único por evento.
   - Mensagens de erro 409 quando apropriado.

7. Renderização de ingresso (imagem)
   - Chamar GET /api/eventos/{evento_id}/ingresso/{ingresso_id}/render.jpg e validar:
     - status 200, content-type image/jpeg
     - headers Cache-Control e ETag presentes
     - responda 304 quando If-None-Match bater com ETag
     - validar que QR code e textos básicos foram desenhados (verificar tamanho do payload ou hash)

8. Fluxo "meu ingresso"
   - POST /api/inscricao/{slug}/buscar-ingresso com CPF válido retorna ingresso_id
   - Fluxo UI: submissão redireciona para /ingresso/{id} e página mostra <img src>/api/eventos/.../render.jpg

9. Upload de captura
   - POST /api/eventos/{evento}/ingresso/{ingresso}/capture salva imagem e grava caminho no DB

10. Concorrência
   - Simular N requisicoes paralelas POST /inscricao/{slug} com mesmo CPF e garantir apenas 1 ingresso criado e os demais recebem 409 ou são rejeitados de forma consistente.
   - Testar locks/atomicidade se necessário.

11. Segurança e tokens
   - Verificar que link de upload inválido retorna 404.
   - Verificar que endpoints administrativos requerem token JWT (testar acesso sem credenciais e com credenciais inválidas).

Qualidade e confiabilidade dos testes
- Usar dados gerados dinamicamente e fixtures para evitar dependências externas.
- Limpar estado entre testes (truncate coleções ou criar DB novo por teste).
- Evitar asserts frágeis em timestamps; usar freezegun se precisar verificar datas.
- Marcar testes de longa duração (ex.: concorrência) com marcação pytest -m slow e rodar separadamente se necessário.

Integração com CI (GitHub Actions sugestão)
- job: services: mongodb:latest
- steps:
  - checkout
  - setup python
  - pip install -r requirements.txt
  - export TEST env vars (e.g., TEST_STATIC_DIR=/tmp/test_uploads)
  - run pytest -q tests/integration --dist=loadscope -n auto (opcional xdist)
- Upload de artefatos: logs, relatórios (pytest-html), e arquivos de snapshot ao falhar

Métrica de cobertura e reporting
- Integrar cobertura apenas para a camada de integração (coverage run -m pytest)
- Gerar relatório pytest-html para análise de falhas

Plano de entrega (fases e estimativa)
1. Infra e fixtures (1-2 dias)
   - Docker compose/test setup, conftest com fixtures mongodb e app_client
2. Testes básicos de endpoints (2-3 dias)
   - Inscrição pública, criação evento, tipos ingresso
3. Testes de arquivos (2 dias)
   - Geração de planilha modelo, upload público via token, processamento
4. Renderização / Emissão / Capture (2 dias)
   - Tests para render.jpg, meta endpoints e capture
5. Concorrência e segurança (2 dias)
   - Tests para concorrência CPF único, tokens
6. CI e estabilização (1-2 dias)
   - Integração com GitHub Actions, ajustar tempo limite, retries, e relatórios

Exemplo de esqueleto de teste (pytest + httpx)

```python
# tests/integration/test_inscricao_publica.py
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_post_inscricao_creates_participant_and_ingresso(async_client: AsyncClient, seeded_event):
    cliente = async_client
    payload = {"nome":"Carlos","email":"carlos@example.com","cpf":"529.982.247-25"}
    resp = await cliente.post(f"/inscricao/{seeded_event['nome_normalizado']}", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert 'ingresso' in body
```

Checklist de implementação
- [ ] Criar /tests/integration/conftest.py com fixtures descritas
- [ ] Implementar helpers para geração de XLSX/CSV
- [ ] Implementar testes por arquivo descritos acima
- [ ] Configurar docker-compose.test.yml (mongodb)
- [ ] Adicionar job no CI rodando testes de integração e upload de relatórios
- [ ] Revisar e estabilizar testes com retries e tempos de espera controlados

Observações finais
- Preferir instância real de MongoDB em CI (via Docker) para reproduzir índices/behavior exato de produção; usar Testcontainers localmente se conveniente.
- Evitar usar `mongomock` para testes de integração críticos que dependem de índices únicos e comportamentos de transações.
- Priorizar testes de fluxo crítico (inscrições e uploads) antes de cobrir todos os caminhos auxiliares.


---

Implementação deste plano pode ser dividida em milestones pequenas para entrega incremental e integração contínua.
