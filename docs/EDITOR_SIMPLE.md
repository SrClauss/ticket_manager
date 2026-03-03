# ✅ Editor de Layout - VERSÃO FINAL SIMPLIFICADA

## 🎯 Arquitetura (SEM MUDANÇAS NO BANCO!)

```
evento (collection existente)
  └── layout_ingresso (subdocumento)
       ├── canvas: { width, height, orientation, padding }
       ├── elements: [ {...}, {...} ]
       └── groups: [ {...} ]
```

**ZERO collections novas criadas!** Layout é parte do evento.

---

## 📡 Endpoints

### API REST
- `GET  /api/eventos/{evento_id}/layout` - Busca layout do evento
- `PUT  /api/eventos/{evento_id}/layout` - Salva layout do evento

### Interface Web
- `GET  /admin/editor?evento_id={id}` - Abre editor React

---

## 🚀 Deploy

```bash
./scripts/deploy_simple.sh
```

Isso faz:
1. Build do React (Vite)
2. Copia para `app/static/editor/`
3. Pronto!

---

## 💻 Uso no Template

```html
<!-- Na página de detalhes do evento -->
<a href="/admin/editor?evento_id={{ evento._id }}" 
   class="btn btn-primary">
    <i class="material-symbols-outlined">palette</i>
    Editar Layout
</a>
```

Mais exemplos: [`docs/EDITOR_UI_SNIPPETS.html`](EDITOR_UI_SNIPPETS.html)

---

## 🔧 Como Funciona

1. Admin clica "Editar Layout" na página do evento
2. Vai para `/admin/editor?evento_id=abc123`
3. React app carrega via `GET /api/eventos/abc123/layout`
4. Editor mostra canvas (Fabric.js) com elementos
5. User edita e clica "Salvar"
6. `PUT /api/eventos/abc123/layout` atualiza `evento.layout_ingresso`
7. Redirect de volta para página do evento

---

## 📂 Arquivos Criados

### Backend
- `app/models/layout.py` - Modelos Pydantic
- `app/routers/layout_api.py` - API endpoints
- `app/routers/layout_editor.py` - Serve React app
- `app/templates/admin/editor_layout.html` - Template HTML

### Scripts
- `scripts/deploy_simple.sh` - Deploy automatizado
- `scripts/dev_editor.sh` - Modo desenvolvimento
- `scripts/build_editor.sh` - Build produção

### Docs
- `docs/EDITOR_UI_SNIPPETS.html` - Exemplos de integração

---

## 🛠️ Desenvolvimento

### Modo Dev (Hot Reload)

```bash
# Terminal 1: Backend
uvicorn app.main:app --reload --port 8000

# Terminal 2: Vite dev server
./scripts/dev_editor.sh
```

Vite roda na porta 5173, template detecta `dev_mode` e carrega de lá.

### Modo Produção

```bash
./scripts/deploy_simple.sh
uvicorn app.main:app --port 8000
```

---

## ⚙️ Próximo Passo: Adaptar React App

O editor React atual usa `localStorage`. Precisa adaptar para API:

**Arquivo**: `editor-de-layout-de/src/App.tsx`

```typescript
// Ao carregar o app
useEffect(() => {
  const { eventoId, apiBaseUrl } = window.__INITIAL_DATA__
  
  fetch(`${apiBaseUrl}/api/eventos/${eventoId}/layout`)
    .then(res => res.json())
    .then(data => {
      setLayoutState({
        canvas: data.layout.canvas,
        elements: data.layout.elements,
        groups: data.layout.groups
      })
    })
}, [])

// Ao salvar
const saveLayout = async () => {
  const { eventoId, apiBaseUrl } = window.__INITIAL_DATA__
  
  const response = await fetch(
    `${apiBaseUrl}/api/eventos/${eventoId}/layout`,
    {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({
        canvas: layoutState.canvas,
        elements: layoutState.elements,
        groups: layoutState.groups
      })
    }
  )
  
  if (response.ok) {
    toast.success('Layout salvo!')
    // Opcional: redirecionar de volta
    // window.location.href = window.__INITIAL_DATA__.backUrl
  }
}
```

---

## 🔒 Segurança

- ✅ Todas as rotas requerem autenticação (`get_current_admin`)
- ✅ Apenas admins autenticados podem editar layouts
- ✅ Layout é parte do evento (permissões herdadas)

---

## 📊 Estrutura de Dados

```javascript
// evento.layout_ingresso
{
  "canvas": {
    "width": 62,         // mm
    "height": 120,       // mm
    "orientation": "portrait",
    "padding": 5         // mm
  },
  "elements": [
    {
      "id": "elem-1",
      "type": "text",    // text|qrcode|divider
      "y": 10,           // posição vertical em mm
      "horizontal_position": "center",  // left|center|right
      "margin_left": 0,
      "margin_right": 0,
      "groupId": null,
      "value": "{NOME}",
      "size": 14,
      "font": "Arial",
      "bold": false
    },
    {
      "id": "elem-2",
      "type": "qrcode",
      "y": 45,
      "horizontal_position": "center",
      "size_mm": 30
    }
  ],
  "groups": []
}
```

### Template Tags Disponíveis
- `{NOME}` - Nome do participante
- `{CPF}` - CPF formatado
- `{EMAIL}` - Email
- `{TIPO_INGRESSO}` - Tipo de ingresso
- `{EVENTO_NOME}` - Nome do evento
- `{DATA}` - Data do evento
- `{HORARIO}` - Horário
- `{qrcode_hash}` - Hash para QR code

---

## ✨ Resumo

| Aspecto | Status |
|---------|--------|
| **Banco de dados** | ✅ Zero mudanças necessárias |
| **Compatibilidade** | ✅ 100% retrocompatível |
| **Deploy** | ✅ Script automatizado |
| **Editor** | ✅ React + Fabric.js funcionando |
| **API** | ✅ GET/PUT prontos |
| **Integração** | ⚠️ Precisa adaptar App.tsx |

**Status atual**: Backend 100% pronto. Falta adaptar React para consumir API.
