/**
 * Layout Editor with Groups - Alpine.js Store
 * Features:
 * - Horizontal alignment (left/center/right) with margin support
 * - Group component with isolated editing mode
 * - Groups rendered as images (backend)
 * - Draft state (localStorage)
 * - Margin support for fine-tuning
 */

document.addEventListener('alpine:init', () => {
  Alpine.store('layoutEditor', {
    // Editor mode
    mode: 'normal', // 'normal' | 'editing-group'
    editingGroupId: null,
    
    // Canvas configuration
    canvas: {
      width: 62,
      height: 120,
      orientation: 'portrait',
      padding: 5,
      dpi: 300
    },
    
    // Elements and groups
    elements: [],
    groups: [],
    
    // Selection
    selectedElement: null,
    selectedGroup: null,
    
    // State
    isDirty: false,
    isSaving: false,
    lastSaved: null,
    
    // Preview
    previewUrl: null,
    previewLoading: false,
    
    // Initialize
    init() {
      this.loadDraft();
      this.setupKeyboardShortcuts();
    },
    
    // Computed: currently editing group
    get editingGroup() {
      return this.groups.find(g => g.id === this.editingGroupId) || null;
    },
    
    // Swap orientation (portrait <-> landscape)
    swapOrientation() {
      const temp = this.canvas.width;
      this.canvas.width = this.canvas.height;
      this.canvas.height = temp;
      this.canvas.orientation = this.canvas.orientation === 'portrait' ? 'landscape' : 'portrait';
      this.saveDraft();
    },
    
    // Compute CSS position style for an element based on horizontal_position and margins
    getElementPositionStyle(element) {
      const ml = element.margin_left || 0;
      const mr = element.margin_right || 0;
      const hp = element.horizontal_position || 'left';
      const cw = this.canvas.width;

      if (element.type === 'text') {
        // Text elements span available width; text-align controls direction
        return `left: ${ml}mm; right: ${mr}mm;`;
      }

      // QR code / divider: use size_mm or length_mm (default 30mm if not set)
      const size = element.size_mm || element.length_mm || 30;
      switch (hp) {
        case 'left':
          return `left: ${ml}mm;`;
        case 'center':
          return `left: ${Math.max(0, (cw - size) / 2 + ml - mr)}mm;`;
        case 'right':
          return `left: ${Math.max(0, cw - size - mr)}mm;`;
        default:
          return `left: ${ml}mm;`;
      }
    },
    
    // Compute CSS position style for a group based on horizontal_position and margins
    getGroupPositionStyle(group) {
      const ml = group.margin_left || 0;
      const mr = group.margin_right || 0;
      const hp = group.horizontal_position || 'left';
      const w = group.width || 40;
      const cw = this.canvas.width;

      switch (hp) {
        case 'left':
          return `left: ${ml}mm;`;
        case 'center':
          // Centers the group on the canvas; asymmetric margins shift the center point
          return `left: ${Math.max(0, (cw - w) / 2 + ml - mr)}mm;`;
        case 'right':
          return `left: ${Math.max(0, cw - w - mr)}mm;`;
        default:
          return `left: ${ml}mm;`;
      }
    },
    
    
    // Load draft from localStorage
    loadDraft() {
      const draft = localStorage.getItem(`layout_draft_${window.eventoId}`);
      if (draft) {
        try {
          const data = JSON.parse(draft);
          this.canvas = data.canvas || this.canvas;
          this.elements = data.elements || [];
          this.groups = data.groups || [];
          this.isDirty = true;
        } catch (e) {
          console.error('Failed to load draft:', e);
        }
      }
    },
    
    // Save draft to localStorage
    saveDraft() {
      const draft = {
        canvas: this.canvas,
        elements: this.elements,
        groups: this.groups,
        timestamp: new Date().toISOString()
      };
      localStorage.setItem(`layout_draft_${window.eventoId}`, JSON.stringify(draft));
      this.isDirty = true;
    },
    
    // Clear draft
    clearDraft() {
      localStorage.removeItem(`layout_draft_${window.eventoId}`);
      this.isDirty = false;
    },
    
    // Add element
    addElement(type) {
      const newElement = {
        id: `elem-${Date.now()}`,
        type: type,
        x: 0,
        y: 20,
        horizontal_position: 'center',
        margin_left: 0,
        margin_right: 0,
        z_index: this.elements.length + 1
      };
      
      // Type-specific defaults
      switch(type) {
        case 'text':
          Object.assign(newElement, {
            value: 'Texto',
            size: 12,
            font: 'Arial',
            align: 'center',
            bold: false,
            italic: false,
            underline: false
          });
          break;
        case 'qrcode':
          Object.assign(newElement, {
            value: '{qrcode_hash}',
            size_mm: 30
          });
          break;
        case 'divider':
          Object.assign(newElement, {
            direction: 'horizontal',
            length_mm: 40,
            thickness: 2
          });
          break;
      }
      
      if (this.mode === 'editing-group' && this.editingGroupId) {
        // Add to group
        const group = this.groups.find(g => g.id === this.editingGroupId);
        if (group) {
          group.elements.push(newElement);
        }
      } else {
        // Add to canvas
        this.elements.push(newElement);
      }
      
      this.saveDraft();
      this.selectElement(newElement.id);
    },
    
    // Add group
    addGroup() {
      const newGroup = {
        id: `group-${Date.now()}`,
        x: 0,
        y: 30,
        width: 40,
        height: 30,
        horizontal_position: 'center',
        align_items: 'left',
        margin_left: 0,
        margin_right: 0,
        elements: [],
        snapshot_image: null,
        z_index: this.elements.length + this.groups.length + 1
      };
      
      this.groups.push(newGroup);
      this.saveDraft();
      this.selectGroup(newGroup.id);
    },
    
    // Select element
    selectElement(elementId) {
      const element = this.mode === 'editing-group' && this.editingGroupId
        ? this.groups.find(g => g.id === this.editingGroupId)?.elements.find(e => e.id === elementId)
        : this.elements.find(e => e.id === elementId);
      
      this.selectedElement = element;
      this.selectedGroup = null;
    },
    
    // Select group
    selectGroup(groupId) {
      this.selectedGroup = this.groups.find(g => g.id === groupId);
      this.selectedElement = null;
    },
    
    // Enter group editing mode
    async enterGroupEditMode(groupId) {
      this.mode = 'editing-group';
      this.editingGroupId = groupId;
      this.selectedGroup = this.groups.find(g => g.id === groupId);
      this.selectedElement = null;
    },
    
    // Exit group editing mode
    async exitGroupEditMode() {
      if (this.editingGroupId) {
        const group = this.groups.find(g => g.id === this.editingGroupId);
        if (group) {
          // Render group as image
          await this.renderGroupAsImage(group);
        }
      }
      
      this.mode = 'normal';
      this.editingGroupId = null;
      this.selectedElement = null;
    },
    
    // Render group as image (backend call)
    async renderGroupAsImage(group) {
      try {
        const response = await fetch(`/admin/eventos/layout/${window.eventoId}/render-group`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ group })
        });
        
        if (response.ok) {
          const data = await response.json();
          group.snapshot_image = data.snapshot_image;
          this.saveDraft();
          showToast('Grupo renderizado com sucesso', 'success');
        } else {
          showToast('Erro ao renderizar grupo', 'error');
        }
      } catch (error) {
        console.error('Error rendering group:', error);
        showToast('Erro ao renderizar grupo', 'error');
      }
    },
    
    // Update element position
    updateElementPosition(elementId, x, y) {
      const element = this.mode === 'editing-group' && this.editingGroupId
        ? this.groups.find(g => g.id === this.editingGroupId)?.elements.find(e => e.id === elementId)
        : this.elements.find(e => e.id === elementId);
      
      if (element) {
        element.y = y;
        
        if (this.mode !== 'editing-group') {
          // Snap to left / center / right based on thirds of canvas width
          const cw = this.canvas.width;
          if (x < cw / 3) {
            element.horizontal_position = 'left';
          } else if (x < 2 * cw / 3) {
            element.horizontal_position = 'center';
          } else {
            element.horizontal_position = 'right';
          }
        } else {
          element.x = x; // Free positioning inside group
        }
        
        this.saveDraft();
      }
    },
    
    // Update element property
    updateElementProperty(property, value) {
      if (this.selectedElement) {
        this.selectedElement[property] = value;
        this.saveDraft();
      } else if (this.selectedGroup) {
        this.selectedGroup[property] = value;
        this.saveDraft();
      }
    },
    
    // Delete element
    deleteElement(elementId) {
      if (this.mode === 'editing-group' && this.editingGroupId) {
        const group = this.groups.find(g => g.id === this.editingGroupId);
        if (group) {
          group.elements = group.elements.filter(e => e.id !== elementId);
        }
      } else {
        this.elements = this.elements.filter(e => e.id !== elementId);
      }
      
      this.selectedElement = null;
      this.saveDraft();
    },
    
    // Delete group
    deleteGroup(groupId) {
      this.groups = this.groups.filter(g => g.id !== groupId);
      this.selectedGroup = null;
      this.saveDraft();
    },
    
    // Save layout to server (final)
    async saveLayout() {
      if (!confirm('⚠️ ATENÇÃO: Ao salvar, o histórico de alterações será apagado e esta versão será usada para emissão de ingressos.\n\nDeseja continuar?')) {
        return;
      }
      
      this.isSaving = true;
      
      try {
        const response = await fetch(`/admin/eventos/layout/${window.eventoId}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            layout_ingresso: {
              canvas: this.canvas,
              elements: this.elements,
              groups: this.groups
            }
          })
        });
        
        if (response.ok) {
          this.clearDraft();
          this.lastSaved = new Date();
          showToast('✅ Layout salvo com sucesso!', 'success');
          
          // Refresh preview
          await this.refreshPreview();
        } else {
          const error = await response.json();
          showToast(`❌ Erro: ${error.detail}`, 'error');
        }
      } catch (error) {
        console.error('Error saving layout:', error);
        showToast('❌ Erro ao salvar layout', 'error');
      } finally {
        this.isSaving = false;
      }
    },
    
    // Compute URL for print-specific preview image (query string only)
    printPreviewUrl() {
      // uses the new endpoint created to render an image with accurate millimeter
      // dimensions and optional rotation.  orientation is included for clarity but
      // only used when landscape is selected.
      let params = new URLSearchParams();
      params.set('width_mm', this.canvas.width);
      params.set('height_mm', this.canvas.height);
      params.set('dpi', this.canvas.dpi || 300);
      if (this.canvas.orientation && this.canvas.orientation.toLowerCase() === 'landscape') {
        params.set('orientation', 'landscape');
      }
      return `/api/eventos/labels/print.png?` + params.toString();
    },

    // Refresh preview
    async refreshPreview() {
      this.previewLoading = true;
      
      try {
        const response = await fetch(`/admin/eventos/layout/${window.eventoId}/preview`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            canvas: this.canvas,
            elements: this.elements,
            groups: this.groups
          })
        });
        
        if (response.ok) {
          const blob = await response.blob();
          const url = URL.createObjectURL(blob);
          
          if (this.previewUrl) {
            URL.revokeObjectURL(this.previewUrl);
          }
          
          this.previewUrl = url;
        }
      } catch (error) {
        console.error('Error refreshing preview:', error);
      } finally {
        this.previewLoading = false;
      }
    },
    
    // Setup keyboard shortcuts
    setupKeyboardShortcuts() {
      document.addEventListener('keydown', (e) => {
        // Escape: exit group edit mode
        if (e.key === 'Escape' && this.mode === 'editing-group') {
          this.exitGroupEditMode();
        }
        
        // Delete: remove selected element/group
        if ((e.key === 'Delete' || e.key === 'Backspace') && !e.target.matches('input, textarea')) {
          e.preventDefault();
          if (this.selectedElement) {
            this.deleteElement(this.selectedElement.id);
          } else if (this.selectedGroup) {
            this.deleteGroup(this.selectedGroup.id);
          }
        }
        
        // Ctrl+S: Save
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
          e.preventDefault();
          this.saveLayout();
        }
      });
    }
  });
});

// Utility: Show toast notification
function showToast(message, type = 'info') {
  // Bootstrap toast implementation
  const toastHTML = `
    <div class="toast align-items-center text-white bg-${type === 'success' ? 'success' : type === 'error' ? 'danger' : 'info'} border-0" role="alert">
      <div class="d-flex">
        <div class="toast-body">${message}</div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
      </div>
    </div>
  `;
  
  const container = document.getElementById('toast-container');
  if (container) {
    container.insertAdjacentHTML('beforeend', toastHTML);
    const toastEl = container.lastElementChild;
    const toast = new bootstrap.Toast(toastEl);
    toast.show();
    toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove());
  }
}

// Debounce utility
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}
