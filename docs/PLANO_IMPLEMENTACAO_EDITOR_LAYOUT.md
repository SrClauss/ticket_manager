# 📋 Plano de Implementação - Editor de Layout de Ingressos

**Versão:** 1.0  
**Data:** 04/02/2026  
**Objetivo:** Reconstruir completamente o editor de layout com vanilla JavaScript + Alpine.js

---

## 🎯 Visão Geral

### Stack Tecnológica
- **Backend:** FastAPI (Python) - sem alterações significativas
- **Frontend:** Vanilla JavaScript + Alpine.js (gerenciamento de estado)
- **Drag & Drop:** Interact.js (mantém biblioteca atual)
- **Estilo:** Tailwind CSS (atual)
- **Preview:** Server-side rendering (PIL/Pillow)

### Prioridades
1. **[P1]** Drag and drop fluido com sync de inputs
2. **[P2]** Preview em tempo real (auto-refresh)
3. **[P3]** Interface mobile-friendly
4. **[P4]** Templates prontos (aplicados ao criar evento)

---

## 🏗️ Arquitetura da Interface

```
┌─────────────────────────────────────────────────────────┐
│  Header: Editor de Layout - [Nome do Evento]           │
└─────────────────────────────────────────────────────────┘
┌──────────────┬──────────────────────────────────────────┐
│              │                                          │
│   SIDEBAR    │          CANVAS AREA                     │
│   (300px)    │          (flex-grow)                     │
│              │                                          │
│  - Canvas    │  ┌────────────────────────────────┐     │
│    Config    │  │                                │     │
│  - Elementos │  │      Ticket Canvas             │     │
│  - Lista     │  │      (com réguas)              │     │
│              │  │                                │     │
│              │  └────────────────────────────────┘     │
│              │                                          │
│              │  [Botões: Salvar | Limpar | Template]   │
├──────────────┴──────────────────────────────────────────┤
│                    PREVIEW AREA                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Preview com dados fictícios (auto-refresh)      │  │
│  │  Nome: Edson Arantes do Nascimento               │  │
│  │  CPF: 123.456.789-00                             │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## 📦 Estrutura de Dados

### Modelo de Layout (MongoDB)
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
      "id": "elem-1",
      "type": "text|qrcode|logo|divider",
      "x": 10.5,
      "y": 20.0,
      "value": "{NOME}|static text",
      "size": 12,
      "size_mm": 30,
      "font": "Arial",
      "align": "left|center|right",
      "bold": false,
      "italic": false,
      "underline": false,
      "strikethrough": false,
      "margin_mm": 0,
      "z_index": 1
    }
  ],
  "template_name": "Padrão VIP|Simples|Custom"
}
```

### Estado do Alpine.js
```javascript
Alpine.data('layoutEditor', () => ({
  // Canvas state
  canvas: {
    width: 62,
    height: 120,
    orientation: 'portrait',
    padding: 5
  },
  
  // Elements array
  elements: [],
  
  // Selected element
  selectedElement: null,
  
  // Undo/Redo stacks
  history: [],
  historyIndex: -1,
  
  // Preview state
  previewUrl: null,
  previewLoading: false,
  
  // Methods
  addElement(type) { },
  deleteElement(id) { },
  updateElement(id, props) { },
  selectElement(id) { },
  saveLayout() { },
  loadTemplate(name) { },
  undo() { },
  redo() { }
}))
```

---

## 🔧 Componentes e Funcionalidades

### 1️⃣ SIDEBAR - Configurações do Canvas
**Arquivo:** `ticket_layout.html` - Seção Sidebar

#### Campos:
- **Orientação:** Dropdown (Portrait | Landscape)
- **Largura fixa:** 29mm | 62mm (dropdown)
- **Altura variável:** Input number (min: 10mm)
- **Padding:** Input number (default: 5mm)
- **DPI:** Fixed 300 (não editável, apenas info)

#### Comportamento:
- Ao alterar orientação → swap width/height
- Ao alterar dimensões → recalcular elementos em % → aplicar nova escala
- Validação: altura mínima 10mm

---

### 2️⃣ SIDEBAR - Adicionar Elementos
**Arquivo:** `ticket_layout.html` - Seção Sidebar

