import { useEffect, useRef, useImperativeHandle, forwardRef } from 'react'
import * as fabric from 'fabric'
import type { TicketElement, CanvasConfig } from '@/types/layout'
import { mmToPx, calculateHorizontalPosition } from '@/lib/canvas-utils'

interface TicketCanvasProps {
  config: CanvasConfig
  elements: TicketElement[]
  selectedElementIds: string[]
  onElementModified: (id: string, y: number) => void
  onElementSelect: (id: string, shiftKey: boolean) => void
}

export interface TicketCanvasRef {
  getDataURL: () => string
  clearCanvas: () => void
}

export const TicketCanvas = forwardRef<TicketCanvasRef, TicketCanvasProps>(
  (
    {
      config,
      elements,
      selectedElementIds,
      onElementModified,
      onElementSelect,
    },
    ref
  ) => {
    const canvasRef = useRef<HTMLCanvasElement>(null)
    const fabricCanvasRef = useRef<fabric.Canvas | null>(null)

    useImperativeHandle(ref, () => ({
      getDataURL: () => {
        if (!fabricCanvasRef.current) return ''
        fabricCanvasRef.current.discardActiveObject()
        fabricCanvasRef.current.renderAll()
        return fabricCanvasRef.current.toDataURL({ format: 'png', multiplier: 2 })
      },
      clearCanvas: () => {
        if (fabricCanvasRef.current) {
          fabricCanvasRef.current.clear()
        }
      },
    }))

    useEffect(() => {
      if (!canvasRef.current) return

      const canvas = new fabric.Canvas(canvasRef.current, {
        selection: true,
        preserveObjectStacking: true,
        backgroundColor: '#ffffff',
      })

      fabricCanvasRef.current = canvas

      canvas.on('object:modified', (e) => {
        const obj = e.target
        if (!obj) return

        const newYMm = Math.max(0, obj.top! / 3.78)

        if ((obj as any).elementId) {
          const elementId = (obj as any).elementId
          if (elementId) {
            onElementModified(elementId, parseFloat(newYMm.toFixed(2)))
          }
        }
      })

      canvas.on('selection:created', (e) => {
        const obj = e.selected?.[0]
        if (!obj) return

        if ((obj as any).elementId) {
          onElementSelect((obj as any).elementId, false)
        }
      })

      canvas.on('selection:updated', (e) => {
        const obj = e.selected?.[0]
        if (!obj) return

        if ((obj as any).elementId) {
          onElementSelect((obj as any).elementId, false)
        }
      })

      canvas.on('selection:cleared', () => {
        // Não limpar seleção automaticamente - deixar o usuário controlar via UI
      })

      return () => {
        canvas.dispose()
        fabricCanvasRef.current = null
      }
    }, [onElementModified, onElementSelect])

    useEffect(() => {
      if (!fabricCanvasRef.current) return

      const canvas = fabricCanvasRef.current
      canvas.clear()

      const wPx = mmToPx(config.width)
      const hPx = mmToPx(config.height)

      canvas.setDimensions({ width: wPx, height: hPx })
      canvas.set({ backgroundColor: '#ffffff' })

      drawGuides(canvas, wPx, hPx, config.padding)

      // Renderizar elementos com links
      elements.forEach((el) => drawElement(canvas, el, config.width, elements))

      canvas.renderAll()

      restoreSelection(canvas)
    }, [config, elements, selectedElementIds])

    const drawGuides = (
      canvas: fabric.Canvas,
      w: number,
      h: number,
      padding: number
    ) => {
      const pad = mmToPx(padding)
      const guideColor = 'rgba(59,130,246,0.2)'
      const props = {
        stroke: guideColor,
        strokeWidth: 1,
        selectable: false,
        evented: false,
      }

      canvas.add(
        new fabric.Line([pad, 0, pad, h], props),
        new fabric.Line([w - pad, 0, w - pad, h], props),
        new fabric.Line([w / 2, 0, w / 2, h], {
          ...props,
          strokeDashArray: [4, 4],
        })
      )
    }

    const drawElement = (
      canvas: fabric.Canvas,
      el: TicketElement,
      containerWidthMm: number,
      allElements: TicketElement[]
    ) => {
      let obj: fabric.Object | null = null
      let top = mmToPx(el.y || 0)
      
      // Se o elemento tem link, calcular posição relativa
      if (el.link) {
        const targetEl = allElements.find(e => e.id === el.link!.targetId)
        if (targetEl) {
          if (el.link.position === 'right') {
            // Posicionar à direita do elemento alvo (lógica será aplicada no positionData)
          } else if (el.link.position === 'below') {
            top = mmToPx((targetEl.y || 0) + 20) // Placeholder - ajustar baseado no tamanho do alvo
          }
        }
      }

      const positionData = calculateHorizontalPosition(el, containerWidthMm)

      if (el.type === 'text') {
        const maxWidth = el.wrapText ? mmToPx(containerWidthMm - (el.margin_left + el.margin_right)) : undefined
        
        obj = new fabric.Text(el.value || 'Texto', {
          fontSize: el.size || 14,
          fontFamily: el.font || 'Arial',
          fontWeight: el.bold ? 'bold' : 'normal',
          fontStyle: el.italic ? 'italic' : 'normal',
          fill: '#000000',
          ...(maxWidth && {
            splitByGrapheme: true,
            textAlign: el.horizontal_position,
          }),
        })
        
        // Aplicar quebra de linha manual se necessário
        if (maxWidth && obj.width! > maxWidth) {
          (obj as fabric.Text).set({ width: maxWidth })
        }
      } else if (el.type === 'qrcode' || el.type === 'logo') {
        const size = mmToPx(el.size_mm || 30)
        const rect = new fabric.Rect({
          width: size,
          height: size,
          fill: '#f1f5f9',
          stroke: '#94a3b8',
          strokeWidth: 1,
        })
        const text = new fabric.Text(
          el.type === 'qrcode' ? 'QR Code' : 'LOGO',
          {
            fontSize: 12,
            fill: '#475569',
            originX: 'center',
            originY: 'center',
          }
        )
        obj = new fabric.Group([rect, text], {
          left: size / 2,
          top: size / 2,
        })
      } else if (el.type === 'divider') {
        const length = mmToPx(el.length_mm || 40)
        const thickness = el.thickness || 2
        obj = new fabric.Rect({
          width: length,
          height: thickness,
          fill: '#000',
        })
      }

      if (obj) {
        obj.set({
          left: positionData.left,
          top: top,
          originX: positionData.originX,
          lockMovementX: true,
          lockScalingX: true,
          lockScalingY: true,
          lockRotation: true,
          hasControls: false,
          borderColor: '#3b82f6',
        } as any)

        ;(obj as any).elementId = el.id

        // Marcar se o elemento está vinculado
        if (el.link) {
          ;(obj as any).isLinked = true
          // Adicionar visual para indicar vínculo (borda diferente)
          obj.set({ borderColor: '#10b981', strokeWidth: 2 } as any)
        }

        canvas.add(obj)
      }
    }

    const restoreSelection = (canvas: fabric.Canvas) => {
      if (selectedElementIds.length === 0) return

      const objsToSelect = canvas.getObjects().filter((o: any) => 
        selectedElementIds.includes(o.elementId)
      )

      if (objsToSelect.length > 0) {
        if (objsToSelect.length === 1) {
          canvas.setActiveObject(objsToSelect[0])
        } else {
          const selection = new fabric.ActiveSelection(objsToSelect, { canvas })
          canvas.setActiveObject(selection)
        }
        canvas.requestRenderAll()
      }
    }

    return (
      <div className="canvas-container">
        <canvas ref={canvasRef} />
      </div>
    )
  }
)

TicketCanvas.displayName = 'TicketCanvas'
