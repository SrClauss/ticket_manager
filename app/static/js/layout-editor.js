/**
 * Layout Editor with Groups - Alpine.js Store
 * Features:
 * - Horizontal snap positioning (10mm, 31mm, 52mm)
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
    
    // Horizontal snap positions (mm)
    horizontalPositions: {
      left: 10,
      center: 31,
      right: 52
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
        x: this.horizontalPositions.center,
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
        x: this.horizontalPositions.center,
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
        
        // Snap horizontal position
        if (this.mode !== 'editing-group') {
          const distances = Object.entries(this.horizontalPositions).map(([pos, val]) => ({
            position: pos,
            value: val,
            distance: Math.abs(x - val)
          }));
          const closest = distances.reduce((a, b) => a.distance < b.distance ? a : b);
          
          element.x = closest.value;
          element.horizontal_position = closest.position;
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