#### Formulário:
```html
<select id="elementType">
  <option value="text">📝 Texto</option>
  <option value="qrcode">🔲 QR Code</option>
  <option value="logo">🖼️ Logo</option>
  <option value="divider">➖ Linha</option>
</select>

<!-- Campos dinâmicos baseado no tipo -->
<div x-show="elementType === 'text'">
  <input type="text" placeholder="Conteúdo ou tag" />
  <input type="number" placeholder="Tamanho (px)" />
  
  <select id="fontFamily">
    <option>Arial</option>
    <option>Times New Roman</option>
    <option>Courier New</option>
  </select>
  
  <select id="textAlign">
    <option value="left">⬅️ Esquerda</option>
    <option value="center">↔️ Centro</option>
    <option value="right">➡️ Direita</option>
  </select>
  
  <div class="flex gap-2">
    <button @click="toggleBold">B</button>
    <button @click="toggleItalic">I</button>
    <button @click="toggleUnderline">U</button>
    <button @click="toggleStrike">S</button>
  </div>
  
  <!-- Tags disponíveis -->
  <div class="tags-list">
    <span class="tag" @click="insertTag('{NOME}')">{NOME}</span>
    <span class="tag" @click="insertTag('{CPF}')">{CPF}</span>
    <span class="tag" @click="insertTag('{EMAIL}')">{EMAIL}</span>
    <span class="tag" @click="insertTag('{TIPO_INGRESSO}')">{TIPO_INGRESSO}</span>
    <span class="tag" @click="insertTag('{EVENTO_NOME}')">{EVENTO_NOME}</span>
    <span class="tag" @click="insertTag('{DATA_EVENTO}')">{DATA_EVENTO}</span>
    <span class="tag" @click="insertTag('{qrcode_hash}')">{qrcode_hash}</span>
  </div>
</div>

<div x-show="elementType === 'qrcode'">
  <input type="number" placeholder="Tamanho (mm)" min="10" max="50" />
  <p class="hint">QR Code usa automaticamente {qrcode_hash}</p>
</div>

<div x-show="elementType === 'logo'">
  <p class="hint">Logo será carregada do evento</p>
  <input type="number" placeholder="Tamanho (mm)" />
</div>

<div x-show="elementType === 'divider'">
  <select>
    <option value="horizontal">Horizontal —</option>
    <option value="vertical">Vertical |</option>
  </select>
  <input type="number" placeholder="Espessura (px)" min="1" max="10" />
</div>

<button @click="addElement" class="btn-primary">
  ➕ Adicionar ao Canvas
</button>
```

---

### 3️⃣ SIDEBAR - Lista de Elementos
**Arquivo:** `ticket_layout.html` - Seção Sidebar

#### Layout:
```html
<div class="elements-list" x-data="{ dragging: null }">
  <h6>📋 Elementos no Layout</h6>
  
  <template x-for="(element, index) in elements" :key="element.id">
    <div 
      class="element-item"
      :class="{ 'selected': selectedElement?.id === element.id }"
      @click="selectElement(element.id)"
      draggable="true"
      @dragstart="dragging = index"
      @dragover.prevent
      @drop="reorderElements(index, dragging)"
    >
      <span class="element-icon" x-text="getIcon(element.type)"></span>
      <span class="element-label" x-text="getLabel(element)"></span>
      <button @click.stop="deleteElement(element.id)" class="btn-delete">🗑️</button>
    </div>
  </template>
  
  <p x-show="elements.length === 0" class="text-muted">
    Nenhum elemento adicionado
  </p>
</div>
```

#### Comportamento:
- **Drag & Drop:** Reordenar elementos (altera z_index)
- **Click:** Seleciona elemento (destaque visual + painel de propriedades)
- **Delete:** Confirmação + remove elemento
- **Visual:** Highlight do elemento selecionado

---

### 4️⃣ CANVAS - Área de Trabalho
**Arquivo:** `ticket_layout.html` - Main Canvas

