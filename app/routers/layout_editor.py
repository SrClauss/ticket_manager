"""
Router web para servir a interface do editor de layout React.
O layout é um subdocumento dentro de evento.layout_ingresso.
O Jinja serve uma página HTML que carrega o React build de /static/editor/
"""
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from bson import ObjectId

from app.config.database import get_database
from app.config.auth import get_current_admin_web
from app.models.admin import Admin


router = APIRouter(prefix="/admin/editor", tags=["Layout Editor"])


def get_db():
    """Helper para obter database"""
    return get_database()


@router.get("/", response_class=HTMLResponse)
async def editor_page(
    request: Request,
    evento_id: str,
    current_admin: Admin = Depends(get_current_admin_web)
):
    """
    Serve página HTML simples que carrega o React build.
    O React já foi compilado e está em /static/editor/ (servido pelo FastAPI).
    
    Query params:
    - evento_id: ID do evento (obrigatório)
    """
    db = get_db()
    
    # Verifica se evento existe
    try:
        evento = await db.eventos.find_one({"_id": ObjectId(evento_id)})
        if not evento:
            raise HTTPException(status_code=404, detail="Evento não encontrado")
    except Exception:
        raise HTTPException(status_code=400, detail="ID de evento inválido")
    
    # URL de retorno
    back_url = f"/admin/eventos/{evento_id}"
    
    # Jinja renderiza HTML que carrega JS estático
    return request.app.state.templates.TemplateResponse(
        "admin/editor_layout.html",
        {
            "request": request,
            "evento_id": evento_id,
            "evento_nome": evento.get("nome", ""),
            "api_base_url": str(request.base_url).rstrip("/"),
            "back_url": back_url,
        }
    )
