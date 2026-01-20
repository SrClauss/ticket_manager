from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class EventoBase(BaseModel):
    """Modelo base de Evento"""
    nome: str = Field(..., min_length=1, max_length=200)
    descricao: str = Field(..., min_length=1)
    data_evento: datetime
    layout_ingresso: Dict[str, Any] = Field(
        default={
            "canvas": {"width": 80, "unit": "mm"},
            "elements": [
                {"type": "text", "value": "{participante_nome}", "x": 10, "y": 5, "size": 12},
                {"type": "qrcode", "value": "{qrcode_hash}", "x": 10, "y": 20, "size": 40},
                {"type": "text", "value": "{tipo_ingresso}", "x": 10, "y": 65, "size": 10}
            ]
        }
    )


class EventoCreate(EventoBase):
    """Modelo para criação de Evento"""
    pass


class EventoUpdate(BaseModel):
    """Modelo para atualização de Evento"""
    nome: Optional[str] = Field(None, min_length=1, max_length=200)
    descricao: Optional[str] = Field(None, min_length=1)
    data_evento: Optional[datetime] = None
    layout_ingresso: Optional[Dict[str, Any]] = None


class Evento(EventoBase):
    """Modelo completo de Evento"""
    id: str = Field(..., alias="_id")
    data_criacao: datetime
    token_bilheteria: str
    token_portaria: str
    
    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "_id": "507f1f77bcf86cd799439011",
                "nome": "Tech Conference 2024",
                "descricao": "Conferência anual de tecnologia",
                "data_criacao": "2024-01-20T10:00:00",
                "data_evento": "2024-06-15T09:00:00",
                "token_bilheteria": "abc123def456",
                "token_portaria": "xyz789uvw012",
                "layout_ingresso": {
                    "canvas": {"width": 80, "unit": "mm"},
                    "elements": []
                }
            }
        }
