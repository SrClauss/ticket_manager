# 🚀 Deploy SIMPLES - Ticket Manager + Editor React

## A Verdade Simples

O FastAPI **JÁ SERVE** arquivos estáticos de `/static/`.  
O Jinja **JÁ RENDERIZA** templates HTML.  
O React **É SÓ JS COMPILADO**.

**É SÓ ISSO!**

---

## 📦 Desenvolvimento

```bash
# 1. Builda o React (uma vez)
./scripts/build_react.sh

# 2. Roda o FastAPI
uvicorn app.main:app --reload

# 3. Acessa
http://localhost:8000/admin/editor?evento_id=XXX
```

**O Jinja carrega `/static/editor/index.js` - PRONTO!**

---

## 🐳 Deploy com Docker (Recomendado)

```bash
# Build e run (faz build do React automaticamente)
docker-compose -f docker-compose.prod.yml up -d --build

# Pronto! Tudo rodando:
# - MongoDB em :27017
# - FastAPI em :8000 (serve API + React build)
```

**O Dockerfile faz:**
1. Stage 1: `npm run build` → cria `dist/`
2. Stage 2: Copia `dist/` para `app/static/editor/`
3. FastAPI serve tudo via `/static/`

---

## 🎯 Deploy Manual (VPS)

```bash
# 1. Builda o React
cd editor-de-layout-de
npm install
npm run build
cd ..

# 2. Copia o build
rm -rf app/static/editor
cp -r editor-de-layout-de/dist app/static/editor

# 3. Roda o FastAPI normal
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Ou com Gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

**ZERO servidor Node em produção!**  
**ZERO complexidade extra!**

---

## 📂 Como Funciona

```
1. Usuario acessa: /admin/editor?evento_id=abc123

2. FastAPI → Jinja renderiza: templates/admin/editor_layout.html
   
3. Template carrega:
   <script src="/static/editor/assets/index.js"></script>
   
4. FastAPI serve /static/editor/ (build do React)

5. React carrega e consome:
   GET /api/eventos/abc123/layout
   PUT /api/eventos/abc123/layout
```

**Tudo servido pelo FastAPI. Simples.**

---

## 🔄 Atualizar o Editor

```bash
# Rebuilda o React
./scripts/build_react.sh

# Docker: rebuild
docker-compose -f docker-compose.prod.yml up -d --build app

# Pronto!
```

---

## 📊 Estrutura Final

```
app/
  static/
    editor/           ← React build (index.html, assets/)
      assets/
        index.js
        index.css
  templates/
    admin/
      editor_layout.html  ← Carrega /static/editor/assets/index.js
  routers/
    layout_api.py         ← GET/PUT /api/eventos/{id}/layout
    layout_editor.py      ← GET /admin/editor (serve template)

editor-de-layout-de/      ← Código fonte React
  src/
  dist/                   ← Build (vai pra app/static/editor/)
```

---

## ✨ Resumo

| O que | Como | Complexidade |
|-------|------|--------------|
| **React** | Build → `/static/editor/` | ⭐ npm run build |
| **FastAPI** | Serve `/static/` normal | ⭐ Já faz isso |
| **Template** | Carrega JS estático | ⭐ HTML básico |
| **Deploy** | Docker faz build auto | ⭐⭐ 1 comando |

**NÃO EXISTE "megazord"!** É FastAPI normal + 1 build de React.

---

## 🎯 TL;DR

```bash
# Dev
./scripts/build_react.sh && uvicorn app.main:app --reload

# Produção
docker-compose -f docker-compose.prod.yml up -d --build
```

**FIM!** 🎉
