// layout-editor.js - Editor de Layout com Alpine.js e Fabric.js
document.addEventListener('alpine:init', () => {
  Alpine.store('layoutEditor', {
    // Configuração do canvas
    canvas: {
      width: 62,
      height: 120,
      orientation: 'portrait',
      padding: 5,
    },

    // Elementos e grupos
    elements: [],
    groups: [],

    // Seleção
    selectedElementId: null,
    selectedGroupId: null,

    // Modo de edição
    mode: 'normal', // 'normal' ou 'editing-group'
    editingGroupId: null,

    // Referências ao Fabric
    fabricCanvas: null,          // canvas principal
    fabricGroupCanvas: null,     // canvas de edição do grupo (opcional)

    // Preview
    previewUrl: null,
    previewLoading: false,

    // Histórico (undo/redo simples)
    history: [],
    historyIndex: -1,

    // Inicialização
    init() {
      this.loadDraft();
      this.initFabric();
      this.setupKeyboard();
      this.saveState();
    },

    // Inicializa o canvas Fabric
    initFabric() {
      const canvasEl = document.getElementById('ticket-canvas');
      if (!canvasEl) return;
      this.fabricCanvas = new fabric.Canvas(canvasEl, {
        selection: true,
        preserveObjectStacking: true,
        backgroundColor: '#ffffff',
      });
      this.fabricCanvas.on('object:modified', (e) => this.onObjectModified(e));
      this.fabricCanvas.on('selection:created', (e) => this.onSelection(e));
      this.fabricCanvas.on('selection:updated', (e) => this.onSelection(e));
      this.fabricCanvas.on('selection:cleared', () => this.clearSelection());
      this.renderCanvas();
    },

    // Renderiza todo o canvas principal
    renderCanvas() {
      if (!this.fabricCanvas) return;
      this.fabricCanvas.clear();
      this.fabricCanvas.setDimensions({
        width: this.mmToPx(this.canvas.width),
        height: this.mmToPx(this.canvas.height),
      });
      this.fabricCanvas.setBackgroundColor('#ffffff', () => {});

      // Desenha guias de padding e centro
      this.drawGuides();

      // Desenha grupos primeiro (para ficarem atrás)
      this.groups.forEach(group => this.drawGroup(group));

      // Desenha elementos que não pertencem a grupos
      this.elements
        .filter(el => !el.groupId)
        .forEach(el => this.drawElement(el));

      this.fabricCanvas.renderAll();
    },

    drawGuides() {
      const w = this.mmToPx(this.canvas.width);
      const h = this.mmToPx(this.canvas.height);
      const pad = this.mmToPx(this.canvas.padding);
      const guideColor = 'rgba(59,130,246,0.3)';
      // Linhas verticais de padding
      this.fabricCanvas.add(new fabric.Line([pad, 0, pad, h], {
        stroke: guideColor, strokeWidth: 1, selectable: false, evented: false,
      }));
      this.fabricCanvas.add(new fabric.Line([w - pad, 0, w - pad, h], {
        stroke: guideColor, strokeWidth: 1, selectable: false, evented: false,
      }));
      // Linha central
      this.fabricCanvas.add(new fabric.Line([w / 2, 0, w / 2, h], {
        stroke: guideColor, strokeWidth: 1, selectable: false, evented: false,
      }));
    },

    drawElement(el) {
      let obj;
      const absPos = this.getElementAbsolutePosition(el);
      const left = this.getAlignedLeft(el, absPos.x);
      const top = this.mmToPx(absPos.y);

      if (el.type === 'text') {
        const textValue = el.value || 'Texto';
        obj = new fabric.Text(textValue, {
          left, top,
          fontSize: el.size || 12,
          fontFamily: el.font || 'Arial',
          fontWeight: el.bold ? 'bold' : 'normal',
          fontStyle: el.italic ? 'italic' : 'normal',
          underline: el.underline || false,
          fill: el.color || '#000000',
          originX: this.getOriginX(el),
        });
      } else if (el.type === 'qrcode' || el.type === 'logo') {
        const size = this.mmToPx(el.size_mm || 30);
        const rect = new fabric.Rect({
          width: size, height: size, fill: '#e2e8f0', stroke: '#94a3b8', strokeWidth: 1,
        });
        const text = new fabric.Text(el.type === 'qrcode' ? 'QR' : 'LOGO', {
          fontSize: 12, fill: '#334155', originX: 'center', originY: 'center',
        });
        obj = new fabric.Group([rect, text], {
          left, top,
          originX: this.getOriginX(el),
        });
      } else if (el.type === 'divider') {
        const length = this.mmToPx(el.length_mm || 50);
        const thickness = el.thickness || 2;
        if (el.direction === 'vertical') {
          obj = new fabric.Rect({ width: thickness, height: length, fill: '#000', left, top });
        } else {
          obj = new fabric.Rect({ width: length, height: thickness, fill: '#000', left, top });
        }
        obj.set({ originX: this.getOriginX(el) });
      }

      if (obj) {
        obj.set({
          elementId: el.id,
          groupId: el.groupId || null,
          hasBorders: true,
          hasControls: false,
          lockMovementX: true,  // bloqueia movimento horizontal
          lockScalingX: true,
          lockScalingY: true,
          lockRotation: true,
        });
        this.fabricCanvas.add(obj);
        if (el.id === this.selectedElementId) {
          this.fabricCanvas.setActiveObject(obj);
        }
      }
    },

    getOriginX(el) {
      if (el.align === 'center') return 'center';
      if (el.align === 'right') return 'right';
      if (el.horizontal_position === 'center') return 'center';
      if (el.horizontal_position === 'right') return 'right';
      return 'left';
    },

    drawGroup(group) {
      // Desenha o contorno do grupo (tracejado)
      const left = this.getAlignedLeft(group, group.x || 0);
      const top = this.mmToPx(group.y || 0);
      const width = this.mmToPx(group.width || 40);
      const height = this.mmToPx(group.height || 30);
      const rect = new fabric.Rect({
        left, top, width, height,
        fill: 'rgba(99,102,241,0.05)',
        stroke: '#6366f1',
        strokeWidth: 1,
        strokeDashArray: [6, 4],
        selectable: true,
        hasControls: false,
        lockMovementX: true,
        lockMovementY: false,
      });
      rect.set({
        groupId: group.id,
        isGroupFrame: true,
      });
      this.fabricCanvas.add(rect);

      // Se o grupo tem snapshot, desenha a imagem por cima
      if (group.snapshot) {
        fabric.Image.fromURL(group.snapshot, (img) => {
          img.set({ 
            left, top, 
            scaleX: width / img.width,
            scaleY: height / img.height,
            selectable: false, 
            evented: false 
          });
          this.fabricCanvas.add(img);
          this.fabricCanvas.renderAll();
        });
      } else {
        // Placeholder
        const text = new fabric.Text('📦 Grupo', {
          left: left + width/2, top: top + height/2,
          fontSize: 12, fill: '#6366f1', originX: 'center', originY: 'center',
          selectable: false, evented: false,
        });
        this.fabricCanvas.add(text);
      }
    },

    // Retorna a posição absoluta (x,y em mm) de um elemento, considerando grupo pai
    getElementAbsolutePosition(el) {
      let x = parseFloat(el.x) || 0;
      let y = parseFloat(el.y) || 0;
      if (el.groupId) {
        const group = this.groups.find(g => g.id === el.groupId);
        if (group) {
          x += parseFloat(group.x) || 0;
          y += parseFloat(group.y) || 0;
        }
      }
      return { x, y };
    },

    // Calcula o left em pixels baseado no alinhamento e margens
    getAlignedLeft(el, anchorXmm) {
      const canvasWidthPx = this.mmToPx(this.canvas.width);
      const anchorPx = this.mmToPx(anchorXmm);
      const marginLeft = this.mmToPx(el.margin_left || 0);
      const marginRight = this.mmToPx(el.margin_right || 0);
      const padPx = this.mmToPx(this.canvas.padding);
      
      // A posição final depende do alinhamento
      if (el.horizontal_position === 'left') {
        return padPx + marginLeft;
      } else if (el.horizontal_position === 'center') {
        return (canvasWidthPx / 2) + marginLeft - marginRight;
      } else if (el.horizontal_position === 'right') {
        return canvasWidthPx - padPx - marginRight;
      }
      return anchorPx;
    },

    mmToPx(mm) { return mm * 3.78; }, // 96 DPI
    pxToMm(px) { return px / 3.78; },

    // Eventos Fabric
    onObjectModified(e) {
      const obj = e.target;
      if (!obj) return;
      if (obj.isGroupFrame) {
        // Grupo foi movido verticalmente
        const group = this.groups.find(g => g.id === obj.groupId);
        if (group) {
          group.y = this.pxToMm(obj.top || 0);
          this.saveState();
          this.renderCanvas();
        }
        return;
      }
      const element = this.elements.find(el => el.id === obj.elementId);
      if (element) {
        // Atualiza apenas Y, X não muda
        const absY = this.pxToMm(obj.top || 0);
        if (element.groupId) {
          const group = this.groups.find(g => g.id === element.groupId);
          if (group) {
            element.y = absY - (group.y || 0);
          }
        } else {
          element.y = absY;
        }
        this.saveState();
        this.renderCanvas();
      }
    },

    onSelection(e) {
      const obj = e.selected ? e.selected[0] : (e.target || null);
      if (!obj) return;
      if (obj.isGroupFrame) {
        this.selectedGroupId = obj.groupId;
        this.selectedElementId = null;
      } else if (obj.elementId) {
        this.selectedElementId = obj.elementId;
        this.selectedGroupId = null;
      }
    },

    clearSelection() {
      this.selectedElementId = null;
      this.selectedGroupId = null;
    },

    // Adicionar elemento
    addElement(type, initialProps = {}) {
      const newEl = {
        id: `elem-${Date.now()}-${Math.random()}`,
        type,
        x: 0,
        y: 10, // posição vertical inicial
        horizontal_position: 'center',
        margin_left: 0,
        margin_right: 0,
        align: 'left',
        ...initialProps,
      };
      // Se está editando um grupo, o elemento pertence a ele
      if (this.mode === 'editing-group' && this.editingGroupId) {
        newEl.groupId = this.editingGroupId;
      }
      this.elements.push(newEl);
      this.saveState();
      this.renderCanvas();
      this.toast('Elemento adicionado', 'success');
    },

    // Adicionar grupo
    addGroup() {
      const newGroup = {
        id: `group-${Date.now()}-${Math.random()}`,
        x: 0,
        y: 10,
        width: 40,
        height: 30,
        horizontal_position: 'center',
        margin_left: 0,
        margin_right: 0,
        direction: 'row', // 'row' ou 'column'
        align_items: 'left', // ou 'center', 'right', 'space-between'
        spacing: 2, // mm
        snapshot: null, // imagem do grupo renderizado
      };
      this.groups.push(newGroup);
      this.saveState();
      this.renderCanvas();
      this.toast('Grupo adicionado', 'success');
    },

    // Entrar no modo de edição de grupo
    enterGroupEditMode(groupId) {
      const group = this.groups.find(g => g.id === groupId);
      if (!group) return;
      this.mode = 'editing-group';
      this.editingGroupId = groupId;
      this.selectedElementId = null;
      this.selectedGroupId = null;
      // Aguardar próximo tick para o DOM atualizar
      setTimeout(() => {
        this.initGroupCanvas(group);
      }, 100);
    },

    initGroupCanvas(group) {
      const container = document.getElementById('group-edit-container');
      if (!container) return;
      container.innerHTML = '<canvas id="group-canvas" style="border:2px solid #6366f1; background:white;"></canvas>';
      const canvasEl = document.getElementById('group-canvas');
      this.fabricGroupCanvas = new fabric.Canvas(canvasEl, {
        selection: true,
        preserveObjectStacking: true,
        backgroundColor: '#ffffff',
        width: this.mmToPx(group.width),
        height: this.mmToPx(group.height),
      });
      
      // Desenha elementos internos
      const groupElements = this.elements.filter(el => el.groupId === group.id);
      groupElements.forEach(el => this.drawElementInGroup(el, group));
      
      this.fabricGroupCanvas.on('object:modified', (e) => this.onGroupObjectModified(e, group));
      this.fabricGroupCanvas.on('selection:created', (e) => this.onGroupSelection(e));
      this.fabricGroupCanvas.on('selection:updated', (e) => this.onGroupSelection(e));
      this.fabricGroupCanvas.on('selection:cleared', () => this.clearSelection());
      this.fabricGroupCanvas.renderAll();
    },

    drawElementInGroup(el, group) {
      let obj;
      // No grupo, a posição é relativa ao grupo
      const left = this.mmToPx(el.x || 0);
      const top = this.mmToPx(el.y || 0);

      if (el.type === 'text') {
        const textValue = el.value || 'Texto';
        obj = new fabric.Text(textValue, {
          left, top,
          fontSize: el.size || 12,
          fontFamily: el.font || 'Arial',
          fontWeight: el.bold ? 'bold' : 'normal',
          fontStyle: el.italic ? 'italic' : 'normal',
          underline: el.underline || false,
          fill: el.color || '#000000',
          originX: 'left',
        });
      } else if (el.type === 'qrcode' || el.type === 'logo') {
        const size = this.mmToPx(el.size_mm || 30);
        const rect = new fabric.Rect({
          width: size, height: size, fill: '#e2e8f0', stroke: '#94a3b8', strokeWidth: 1,
        });
        const text = new fabric.Text(el.type === 'qrcode' ? 'QR' : 'LOGO', {
          fontSize: 12, fill: '#334155', originX: 'center', originY: 'center',
        });
        obj = new fabric.Group([rect, text], {
          left, top,
          originX: 'left',
        });
      } else if (el.type === 'divider') {
        const length = this.mmToPx(el.length_mm || 50);
        const thickness = el.thickness || 2;
        if (el.direction === 'vertical') {
          obj = new fabric.Rect({ width: thickness, height: length, fill: '#000', left, top });
        } else {
          obj = new fabric.Rect({ width: length, height: thickness, fill: '#000', left, top });
        }
        obj.set({ originX: 'left' });
      }

      if (obj) {
        obj.set({
          elementId: el.id,
          groupId: el.groupId,
          hasBorders: true,
          hasControls: false,
          lockScalingX: true,
          lockScalingY: true,
          lockRotation: true,
        });
        this.fabricGroupCanvas.add(obj);
        if (el.id === this.selectedElementId) {
          this.fabricGroupCanvas.setActiveObject(obj);
        }
      }
    },

    onGroupObjectModified(e, group) {
      const obj = e.target;
      if (!obj) return;
      const element = this.elements.find(el => el.id === obj.elementId);
      if (element) {
        // Atualiza posição relativa ao grupo
        element.x = this.pxToMm(obj.left || 0);
        element.y = this.pxToMm(obj.top || 0);
        this.saveState();
      }
    },

    onGroupSelection(e) {
      const obj = e.selected ? e.selected[0] : (e.target || null);
      if (obj && obj.elementId) {
        this.selectedElementId = obj.elementId;
        this.selectedGroupId = null;
      }
    },

    exitGroupEditMode() {
      if (!this.editingGroupId) return;
      // Renderizar grupo como imagem (snapshot)
      const group = this.groups.find(g => g.id === this.editingGroupId);
      if (group && this.fabricGroupCanvas) {
        group.snapshot = this.fabricGroupCanvas.toDataURL('png');
      }
      this.mode = 'normal';
      this.editingGroupId = null;
      this.fabricGroupCanvas = null;
      this.initFabric(); // recria o canvas principal
      this.toast('Modo de edição de grupo encerrado', 'info');
    },

    // Atualizar propriedade de elemento ou grupo
    updateProperty(prop, value) {
      if (this.selectedElementId) {
        const el = this.elements.find(e => e.id === this.selectedElementId);
        if (el) {
          el[prop] = value;
          this.saveState();
          if (this.mode === 'editing-group') {
            const group = this.groups.find(g => g.id === this.editingGroupId);
            if (group) this.initGroupCanvas(group);
          } else {
            this.renderCanvas();
          }
        }
      } else if (this.selectedGroupId) {
        const g = this.groups.find(g => g.id === this.selectedGroupId);
        if (g) {
          g[prop] = value;
          this.saveState();
          this.renderCanvas();
        }
      }
    },

    // Delete
    deleteSelected() {
      if (this.selectedElementId) {
        this.elements = this.elements.filter(e => e.id !== this.selectedElementId);
        this.selectedElementId = null;
        this.saveState();
        if (this.mode === 'editing-group') {
          const group = this.groups.find(g => g.id === this.editingGroupId);
          if (group) this.initGroupCanvas(group);
        } else {
          this.renderCanvas();
        }
        this.toast('Elemento removido', 'info');
      } else if (this.selectedGroupId) {
        this.groups = this.groups.filter(g => g.id !== this.selectedGroupId);
        // Remover elementos do grupo
        this.elements = this.elements.filter(e => e.groupId !== this.selectedGroupId);
        this.selectedGroupId = null;
        this.saveState();
        this.renderCanvas();
        this.toast('Grupo removido', 'info');
      }
    },

    // Undo/Redo
    saveState() {
      const state = {
        canvas: { ...this.canvas },
        elements: JSON.parse(JSON.stringify(this.elements)),
        groups: JSON.parse(JSON.stringify(this.groups)),
      };
      if (this.historyIndex < this.history.length - 1) {
        this.history = this.history.slice(0, this.historyIndex + 1);
      }
      this.history.push(state);
      if (this.history.length > 50) {
        this.history.shift();
      } else {
        this.historyIndex++;
      }
      this.saveDraft();
    },

    undo() {
      if (this.historyIndex <= 0) {
        this.toast('Nada para desfazer', 'info');
        return;
      }
      this.historyIndex--;
      this.loadState(this.history[this.historyIndex]);
      this.toast('Desfeito', 'info');
    },

    redo() {
      if (this.historyIndex >= this.history.length - 1) {
        this.toast('Nada para refazer', 'info');
        return;
      }
      this.historyIndex++;
      this.loadState(this.history[this.historyIndex]);
      this.toast('Refeito', 'info');
    },

    loadState(state) {
      this.canvas = state.canvas;
      this.elements = state.elements;
      this.groups = state.groups;
      if (this.mode === 'editing-group') {
        const group = this.groups.find(g => g.id === this.editingGroupId);
        if (group) this.initGroupCanvas(group);
      } else {
        this.renderCanvas();
      }
    },

    // Trocar orientação
    swapOrientation() {
      const temp = this.canvas.width;
      this.canvas.width = this.canvas.height;
      this.canvas.height = temp;
      this.saveState();
      this.renderCanvas();
    },

    // Persistência
    loadDraft() {
      const saved = localStorage.getItem('layout_draft');
      if (saved) {
        try {
          const data = JSON.parse(saved);
          this.canvas = data.canvas || this.canvas;
          this.elements = data.elements || [];
          this.groups = data.groups || [];
        } catch (e) {
          console.error('Erro ao carregar rascunho:', e);
        }
      }
    },

    saveDraft() {
      const data = {
        canvas: this.canvas,
        elements: this.elements,
        groups: this.groups,
      };
      localStorage.setItem('layout_draft', JSON.stringify(data));
    },

    clearDraft() {
      localStorage.removeItem('layout_draft');
      this.toast('Rascunho limpo', 'info');
    },

    // Preview
    async refreshPreview() {
      this.previewLoading = true;
      // Cria um canvas temporário para preview com dados fictícios
      const previewCanvas = document.createElement('canvas');
      previewCanvas.width = this.mmToPx(this.canvas.width);
      previewCanvas.height = this.mmToPx(this.canvas.height);
      const fabricPreview = new fabric.StaticCanvas(previewCanvas, {
        backgroundColor: '#ffffff',
      });

      // Mock data para tags
      const mockData = {
        '{NOME}': 'João da Silva',
        '{CPF}': '123.456.789-00',
        '{EMAIL}': 'joao@example.com',
        '{TIPO_INGRESSO}': 'VIP',
        '{EVENTO_NOME}': 'Festival 2026',
        '{DATA}': '15/03/2026',
        '{HORARIO}': '20:00',
        '{qrcode_hash}': 'ABC123XYZ',
      };

      // Renderiza elementos no preview
      for (const el of this.elements.filter(e => !e.groupId)) {
        await this.addElementToPreviewCanvas(fabricPreview, el, mockData);
      }

      // Renderiza grupos no preview
      for (const group of this.groups) {
        if (group.snapshot) {
          await new Promise((resolve) => {
            fabric.Image.fromURL(group.snapshot, (img) => {
              const left = this.getAlignedLeft(group, group.x || 0);
              const top = this.mmToPx(group.y || 0);
              const width = this.mmToPx(group.width);
              const height = this.mmToPx(group.height);
              img.set({ 
                left, top, 
                scaleX: width / img.width,
                scaleY: height / img.height,
              });
              fabricPreview.add(img);
              resolve();
            });
          });
        }
      }

      fabricPreview.renderAll();
      this.previewUrl = previewCanvas.toDataURL('png');
      this.previewLoading = false;
      this.toast('Preview atualizado', 'success');
    },

    async addElementToPreviewCanvas(fabricPreview, el, mockData) {
      let obj;
      const absPos = this.getElementAbsolutePosition(el);
      const left = this.getAlignedLeft(el, absPos.x);
      const top = this.mmToPx(absPos.y);

      if (el.type === 'text') {
        let textValue = el.value || 'Texto';
        // Substituir tags
        Object.keys(mockData).forEach(tag => {
          textValue = textValue.replace(new RegExp(tag.replace(/[{}]/g, '\\$&'), 'g'), mockData[tag]);
        });
        obj = new fabric.Text(textValue, {
          left, top,
          fontSize: el.size || 12,
          fontFamily: el.font || 'Arial',
          fontWeight: el.bold ? 'bold' : 'normal',
          fontStyle: el.italic ? 'italic' : 'normal',
          underline: el.underline || false,
          fill: el.color || '#000000',
          originX: this.getOriginX(el),
        });
      } else if (el.type === 'qrcode') {
        // Simula QR Code
        const size = this.mmToPx(el.size_mm || 30);
        const rect = new fabric.Rect({
          width: size, height: size, fill: '#000000',
        });
        obj = new fabric.Group([rect], {
          left, top,
          originX: this.getOriginX(el),
        });
      } else if (el.type === 'logo') {
        const size = this.mmToPx(el.size_mm || 30);
        const rect = new fabric.Rect({
          width: size, height: size, fill: '#3b82f6', stroke: '#1e40af', strokeWidth: 2,
        });
        obj = new fabric.Group([rect], {
          left, top,
          originX: this.getOriginX(el),
        });
      } else if (el.type === 'divider') {
        const length = this.mmToPx(el.length_mm || 50);
        const thickness = el.thickness || 2;
        if (el.direction === 'vertical') {
          obj = new fabric.Rect({ width: thickness, height: length, fill: '#000', left, top });
        } else {
          obj = new fabric.Rect({ width: length, height: thickness, fill: '#000', left, top });
        }
        obj.set({ originX: this.getOriginX(el) });
      }

      if (obj) {
        fabricPreview.add(obj);
      }
    },

    // Teclado
    setupKeyboard() {
      document.addEventListener('keydown', (e) => {
        // Ignora se estiver em input/textarea
        if (e.target.matches('input,textarea,select')) return;

        if (e.key === 'Escape' && this.mode === 'editing-group') {
          this.exitGroupEditMode();
        }
        if (e.key === 'Delete' || e.key === 'Backspace') {
          e.preventDefault();
          this.deleteSelected();
        }
        if ((e.ctrlKey || e.metaKey) && e.key === 'z') {
          e.preventDefault();
          if (e.shiftKey) this.redo(); 
          else this.undo();
        }
        if ((e.ctrlKey || e.metaKey) && e.key === 'y') {
          e.preventDefault();
          this.redo();
        }
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
          e.preventDefault();
          this.saveLayout();
        }
      });
    },

    // Salvar no backend
    async saveLayout() {
      const eventoId = window.eventoId;
      if (!eventoId) {
        this.toast('ID do evento não encontrado', 'error');
        return;
      }

      const payload = {
        layout_ingresso: {
          canvas: this.canvas,
          elements: this.elements,
          groups: this.groups,
        }
      };

      try {
        const response = await fetch(`/admin/eventos/layout/${eventoId}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(payload),
        });

        if (response.ok) {
          this.toast('Layout salvo com sucesso!', 'success');
          this.clearDraft();
        } else {
          const error = await response.json();
          this.toast(`Erro ao salvar: ${error.detail || 'Desconhecido'}`, 'error');
        }
      } catch (error) {
        console.error('Erro ao salvar layout:', error);
        this.toast('Erro de conexão ao salvar', 'error');
      }
    },

    // Toast simples
    toast(message, type = 'info') {
      const container = document.getElementById('toast-container');
      if (!container) return;
      const toast = document.createElement('div');
      toast.className = `toast toast-${type}`;
      toast.textContent = message;
      container.appendChild(toast);
      setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s';
        setTimeout(() => toast.remove(), 300);
      }, 3000);
    },
  });
});
