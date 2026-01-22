from pydantic import BaseModel, Field, EmailStr, field_validator, ConfigDict
from typing import Optional
import re


from app.utils.validations import validate_cpf



class ParticipanteBase(BaseModel):
    """Modelo base de Participante/Lead"""
    nome: str = Field(..., min_length=1, max_length=200)
    email: EmailStr
    cpf: str = Field(..., min_length=11, max_length=14)
    telefone: Optional[str] = Field(None, max_length=20)
    empresa: Optional[str] = Field(None, max_length=200)
    nacionalidade: Optional[str] = Field(None, max_length=100)

    @field_validator('cpf')
    def cpf_validator(cls, v: str) -> str:
        return validate_cpf(v)


class ParticipanteCreate(ParticipanteBase):
    """Modelo para criação de Participante"""
    pass


class ParticipanteUpdate(BaseModel):
    """Modelo para atualização de Participante"""
    nome: Optional[str] = Field(None, min_length=1, max_length=200)
    email: Optional[EmailStr] = None
    cpf: Optional[str] = None
    telefone: Optional[str] = Field(None, max_length=20)
    empresa: Optional[str] = Field(None, max_length=200)
    nacionalidade: Optional[str] = Field(None, max_length=100)


class Participante(ParticipanteBase):
    """Modelo completo de Participante"""
    id: str = Field(..., alias="_id")

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "_id": "507f1f77bcf86cd799439015",
                "nome": "João Silva",
                "email": "joao.silva@example.com",
                "telefone": "+55 11 99999-9999",
                "empresa": "Tech Corp",
                "nacionalidade": "Brasil",
                "cpf": "52998224725"
            }
        }
    )
