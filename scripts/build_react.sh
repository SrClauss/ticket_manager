#!/bin/bash
# Deploy SIMPLES - só builda o React e copia

set -e

echo "🚀 Deploy Simplificado"
echo "====================="
echo ""

# Build do React
echo "📦 Building React editor..."
cd editor-de-layout-de

if [ ! -d "node_modules" ]; then
    echo "  Instalando deps..."
    npm install
fi

npm run build

echo ""
echo "📁 Copiando para app/static/editor..."
cd ..
rm -rf app/static/editor
mkdir -p app/static/editor
cp -r editor-de-layout-de/dist/* app/static/editor/

echo ""
echo "✅ PRONTO!"
echo ""
echo "O FastAPI já serve /static/editor/ automaticamente."
echo "O template Jinja carrega o JS compilado."
echo ""
echo "Para rodar:"
echo "  uvicorn app.main:app --reload"
echo ""
