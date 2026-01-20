"""
Operational Web Interfaces for Box Office, Gate, Lead Collector, and Self-Service
"""
from fastapi import APIRouter, Request, HTTPException, status, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from bson import ObjectId
from app.config.database import get_database

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# ==================== BOX OFFICE / CREDENTIALING ====================

@router.get("/bilheteria/credenciamento", response_class=HTMLResponse)
async def bilheteria_credenciamento_page(
    request: Request,
    token: Optional[str] = Query(None, description="Token de bilheteria")
):
    """Box Office/Credentialing interface"""
    if not token:
        return templates.TemplateResponse(
            "operational/token_required.html",
            {
                "request": request,
                "module_name": "Bilheteria",
                "module_description": "Credenciamento e Emissão de Ingressos"
            }
        )
    
    # Verify token and get event
    db = get_database()
    evento = await db.eventos.find_one({"token_bilheteria": token})
    
    if not evento:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de bilheteria inválido"
        )
    
    evento["_id"] = str(evento["_id"])
    evento["id"] = evento["_id"]
    
    return templates.TemplateResponse(
        "operational/bilheteria_credenciamento.html",
        {
            "request": request,
            "evento": evento,
            "token": token
        }
    )


# ==================== GATE / ACCESS CONTROL ====================

@router.get("/portaria/controle", response_class=HTMLResponse)
async def portaria_controle_page(
    request: Request,
    token: Optional[str] = Query(None, description="Token de portaria")
):
    """Gate/Access Control interface with QR scanner"""
    if not token:
        return templates.TemplateResponse(
            "operational/token_required.html",
            {
                "request": request,
                "module_name": "Portaria",
                "module_description": "Controle de Acesso"
            }
        )
    
    # Verify token and get event
    db = get_database()
    evento = await db.eventos.find_one({"token_portaria": token})
    
    if not evento:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de portaria inválido"
        )
    
    evento["_id"] = str(evento["_id"])
    evento["id"] = evento["_id"]
    
    # Get ilhas for this event
    ilhas = []
    cursor = db.ilhas.find({"evento_id": evento["id"]})
    async for ilha in cursor:
        ilha["_id"] = str(ilha["_id"])
        ilha["id"] = ilha["_id"]
        ilhas.append(ilha)
    
    return templates.TemplateResponse(
        "operational/portaria_controle.html",
        {
            "request": request,
            "evento": evento,
            "ilhas": ilhas,
            "token": token
        }
    )


# ==================== LEAD COLLECTOR ====================

@router.get("/leads/coletor", response_class=HTMLResponse)
async def lead_collector_page(request: Request):
    """Lead Collector interface"""
    return templates.TemplateResponse(
        "operational/lead_collector.html",
        {"request": request}
    )


# ==================== SELF-CREDENTIALING ====================

@router.get("/auto-credenciamento", response_class=HTMLResponse)
async def auto_credenciamento_page(
    request: Request,
    evento_id: Optional[str] = Query(None, description="ID do evento")
):
    """Self-service credentialing interface"""
    evento = None
    
    if evento_id:
        db = get_database()
        try:
            evento = await db.eventos.find_one({"_id": ObjectId(evento_id)})
            if evento:
                evento["_id"] = str(evento["_id"])
                evento["id"] = evento["_id"]
        except Exception:
            pass
    
    return templates.TemplateResponse(
        "operational/auto_credenciamento.html",
        {
            "request": request,
            "evento": evento
        }
    )