#### Estrutura:
```html
<div class="canvas-wrapper">
  <!-- Réguas -->
  <div class="ruler ruler-horizontal">
    <!-- Marcações de 0 a width em mm -->
    <template x-for="i in Math.ceil(canvas.width / 10)">
      <span class="ruler-mark" :style="`left: ${i * 10}mm`">
        <span x-text="i * 10"></span>
      </span>
    </template>
  </div>
  
  <div class="ruler ruler-vertical">
    <!-- Marcações de 0 a height em mm -->
    <template x-for="i in Math.ceil(canvas.height / 10)">
      <span class="ruler-mark" :style="`top: ${i * 10}mm`">
        <span x-text="i * 10"></span>
      </span>
    </template>
  </div>
  
  <!-- Canvas principal -->
  <div 
    id="ticketCanvas"
    class="canvas-container"
    :style="`width: ${canvas.width}mm; height: ${canvas.height}mm;`"
    @click.self="deselectElement()"
  >
    <!-- Elementos draggable -->
    <template x-for="element in elements" :key="element.id">
      <div
        :id="element.id"
        class="draggable-element"
        :class="{ 
          'selected': selectedElement?.id === element.id,
          [`type-${element.type}`]: true
        }"
        :style="`
          left: ${element.x}mm;
          top: ${element.y}mm;
          font-size: ${element.size}px;
          font-family: ${element.font};
          text-align: ${element.align};
          font-weight: ${element.bold ? 'bold' : 'normal'};
          font-style: ${element.italic ? 'italic' : 'normal'};
          text-decoration: ${getTextDecoration(element)};
        `"
        @click.stop="selectElement(element.id)"
        x-text="getElementContent(element)"
      ></div>
    </template>
  </div>
</div>
```

#### Interact.js - Drag & Drop
```javascript
// Inicializar drag para cada elemento
function initDraggable(elementId) {
  interact(`#${elementId}`)
    .draggable({
      inertia: true,
      modifiers: [
        interact.modifiers.restrictRect({
          restriction: 'parent',
          endOnly: true
        })
      ],
      listeners: {
        move(event) {
          const element = event.target;
          const x = parseFloat(element.getAttribute('data-x')) || 0;
          const y = parseFloat(element.getAttribute('data-y')) || 0;
          
          // Atualizar transformação
          element.style.transform = `translate(${event.dx}px, ${event.dy}px)`;
          element.setAttribute('data-x', x + event.dx);
          element.setAttribute('data-y', y + event.dy);
        },
        
        end(event) {
          // Mostrar botão "Confirmar Posição"
          showConfirmPositionButton(event.target);
        }
      }
    });
}

