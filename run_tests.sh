#!/usr/bin/env bash
# Script para executar testes com diferentes configurações

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   Ticket Manager - Test Runner${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Verificar se requirements-test.txt está instalado
echo -e "${YELLOW}Verificando dependências de teste...${NC}"
if ! python -c "import pytest" 2>/dev/null; then
    echo -e "${RED}Pytest não encontrado. Instalando dependências...${NC}"
    pip install -r requirements-test.txt
fi

# Função para executar testes
run_tests() {
    local test_type=$1
    shift
    echo -e "${YELLOW}Executando ${test_type}...${NC}"
    pytest "$@"
    local exit_code=$?
    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}✓ ${test_type} passou!${NC}"
    else
        echo -e "${RED}✗ ${test_type} falhou!${NC}"
    fi
    echo ""
    return $exit_code
}

# Parse argumentos
case "${1:-all}" in
    "quick")
        echo "Modo Rápido: Executando testes sem cobertura"
        run_tests "Testes Rápidos" -v
        ;;
    
    "coverage")
        echo "Modo Cobertura: Executando testes com relatório de cobertura"
        run_tests "Testes com Cobertura" --cov=app --cov-report=html --cov-report=term
        echo -e "${GREEN}Relatório de cobertura HTML gerado em: htmlcov/index.html${NC}"
        ;;
    
    "admin")
        echo "Testando apenas endpoints administrativos"
        run_tests "Testes Admin" tests/test_admin_endpoints.py -v
        ;;
    
    "bilheteria")
        echo "Testando apenas endpoints de bilheteria"
        run_tests "Testes Bilheteria" tests/test_bilheteria_endpoints.py -v
        ;;
    
    "portaria")
        echo "Testando apenas endpoints de portaria"
        run_tests "Testes Portaria" tests/test_portaria_endpoints.py -v
        ;;
    
    "auth")
        echo "Testando apenas autenticação"
        run_tests "Testes Autenticação" tests/test_authentication.py -v
        ;;
    
    "integration")
        echo "Testando apenas fluxos de integração"
        run_tests "Testes Integração" tests/test_integration.py -v
        ;;
    
    "unit")
        echo "Testando apenas testes unitários (excluindo integração)"
        run_tests "Testes Unitários" tests/ -v --ignore=tests/test_integration.py
        ;;
    
    "all")
        echo "Executando TODOS os testes"
        run_tests "Todos os Testes" --cov=app --cov-report=html --cov-report=term-missing -v
        echo -e "${GREEN}Relatório de cobertura HTML gerado em: htmlcov/index.html${NC}"
        ;;
    
    "ci")
        echo "Modo CI/CD: Executando testes para integração contínua"
        run_tests "Testes CI" --cov=app --cov-report=xml --cov-report=term -v
        ;;
    
    "watch")
        echo "Modo Watch: Executando testes em modo watch (requer pytest-watch)"
        if ! python -c "import pytest_watch" 2>/dev/null; then
            echo -e "${YELLOW}pytest-watch não encontrado. Instalando...${NC}"
            pip install pytest-watch
        fi
        ptw -- -v
        ;;
    
    "help"|"-h"|"--help")
        echo "Uso: $0 [modo]"
        echo ""
        echo "Modos disponíveis:"
        echo "  quick        - Testes rápidos sem cobertura"
        echo "  coverage     - Testes com relatório de cobertura HTML"
        echo "  admin        - Apenas testes de endpoints administrativos"
        echo "  bilheteria   - Apenas testes de bilheteria"
        echo "  portaria     - Apenas testes de portaria"
        echo "  auth         - Apenas testes de autenticação"
        echo "  integration  - Apenas testes de integração"
        echo "  unit         - Apenas testes unitários"
        echo "  all          - Todos os testes com cobertura (padrão)"
        echo "  ci           - Modo CI/CD (XML coverage)"
        echo "  watch        - Modo watch (auto-reload)"
        echo "  help         - Mostra esta mensagem"
        echo ""
        echo "Exemplos:"
        echo "  $0              # Executa todos os testes"
        echo "  $0 quick        # Executa testes rápidos"
        echo "  $0 coverage     # Gera relatório de cobertura"
        echo "  $0 admin        # Testa apenas endpoints admin"
        ;;
    
    *)
        echo -e "${RED}Modo desconhecido: $1${NC}"
        echo "Use '$0 help' para ver os modos disponíveis"
        exit 1
        ;;
esac

exit $?
