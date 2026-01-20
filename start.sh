#!/bin/bash

# Script de inicialização do EventMaster Admin
echo "🚀 Iniciando EventMaster Admin..."

# Verificar se o .env existe
if [ ! -f .env ]; then
    echo "📝 Criando arquivo .env a partir do .env.example..."
    cp .env.example .env
fi

# Parar containers existentes
echo "🛑 Parando containers existentes..."
docker compose down

# Construir e iniciar os serviços
echo "🏗️  Construindo e iniciando os serviços..."
docker compose up --build -d

# Aguardar serviços estarem prontos
echo "⏳ Aguardando serviços iniciarem..."
sleep 10

# Verificar status
echo "✅ Verificando status dos serviços..."
docker compose ps

echo ""
echo "======================================"
echo "✨ EventMaster Admin está rodando!"
echo "======================================"
echo ""
echo "📱 Acesse o painel admin em:"
echo "   http://localhost:8000/admin/login"
echo ""
echo "🔑 Chave de acesso padrão:"
echo "   admin_key_change_in_production"
echo ""
echo "📚 Documentação da API:"
echo "   http://localhost:8000/docs"
echo ""
echo "🔍 Verificar logs:"
echo "   docker compose logs -f fastapi"
echo ""
echo "🛑 Parar serviços:"
echo "   docker compose down"
echo ""