// Confirmar posição - converte px → mm e salva no estado
function confirmPosition(elementId) {
  const element = document.getElementById(elementId);
  const canvas = document.getElementById('ticketCanvas');
  
  const rect = element.getBoundingClientRect();
  const canvasRect = canvas.getBoundingClientRect();
  
  // Calcular posição em mm
  const xPx = rect.left - canvasRect.left;
  const yPx = rect.top - canvasRect.top;
  
  const xMm = (xPx / canvasRect.width) * Alpine.store('editor').canvas.width;
  const yMm = (yPx / canvasRect.height) * Alpine.store('editor').canvas.height;
  
  // Atualizar estado Alpine
  Alpine.store('editor').updateElementPosition(elementId, xMm, yMm);
  
  // Reset transform
  element.style.transform = '';
  element.setAttribute('data-x', 0);
  element.setAttribute('data-y', 0);
  
  // Esconder botão
  hideConfirmPositionButton();
  
  // Trigger preview refresh
  refreshPreview();
}
```

---

### 5️⃣ PAINEL DE PROPRIEDADES (Sidebar Direita ou Integrado)
**Arquivo:** `ticket_layout.html` - Properties Panel

#### Quando elemento selecionado:
```html
<div x-show="selectedElement" class="properties-panel">
  <h6>🎨 Propriedades do Elemento</h6>
  
  <div class="property-group">
    <label>Tipo:</label>
    <span x-text="selectedElement?.type"></span>
  </div>
  
  <!-- Posição X/Y em mm -->
  <div class="property-group">
    <label>Posição X (mm):</label>
    <input 
      type="number" 
      step="0.1"
      :value="selectedElement?.x"
      @input="updateElementProperty('x', parseFloat($event.target.value))"
    />
  </div>
  
  <div class="property-group">
    <label>Posição Y (mm):</label>
    <input 
      type="number" 
      step="0.1"
      :value="selectedElement?.y"
      @input="updateElementProperty('y', parseFloat($event.target.value))"
    />
  </div>
  
  <!-- Propriedades específicas por tipo -->
  <template x-if="selectedElement?.type === 'text'">
    <div>
      <div class="property-group">
        <label>Conteúdo:</label>
        <input 
          type="text"
          :value="selectedElement?.value"
          @input="updateElementProperty('value', $event.target.value)"
        />
      </div>
      
      <div class="property-group">
        <label>Tamanho (px):</label>
        <input 
          type="number"
          :value="selectedElement?.size"
          @input="updateElementProperty('size', parseInt($event.target.value))"
        />
      </div>
      
      <div class="property-group">
        <label>Alinhamento:</label>
        <select 
          :value="selectedElement?.align"
          @change="updateElementProperty('align', $event.target.value)"
        >
          <option value="left">Esquerda</option>
          <option value="center">Centro</option>
          <option value="right">Direita</option>
        </select>
      </div>
      
      <div class="property-group">
        <label>Formatação:</label>
        <div class="format-buttons">
          <button 
            :class="{ active: selectedElement?.bold }"
            @click="toggleFormat('bold')"
          >B</button>
          <button 
            :class="{ active: selectedElement?.italic }"
            @click="toggleFormat('italic')"
          >I</button>
          <button 
            :class="{ active: selectedElement?.underline }"
            @click="toggleFormat('underline')"
          >U</button>
          <button 
            :class="{ active: selectedElement?.strikethrough }"
            @click="toggleFormat('strikethrough')"
          >S</button>
        </div>
      </div>
    </div>
  </template>
  
  <template x-if="selectedElement?.type === 'qrcode'">
    <div class="property-group">
      <label>Tamanho (mm):</label>
      <input 
        type="number"
        :value="selectedElement?.size_mm"
        @input="updateElementProperty('size_mm', parseFloat($event.target.value))"
      />
    </div>
  </template>
  
  <!-- Botões de alinhamento rápido -->
  <div class="quick-align">
    <button @click="alignLeft">⬅️ Esquerda</button>
    <button @click="alignCenter">↔️ Centro</button>
    <button @click="alignRight">➡️ Direita</button>
  </div>
  
  <button @click="deleteElement(selectedElement.id)" class="btn-danger">
    🗑️ Remover Elemento
  </button>
</div>
```

---

### 6️⃣ PREVIEW EM TEMPO REAL
**Arquivo:** `ticket_layout.html` - Preview Section

#### HTML:
```html
<div class="preview-section">
  <h5>👁️ Preview em Tempo Real</h5>
  <p class="text-muted">
    Dados fictícios: Edson Arantes do Nascimento | CPF: 123.456.789-00
  </p>
  
  <div class="preview-container" x-data="{ loading: false }">
    <div x-show="loading" class="loading-spinner">Carregando...</div>
    
    <img 
      id="previewImage"
      :src="previewUrl"
      alt="Preview do ingresso"
      @load="loading = false"
      @error="handlePreviewError"
      class="preview-image"
    />
  </div>
  
  <button @click="refreshPreview" class="btn-secondary">
    🔄 Atualizar Preview
  </button>
</div>
```

#### JavaScript - Auto-refresh:
```javascript
// Debounce para evitar requests excessivos
let previewTimeout = null;

