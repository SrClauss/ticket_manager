from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from decimal import Decimal


class TipoIngressoBase(BaseModel):
    """Modelo base de Tipo de Ingresso"""
    descricao: str = Field(..., min_length=1, max_length=100)
    valor: float = Field(..., ge=0)
    permissoes: List[str] = Field(default_factory=list)  # Lista de IDs de Ilhas
    layout_ingresso: Optional[Dict[str, Any]] = Field(
        default={
            "canvas": {"width": 62, "height": 90, "unit": "mm"},
            "elements": [
                {"type": "text", "value": "{NOME}", "x": 5, "y": 5, "size": 12},
                {"type": "qrcode", "value": "{qrcode_hash}", "x": 5, "y": 20, "size": 30},
                {"type": "text", "value": "{TIPO_INGRESSO}", "x": 5, "y": 60, "size": 10}
            ]
        }
    )


class TipoIngressoCreate(TipoIngressoBase):
    """Modelo para criação de Tipo de Ingresso"""
    evento_id: str


class TipoIngressoUpdate(BaseModel):
    """Modelo para atualização de Tipo de Ingresso"""
    descricao: Optional[str] = Field(None, min_length=1, max_length=100)
    valor: Optional[float] = Field(None, ge=0)
    permissoes: Optional[List[str]] = None
    layout_ingresso: Optional[Dict[str, Any]] = None


class TipoIngresso(TipoIngressoBase):
    """Modelo completo de Tipo de Ingresso"""
    id: str = Field(..., alias="_id")
    evento_id: str
    
    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "_id": "507f1f77bcf86cd799439013",
                "evento_id": "507f1f77bcf86cd799439011",
                "descricao": "VIP",
                "valor": 150.00,
                "permissoes": ["507f1f77bcf86cd799439012", "507f1f77bcf86cd799439014"],
                "layout_ingresso": {"canvas": {"width": 62, "height": 90, "unit": "mm"}, "elements": []}
            }
        }
