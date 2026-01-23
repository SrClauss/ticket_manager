from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional
from datetime import datetime
from bson import ObjectId


class AdminBase(BaseModel):
    """Modelo base de Administrador"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    nome: str = Field(..., min_length=1, max_length=100)
    ativo: bool = Field(default=True)


class AdminCreate(AdminBase):
    """Modelo para criação de Administrador"""
    password: str = Field(..., min_length=8)


class AdminUpdate(BaseModel):
    """Modelo para atualização de Administrador"""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    nome: Optional[str] = Field(None, min_length=1, max_length=100)
    ativo: Optional[bool] = None
    # Enforce minimum 8 chars on update.
    password: Optional[str] = Field(None, min_length=8)


class Admin(AdminBase):
    """Modelo completo de Administrador"""
    id: str = Field(..., alias="_id")
    password_hash: str
    data_criacao: datetime
    ultimo_login: Optional[datetime] = None

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "_id": "507f1f77bcf86cd799439011",
                "username": "admin",
                "email": "admin@example.com",
                "nome": "Administrador",
                "ativo": True,
                "password_hash": "$2b$12$...",
                "data_criacao": "2024-01-20T10:00:00",
                "ultimo_login": "2024-01-20T15:30:00"
            }
        }
    )

    @classmethod
    def from_mongo(cls, data: dict):
        """Cria instância a partir de dados do MongoDB"""
        if "_id" in data and isinstance(data["_id"], ObjectId):
            data["_id"] = str(data["_id"])
        # Provide defaults for missing legacy fields for compatibility in tests
        data.setdefault("nome", "")
        data.setdefault("ativo", True)
        return cls(**data)