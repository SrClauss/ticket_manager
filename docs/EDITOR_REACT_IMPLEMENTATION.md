# 🎨 Editor de Layout React - Implementação

Implementação de um editor de layout de ingressos usando React + Fabric.js, integrado ao sistema FastAPI + MongoDB existente.

## 📁 Arquivos Criados

### Backend (FastAPI + MongoDB)

1. **Models**
   - [`app/models/layout.py`](../app/models/layout.py) - Modelos Pydantic para layouts

2. **Routers**
   - [`app/routers/layout_api.py`](../app/routers/layout_api.py) - API REST para CRUD de layouts
   - [`app/routers/layout_editor.py`](../app/routers/layout_editor.py) - Rotas web para servir o editor

3. **Templates**
   - [`app/templates/admin/editor_layout.html`](../app/templates/admin/editor_layout.html) - Template que carrega o React app

4. **Scripts**
   - [`scripts/build_editor.sh`](../scripts/build_editor.sh) - Build de produção do editor
   - [`scripts/dev_editor.sh`](../scripts/dev_editor.sh) - Modo desenvolvimento

5. **Documentação**
   - [`docs/EDITOR_INTEGRATION.md`](EDITOR_INTEGRATION.md) - Guia completo de integração

### Atualizações

- ✅ `app/main.py` - Registrados novos routers
- ✅ `app/models/evento.py` - Adicionado campo `layout_id`

## 🚀 Como Usar

### Modo Desenvolvimento

```bash
# Terminal 1: Backend FastAPI
uvicorn app.main:app --reload --port 8000

# Terminal 2: Editor React (Vite dev server)
./scripts/dev_editor.sh
```

Acesse: http://localhost:8000/admin/editor

### Modo Produção

```bash
# 1. Build do editor
./scripts/build_editor.sh

# 2. Inicie o FastAPI normalmente
uvicorn app.main:app --port 8000
```

## 🔗 Endpoints Disponíveis

### Interface Web
- `GET /admin/editor?layout_id={id}` - Abre editor com layout
- `GET /admin/editor/novo` - Cria novo layout

### API REST
- `GET /api/layouts/` - Lista layouts
- `GET /api/layouts/{id}` - Busca layout
- `POST /api/layouts/` - Cria layout
- `PUT /api/layouts/{id}` - Atualiza layout
- `DELETE /api/layouts/{id}` - Deleta layout
- `POST /api/layouts/{id}/duplicate` - Duplica layout

## 📊 Estrutura de Dados

```javascript
// Layout no MongoDB
{
  "_id": ObjectId,
  "nome": "Layout Padrão",
  "canvas": {
    "width": 62,
    "height": 120,
    "orientation": "portrait",
    "padding": 5
  },
  "elements": [
    {
      "id": "elem-1",
      "type": "text",  // text | qrcode | divider
      "y": 10,
      "horizontal_position": "center",
      "value": "{NOME}",
      "size": 14,
      "font": "Arial",
      "bold": false
    }
  ],
  "groups": [],
  "preview_image": "data:image/png;base64,...",
  "created_at": ISODate,
  "updated_at": ISODate,
  "created_by": "admin_id"
}
```

## ⚙️ Próximos Passos

### 1. Adaptar o React App

O editor React atual usa `localStorage`. Para consumir a API:

**Arquivo**: `editor-de-layout-de/src/App.tsx`

```typescript
// Substituir useKV por fetch API
const [layoutState, setLayoutState] = useState<LayoutState | null>(null)

useEffect(() => {
  const { layoutId, apiBaseUrl } = window.__INITIAL_DATA__
  
  if (layoutId) {
    fetch(`${apiBaseUrl}/api/layouts/${layoutId}`)
      .then(res => res.json())
      .then(data => setLayoutState({
        canvas: data.canvas,
        elements: data.elements,
        groups: data.groups
      }))
  }
}, [])

const saveLayout = async () => {
  const { layoutId, apiBaseUrl } = window.__INITIAL_DATA__
  
  await fetch(`${apiBaseUrl}/api/layouts/${layoutId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({
      ...layoutState,
      preview_image: mainCanvasRef.current?.getDataURL()
    })
  })
  
  toast.success('Layout salvo!')
}
```

### 2. Link nos Templates Admin

**Arquivo**: `app/templates/admin/evento_detalhes.html`

Adicionar botão para editar layout:

```html
<div class="card">
  <h3>Layout do Ingresso</h3>
  <button onclick="window.location.href='/admin/editor?layout_id={{ evento.layout_id }}'">
    <i class="material-symbols-outlined">edit</i>
    Editar Layout
  </button>
</div>
```

### 3. Criar Index de Gerenciamento

**Arquivo**: `app/templates/admin/layouts_list.html`

Página para listar, criar e gerenciar todos os layouts.

### 4. Migração de Dados (Opcional)

Se já existem eventos com `layout_ingresso` (formato antigo):

```python
# Script para migrar layouts antigos para nova estrutura
async def migrar_layouts():
    db = get_database()
    async for evento in db.eventos.find({"layout_ingresso": {"$exists": True}}):
        # Criar layout a partir do layout_ingresso
        # Adicionar layout_id ao evento
        pass
```

## 🔒 Segurança

- ✅ Todas as rotas requerem autenticação (`get_current_admin`)
- ✅ Layouts são associados ao criador
- ✅ Não é possível deletar layouts em uso
- ✅ CORS configurado no FastAPI

## 🧪 Testes

Para testar a integração:

```bash
# 1. Inicie o backend
uvicorn app.main:app --reload

# 2. Acesse o editor
curl -X GET http://localhost:8000/admin/editor/novo

# 3. Teste a API
curl -X GET http://localhost:8000/api/layouts/
```

## 📚 Recursos

- **Fabric.js**: Canvas manipulation
- **shadcn/ui**: Componentes React
- **Vite**: Build tool
- **FastAPI**: Backend framework
- **MongoDB**: Banco de dados

## 💡 Benefícios

1. ✅ **Editor visual** profissional para layouts
2. ✅ **Zero dependências** de Alpine.js
3. ✅ **API REST** desacoplada
4. ✅ **Mantém** o editor React original
5. ✅ **Integração** simples com sistema existente
6. ✅ **Reutilizável** - layouts podem ser usados por múltiplos eventos

---

**Status**: ✅ Implementação base completa  
**Próxima etapa**: Adaptar App.tsx para consumir API
