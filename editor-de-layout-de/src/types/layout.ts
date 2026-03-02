export type ElementType = 'text' | 'qrcode' | 'logo' | 'divider'

export type HorizontalPosition = 'left' | 'center' | 'right'

export interface TicketElement {
  id: string
  type: ElementType
  y: number
  horizontal_position: HorizontalPosition
  margin_left: number
  margin_right: number
  groupId: string | null
  
  value?: string
  size?: number
  font?: string
  bold?: boolean
  italic?: boolean
  
  size_mm?: number
  
  length_mm?: number
  thickness?: number
}

export interface TicketGroup {
  id: string
  y: number
  width: number
  height: number
  horizontal_position: HorizontalPosition
  margin_left: number
  margin_right: number
  snapshot: string | null
}

export interface CanvasConfig {
  width: number
  height: number
  orientation: 'portrait' | 'landscape'
  padding: number
}

export interface LayoutState {
  canvas: CanvasConfig
  elements: TicketElement[]
  groups: TicketGroup[]
}

export type EditorMode = 'normal' | 'editing-group'
