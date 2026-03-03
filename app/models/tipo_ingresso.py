from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any


class TipoIngressoBase(BaseModel):
    """Modelo base de Tipo de Ingresso"""
    descricao: str = Field(..., min_length=1, max_length=100)
    numero: Optional[int] = None
    padrao: bool = Field(default=False)
    valor: Optional[float] = Field(None, ge=0)
    permissoes: List[str] = Field(default_factory=list)  # Lista de IDs de Ilhas


class TipoIngressoCreate(TipoIngressoBase):
    """Modelo para criação de Tipo de Ingresso"""
    evento_id: str


class TipoIngressoUpdate(BaseModel):
    """Modelo para atualização de Tipo de Ingresso"""
    descricao: Optional[str] = Field(None, min_length=1, max_length=100)
    valor: Optional[float] = Field(None, ge=0)
    numero: Optional[int] = None
    padrao: Optional[bool] = None
    permissoes: Optional[List[str]] = None


class TipoIngresso(TipoIngressoBase):
    """Modelo completo de Tipo de Ingresso"""
    id: str = Field(..., alias="_id")
    evento_id: str
    
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "_id": "507f1f77bcf86cd799439013",
                "evento_id": "507f1f77bcf86cd799439011",
                "descricao": "VIP",
                "numero": 1,
                "padrao": True,
                "valor": 150.00,
                "permissoes": ["507f1f77bcf86cd799439012", "507f1f77bcf86cd799439014"],
            }
        }
    )
