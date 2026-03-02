import type { HorizontalPosition } from '@/types/layout'

export const mmToPx = (mm: number): number => {
  return mm * 3.78
}

export const pxToMm = (px: number): number => {
  return px / 3.78
}

export const calculateHorizontalPosition = (
  item: {
    horizontal_position: HorizontalPosition
    margin_left: number
    margin_right: number
  },
  containerWidthMm: number
): { left: number; originX: 'left' | 'center' | 'right' } => {
  const containerWidthPx = mmToPx(containerWidthMm)
  const marginL = mmToPx(item.margin_left || 0)
  const marginR = mmToPx(item.margin_right || 0)

  let left = 0
  let originX: 'left' | 'center' | 'right' = 'left'

  if (item.horizontal_position === 'left') {
    left = marginL
    originX = 'left'
  } else if (item.horizontal_position === 'right') {
    left = containerWidthPx - marginR
    originX = 'right'
  } else {
    left = containerWidthPx / 2 + marginL - marginR
    originX = 'center'
  }

  return { left, originX }
}

export const mockTemplateData: Record<string, string> = {
  '{NOME}': 'João da Silva Sauro',
  '{CPF}': '123.456.789-00',
  '{EMAIL}': 'joao@exemplo.com',
  '{TIPO_INGRESSO}': 'Pista Premium VIP',
  '{EVENTO_NOME}': 'Festival de Verão 2026',
  '{DATA}': '15/12/2026',
  '{HORARIO}': '20:00',
  '{qrcode_hash}': 'hash_ficticio_123',
}

export const replaceTemplateTags = (text: string): string => {
  let result = text
  Object.entries(mockTemplateData).forEach(([tag, value]) => {
    result = result.split(tag).join(value)
  })
  return result
}
