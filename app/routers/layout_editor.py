"""
Router web para servir a interface do editor de layout (Alpine.js + Fabric.js).
O layout é um subdocumento dentro de evento.layout_ingresso.
"""
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from bson import ObjectId

from app.config.database import get_database
from app.config.auth import verify_jwt_token


router = APIRouter(prefix="/admin/editor", tags=["Layout Editor"])


def get_db():
    """Helper para obter database"""
    return get_database()


def check_admin_session(request: Request):
    """Check if admin is logged in via JWT cookie"""
    jwt_token = request.cookies.get("admin_jwt")
    if not jwt_token:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    
    try:
        payload = verify_jwt_token(jwt_token)
        if payload.get("role") != "admin":
            return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
        return None
    except HTTPException:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/", response_class=HTMLResponse)
async def editor_page(
    request: Request,
    evento_id: str
):
    """
    Serve o editor de layout Alpine.js + Fabric.js para um evento.

    Query params:
    - evento_id: ID do evento (obrigatório)
    """
    # Verificar autenticação
    redirect = check_admin_session(request)
    if redirect:
        return redirect

    db = get_db()

    # Verifica se evento existe
    try:
        evento = await db.eventos.find_one({"_id": ObjectId(evento_id)})
        if not evento:
            raise HTTPException(status_code=404, detail="Evento não encontrado")
    except Exception:
        raise HTTPException(status_code=400, detail="ID de evento inválido")

    import json as _json
    layout_ingresso = evento.get("layout_ingresso") or {}
    back_url = f"/admin/eventos/{evento_id}"

    return request.app.state.templates.TemplateResponse(
        "admin/editor_layout.html",
        {
            "request": request,
            "evento_id": evento_id,
            "evento_nome": evento.get("nome", ""),
            "back_url": back_url,
            "initial_layout": _json.dumps(layout_ingresso, default=str),
        }
    )
