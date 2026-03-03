# Integração do Editor React com FastAPI

Este documento explica como o editor de layout React está integrado ao sistema FastAPI + MongoDB.

## Arquitetura

```
┌─────────────────────────────────────────┐
│   FastAPI Backend (Python)              │
│                                         │
│   ┌──────────────────────────────┐     │
│   │  MongoDB                     │     │
│   │  - layouts (collection)      │     │
│   │  - eventos (collection)      │     │
│   └──────────────────────────────┘     │
│                                         │
│   Routers:                              │
│   - /api/layouts/* (CRUD de layouts)   │
│   - /admin/editor (serve página React) │
└─────────────────────────────────────────┘
              │
              │ HTTP REST API
              ↓
┌─────────────────────────────────────────┐
│   Editor React (TypeScript + Vite)     │
│                                         │
│   - Fabric.js (canvas)                  │
│   - shadcn/ui (componentes)             │
│   - Consome API /api/layouts/*          │
└─────────────────────────────────────────┘
```

## Endpoints da API

### Layouts API (`/api/layouts`)

- `GET /api/layouts/` - Lista todos os layouts
- `GET /api/layouts/{id}` - Obtém layout específico
- `POST /api/layouts/` - Cria novo layout
- `PUT /api/layouts/{id}` - Atualiza layout
- `DELETE /api/layouts/{id}` - Deleta layout
- `POST /api/layouts/{id}/duplicate` - Duplica layout

### Editor Web (`/admin/editor`)

- `GET /admin/editor?layout_id={id}` - Abre editor com layout específico
- `GET /admin/editor/novo` - Cria novo layout e abre editor

## Modelo de Dados

```typescript
interface Layout {
  id: string  // MongoDB _id
  nome: string
  canvas: {
    width: number
    height: number
    orientation: "portrait" | "landscape"
    padding: number
  }
  elements: LayoutElement[]
  groups: LayoutGroup[]
  preview_image?: string  // base64 PNG
  created_at: datetime
  updated_at: datetime
  created_by?: string  // Admin ID
}
```

## Como Usar

### Desenvolvimento

1. **Backend**: Rode o FastAPI normalmente
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

2. **Editor em dev mode**: Use Vite dev server
   ```bash
   ./scripts/dev_editor.sh
   ```
   
   O template `editor_layout.html` detecta modo dev e carrega do Vite (porta 5173)

### Produção

1. **Build do editor**:
   ```bash
   ./scripts/build_editor.sh
   ```
   
   Isso cria `app/static/editor/` com os arquivos compilados

2. **Deploy**: O FastAPI serve os arquivos estáticos automaticamente

## Adaptações Necessárias no React

Para consumir a API ao invés de localStorage, adapte `App.tsx`:

```typescript
// Ao invés de useKV (localStorage):
const [layoutState, setLayoutState] = useKV<LayoutState>('ticket-layout', {...})

// Use fetch para carregar/salvar:
useEffect(() => {
  const layoutId = window.__INITIAL_DATA__.layoutId
  if (layoutId) {
    fetch(`${window.__INITIAL_DATA__.apiBaseUrl}/api/layouts/${layoutId}`)
      .then(res => res.json())
      .then(data => setLayoutState({
        canvas: data.canvas,
        elements: data.elements,
        groups: data.groups
      }))
  }
}, [])

// No saveLayout:
const saveLayout = async () => {
  const response = await fetch(
    `${window.__INITIAL_DATA__.apiBaseUrl}/api/layouts/${layoutId}`,
    {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(layoutState)
    }
  )
  if (response.ok) {
    toast.success('Layout salvo!')
  }
}
```

## Variáveis de Template

Tags disponíveis no editor:
- `{NOME}` - Nome do participante
- `{CPF}` - CPF do participante
- `{EMAIL}` - Email do participante
- `{TIPO_INGRESSO}` - Tipo de ingresso
- `{EVENTO_NOME}` - Nome do evento
- `{DATA}` - Data do evento
- `{HORARIO}` - Horário do evento
- `{qrcode_hash}` - Hash para QR code (gerado automaticamente)

## Fluxo de Trabalho

1. Admin acessa `/admin/eventos/{id}`
2. Clica em "Editar Layout do Ingresso"
3. É redirecionado para `/admin/editor?layout_id={layout_id}`
4. Editor React carrega via API
5. Admin edita e salva (PUT para API)
6. Volta para página do evento

## Segurança

- Todas as rotas do editor requerem autenticação (Depends(get_current_admin_web))
- API valida tokens JWT em cada requisição
- Layouts são associados ao admin que os criou
- Não é possível deletar layouts em uso por eventos
