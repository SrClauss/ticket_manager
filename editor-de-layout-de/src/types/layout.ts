export type ElementType = 'text' | 'qrcode' | 'logo' | 'divider'

export type HorizontalPosition = 'left' | 'center' | 'right'

export type LinkGapType = 'fixed' | 'between'

export interface ElementLink {
  targetId: string
  gap: number
  gapType: LinkGapType
  position: 'right' | 'below'  // posição relativa ao elemento alvo
}

export interface TicketElement {
  id: string
  type: ElementType
  y: number
  horizontal_position: HorizontalPosition
  margin_left: number
  margin_right: number
  link?: ElementLink  // vínculo com outro elemento
  wrapText?: boolean  // quebra de linha automática
  
  value?: string
  size?: number
  font?: string
  bold?: boolean
  italic?: boolean
  
  size_mm?: number
  
  length_mm?: number
  thickness?: number
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
}

export type EditorMode = 'normal'
