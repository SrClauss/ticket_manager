import { useEffect, useRef, useImperativeHandle, forwardRef } from 'react'
import * as fabric from 'fabric'
import type { TicketElement, TicketGroup, CanvasConfig } from '@/types/layout'
import { mmToPx, calculateHorizontalPosition } from '@/lib/canvas-utils'

interface TicketCanvasProps {
  config: CanvasConfig
  elements: TicketElement[]
  groups?: TicketGroup[]
  isGroupMode?: boolean
  selectedElementId: string | null
  selectedGroupId: string | null
  onElementModified: (id: string, y: number) => void
  onGroupModified?: (id: string, y: number) => void
  onElementSelect: (id: string | null) => void
  onGroupSelect?: (id: string | null) => void
  onGroupDoubleClick?: (id: string) => void
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
      groups = [],
      isGroupMode = false,
      selectedElementId,
      selectedGroupId,
      onElementModified,
      onGroupModified,
      onElementSelect,
      onGroupSelect,
      onGroupDoubleClick,
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

        if ((obj as any).isGroupFrame) {
          const groupId = (obj as any).groupId
          if (groupId && onGroupModified) {
            onGroupModified(groupId, parseFloat(newYMm.toFixed(2)))
          }
        } else if ((obj as any).elementId) {
          const elementId = (obj as any).elementId
          if (elementId) {
            onElementModified(elementId, parseFloat(newYMm.toFixed(2)))
          }
        }
      })

      canvas.on('selection:created', (e) => {
        const obj = e.selected?.[0]
        if (!obj) return

        if ((obj as any).isGroupFrame) {
          if (onGroupSelect) onGroupSelect((obj as any).groupId)
        } else if ((obj as any).elementId) {
          onElementSelect((obj as any).elementId)
        }
      })

      canvas.on('selection:updated', (e) => {
        const obj = e.selected?.[0]
        if (!obj) return

        if ((obj as any).isGroupFrame) {
          if (onGroupSelect) onGroupSelect((obj as any).groupId)
        } else if ((obj as any).elementId) {
          onElementSelect((obj as any).elementId)
        }
      })

      canvas.on('selection:cleared', () => {
        onElementSelect(null)
        if (onGroupSelect) onGroupSelect(null)
      })

      canvas.on('mouse:dblclick', (e) => {
        const obj = e.target
        if (obj && (obj as any).isGroupFrame && onGroupDoubleClick) {
          onGroupDoubleClick((obj as any).groupId)
        }
      })

      return () => {
        canvas.dispose()
        fabricCanvasRef.current = null
      }
    }, [])

    useEffect(() => {
      if (!fabricCanvasRef.current) return

      const canvas = fabricCanvasRef.current
      canvas.clear()

      const wPx = mmToPx(config.width)
      const hPx = mmToPx(config.height)

      canvas.setDimensions({ width: wPx, height: hPx })
      canvas.set({ backgroundColor: '#ffffff' })

      drawGuides(canvas, wPx, hPx, config.padding)

      if (!isGroupMode) {
        groups.forEach((group) => drawGroupFrame(canvas, group, config.width))
      }

      elements.forEach((el) => drawElement(canvas, el, config.width))

      canvas.renderAll()

      restoreSelection(canvas)
    }, [config, elements, groups, isGroupMode])

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
      containerWidthMm: number
    ) => {
      let obj: fabric.Object | null = null
      const top = mmToPx(el.y || 0)

      const positionData = calculateHorizontalPosition(el, containerWidthMm)

      if (el.type === 'text') {
        obj = new fabric.Text(el.value || 'Texto', {
          fontSize: el.size || 14,
          fontFamily: el.font || 'Arial',
          fontWeight: el.bold ? 'bold' : 'normal',
          fontStyle: el.italic ? 'italic' : 'normal',
          fill: '#000000',
        })
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
        ;(obj as any).groupId = el.groupId || null

        canvas.add(obj)
      }
    }

    const drawGroupFrame = (
      canvas: fabric.Canvas,
      group: TicketGroup,
      canvasWidth: number
    ) => {
      const positionData = calculateHorizontalPosition(group, canvasWidth)
      const top = mmToPx(group.y || 0)
      const width = mmToPx(group.width || 40)
      const height = mmToPx(group.height || 30)

      const rect = new fabric.Rect({
        width: width,
        height: height,
        fill: 'rgba(245, 158, 11, 0.05)',
        stroke: '#f59e0b',
        strokeWidth: 1,
        strokeDashArray: [6, 4],
        originX: 'left',
        originY: 'top',
      })

      const groupObjs: fabric.Object[] = [rect]

      if (group.snapshot) {
        fabric.Image.fromURL(group.snapshot).then((img) => {
          img.set({
            width: width,
            height: height,
            originX: 'left',
            originY: 'top',
          })

          const groupObj = new fabric.Group([rect, img], {
            left: positionData.left,
            top: top,
            originX: positionData.originX,
            selectable: true,
            hasControls: false,
            lockMovementX: true,
            lockScalingX: true,
            lockScalingY: true,
            lockRotation: true,
            borderColor: '#f59e0b',
          } as any)

          ;(groupObj as any).groupId = group.id
          ;(groupObj as any).isGroupFrame = true

          canvas.add(groupObj)
          canvas.renderAll()
        })
      } else {
        const text = new fabric.Text('📦 Grupo (Duplo clique)', {
          fontSize: 10,
          fill: '#d97706',
          originX: 'center',
          originY: 'center',
        })

        const groupObj = new fabric.Group([rect, text], {
          left: positionData.left,
          top: top,
          originX: positionData.originX,
          selectable: true,
          hasControls: false,
          lockMovementX: true,
          lockScalingX: true,
          lockScalingY: true,
          lockRotation: true,
          borderColor: '#f59e0b',
        } as any)

        ;(groupObj as any).groupId = group.id
        ;(groupObj as any).isGroupFrame = true

        canvas.add(groupObj)
      }
    }

    const restoreSelection = (canvas: fabric.Canvas) => {
      const activeId = selectedElementId || selectedGroupId
      if (!activeId) return

      const objToSelect = canvas.getObjects().find((o: any) => {
        return (
          (selectedElementId && o.elementId === activeId) ||
          (selectedGroupId && o.groupId === activeId && o.isGroupFrame)
        )
      })

      if (objToSelect) {
        canvas.setActiveObject(objToSelect)
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