function refreshPreview() {
  clearTimeout(previewTimeout);
  
  previewTimeout = setTimeout(async () => {
    const state = Alpine.store('editor');
    
    try {
      const response = await fetch(`/admin/eventos/layout/${eventoId}/preview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          canvas: state.canvas,
          elements: state.elements
        })
      });
      
      if (response.ok) {
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        
        // Atualizar imagem
        document.getElementById('previewImage').src = url;
        
        // Limpar URL antiga
        if (state.previewUrl) {
          URL.revokeObjectURL(state.previewUrl);
        }
        
        state.previewUrl = url;
      }
    } catch (error) {
      showToast('Erro ao gerar preview', 'error');
    }
  }, 500); // Debounce de 500ms
}

// Trigger auto-refresh em mudanças
Alpine.effect(() => {
  // Observa mudanças em elements e canvas
  const state = Alpine.store('editor');
  JSON.stringify(state.elements);
  JSON.stringify(state.canvas);
  
  refreshPreview();
});
```

---

### 7️⃣ TEMPLATES PRONTOS
**Arquivo:** `app/routers/admin_web.py` - Backend

#### Templates Pré-definidos:
```python
LAYOUT_TEMPLATES = {
    "padrao_vip": {
        "name": "Padrão VIP",
        "canvas": {"width": 62, "height": 120, "orientation": "portrait", "padding": 5},
        "elements": [
            {
                "id": "title",
                "type": "text",
                "x": 31,  # Centro horizontal (62/2)
                "y": 10,
                "value": "{EVENTO_NOME}",
                "size": 16,
                "font": "Arial",
                "align": "center",
                "bold": True
            },
            {
                "id": "qrcode",
                "type": "qrcode",
                "x": 16,  # Centro - (30/2)
                "y": 35,
                "value": "{qrcode_hash}",
                "size_mm": 30
            },
            {
                "id": "nome",
                "type": "text",
                "x": 31,
                "y": 75,
                "value": "{NOME}",
                "size": 12,
                "font": "Arial",
                "align": "center",
                "bold": False
            },
            {
                "id": "tipo",
                "type": "text",
                "x": 5,
                "y": 100,
                "value": "{TIPO_INGRESSO}",
                "size": 10,
                "font": "Arial",
                "align": "left"
            },
            {
                "id": "data",
                "type": "text",
                "x": 57,  # Alinhado à direita com margin
                "y": 100,
                "value": "{DATA_EVENTO}",
                "size": 10,
                "font": "Arial",
                "align": "right"
            }
        ]
    },
    
    "simples": {
        "name": "Simples",
        "canvas": {"width": 62, "height": 100, "orientation": "portrait", "padding": 5},
        "elements": [
            {
                "id": "qrcode",
                "type": "qrcode",
                "x": 16,
                "y": 10,
                "value": "{qrcode_hash}",
                "size_mm": 30
            },
            {
                "id": "nome",
                "type": "text",
                "x": 31,
                "y": 50,
                "value": "{NOME}",
                "size": 14,
                "font": "Arial",
                "align": "center",
                "bold": True
            },
            {
                "id": "tipo",
                "type": "text",
                "x": 31,
                "y": 70,
                "value": "{TIPO_INGRESSO}",
                "size": 10,
                "font": "Arial",
                "align": "center"
            }
        ]
    }
}

# Endpoint para carregar template
@router.get("/admin/templates/layout/{template_name}")
async def get_layout_template(template_name: str):
    if template_name not in LAYOUT_TEMPLATES:
        raise HTTPException(404, "Template não encontrado")
    return LAYOUT_TEMPLATES[template_name]

# Ao criar evento, aplicar template padrão
@router.post("/admin/eventos")
async def create_evento(...):
    # ... código de criação ...
    
    # Aplicar template padrão
    evento_data["layout"] = LAYOUT_TEMPLATES["padrao_vip"].copy()
    
    # ... salvar no MongoDB ...
```

#### Frontend - Carregar Template:
```javascript
async function loadTemplate(templateName) {
  try {
    const response = await fetch(`/admin/templates/layout/${templateName}`);
    const template = await response.json();
    
    const state = Alpine.store('editor');
    state.canvas = template.canvas;
    state.elements = template.elements;
    
    // Salvar no histórico
    state.saveToHistory();
    
    showToast(`Template "${template.name}" carregado com sucesso`, 'success');
    refreshPreview();
  } catch (error) {
    showToast('Erro ao carregar template', 'error');
  }
}
```

---

### 8️⃣ UNDO/REDO
**Arquivo:** `ticket_layout.html` - Alpine.js State

#### Implementação:
```javascript
Alpine.store('editor', {
  elements: [],
  canvas: {},
  selectedElement: null,
  
  // Histórico
  history: [],
  historyIndex: -1,
  maxHistory: 50,
  
  // Salvar estado no histórico
  saveToHistory() {
    // Remove estados futuros se estiver no meio da pilha
    this.history = this.history.slice(0, this.historyIndex + 1);
    
    // Adiciona novo estado
    const snapshot = {
      elements: JSON.parse(JSON.stringify(this.elements)),
      canvas: JSON.parse(JSON.stringify(this.canvas))
    };
    
    this.history.push(snapshot);
    
    // Limita tamanho do histórico
    if (this.history.length > this.maxHistory) {
      this.history.shift();
    } else {
      this.historyIndex++;
    }
  },
  
  // Desfazer
  undo() {
    if (this.historyIndex > 0) {
      this.historyIndex--;
      const snapshot = this.history[this.historyIndex];
      this.elements = JSON.parse(JSON.stringify(snapshot.elements));
      this.canvas = JSON.parse(JSON.stringify(snapshot.canvas));
      refreshPreview();
      showToast('Desfeito', 'info');
    }
  },
  
  // Refazer
  redo() {
    if (this.historyIndex < this.history.length - 1) {
      this.historyIndex++;
      const snapshot = this.history[this.historyIndex];
      this.elements = JSON.parse(JSON.stringify(snapshot.elements));
      this.canvas = JSON.parse(JSON.stringify(snapshot.canvas));
      refreshPreview();
      showToast('Refeito', 'info');
    }
  },
  
  // Atalhos de teclado
  init() {
    document.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'z') {
        e.preventDefault();
        if (e.shiftKey) {
          this.redo();
        } else {
          this.undo();
        }
      }
    });
  }
});
```

#### UI - Botões:
```html
<div class="history-controls">
  <button 
    @click="$store.editor.undo()"
    :disabled="$store.editor.historyIndex <= 0"
    class="btn-icon"
    title="Desfazer (Ctrl+Z)"
  >
    ↶ Desfazer
  </button>
  
  <button 
    @click="$store.editor.redo()"
    :disabled="$store.editor.historyIndex >= $store.editor.history.length - 1"
    class="btn-icon"
    title="Refazer (Ctrl+Shift+Z)"
  >
    ↷ Refazer
  </button>
</div>
```

---

### 9️⃣ VALIDAÇÕES
**Arquivo:** `ticket_layout.html` - Validation Functions

#### Validar antes de salvar:
```javascript
function validateLayout() {
  const state = Alpine.store('editor');
  const errors = [];
  const warnings = [];
  
  // 1. Elementos fora do canvas
  state.elements.forEach(el => {
    if (el.x < 0 || el.y < 0) {
      errors.push(`Elemento "${el.value}" está com posição negativa`);
    }
    
    if (el.x > state.canvas.width || el.y > state.canvas.height) {
      warnings.push(`Elemento "${el.value}" pode estar fora do canvas`);
    }
  });
  
  // 2. Elementos alinhados à direita - verificar overflow
  state.elements.forEach(el => {
    if (el.align === 'right' && el.type === 'text') {
      // Estimar largura do texto (aproximado)
      const estimatedWidth = (el.value.length * el.size * 0.6) / 3.779; // px to mm
      
      if (el.x - estimatedWidth < 0) {
        errors.push(`Texto "${el.value}" alinhado à direita será cortado. Ajuste a posição X.`);
      }
    }
  });
  
  // 3. QR Code muito pequeno
  state.elements.forEach(el => {
    if (el.type === 'qrcode' && el.size_mm < 15) {
      warnings.push(`QR Code muito pequeno (${el.size_mm}mm). Recomendado: mínimo 20mm.`);
    }
  });
  
  // 4. Validar tags obrigatórias para QR Code
  const hasQrCode = state.elements.some(el => el.type === 'qrcode');
  if (hasQrCode) {
    const qrCodeElement = state.elements.find(el => el.type === 'qrcode');
    if (!qrCodeElement.value.includes('{qrcode_hash}')) {
      errors.push('QR Code deve conter a tag {qrcode_hash}');
    }
  }
  
  return { errors, warnings };
}

// Chamar ao salvar
async function saveLayout() {
  const validation = validateLayout();
  
  if (validation.errors.length > 0) {
    showToast(`Erros encontrados:\n${validation.errors.join('\n')}`, 'error');
    return;
  }
  
  if (validation.warnings.length > 0) {
    const confirm = await showConfirm(
      `Avisos:\n${validation.warnings.join('\n')}\n\nDeseja continuar?`
    );
    if (!confirm) return;
  }
  
  // Prosseguir com salvamento
  // ...
}
```

---

### 🔟 SALVAMENTO
**Arquivo:** `app/routers/admin_web.py` - Backend

#### Endpoint:
```python
@router.post("/admin/eventos/{evento_id}/layout/save")
async def save_layout(
    evento_id: str,
    layout: dict,
    db: AsyncIOMotorClient = Depends(get_database)
):
    """Salva o layout do ingresso"""
    
    # Validações server-side
    if not layout.get('canvas'):
        raise HTTPException(400, "Canvas configuration missing")
    
    if not layout.get('elements'):
        raise HTTPException(400, "No elements defined")
    
    # Atualizar no MongoDB
    result = await db.eventos.update_one(
        {"_id": ObjectId(evento_id)},
        {"$set": {"layout": layout}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(404, "Evento não encontrado")
    
    return {"success": True, "message": "Layout salvo com sucesso"}
```

#### Frontend:
```javascript
async function saveLayout() {
  const validation = validateLayout();
  if (validation.errors.length > 0) return;
  
  const state = Alpine.store('editor');
  
  try {
    const response = await fetch(`/admin/eventos/${eventoId}/layout/save`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        canvas: state.canvas,
        elements: state.elements
      })
    });
    
    if (response.ok) {
      showToast('✅ Layout salvo com sucesso!', 'success');
      state.saveToHistory(); // Salvar no histórico local
    } else {
      const error = await response.json();
      showToast(`❌ Erro: ${error.detail}`, 'error');
    }
  } catch (error) {
    showToast('❌ Erro ao salvar layout', 'error');
  }
}
```

---

## 📱 Responsividade Mobile

### Breakpoints:
```css
/* Desktop: Sidebar + Canvas + Preview */
@media (min-width: 1024px) {
  .layout-editor {
    display: grid;
    grid-template-columns: 300px 1fr;
    grid-template-rows: auto 1fr;
  }
  
  .sidebar { grid-column: 1; grid-row: 1 / 3; }
  .canvas-area { grid-column: 2; grid-row: 1; }
  .preview-area { grid-column: 2; grid-row: 2; }
}

/* Tablet: Tabs (Canvas | Preview) */
@media (min-width: 768px) and (max-width: 1023px) {
  .layout-editor {
    display: flex;
    flex-direction: column;
  }
  
  .sidebar { order: 1; }
  
  .canvas-preview-tabs { 
    order: 2;
    display: flex;
    gap: 1rem;
  }
}

/* Mobile: Accordion */
@media (max-width: 767px) {
  .layout-editor {
    display: flex;
    flex-direction: column;
  }
  
  .sidebar,
  .canvas-area,
  .preview-area {
    width: 100%;
  }
  
  /* Botões fixos no bottom */
  .save-bar {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: var(--bg-dark);
    padding: 1rem;
    box-shadow: 0 -2px 10px rgba(0,0,0,0.3);
  }
}
```

---

## 🗂️ Estrutura de Arquivos

```
app/
├── routers/
│   └── admin_web.py          # Endpoints do editor
├── templates/
│   └── admin/
│       └── ticket_layout.html  # Template principal (REFAZER)
├── static/
│   ├── css/
│   │   └── layout-editor.css   # Estilos do editor (NOVO)
│   └── js/
│       └── layout-editor.js    # Lógica Alpine.js (NOVO)
└── utils/
    └── layout_renderer.py      # Renderização PIL (usar existente)

docs/
└── PLANO_IMPLEMENTACAO_EDITOR_LAYOUT.md  # Este arquivo
```

---

## 🚀 Roadmap de Implementação

### FASE 1: Setup Base (2-3 horas)
- [ ] Instalar Alpine.js via CDN
- [ ] Criar estrutura HTML base (sidebar + canvas + preview)
- [ ] Implementar Alpine.store com estado inicial
- [ ] Configurar Interact.js para drag básico
- [ ] CSS base para layout grid

### FASE 2: Canvas & Elementos (4-5 horas)
- [ ] Renderizar elementos no canvas via Alpine
- [ ] Drag & drop com atualização de posição
- [ ] Botão "Confirmar Posição" após drag
- [ ] Conversão px ↔ mm
- [ ] Réguas horizontais e verticais
- [ ] Seleção de elementos (click)

### FASE 3: Sidebar - Adicionar Elementos (3-4 horas)
- [ ] Formulário dinâmico por tipo de elemento
- [ ] Botões de tags inteligentes
- [ ] Adicionar texto/qrcode/logo/divider
- [ ] Lista de elementos com drag para reordenar
- [ ] Delete com confirmação

### FASE 4: Painel de Propriedades (3-4 horas)
- [ ] Inputs X/Y sincronizados com drag
- [ ] Propriedades específicas por tipo
- [ ] Formatação de texto (B/I/U/S)
- [ ] Alinhamento rápido (esquerda/centro/direita)
- [ ] Atualização em tempo real no canvas

### FASE 5: Preview em Tempo Real (2-3 horas)
- [ ] Endpoint `/preview` com dados fictícios
- [ ] Dados: "Edson Arantes do Nascimento", CPF "123.456.789-00"
- [ ] Auto-refresh com debounce (500ms)
- [ ] Loading state
- [ ] Error handling

### FASE 6: Templates & Histórico (3-4 horas)
- [ ] Criar templates "Padrão VIP" e "Simples"
- [ ] Endpoint para listar/carregar templates
- [ ] Aplicar template ao criar evento
- [ ] Implementar undo/redo com Alpine
- [ ] Atalhos de teclado (Ctrl+Z / Ctrl+Shift+Z)

### FASE 7: Validações & Salvamento (2-3 horas)
- [ ] Validar elementos fora do canvas
- [ ] Validar alinhamento à direita (overflow)
- [ ] Validar tamanho mínimo QR Code
- [ ] Toast notifications
- [ ] Endpoint de salvamento
- [ ] Confirmações de sucesso/erro

### FASE 8: Responsividade & Polish (3-4 horas)
- [ ] Media queries para tablet/mobile
- [ ] Touch-friendly drag on mobile
- [ ] Fixed save bar no mobile
- [ ] Testar em diferentes resoluções
- [ ] Ajustes finais de UX

### FASE 9: Testes & Deploy (2-3 horas)
- [ ] Testar fluxo completo
- [ ] Testar undo/redo extensivamente
- [ ] Testar preview com dados reais
- [ ] Documentar uso do editor
- [ ] Deploy remoto

---

## ⏱️ Estimativa Total
**25-30 horas de desenvolvimento**

---

## 🎯 Dependências

### NPM/CDN:
```html
<!-- Alpine.js -->
<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>

<!-- Interact.js (já instalado) -->
<script src="https://cdn.jsdelivr.net/npm/interactjs@1.10.19/dist/interact.min.js"></script>

<!-- Tailwind CSS (já instalado) -->
```

### Python:
```txt
# requirements.txt (já instalados)
fastapi
pillow
pymongo
motor
```

---

## 📝 Checklist de Validação Final

Antes de considerar completo, validar:

- [ ] Drag & drop funciona fluido em desktop
- [ ] Inputs X/Y sincronizam com drag
- [ ] Preview atualiza automaticamente (< 1s)
- [ ] Dados fictícios aparecem no preview
- [ ] Templates carregam corretamente
- [ ] Undo/Redo funciona (mínimo 10 ações)
- [ ] Salvar persiste no MongoDB
- [ ] Validações bloqueiam saves inválidos
- [ ] Responsivo em mobile (360px width)
- [ ] Réguas aparecem e estão precisas
- [ ] Elementos não saem do canvas
- [ ] Formatação de texto funciona (B/I/U/S)
- [ ] QR Code renderiza corretamente
- [ ] Logo carrega do evento
- [ ] Divisor horizontal/vertical renderiza

---

## 🐛 Riscos & Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| Preview lento | Média | Alto | Debounce agressivo (1s), cache server-side |
| Alpine.js conflito | Baixa | Médio | Testar em ambiente isolado primeiro |
| Drag impreciso mobile | Alta | Médio | Usar touch events específicos do Interact.js |
| Conversão px↔mm incorreta | Média | Alto | Testes unitários para cálculos, logging extensivo |
| Histórico estoura memória | Baixa | Baixo | Limitar a 50 estados, usar JSON.stringify compacto |

---

## 📚 Referências

- **Alpine.js Docs:** https://alpinejs.dev/
- **Interact.js Docs:** https://interactjs.io/
- **Tailwind CSS:** https://tailwindcss.com/
- **PIL/Pillow:** https://pillow.readthedocs.io/

---

## ✅ Próximos Passos

1. **Aprovação deste plano** pelo stakeholder
2. **Criar branch** `feature/new-layout-editor`
3. **Implementar FASE 1** (setup base)
4. **Review incremental** a cada fase concluída
5. **Deploy em staging** após FASE 8
6. **Deploy em produção** após validação completa

---

**Documento vivo - atualizar conforme implementação avança**
