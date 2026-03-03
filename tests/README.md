# Guia de Testes - Ticket Manager

## 📋 Visão Geral

Esta suíte de testes fornece cobertura abrangente para toda a aplicação Ticket Manager, incluindo testes unitários, de integração e end-to-end.

## 🏗️ Estrutura de Testes

```
tests/
├── conftest.py                      # Fixtures e configuração compartilhada
├── test_admin_endpoints.py          # Testes dos endpoints administrativos
├── test_bilheteria_endpoints.py     # Testes dos endpoints de bilheteria
├── test_portaria_endpoints.py       # Testes dos endpoints de portaria
├── test_authentication.py           # Testes de autenticação e autorização
├── test_integration.py              # Testes de integração (fluxos completos)
├── test_phase*.py                   # Testes existentes (mantidos)
└── README.md                        # Este arquivo
```

## 🚀 Instalação

### 1. Instalar Dependências de Teste

```bash
pip install -r requirements-test.txt
```

### 2. Configurar Ambiente

```bash
cp .env.example .env
# Edite .env conforme necessário para testes
```

## ▶️ Executando os Testes

### Executar Todos os Testes

```bash
pytest
```

### Executar com Cobertura

```bash
pytest --cov=app --cov-report=html --cov-report=term
```

### Executar Testes Específicos

```bash
# Testes de um módulo específico
pytest tests/test_admin_endpoints.py

# Testes de uma classe específica
pytest tests/test_admin_endpoints.py::TestEventosAdmin

# Teste individual
pytest tests/test_admin_endpoints.py::TestEventosAdmin::test_create_evento_success

# Testes por marcador
pytest -m asyncio
```

### Executar com Verbosidade

```bash
# Modo verbose
pytest -v

# Modo extra verbose com saída
pytest -vv -s
```

### Executar Testes em Paralelo

```bash
# Instalar pytest-xdist
pip install pytest-xdist

# Executar em paralelo
pytest -n auto
```

## 📊 Cobertura de Testes

### Módulos Cobertos

1. **Endpoints Administrativos** (`test_admin_endpoints.py`)
   - ✅ CRUD de Eventos
   - ✅ CRUD de Ilhas/Setores
   - ✅ CRUD de Tipos de Ingresso
   - ✅ Relatórios de Vendas
   - ✅ Paginação
   - ✅ Tratamento de Erros

2. **Endpoints de Bilheteria** (`test_bilheteria_endpoints.py`)
   - ✅ Cadastro de Participantes
   - ✅ Busca de Participantes (nome, CPF, email)
   - ✅ Emissão de Ingressos
   - ✅ Reimpressão de Ingressos
   - ✅ Geração de QR Codes
   - ✅ Validação de CPF

3. **Endpoints de Portaria** (`test_portaria_endpoints.py`)
   - ✅ Validação de QR Codes
   - ✅ Controle de Acesso por Setores
   - ✅ Verificação de Permissões
   - ✅ Estatísticas de Validação
   - ✅ Segurança e Autenticação

4. **Autenticação** (`test_authentication.py`)
   - ✅ JWT (criação, validação, expiração)
   - ✅ Tokens de Bilheteria
   - ✅ Tokens de Portaria
   - ✅ Autenticação de Administradores
   - ✅ Hashing de Senhas
   - ✅ Middleware de Autorização

5. **Integração** (`test_integration.py`)
   - ✅ Fluxo Completo de Evento
   - ✅ Fluxo Completo de Credenciamento
   - ✅ Fluxo Completo de Validação
   - ✅ Múltiplos Participantes
   - ✅ Geração de Relatórios
   - ✅ Tratamento de Erros

## 🎯 Fixtures Disponíveis

Todas as fixtures estão definidas em `conftest.py`:

- `fake_db`: Banco de dados MongoDB mockado
- `sample_evento`: Evento de exemplo
- `sample_ilha`: Ilha/Setor de exemplo
- `sample_tipo_ingresso`: Tipo de ingresso de exemplo
- `sample_participante`: Participante de exemplo
- `sample_ingresso`: Ingresso emitido de exemplo
- `mock_get_database`: Mock da função get_database
- `mock_verify_admin`: Mock da autenticação admin
- `mock_verify_bilheteria`: Mock da autenticação bilheteria
- `mock_verify_portaria`: Mock da autenticação portaria

## 📝 Convenções de Teste

### Nomenclatura

- Classes de teste: `Test<Módulo><Funcionalidade>`
- Métodos de teste: `test_<ação>_<cenário>`

Exemplos:
- `TestEventosAdmin::test_create_evento_success`
- `TestValidacaoPortaria::test_validar_acesso_negado_sem_permissao`

### Estrutura de um Teste

```python
@pytest.mark.asyncio
async def test_example(self, fake_db, mock_get_database, sample_evento):
    """Docstring descrevendo o que o teste faz."""
    # 1. Arrange (preparar)
    fake_db.eventos.docs.append(sample_evento)
    
    # 2. Act (executar)
    result = await some_function(sample_evento["_id"])
    
    # 3. Assert (verificar)
    assert result.nome == "Expected Name"
```

## 🔍 Debugging de Testes

### Ver Logs Durante Testes

```bash
pytest -s
```

### Parar no Primeiro Erro

```bash
pytest -x
```

### Ver Traceback Completo

```bash
pytest --tb=long
```

### Usar Debugger

```python
import pytest

@pytest.mark.asyncio
async def test_with_debugger():
    # ... código de teste ...
    import pdb; pdb.set_trace()  # Breakpoint
    # ... mais código ...
```

## 📈 Métricas de Qualidade

### Cobertura Alvo

- **Objetivo Mínimo**: 80%
- **Objetivo Ideal**: 90%+

### Verificar Cobertura Atual

```bash
pytest --cov=app --cov-report=term-missing
```

Isso mostrará quais linhas não estão cobertas.

### Gerar Relatório HTML

```bash
pytest --cov=app --cov-report=html
open htmlcov/index.html  # Linux/Mac
start htmlcov/index.html  # Windows
```

## 🛠️ Ferramentas Adicionais

### pytest-watch (Auto-reload)

```bash
pip install pytest-watch
ptw
```

### pytest-testmon (Executar apenas testes afetados)

```bash
pip install pytest-testmon
pytest --testmon
```

## ⚠️ Problemas Comuns

### Testes Falhando por Timeout

```bash
# Aumentar timeout
pytest --timeout=300
```

### Conflitos de MongoDB

Os testes usam banco de dados mockado (FakeDB), então não há conflito com instâncias reais do MongoDB.

### Problemas com Fixtures Assíncronas

Certifique-se de usar `@pytest.mark.asyncio` em todos os testes assíncronos.

## 🚦 CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-test.txt
      - name: Run tests
        run: pytest --cov=app --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

## 📚 Recursos Adicionais

- [Pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Coverage.py](https://coverage.readthedocs.io/)

## 🤝 Contribuindo com Testes

Ao adicionar novas funcionalidades:

1. **Escreva os testes primeiro** (TDD) ou junto com o código
2. **Cubra casos de sucesso e erro**
3. **Use fixtures existentes** quando possível
4. **Documente comportamentos complexos**
5. **Mantenha testes independentes** (sem dependências entre testes)
6. **Execute toda a suíte** antes de fazer commit

## 📊 Status Atual

```
Total de Testes: 100+
Cobertura: ~85%
Tempo de Execução: ~10-15 segundos
```

---

**Última Atualização**: 2026-01-22  
**Mantido por**: Equipe de Desenvolvimento Ticket Manager
