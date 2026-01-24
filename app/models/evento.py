from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime


class EventoBase(BaseModel):
    """Modelo base de Evento"""
    nome: str = Field(..., min_length=1, max_length=200)
    nome_normalizado: Optional[str] = Field(None, max_length=300)
    descricao: str = Field(..., min_length=1)
    data_evento: datetime
    logo_base64: Optional[str] = None
    ativo: bool = Field(default=True)
    # Entidades embutidas
    class IlhaEmbedded(BaseModel):
        id: Optional[str] = Field(None, alias="_id")
        nome_setor: str = Field(..., min_length=1, max_length=100)
        capacidade_maxima: int = Field(..., gt=0)

    class TipoIngressoEmbedded(BaseModel):
        id: Optional[str] = Field(None, alias="_id")
        descricao: str = Field(..., min_length=1, max_length=100)
        numero: Optional[int] = None
        padrao: bool = Field(default=False)
        valor: Optional[float] = Field(None, ge=0)
        permissoes: List[str] = Field(default_factory=list)

    ilhas: List[IlhaEmbedded] = Field(default_factory=list)
    tipos_ingresso: List[TipoIngressoEmbedded] = Field(default_factory=list)
    layout_ingresso: Dict[str, Any] = Field(
        default={
            "canvas": {"width": 80, "height": 120, "unit": "mm"},
            "elements": [
                {"type": "text", "value": "{NOME}", "x": 10, "y": 5, "size": 12},
                {"type": "qrcode", "value": "{qrcode_hash}", "x": 10, "y": 20, "size": 40},
                {"type": "text", "value": "{TIPO_INGRESSO}", "x": 10, "y": 65, "size": 10}
            ]
        }
    )
    campos_obrigatorios_planilha: List[str] = Field(default_factory=list)
    token_inscricao: Optional[str] = None
    aceita_inscricoes: bool = Field(default=False)

    class PlanilhaEmbedded(BaseModel):
        id: Optional[str] = Field(None, alias="_id")
        filename: str = Field(..., min_length=1)
        original_filename: Optional[str] = None
        uploaded_at: Optional[datetime] = None
        uploaded_by: Optional[str] = None
        rows: Optional[int] = None
        errors: List[str] = Field(default_factory=list)
        status: str = Field(default="uploaded")

    planilhas_enviadas: List[PlanilhaEmbedded] = Field(default_factory=list)


class EventoCreate(EventoBase):
    """Modelo para criação de Evento"""
    pass


class EventoUpdate(BaseModel):
    """Modelo para atualização de Evento"""
    nome: Optional[str] = Field(None, min_length=1, max_length=200)
    descricao: Optional[str] = Field(None, min_length=1)
    data_evento: Optional[datetime] = None
    logo_base64: Optional[str] = None
    ativo: Optional[bool] = None
    layout_ingresso: Optional[Dict[str, Any]] = None
    campos_obrigatorios_planilha: Optional[List[str]] = None
    token_inscricao: Optional[str] = None


class Evento(EventoBase):
    """Modelo completo de Evento"""
    id: str = Field(..., alias="_id")
    data_criacao: datetime
    token_bilheteria: str
    token_portaria: str
    
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "_id": "507f1f77bcf86cd799439011",
                "nome": "Tech Conference 2024",
                "descricao": "Conferência anual de tecnologia",
                "data_criacao": "2024-01-20T10:00:00",
                "data_evento": "2024-06-15T09:00:00",
                "token_bilheteria": "abc123def456",
                "token_portaria": "xyz789uvw012",
                "token_inscricao": "publictoken123",
                "campos_obrigatorios_planilha": ["Nome", "Email", "CPF"],
                "layout_ingresso": {
                    "canvas": {"width": 80, "unit": "mm"},
                    "elements": []
                }
            }
        }
    )
