import { useState, useRef, useCallback, useEffect } from 'react'
import { useKV } from '@github/spark/hooks'
import { toast } from 'sonner'
import { Toaster } from '@/components/ui/sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import {
  ArrowCounterClockwise,
  ArrowClockwise,
  FloppyDisk,
  Plus,
  Trash,
  TextT,
  QrCode,
  Minus,
  Package,
  PencilSimple,
  Check,
} from '@phosphor-icons/react'
import { TicketCanvas, TicketCanvasRef } from '@/components/TicketCanvas'
import type { TicketElement, TicketGroup, CanvasConfig, LayoutState, EditorMode } from '@/types/layout'

const TEMPLATE_TAGS = ['{NOME}', '{CPF}', '{EMAIL}', '{TIPO_INGRESSO}', '{EVENTO_NOME}', '{DATA}', '{HORARIO}']

export default function App() {
  const [layoutState, setLayoutState, deleteLayoutState] = useKV<LayoutState>('ticket-layout', {
    canvas: {
      width: 62,
      height: 120,
      orientation: 'portrait',
      padding: 5,
    },
    elements: [],
    groups: [],
  })

  const [selectedElementId, setSelectedElementId] = useState<string | null>(null)
  const [selectedGroupId, setSelectedGroupId] = useState<string | null>(null)
  const [mode, setMode] = useState<EditorMode>('normal')
  const [editingGroupId, setEditingGroupId] = useState<string | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)

  const mainCanvasRef = useRef<TicketCanvasRef>(null)
  const groupCanvasRef = useRef<TicketCanvasRef>(null)

  if (!layoutState) {
    return <div className="h-screen flex items-center justify-center">Loading...</div>
  }

  const selectedElement = layoutState.elements.find((e) => e.id === selectedElementId)
  const selectedGroup = layoutState.groups.find((g) => g.id === selectedGroupId)
  const editingGroup = layoutState.groups.find((g) => g.id === editingGroupId)

  const currentElements =
    mode === 'editing-group'
      ? layoutState.elements.filter((e) => e.groupId === editingGroupId)
      : layoutState.elements.filter((e) => !e.groupId)

  const updateCanvas = useCallback((updates: Partial<CanvasConfig>) => {
    setLayoutState((prev) => {
      const current = prev || { canvas: { width: 62, height: 120, orientation: 'portrait' as const, padding: 5 }, elements: [], groups: [] }
      return {
        ...current,
        canvas: { ...current.canvas, ...updates },
      } as LayoutState
    })
  }, [setLayoutState])

  const addElement = useCallback(
    (type: 'text' | 'qrcode' | 'divider', initialProps = {}) => {
      const newEl: TicketElement = {
        id: `elem-${Date.now()}`,
        type,
        y: 10,
        horizontal_position: 'center',
        margin_left: 0,
        margin_right: 0,
        groupId: mode === 'editing-group' ? editingGroupId : null,
        ...(type === 'text' && { value: '{NOME}', size: 14, font: 'Arial', bold: false, italic: false }),
        ...(type === 'qrcode' && { size_mm: 30 }),
        ...(type === 'divider' && { length_mm: 40, thickness: 2 }),
        ...initialProps,
      }

      setLayoutState((prev) => {
        const current = prev || { canvas: { width: 62, height: 120, orientation: 'portrait' as const, padding: 5 }, elements: [], groups: [] }
        return {
          ...current,
          elements: [...current.elements, newEl],
        } as LayoutState
      })
      setSelectedElementId(newEl.id)
      setSelectedGroupId(null)
    },
    [mode, editingGroupId, setLayoutState]
  )

  const addGroup = useCallback(() => {
    if (mode === 'editing-group') {
      toast.error('Cannot create a group inside another group')
      return
    }

    const newGroup: TicketGroup = {
      id: `group-${Date.now()}`,
      y: 10,
      width: 50,
      height: 30,
      horizontal_position: 'center',
      margin_left: 0,
      margin_right: 0,
      snapshot: null,
    }

    setLayoutState((prev) => {
      const current = prev || { canvas: { width: 62, height: 120, orientation: 'portrait' as const, padding: 5 }, elements: [], groups: [] }
      return {
        ...current,
        groups: [...current.groups, newGroup],
      } as LayoutState
    })
    setSelectedGroupId(newGroup.id)
    setSelectedElementId(null)
  }, [mode, setLayoutState])

  const deleteSelected = useCallback(() => {
    if (selectedElementId) {
      setLayoutState((prev) => {
        const current = prev || { canvas: { width: 62, height: 120, orientation: 'portrait' as const, padding: 5 }, elements: [], groups: [] }
        return {
          ...current,
          elements: current.elements.filter((e) => e.id !== selectedElementId),
        } as LayoutState
      })
      setSelectedElementId(null)
    } else if (selectedGroupId) {
      setLayoutState((prev) => {
        const current = prev || { canvas: { width: 62, height: 120, orientation: 'portrait' as const, padding: 5 }, elements: [], groups: [] }
        return {
          ...current,
          groups: current.groups.filter((g) => g.id !== selectedGroupId),
          elements: current.elements.filter((e) => e.groupId !== selectedGroupId),
        } as LayoutState
      })
      setSelectedGroupId(null)
    }
  }, [selectedElementId, selectedGroupId, setLayoutState])

  const updateElement = useCallback(
    (id: string, updates: Partial<TicketElement>) => {
      setLayoutState((prev) => {
        const current = prev || { canvas: { width: 62, height: 120, orientation: 'portrait' as const, padding: 5 }, elements: [], groups: [] }
        return {
          ...current,
          elements: current.elements.map((el) => (el.id === id ? { ...el, ...updates } : el)),
        } as LayoutState
      })
    },
    [setLayoutState]
  )

  const updateGroup = useCallback(
    (id: string, updates: Partial<TicketGroup>) => {
      setLayoutState((prev) => {
        const current = prev || { canvas: { width: 62, height: 120, orientation: 'portrait' as const, padding: 5 }, elements: [], groups: [] }
        return {
          ...current,
          groups: current.groups.map((g) => (g.id === id ? { ...g, ...updates } : g)),
        } as LayoutState
      })
    },
    [setLayoutState]
  )

  const enterGroupEditMode = useCallback((groupId: string) => {
    setMode('editing-group')
    setEditingGroupId(groupId)
    setSelectedElementId(null)
    setSelectedGroupId(null)
  }, [])

  const exitGroupEditMode = useCallback(() => {
    if (!editingGroupId || !groupCanvasRef.current) return

    const snapshot = groupCanvasRef.current.getDataURL()
    updateGroup(editingGroupId, { snapshot })

    setMode('normal')
    setEditingGroupId(null)
    setSelectedElementId(null)
  }, [editingGroupId, updateGroup])

  const generatePreview = useCallback(async () => {
    if (mode === 'editing-group') return

    setPreviewLoading(true)
    await new Promise((resolve) => setTimeout(resolve, 500))

    const url = mainCanvasRef.current?.getDataURL()
    setPreviewUrl(url || null)
    setPreviewLoading(false)
  }, [mode])

  const saveLayout = useCallback(() => {
    toast.success('Layout saved successfully!')
  }, [])

  const copyTag = useCallback((tag: string) => {
    navigator.clipboard.writeText(tag).then(
      () => toast.success(`Tag ${tag} copied!`),
      () => toast.error('Failed to copy tag')
    )
  }, [])

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes((e.target as HTMLElement).tagName)) return

      if (e.key === 'Escape' && mode === 'editing-group') {
        exitGroupEditMode()
      }
      if (e.key === 'Delete' || e.key === 'Backspace') {
        e.preventDefault()
        deleteSelected()
      }
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault()
        saveLayout()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [mode, exitGroupEditMode, deleteSelected, saveLayout])

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-background text-foreground">
      <Toaster />

      <header className="bg-card border-b border-border p-4 flex justify-between items-center shrink-0">
        <div>
          <h1 className="text-xl font-bold text-primary">Ticket Layout Editor</h1>
          <p className="text-xs text-muted-foreground">
            Drag elements vertically on the canvas. Configure properties in the sidebar.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={saveLayout}>
            <FloppyDisk className="mr-2" size={16} />
            Save Layout
          </Button>
        </div>
      </header>

      {mode === 'editing-group' && (
        <div className="bg-accent text-accent-foreground px-4 py-2 text-center font-bold flex justify-center items-center gap-4 shrink-0 shadow-md">
          <span>🎨 Editing Group - Isolated</span>
          <Button variant="secondary" size="sm" onClick={exitGroupEditMode}>
            <Check className="mr-2" size={16} />
            Done Editing (ESC)
          </Button>
        </div>
      )}

      <div className="flex flex-1 overflow-hidden">
        <aside className="w-80 bg-card border-r border-border flex flex-col overflow-y-auto">
          <div className="p-4 border-b border-border">
            <h2 className="text-xs uppercase font-bold text-muted-foreground mb-3 tracking-wider">
              Canvas Settings
            </h2>
            <div className="grid grid-cols-2 gap-2 mb-2">
              <div>
                <Label className="text-xs">Width (mm)</Label>
                <Input
                  type="number"
                  value={layoutState.canvas.width}
                  onChange={(e) => updateCanvas({ width: parseFloat(e.target.value) })}
                  className="h-8"
                />
              </div>
              <div>
                <Label className="text-xs">Height (mm)</Label>
                <Input
                  type="number"
                  value={layoutState.canvas.height}
                  onChange={(e) => updateCanvas({ height: parseFloat(e.target.value) })}
                  className="h-8"
                />
              </div>
            </div>
            <div>
              <Label className="text-xs">Padding (mm)</Label>
              <Input
                type="number"
                value={layoutState.canvas.padding}
                onChange={(e) => updateCanvas({ padding: parseFloat(e.target.value) })}
                className="h-8"
              />
            </div>
          </div>

          <div className="p-4 border-b border-border">
            <h2 className="text-xs uppercase font-bold text-muted-foreground mb-3 tracking-wider">Add Elements</h2>
            <div className="grid grid-cols-2 gap-2">
              <Button variant="secondary" size="sm" onClick={() => addElement('text')}>
                <TextT className="mr-2" size={16} />
                Text
              </Button>
              <Button variant="secondary" size="sm" onClick={() => addElement('qrcode')}>
                <QrCode className="mr-2" size={16} />
                QR Code
              </Button>
              <Button variant="secondary" size="sm" onClick={() => addElement('divider')}>
                <Minus className="mr-2" size={16} />
                Divider
              </Button>
              <Button variant="default" size="sm" onClick={addGroup} className="bg-accent text-accent-foreground">
                <Package className="mr-2" size={16} />
                Group
              </Button>
            </div>
          </div>

          <div className="p-4 flex-1 border-b border-border">
            <h2 className="text-xs uppercase font-bold text-muted-foreground mb-3 tracking-wider">Layers</h2>

            <div className="space-y-1 mb-4">
              {currentElements.map((el) => (
                <div
                  key={el.id}
                  className={`flex items-center justify-between p-2 rounded cursor-pointer border transition ${
                    selectedElementId === el.id
                      ? 'bg-secondary border-primary'
                      : 'border-transparent hover:bg-secondary/50'
                  }`}
                  onClick={() => {
                    setSelectedElementId(el.id)
                    setSelectedGroupId(null)
                  }}
                >
                  <span className="text-sm truncate flex items-center gap-2">
                    {el.type === 'text' && <TextT size={16} />}
                    {el.type === 'qrcode' && <QrCode size={16} />}
                    {el.type === 'divider' && <Minus size={16} />}
                    <span className="text-foreground/80">{el.value || el.type}</span>
                  </span>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 w-6 p-0 text-destructive hover:text-destructive"
                    onClick={(e) => {
                      e.stopPropagation()
                      setSelectedElementId(el.id)
                      deleteSelected()
                    }}
                  >
                    <Trash size={14} />
                  </Button>
                </div>
              ))}
              {currentElements.length === 0 && (
                <p className="text-xs text-muted-foreground italic">No elements.</p>
              )}
            </div>

            {mode === 'normal' && (
              <>
                <h3 className="text-xs font-bold text-muted-foreground mb-2">GROUPS</h3>
                <div className="space-y-1">
                  {layoutState.groups.map((group) => (
                    <div
                      key={group.id}
                      className={`flex items-center justify-between p-2 rounded cursor-pointer border transition ${
                        selectedGroupId === group.id
                          ? 'bg-secondary border-accent'
                          : 'border-transparent hover:bg-secondary/50'
                      }`}
                      onClick={() => {
                        setSelectedGroupId(group.id)
                        setSelectedElementId(null)
                      }}
                    >
                      <span className="text-sm flex items-center gap-2">
                        <Package size={16} className="text-accent" />
                        Group
                        <span className="text-xs text-muted-foreground">
                          ({layoutState.elements.filter((e) => e.groupId === group.id).length} items)
                        </span>
                      </span>
                      <div className="flex gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 w-6 p-0 text-accent hover:text-accent"
                          onClick={(e) => {
                            e.stopPropagation()
                            enterGroupEditMode(group.id)
                          }}
                        >
                          <PencilSimple size={14} />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 w-6 p-0 text-destructive hover:text-destructive"
                          onClick={(e) => {
                            e.stopPropagation()
                            setSelectedGroupId(group.id)
                            deleteSelected()
                          }}
                        >
                          <Trash size={14} />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        </aside>

        <main className="flex-1 bg-muted flex flex-col items-center justify-center p-8 overflow-y-auto">
          {mode === 'normal' && (
            <TicketCanvas
              ref={mainCanvasRef}
              config={layoutState.canvas}
              elements={layoutState.elements}
              groups={layoutState.groups}
              isGroupMode={false}
              selectedElementId={selectedElementId}
              selectedGroupId={selectedGroupId}
              onElementModified={(id, y) => updateElement(id, { y })}
              onGroupModified={(id, y) => updateGroup(id, { y })}
              onElementSelect={setSelectedElementId}
              onGroupSelect={setSelectedGroupId}
              onGroupDoubleClick={enterGroupEditMode}
            />
          )}

          {mode === 'editing-group' && editingGroup && (
            <div className="flex flex-col items-center">
              <p className="text-muted-foreground mb-4 font-medium">
                Group Editing Mode (Size: {editingGroup.width}x{editingGroup.height}mm)
              </p>
              <TicketCanvas
                ref={groupCanvasRef}
                config={{ ...editingGroup, orientation: 'portrait', padding: layoutState.canvas.padding }}
                elements={layoutState.elements.filter((e) => e.groupId === editingGroupId)}
                groups={[]}
                isGroupMode={true}
                selectedElementId={selectedElementId}
                selectedGroupId={null}
                onElementModified={(id, y) => updateElement(id, { y })}
                onElementSelect={setSelectedElementId}
              />
            </div>
          )}
        </main>

        <aside className="w-80 bg-card border-l border-border flex flex-col overflow-y-auto">
          <div className="p-4 border-b border-border flex-1">
            <h2 className="text-xs uppercase font-bold text-muted-foreground mb-3 tracking-wider flex justify-between">
              <span>Properties</span>
              {!selectedElement && !selectedGroup && (
                <span className="text-muted-foreground/50 font-normal">None</span>
              )}
            </h2>

            {selectedElement && (
              <div className="space-y-3">
                <div className="bg-secondary text-xs px-2 py-1 rounded text-center text-primary font-mono">
                  {selectedElement.id}
                </div>

                {selectedElement.type === 'text' && (
                  <>
                    <div>
                      <Label className="text-xs">Value / Tag</Label>
                      <Input
                        value={selectedElement.value || ''}
                        onChange={(e) => updateElement(selectedElement.id, { value: e.target.value })}
                        className="h-8 font-mono text-xs"
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <Label className="text-xs">Font Size</Label>
                        <Input
                          type="number"
                          value={selectedElement.size || 14}
                          onChange={(e) => updateElement(selectedElement.id, { size: parseFloat(e.target.value) })}
                          className="h-8"
                        />
                      </div>
                      <div className="flex items-end">
                        <label className="flex items-center gap-2 text-xs cursor-pointer">
                          <Checkbox
                            checked={selectedElement.bold}
                            onCheckedChange={(checked) =>
                              updateElement(selectedElement.id, { bold: checked as boolean })
                            }
                          />
                          Bold
                        </label>
                      </div>
                    </div>
                    <Separator />
                  </>
                )}

                <div>
                  <Label className="text-xs">Position Y (mm)</Label>
                  <Input
                    type="number"
                    step="0.5"
                    value={selectedElement.y}
                    onChange={(e) => updateElement(selectedElement.id, { y: parseFloat(e.target.value) })}
                    className="h-8"
                  />
                </div>

                <div>
                  <Label className="text-xs">Horizontal Alignment</Label>
                  <Select
                    value={selectedElement.horizontal_position}
                    onValueChange={(value) =>
                      updateElement(selectedElement.id, {
                        horizontal_position: value as 'left' | 'center' | 'right',
                      })
                    }
                  >
                    <SelectTrigger className="h-8">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="left">Left</SelectItem>
                      <SelectItem value="center">Center</SelectItem>
                      <SelectItem value="right">Right</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <Label className="text-xs">Margin Left (mm)</Label>
                    <Input
                      type="number"
                      step="0.5"
                      value={selectedElement.margin_left}
                      onChange={(e) =>
                        updateElement(selectedElement.id, { margin_left: parseFloat(e.target.value) })
                      }
                      className="h-8"
                    />
                  </div>
                  <div>
                    <Label className="text-xs">Margin Right (mm)</Label>
                    <Input
                      type="number"
                      step="0.5"
                      value={selectedElement.margin_right}
                      onChange={(e) =>
                        updateElement(selectedElement.id, { margin_right: parseFloat(e.target.value) })
                      }
                      className="h-8"
                    />
                  </div>
                </div>
              </div>
            )}

            {selectedGroup && (
              <div className="space-y-3">
                <div className="bg-secondary text-xs px-2 py-1 rounded text-center text-accent font-mono">
                  {selectedGroup.id}
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <Label className="text-xs">Width (mm)</Label>
                    <Input
                      type="number"
                      step="0.5"
                      value={selectedGroup.width}
                      onChange={(e) => updateGroup(selectedGroup.id, { width: parseFloat(e.target.value) })}
                      className="h-8"
                    />
                  </div>
                  <div>
                    <Label className="text-xs">Height (mm)</Label>
                    <Input
                      type="number"
                      step="0.5"
                      value={selectedGroup.height}
                      onChange={(e) => updateGroup(selectedGroup.id, { height: parseFloat(e.target.value) })}
                      className="h-8"
                    />
                  </div>
                </div>

                <div>
                  <Label className="text-xs">Position Y (mm)</Label>
                  <Input
                    type="number"
                    step="0.5"
                    value={selectedGroup.y}
                    onChange={(e) => updateGroup(selectedGroup.id, { y: parseFloat(e.target.value) })}
                    className="h-8"
                  />
                </div>

                <div>
                  <Label className="text-xs">Horizontal Alignment</Label>
                  <Select
                    value={selectedGroup.horizontal_position}
                    onValueChange={(value) =>
                      updateGroup(selectedGroup.id, {
                        horizontal_position: value as 'left' | 'center' | 'right',
                      })
                    }
                  >
                    <SelectTrigger className="h-8">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="left">Left</SelectItem>
                      <SelectItem value="center">Center</SelectItem>
                      <SelectItem value="right">Right</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <Label className="text-xs">Margin Left (mm)</Label>
                    <Input
                      type="number"
                      step="0.5"
                      value={selectedGroup.margin_left}
                      onChange={(e) => updateGroup(selectedGroup.id, { margin_left: parseFloat(e.target.value) })}
                      className="h-8"
                    />
                  </div>
                  <div>
                    <Label className="text-xs">Margin Right (mm)</Label>
                    <Input
                      type="number"
                      step="0.5"
                      value={selectedGroup.margin_right}
                      onChange={(e) => updateGroup(selectedGroup.id, { margin_right: parseFloat(e.target.value) })}
                      className="h-8"
                    />
                  </div>
                </div>

                <Button className="w-full" variant="default" size="sm" onClick={() => enterGroupEditMode(selectedGroup.id)}>
                  <PencilSimple className="mr-2" size={16} />
                  Edit Group Content
                </Button>
              </div>
            )}

            <div className="mt-6 pt-4 border-t border-border">
              <h3 className="text-xs font-bold text-muted-foreground mb-2">AVAILABLE TAGS</h3>
              <div className="flex flex-wrap gap-1">
                {TEMPLATE_TAGS.map((tag) => (
                  <Badge
                    key={tag}
                    variant="secondary"
                    className="cursor-pointer hover:bg-primary hover:text-primary-foreground transition text-[10px]"
                    onClick={() => copyTag(tag)}
                  >
                    {tag}
                  </Badge>
                ))}
              </div>
            </div>
          </div>

          <div className="p-4 bg-muted border-t border-border">
            <h2 className="text-xs uppercase font-bold text-muted-foreground mb-2 flex justify-between items-center">
              <span>Real Preview</span>
              <Button
                variant="default"
                size="sm"
                className="h-6 text-[10px]"
                onClick={generatePreview}
                disabled={previewLoading || mode === 'editing-group'}
              >
                {previewLoading ? 'Generating...' : 'Update'}
              </Button>
            </h2>
            <div className="min-h-[150px] bg-white rounded border border-border flex items-center justify-center p-2">
              {mode === 'editing-group' ? (
                <p className="text-xs text-muted-foreground text-center px-4">
                  Exit group editing mode to generate preview.
                </p>
              ) : previewUrl ? (
                <img src={previewUrl} className="max-w-full max-h-[250px] object-contain" alt="Preview" />
              ) : (
                <p className="text-xs text-muted-foreground text-center">
                  Click Update to generate preview with mock data.
                </p>
              )}
            </div>
          </div>
        </aside>
      </div>
    </div>
  )
}
