"""
Operational Web Interfaces for Lead Collector and Self-Service
Note: Box Office and Gate interfaces have been migrated to mobile app
"""
from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from bson import ObjectId
import app.config.database as database

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# ==================== LEAD COLLECTOR ====================

# endpoint removed: @router.get("/leads/coletor", response_class=HTMLResponse)
async def lead_collector_page(request: Request):
    """Lead Collector interface"""
    return templates.TemplateResponse(
        "operational/lead_collector.html",
        {"request": request}
    )


# ==================== SELF-CREDENTIALING ====================

# endpoint removed: @router.get("/auto-credenciamento", response_class=HTMLResponse)
async def auto_credenciamento_page(
    request: Request,
    evento_id: Optional[str] = Query(None, description="ID do evento")
):
    """Self-service credentialing interface"""
    evento = None
    
    if evento_id:
        db = database.get_database()
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
