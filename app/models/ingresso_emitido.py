from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from enum import Enum


class StatusIngresso(str, Enum):
    """Status possíveis de um ingresso"""
    ATIVO = "Ativo"
    CANCELADO = "Cancelado"


class IngressoEmitidoBase(BaseModel):
    """Modelo base de Ingresso Emitido"""
    evento_id: str
    tipo_ingresso_id: str
    participante_id: str
    participante_cpf: Optional[str] = None
    status: StatusIngresso = StatusIngresso.ATIVO


class IngressoEmitidoCreate(IngressoEmitidoBase):
    """Modelo para criação de Ingresso Emitido"""
    pass


class IngressoEmitidoUpdate(BaseModel):
    """Modelo para atualização de Ingresso Emitido"""
    status: Optional[StatusIngresso] = None


class IngressoEmitido(IngressoEmitidoBase):
    """Modelo completo de Ingresso Emitido"""
    id: str = Field(..., alias="_id")
    qrcode_hash: str
    data_emissao: datetime
    # Embedded layout specific for this issued ticket
    layout_ingresso: Optional[dict] = None


class IngressoEmitidoEmbedded(BaseModel):
    """Modelo de ingresso para uso embutido dentro de Participante"""
    id: Optional[str] = Field(None, alias="_id")
    evento_id: str
    tipo_ingresso_id: str
    participante_id: Optional[str] = None
    participante_cpf: Optional[str] = None
    status: StatusIngresso = StatusIngresso.ATIVO
    qrcode_hash: str
    data_emissao: datetime
    layout_ingresso: Optional[dict] = None
    
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "_id": "507f1f77bcf86cd799439016",
                "evento_id": "507f1f77bcf86cd799439011",
                "tipo_ingresso_id": "507f1f77bcf86cd799439013",
                "participante_id": "507f1f77bcf86cd799439015",
                "status": "Ativo",
                "qrcode_hash": "a1b2c3d4e5f6",
                "data_emissao": "2024-01-20T14:30:00",
                "layout_ingresso": {
                    "canvas": {"width": 80, "height": 120, "unit": "mm"},
                    "elements": []
                }
            }
        }
    )
