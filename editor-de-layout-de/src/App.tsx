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
      width: 80,
      height: 120,
      orientation: 'portrait',
      padding: 5,
    },
    elements: [],
  })

  const [selectedElementIds, setSelectedElementIds] = useState<string[]>([])
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)

  const mainCanvasRef = useRef<TicketCanvasRef>(null)

  const selectedElement = layoutState.elements.find((e) => selectedElementIds.includes(e.id)) || null
  const selectedElements = layoutState.elements.filter((e) => selectedElementIds.includes(e.id))

  if (!layoutState) {
    return <div className="h-screen flex items-center justify-center">Carregando...</div>
  }

  const updateCanvas = useCallback((updates: Partial<CanvasConfig>) => {
    setLayoutState((prev) => {
      const current = prev || { canvas: { width: 80, height: 120, orientation: 'portrait' as const, padding: 5 }, elements: [] }
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
        wrapText: type === 'text',
        ...(type === 'text' && { value: '{NOME}', size: 14, font: 'Arial', bold: false, italic: false }),
        ...(type === 'qrcode' && { size_mm: 30 }),
        ...(type === 'divider' && { length_mm: 40, thickness: 2 }),
        ...initialProps,
      }

      setLayoutState((prev) => {
        const current = prev || { canvas: { width: 80, height: 120, orientation: 'portrait' as const, padding: 5 }, elements: [] }
        return {
          ...current,
          elements: [...current.elements, newEl],
        } as LayoutState
      })
      setSelectedElementIds([newEl.id])
    },
    [setLayoutState]
  )

  const deleteSelected = useCallback(() => {
    if (selectedElementIds.length > 0) {
      setLayoutState((prev) => {
        const current = prev || { canvas: { width: 80, height: 120, orientation: 'portrait' as const, padding: 5 }, elements: [] }
        // Remover também os links que referenciam elementos deletados
        const remainingElements = current.elements
          .filter((e) => !selectedElementIds.includes(e.id))
          .map((e) => {
            if (e.link && selectedElementIds.includes(e.link.targetId)) {
              const { link, ...rest } = e
              return rest as TicketElement
            }
            return e
          })
        return {
          ...current,
          elements: remainingElements,
        } as LayoutState
      })
      setSelectedElementIds([])
    }
  }, [selectedElementIds, setLayoutState])

  const updateElement = useCallback(
    (id: string, updates: Partial<TicketElement>) => {
      setLayoutState((prev) => {
        const current = prev || { canvas: { width: 80, height: 120, orientation: 'portrait' as const, padding: 5 }, elements: [] }
        return {
          ...current,
          elements: current.elements.map((el) => (el.id === id ? { ...el, ...updates } : el)),
        } as LayoutState
      })
    },
    [setLayoutState]
  )

  const handleElementClick = useCallback((elementId: string, shiftKey: boolean) => {
    if (shiftKey) {
      setSelectedElementIds((prev) => {
        if (prev.includes(elementId)) {
          return prev.filter((id) => id !== elementId)
        }
        return [...prev, elementId]
      })
    } else {
      setSelectedElementIds([elementId])
    }
  }, [])

  const createLink = useCallback(() => {
    if (selectedElementIds.length !== 2) {
      toast.error('Selecione exatamente 2 elementos para criar um vínculo')
      return
    }

    const [firstId, secondId] = selectedElementIds
    updateElement(secondId, {
      link: {
        targetId: firstId,
        gap: 5,
        gapType: 'fixed',
        position: 'right',
      },
    })
    toast.success('Vínculo criado! O segundo elemento agora está posicionado em relação ao primeiro')
  }, [selectedElementIds, updateElement])

  const removeLink = useCallback(() => {
    if (selectedElementIds.length !== 1) {
      toast.error('Selecione 1 elemento para remover seu vínculo')
      return
    }

    const element = layoutState.elements.find((e) => e.id === selectedElementIds[0])
    if (!element?.link) {
      toast.error('Este elemento não possui vínculo')
      return
    }

    const { link, ...rest } = element
    updateElement(element.id, rest)
    toast.success('Vínculo removido')
  }, [selectedElementIds, layoutState.elements, updateElement])

  const generatePreview = useCallback(async () => {
    setPreviewLoading(true)
    await new Promise((resolve) => setTimeout(resolve, 500))

    const url = mainCanvasRef.current?.getDataURL()
    setPreviewUrl(url || null)
    setPreviewLoading(false)
  }, [])

  const saveLayout = useCallback(() => {
    toast.success('Layout salvo com sucesso!')
  }, [])

  const copyTag = useCallback((tag: string) => {
    navigator.clipboard.writeText(tag).then(
      () => toast.success(`Variável ${tag} copiada!`),
      () => toast.error('Falha ao copiar variável')
    )
  }, [])

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes((e.target as HTMLElement).tagName)) return

      if (e.key === 'Delete' || e.key === 'Backspace') {
        e.preventDefault()
        deleteSelected()
      }
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault()
        saveLayout()
      }
      if ((e.ctrlKey || e.metaKey) && e.key === 'l') {
        e.preventDefault()
        createLink()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [deleteSelected, saveLayout, createLink])

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-background text-foreground">
      <Toaster />

      <header className="bg-card border-b border-border p-4 flex justify-between items-center shrink-0">
        <div>
          <h1 className="text-xl font-bold text-primary">Editor de Layout de Ingressos</h1>
          <p className="text-xs text-muted-foreground">
            Arraste elementos verticalmente. Use Shift+clique para selecionar múltiplos elementos.
          </p>
        </div>
        <div className="flex gap-2">
          {selectedElementIds.length === 2 && (
            <Button variant="secondary" size="sm" onClick={createLink}>
              <Plus className="mr-2" size={16} />
              Vincular (Ctrl+L)
            </Button>
          )}
          {selectedElementIds.length === 1 && selectedElement?.link && (
            <Button variant="destructive" size="sm" onClick={removeLink}>
              <Trash className="mr-2" size={16} />
              Desvincular
            </Button>
          )}
          <Button variant="outline" size="sm" onClick={saveLayout}>
            <FloppyDisk className="mr-2" size={16} />
            Salvar Layout
          </Button>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        <aside className="w-80 bg-card border-r border-border flex flex-col overflow-y-auto">
          <div className="p-4 border-b border-border">
            <h2 className="text-xs uppercase font-bold text-muted-foreground mb-3 tracking-wider">
              Configurações do Canvas
            </h2>
            <div className="grid grid-cols-2 gap-2 mb-2">
              <div>
                <Label className="text-xs">Largura (mm)</Label>
                <Input
                  type="number"
                  value={layoutState.canvas.width}
                  onChange={(e) => updateCanvas({ width: parseFloat(e.target.value) })}
                  className="h-8"
                />
              </div>
              <div>
                <Label className="text-xs">Altura (mm)</Label>
                <Input
                  type="number"
                  value={layoutState.canvas.height}
                  onChange={(e) => updateCanvas({ height: parseFloat(e.target.value) })}
                  className="h-8"
                />
              </div>
            </div>
            <div>
              <Label className="text-xs">Margem Interna (mm)</Label>
              <Input
                type="number"
                value={layoutState.canvas.padding}
                onChange={(e) => updateCanvas({ padding: parseFloat(e.target.value) })}
                className="h-8"
              />
            </div>
            <div className="mt-3">
              <Label className="text-xs">Orientação</Label>
              <div className="flex gap-2 mt-1">
                <Button
                  variant={layoutState.canvas.orientation === 'portrait' ? 'default' : 'outline'}
                  size="sm"
                  className="flex-1 h-8"
                  onClick={() => {
                    const newOrientation = 'portrait';
                    if (layoutState.canvas.orientation !== newOrientation) {
                      // Troca largura e altura
                      updateCanvas({
                        orientation: newOrientation,
                        width: Math.min(layoutState.canvas.width, layoutState.canvas.height),
                        height: Math.max(layoutState.canvas.width, layoutState.canvas.height),
                      });
                    }
                  }}
                >
                  Retrato
                </Button>
                <Button
                  variant={layoutState.canvas.orientation === 'landscape' ? 'default' : 'outline'}
                  size="sm"
                  className="flex-1 h-8"
                  onClick={() => {
                    const newOrientation = 'landscape';
                    if (layoutState.canvas.orientation !== newOrientation) {
                      // Troca largura e altura
                      updateCanvas({
                        orientation: newOrientation,
                        width: Math.max(layoutState.canvas.width, layoutState.canvas.height),
                        height: Math.min(layoutState.canvas.width, layoutState.canvas.height),
                      });
                    }
                  }}
                >
                  Paisagem
                </Button>
              </div>
            </div>
            <div className="mt-3">
              <Label className="text-xs">Tamanhos Padrão</Label>
              <Select
                value=""
                onValueChange={(value) => {
                  const [w, h] = value.split('x').map(Number);
                  updateCanvas({ width: w, height: h, orientation: w < h ? 'portrait' : 'landscape' });
                }}
              >
                <SelectTrigger className="h-8">
                  <SelectValue placeholder="Selecione um tamanho..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="80x120">80mm x 120mm (Padrão)</SelectItem>
                  <SelectItem value="62x100">62mm x 100mm (Brother QL)</SelectItem>
                  <SelectItem value="62x29">62mm x 29mm (Pequena)</SelectItem>
                  <SelectItem value="103x164">103mm x 164mm (Grande)</SelectItem>
                  <SelectItem value="50x25">50mm x 25mm (Mini)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="p-4 border-b border-border">
            <h2 className="text-xs uppercase font-bold text-muted-foreground mb-3 tracking-wider">Adicionar Elementos</h2>
            <div className="grid grid-cols-3 gap-2">
              <Button variant="secondary" size="sm" onClick={() => addElement('text')}>
                <TextT className="mr-2" size={16} />
                Texto
              </Button>
              <Button variant="secondary" size="sm" onClick={() => addElement('qrcode')}>
                <QrCode className="mr-2" size={16} />
                QR Code
              </Button>
              <Button variant="secondary" size="sm" onClick={() => addElement('divider')}>
                <Minus className="mr-2" size={16} />
                Divisor
              </Button>
            </div>
          </div>

          <div className="p-4 flex-1 border-b border-border">
            <h2 className="text-xs uppercase font-bold text-muted-foreground mb-3 tracking-wider">
              Camadas ({selectedElementIds.length > 0 && `${selectedElementIds.length} selecionado${selectedElementIds.length > 1 ? 's' : ''}`})
            </h2>

            <div className="space-y-1 mb-4">
              {layoutState.elements.map((el) => {
                const isSelected = selectedElementIds.includes(el.id)
                const isLinked = el.link !== undefined
                const linkedTarget = isLinked ? layoutState.elements.find(e => e.id === el.link?.targetId) : null
                
                return (
                  <div
                    key={el.id}
                    className={`flex items-center justify-between p-2 rounded cursor-pointer border transition ${
                      isSelected
                        ? 'bg-secondary border-primary'
                        : 'border-transparent hover:bg-secondary/50'
                    }`}
                    onClick={(e) => handleElementClick(el.id, e.shiftKey)}
                  >
                    <span className="text-sm truncate flex items-center gap-2">
                      {el.type === 'text' && <TextT size={16} />}
                      {el.type === 'qrcode' && <QrCode size={16} />}
                      {el.type === 'divider' && <Minus size={16} />}
                      <span className="text-foreground/80">{el.value || el.type}</span>
                      {isLinked && (
                        <span className="text-[10px] text-accent font-bold">
                          → {linkedTarget?.type || 'link'}
                        </span>
                      )}
                    </span>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 w-6 p-0 text-destructive hover:text-destructive"
                      onClick={(e) => {
                        e.stopPropagation()
                        setSelectedElementIds([el.id])
                        deleteSelected()
                      }}
                    >
                      <Trash size={14} />
                    </Button>
                  </div>
                )
              })}
              {layoutState.elements.length === 0 && (
                <p className="text-xs text-muted-foreground italic">Sem elementos.</p>
              )}
            </div>
          </div>
        </aside>

        <main className="flex-1 bg-muted flex flex-col items-center justify-center p-8 overflow-y-auto">
          <TicketCanvas
            ref={mainCanvasRef}
            config={layoutState.canvas}
            elements={layoutState.elements}
            selectedElementIds={selectedElementIds}
            onElementModified={(id, y) => updateElement(id, { y })}
            onElementSelect={handleElementClick}
          />
              <p className="text-muted-foreground mb-4 font-medium">
                Modo de Edição de Grupo (Tamanho: {editingGroup.width}x{editingGroup.height}mm)
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
              <span>Propriedades</span>
              {!selectedElement && !selectedGroup && (
                <span className="text-muted-foreground/50 font-normal">Nenhum</span>
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
                      <Label className="text-xs">Valor / Variável</Label>
                      <Input
                        value={selectedElement.value || ''}
                        onChange={(e) => updateElement(selectedElement.id, { value: e.target.value })}
                        className="h-8 font-mono text-xs"
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <Label className="text-xs">Tamanho da Fonte</Label>
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
                          Negrito
                        </label>
                      </div>
                    </div>
                    <Separator />
                  </>
                )}

                <div>
                  <Label className="text-xs">Posição Y (mm)</Label>
                  <Input
                    type="number"
                    step="0.5"
                    value={selectedElement.y}
                    onChange={(e) => updateElement(selectedElement.id, { y: parseFloat(e.target.value) })}
                    className="h-8"
                  />
                </div>

                <div>
                  <Label className="text-xs">Alinhamento Horizontal</Label>
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
                      <SelectItem value="left">Esquerda</SelectItem>
                      <SelectItem value="center">Centro</SelectItem>
                      <SelectItem value="right">Direita</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <Label className="text-xs">Margem Esquerda (mm)</Label>
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
                    <Label className="text-xs">Margem Direita (mm)</Label>
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

                {selectedElement.type === 'text' && (
                  <div className="flex items-center gap-2 pt-2">
                    <Checkbox
                      id="wrapText"
                      checked={selectedElement.wrapText || false}
                      onCheckedChange={(checked) =>
                        updateElement(selectedElement.id, { wrapText: checked as boolean })
                      }
                    />
                    <Label htmlFor="wrapText" className="text-xs cursor-pointer">
                      Quebra de linha automática
                    </Label>
                  </div>
                )}

                {selectedElement.link && (
                  <>
                    <Separator />
                    <div className="bg-accent/10 p-2 rounded">
                      <h3 className="text-xs font-bold text-accent mb-2">VÍNCULO</h3>
                      <div className="space-y-2">
                        <div>
                          <Label className="text-xs">Posição Relativa</Label>
                          <Select
                            value={selectedElement.link.position}
                            onValueChange={(value) =>
                              updateElement(selectedElement.id, {
                                link: { ...selectedElement.link!, position: value as 'right' | 'below' },
                              })
                            }
                          >
                            <SelectTrigger className="h-8">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="right">À direita</SelectItem>
                              <SelectItem value="below">Abaixo</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                        <div>
                          <Label className="text-xs">Espaçamento (mm)</Label>
                          <Input
                            type="number"
                            step="0.5"
                            value={selectedElement.link.gap}
                            onChange={(e) =>
                              updateElement(selectedElement.id, {
                                link: { ...selectedElement.link!, gap: parseFloat(e.target.value) },
                              })
                            }
                            className="h-8"
                          />
                        </div>
                        <div>
                          <Label className="text-xs">Tipo</Label>
                          <Select
                            value={selectedElement.link.gapType}
                            onValueChange={(value) =>
                              updateElement(selectedElement.id, {
                                link: { ...selectedElement.link!, gapType: value as 'fixed' | 'between' },
                              })
                            }
                          >
                            <SelectTrigger className="h-8">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="fixed">Fixo</SelectItem>
                              <SelectItem value="between">Distribuir</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      </div>
                    </div>
                  </>
                )}
              </div>
            )}

            <div className="mt-6 pt-4 border-t border-border">
              <h3 className="text-xs font-bold text-muted-foreground mb-2">VARIÁVEIS DISPONÍVEIS</h3>
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
              <span>Pré-visualização Real</span>
              <Button
                variant="default"
                size="sm"
                className="h-6 text-[10px]"
                onClick={generatePreview}
                disabled={previewLoading}
              >
                {previewLoading ? 'Gerando...' : 'Atualizar'}
              </Button>
            </h2>
            <div className="min-h-[150px] bg-white rounded border border-border flex items-center justify-center p-2">
              {previewUrl ? (
                <img src={previewUrl} className="max-w-full max-h-[250px] object-contain" alt="Pré-visualização" />
              ) : (
                <p className="text-xs text-muted-foreground text-center">
                  Clique em Atualizar para gerar prévia com dados de exemplo.
                </p>
              )}
            </div>
          </div>
        </aside>
      </div>
    </div>
  )
}
