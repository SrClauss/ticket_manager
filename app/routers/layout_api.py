"""
Router para API de layout de ingressos (subdocumento do evento).
Endpoints RESTful consumidos pelo editor React.
"""
from fastapi import APIRouter, HTTPException, status, Depends
from datetime import datetime
from bson import ObjectId

from app.config.database import get_database
from app.config.auth import verify_admin_access
from app.models.layout import LayoutUpdate


router = APIRouter(prefix="/api/eventos", tags=["Layout API"])


def get_db():
    """Helper para obter database"""
    return get_database()


@router.get("/{evento_id}/layout")
async def get_evento_layout(
    evento_id: str,
    admin_payload: dict = Depends(verify_admin_access)
):
    """Obtém o layout de ingresso de um evento específico"""
    db = get_db()
    
    try:
        evento = await db.eventos.find_one({"_id": ObjectId(evento_id)})
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID inválido"
        )
    
    if not evento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evento não encontrado"
        )
    
    # Retorna layout_ingresso existente ou padrão
    layout = evento.get("layout_ingresso", {
        "canvas": {
            "width": 62,
            "height": 120,
            "orientation": "portrait",
            "padding": 5
        },
        "elements": [],
        "groups": []
    })
    
    return {
        "evento_id": str(evento["_id"]),
        "evento_nome": evento.get("nome"),
        "layout": layout
    }


@router.put("/{evento_id}/layout")
async def update_evento_layout(
    evento_id: str,
    data: LayoutUpdate,
    admin_payload: dict = Depends(verify_admin_access)
):
    """Atualiza o layout de ingresso de um evento"""
    db = get_db()
    
    try:
        obj_id = ObjectId(evento_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID inválido"
        )
    
    evento = await db.eventos.find_one({"_id": obj_id})
    if not evento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evento não encontrado"
        )
    
    # Prepara atualização do layout_ingresso
    layout_dict = data.model_dump(exclude_unset=True)
    
    # Atualiza o subdocumento layout_ingresso
    await db.eventos.update_one(
        {"_id": obj_id},
        {"$set": {"layout_ingresso": layout_dict}}
    )
    
    return {
        "success": True,
        "message": "Layout atualizado com sucesso",
        "evento_id": str(obj_id)
    }
