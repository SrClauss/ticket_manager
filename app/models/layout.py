from pydantic import BaseModel, Field
from typing import Optional, List


class CanvasConfig(BaseModel):
    """Configuração do canvas do layout"""
    width: float = Field(..., gt=0)
    height: float = Field(..., gt=0)
    orientation: str = Field(default="portrait", pattern="^(portrait|landscape)$")
    padding: float = Field(default=5, ge=0)


class ElementLink(BaseModel):
    """Vínculo entre elementos"""
    targetId: str
    gap: float = Field(default=5, ge=0)
    gapType: str = Field(default="fixed", pattern="^(fixed|between)$")
    position: str = Field(default="right", pattern="^(right|below)$")


class LayoutElement(BaseModel):
    """Elemento individual do layout (texto, qrcode, divider)"""
    id: str
    type: str = Field(..., pattern="^(text|qrcode|logo|divider)$")
    y: float = Field(..., ge=0)
    horizontal_position: str = Field(..., pattern="^(left|center|right)$")
    margin_left: float = Field(default=0, ge=0)
    margin_right: float = Field(default=0, ge=0)
    link: Optional[ElementLink] = None
    wrapText: Optional[bool] = None
    
    # Propriedades de texto
    value: Optional[str] = None
    size: Optional[int] = Field(None, gt=0)
    font: Optional[str] = None
    bold: Optional[bool] = None
    italic: Optional[bool] = None
    
    # Propriedades de QR/Logo
    size_mm: Optional[float] = Field(None, gt=0)
    
    # Propriedades de divider
    length_mm: Optional[float] = Field(None, gt=0)
    thickness: Optional[float] = Field(None, gt=0)


class LayoutUpdate(BaseModel):
    """
    Modelo para atualização do layout_ingresso de um evento.
    Este é o subdocumento embutido no evento, não uma entidade separada.
    """
    canvas: CanvasConfig
    elements: List[LayoutElement] = Field(default_factory=list)
    
    @classmethod
    def default_layout(cls):
        """Retorna um layout padrão para novo evento"""
        return {
            "canvas": {
                "width": 80,
                "height": 120,
                "orientation": "portrait",
                "padding": 5
            },
            "elements": [
                {
                    "id": "elem-1",
                    "type": "text",
                    "y": 10,
                    "horizontal_position": "center",
                    "margin_left": 0,
                    "margin_right": 0,
                    "wrapText": False,
                    "value": "{EVENTO_NOME}",
                    "size": 16,
                    "font": "Arial",
                    "bold": True,
                    "italic": False
                },
                {
                    "id": "elem-2",
                    "type": "text",
                    "y": 25,
                    "horizontal_position": "center",
                    "margin_left": 0,
                    "margin_right": 0,
                    "wrapText": True,
                    "value": "{NOME}",
                    "size": 14,
                    "font": "Arial",
                    "bold": False,
                    "italic": False
                },
                {
                    "id": "elem-3",
                    "type": "qrcode",
                    "y": 45,
                    "horizontal_position": "center",
                    "margin_left": 0,
                    "margin_right": 0,
                    "size_mm": 30
                },
                {
                    "id": "elem-4",
                    "type": "text",
                    "y": 85,
                    "horizontal_position": "center",
                    "margin_left": 0,
                    "margin_right": 0,
                    "wrapText": False,
                    "value": "{CPF}",
                    "size": 10,
                    "font": "Arial",
                    "bold": False,
                    "italic": False
                }
            ]
        }
