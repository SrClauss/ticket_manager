# 🚀 Sistema de Layout com Grupos - Implementação Completa

## 📝 Resumo das Alterações

### ✅ **Implementado**

#### 1. **Novo Frontend (Alpine.js + Interact.js)**
- **Arquivo**: `app/static/js/layout-editor.js`
- Store Alpine.js com gerenciamento de estado completo
- Modos: `normal` | `editing-group`
- Posicionamento horizontal travado (10mm, 31mm, 52mm)
- Sistema de rascunho local (localStorage)
- Suporte a margens horizontais (margin_left, margin_right)
- Auto-save em localStorage
- Atalhos de teclado (ESC, Delete, Ctrl+S)

#### 2. **Estilos CSS Modernos**
- **Arquivo**: `app/static/css/layout-editor.css`
- Layout responsivo com CSS Grid
- Desktop: sidebar + canvas + preview lado a lado
- Mobile/Tablet: elementos empilhados
- Floating Action Button (FAB) com indicador de alterações
- Marca d'água no preview quando não salvo
- Modo de edição de grupo com fade out
- Snap guides visuais

#### 3. **Template HTML Refatorado**
- **Arquivo**: `app/templates/admin/ticket_layout_new.html`
- Interface limpa e intuitiva
- Sidebar com:
  - Botões para adicionar elementos (Texto, QR Code, Divisor, Grupo)
  - Tags disponíveis (copiar ao clicar)
  - Painel de propriedades dinâmico
- Canvas com:
  - Réguas horizontais e verticais
  - Guias de snap visuais
  - Elementos e grupos arrastáveis
- Preview com:
  - Marca d'água "SALVAR LAYOUT" se houver alterações
  - Loading state
  - Atualização manual
- FAB para salvar (Ctrl+S)

#### 4. **Backend Endpoints**

##### **POST** `/admin/eventos/layout/{evento_id}/render-group`
- Renderiza grupo como imagem PNG
- Converte para base64 (data URI)
- Retorna `snapshot_image` para armazenar no layout

##### **POST** `/admin/eventos/layout/{evento_id}` (atualizado)
- Salva layout com grupos
- Apaga histórico de rascunhos
- Atualiza ingressos existentes

##### **POST** `/admin/eventos/layout/{evento_id}/preview` (mantido)
- Suporte para grupos com snapshots
- Marca d'água se rascunho não salvo

#### 5. **Funções de Renderização**

##### `app/utils/layouts.py` - `embed_layout()` (atualizado)
- Processa grupos e seus elementos
- Substitui placeholders dentro de grupos
- Mantém compatibilidade com layout antigo

##### `app/routers/evento_api.py` - `_render_layout_to_image()` (atualizado)
- Renderiza grupos como imagens no ingresso final
- Suporta snapshots base64
- Redimensiona proporcionalmente
- Grupos aparecem antes dos elementos soltos (z-index)

#### 6. **Rota de Acesso**
- **GET** `/admin/eventos/layout/{evento_id}` → agora usa `ticket_layout_new.html`

---

## 🎯 **Funcionalidades Implementadas**

### **Componente Grupo**
✅ Arrastar grupo para canvas  
✅ Snap horizontal (10/31/52mm)  
✅ Posicionamento vertical livre  
✅ Redimensionamento (largura/altura)  
✅ Alinhamento interno: `left`, `center`, `right`, `space-between`, `space-around`  
✅ Adicionar elementos dentro do grupo  
✅ Modo de edição isolado (fade out de outros elementos)  
✅ Renderização como imagem PNG (instantânea ao sair do modo edição)  
✅ Snapshot salvo em base64 no layout  

### **Sistema de Rascunho**
✅ Salva alterações em localStorage  
✅ Persiste entre sessões  
✅ Não afeta versão salva no servidor  
✅ Preview mostra marca d'água se não salvo  
✅ Confirmação ao salvar final (irreversível)  

### **Posicionamento**
✅ Horizontal travado em 3 posições (10/31/52mm)  
✅ Vertical livre  
✅ Margens horizontais para ajuste fino  
✅ Drag & drop com Interact.js  
✅ Snap visual com guias  

### **Interface**
✅ Layout responsivo (desktop/mobile)  
✅ Preview lado a lado (desktop) ou abaixo (mobile)  
✅ Floating Action Button com indicador de alterações  
✅ Toast notifications  
✅ Loading states  
✅ Atalhos de teclado  

