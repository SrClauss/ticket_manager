from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class LeadInteracao(BaseModel):
    """Modelo para interação de Lead"""
    id: str = Field(..., alias="_id")
    evento_id: str
    participante_id: str
    qrcode_hash: str
    data_interacao: datetime
    origem: str  # De onde veio a coleta (ex: "stand_x", "scanner_portaria")
    
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "_id": "507f1f77bcf86cd799439017",
                "evento_id": "507f1f77bcf86cd799439011",
                "participante_id": "507f1f77bcf86cd799439015",
                "qrcode_hash": "a1b2c3d4e5f6",
                "data_interacao": "2024-01-20T15:00:00",
                "origem": "stand_patrocinador_1"
            }
        }
    )


class LeadInteracaoCreate(BaseModel):
    """Modelo para criação de interação de Lead"""
    qrcode_hash: str
    origem: str
