from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class TicketStatus(str, Enum):
    """Status possíveis de um ticket"""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(str, Enum):
    """Prioridades possíveis de um ticket"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TicketBase(BaseModel):
    """Modelo base de Ticket"""
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1)
    priority: TicketPriority = TicketPriority.MEDIUM
    status: TicketStatus = TicketStatus.OPEN


class TicketCreate(TicketBase):
    """Modelo para criação de Ticket"""
    pass


class TicketUpdate(BaseModel):
    """Modelo para atualização de Ticket"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, min_length=1)
    priority: Optional[TicketPriority] = None
    status: Optional[TicketStatus] = None


class Ticket(TicketBase):
    """Modelo completo de Ticket"""
    id: str = Field(..., alias="_id")
    created_at: datetime
    updated_at: datetime
    
    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "_id": "507f1f77bcf86cd799439011",
                "title": "Problema com login",
                "description": "Usuário não consegue fazer login no sistema",
                "priority": "high",
                "status": "open",
                "created_at": "2024-01-20T10:00:00",
                "updated_at": "2024-01-20T10:00:00"
            }
        }