---

## 🗂️ **Estrutura de Dados**

### **Layout Completo (MongoDB)**
```json
{
  "canvas": {
    "width": 62,
    "height": 120,
    "orientation": "portrait",
    "padding": 5,
    "dpi": 300
  },
  "elements": [
    {
      "id": "elem-1709876543210",
      "type": "text",
      "x": 31,
      "y": 20,
      "horizontal_position": "center",
      "margin_left": 0,
      "margin_right": 0,
      "value": "{NOME}",
      "size": 14,
      "font": "Arial",
      "align": "center",
      "bold": true,
      "z_index": 1
    }
  ],
  "groups": [
    {
      "id": "group-1709876543211",
      "x": 10,
      "y": 40,
      "width": 42,
      "height": 30,
      "horizontal_position": "left",
      "align_items": "left",
      "margin_left": 0,
      "margin_right": 0,
      "snapshot_image": "data:image/png;base64,iVBORw0KGgoAAAANS...",
      "elements": [
        {
          "id": "elem-1709876543212",
          "type": "text",
          "x": 5,
          "y": 5,
          "value": "Item 1",
          "size": 10
        }
      ],
      "z_index": 2
    }
  ]
}
```

---

## 🔄 **Fluxo de Uso**

1. **Usuário acessa** `/admin/eventos/layout/{id}`
2. **Sistema carrega** rascunho de localStorage (se existir)
3. **Usuário adiciona** elementos e grupos ao canvas
4. **Drag & drop** com snap horizontal automático
5. **Duplo clique em grupo** → entra no modo de edição
6. **Adiciona elementos dentro** do grupo
7. **Clica fora ou ESC** → sai do modo edição
8. **Backend renderiza grupo** como imagem PNG (base64)
9. **Preview atualiza** com marca d'água "SALVAR LAYOUT"
10. **FAB pisca** indicando alterações não salvas
11. **Usuário clica FAB** → confirmação de salvamento
12. **Sistema salva** no MongoDB e apaga rascunho
13. **Ingressos usam** versão salva para emissão

---

## ⚠️ **Notas Importantes**

### **Compatibilidade**
- Layout antigo **continua funcionando** (sem grupos)
- Função `embed_layout()` mantém retrocompatibilidade
- Preview funciona com ambos os formatos

### **Performance**
- Grupos são renderizados como imagem uma única vez
- Preview usa cache de snapshots
- Debounce de 500ms em atualizações

### **Limitações**
- Grupos não podem conter outros grupos (1 nível apenas)
- Snapshot é estático (re-editar grupo gera nova imagem)
- localStorage limitado a ~5MB por domínio

---

## 🧪 **Como Testar**

1. Acesse `/admin/login` (admin/admin_key_change_in_production)
2. Clique em um evento → "Editar Layout"
3. Adicione elementos (texto, QR code, divisor)
4. Adicione um grupo → duplo clique para editar
5. Adicione elementos dentro do grupo
6. Clique fora → grupo vira imagem
7. Verifique marca d'água no preview
8. Clique no FAB → salve o layout
9. Emita um ingresso → verifique renderização final

---

## 📦 **Arquivos Criados/Modificados**

### **Criados**
- `app/static/js/layout-editor.js` (12KB)
- `app/static/css/layout-editor.css` (9KB)
- `app/templates/admin/ticket_layout_new.html` (20KB)
- `docs/IMPLEMENTACAO_LAYOUT_GRUPOS.md` (este arquivo)

### **Modificados**
- `app/routers/admin_web.py`:
  - Alterada rota GET `/admin/eventos/layout/{id}` para usar novo template
  - Adicionado POST `/admin/eventos/layout/{id}/render-group`
- `app/routers/evento_api.py`:
  - Atualizada função `_render_layout_to_image()` para suportar grupos
- `app/utils/layouts.py`:
  - Atualizada função `embed_layout()` para processar grupos

---

## 🚀 **Deploy**

Deploy remoto via script padrão:
```bash
./scripts/deploy_remote.sh "Implementação completa do sistema de layout com grupos"
```

---

**Data**: 2026-03-02  
**Versão**: 2.0.0  
**Status**: ✅ Pronto para produção
