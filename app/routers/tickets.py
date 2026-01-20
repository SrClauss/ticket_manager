from fastapi import APIRouter, HTTPException, status
from typing import List
from datetime import datetime
from bson import ObjectId
from app.models.ticket import Ticket, TicketCreate, TicketUpdate
from app.config.database import get_database

router = APIRouter()


@router.get("/", response_model=List[Ticket])
async def list_tickets(skip: int = 0, limit: int = 10):
    """Lista todos os tickets"""
    db = get_database()
    tickets = []
    cursor = db.tickets.find().skip(skip).limit(limit)
    async for document in cursor:
        document["_id"] = str(document["_id"])
        tickets.append(Ticket(**document))
    return tickets


@router.get("/{ticket_id}", response_model=Ticket)
async def get_ticket(ticket_id: str):
    """Obtém um ticket específico"""
    db = get_database()
    
    try:
        document = await db.tickets.find_one({"_id": ObjectId(ticket_id)})
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID de ticket inválido"
        )
    
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket não encontrado"
        )
    
    document["_id"] = str(document["_id"])
    return Ticket(**document)


@router.post("/", response_model=Ticket, status_code=status.HTTP_201_CREATED)
async def create_ticket(ticket: TicketCreate):
    """Cria um novo ticket"""
    db = get_database()
    
    ticket_dict = ticket.model_dump()
    ticket_dict["created_at"] = datetime.utcnow()
    ticket_dict["updated_at"] = datetime.utcnow()
    
    result = await db.tickets.insert_one(ticket_dict)
    
    created_ticket = await db.tickets.find_one({"_id": result.inserted_id})
    created_ticket["_id"] = str(created_ticket["_id"])
    
    return Ticket(**created_ticket)


@router.put("/{ticket_id}", response_model=Ticket)
async def update_ticket(ticket_id: str, ticket_update: TicketUpdate):
    """Atualiza um ticket existente"""
    db = get_database()
    
    try:
        object_id = ObjectId(ticket_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID de ticket inválido"
        )
    
    # Remove campos None
    update_data = {k: v for k, v in ticket_update.model_dump().items() if v is not None}
    
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nenhum campo para atualizar"
        )
    
    update_data["updated_at"] = datetime.utcnow()
    
    result = await db.tickets.update_one(
        {"_id": object_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket não encontrado"
        )
    
    updated_ticket = await db.tickets.find_one({"_id": object_id})
    updated_ticket["_id"] = str(updated_ticket["_id"])
    
    return Ticket(**updated_ticket)


@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ticket(ticket_id: str):
    """Deleta um ticket"""
    db = get_database()
    
    try:
        object_id = ObjectId(ticket_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID de ticket inválido"
        )
    
    result = await db.tickets.delete_one({"_id": object_id})
    
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket não encontrado"
        )
    
    return None
