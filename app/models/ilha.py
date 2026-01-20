from pydantic import BaseModel, Field
from typing import Optional


class IlhaBase(BaseModel):
    """Modelo base de Ilha (Setor)"""
    nome_setor: str = Field(..., min_length=1, max_length=100)
    capacidade_maxima: int = Field(..., gt=0)


class IlhaCreate(IlhaBase):
    """Modelo para criação de Ilha"""
    evento_id: str


class IlhaUpdate(BaseModel):
    """Modelo para atualização de Ilha"""
    nome_setor: Optional[str] = Field(None, min_length=1, max_length=100)
    capacidade_maxima: Optional[int] = Field(None, gt=0)


class Ilha(IlhaBase):
    """Modelo completo de Ilha"""
    id: str = Field(..., alias="_id")
    evento_id: str
    
    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "_id": "507f1f77bcf86cd799439012",
                "evento_id": "507f1f77bcf86cd799439011",
                "nome_setor": "VIP",
                "capacidade_maxima": 100
            }
        }
