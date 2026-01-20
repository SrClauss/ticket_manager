from fastapi import APIRouter, Request, HTTPException, status, Depends, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from datetime import datetime
from bson import ObjectId
from app.models.evento import EventoUpdate
from app.config.database import get_database
from app.config.auth import verify_admin_access
from PIL import Image
import base64
import io

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# Simple session storage (in production, use proper session management)
admin_sessions = set()


def check_admin_session(request: Request):
    """Check if admin is logged in"""
    session_token = request.cookies.get("admin_session")
    if not session_token or session_token not in admin_sessions:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    return None


@router.get("/login", response_class=HTMLResponse)
async def admin_login_page(request: Request, error: Optional[str] = None):
    """Admin login page"""
    return templates.TemplateResponse(
        "admin/login.html",
        {"request": request, "error": error, "active_page": ""}
    )


@router.post("/login")
async def admin_login(request: Request, admin_key: str = Form(...)):
    """Process admin login"""
    # Simple authentication (in production, use proper authentication)
    if admin_key == "admin_key_change_in_production":
        session_token = base64.b64encode(f"{admin_key}:{datetime.utcnow()}".encode()).decode()
        admin_sessions.add(session_token)
        
        response = RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(key="admin_session", value=session_token, httponly=True)
        return response
    else:
        return templates.TemplateResponse(
            "admin/login.html",
            {"request": request, "error": "Chave de acesso inválida", "active_page": ""}
        )


@router.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """Admin dashboard"""
    redirect = check_admin_session(request)
    if redirect:
        return redirect
    
    db = get_database()
    
    # Get statistics
    total_eventos = await db.eventos.count_documents({})
    eventos_ativos = await db.eventos.count_documents({"ativo": True})
    total_ingressos = await db.ingressos_emitidos.count_documents({})
    
    # Calculate revenue
    pipeline = [
        {"$match": {"status": "Ativo"}},
        {"$lookup": {
            "from": "tipos_ingresso",
            "localField": "tipo_ingresso_id",
            "foreignField": "_id",
            "as": "tipo"
        }},
        {"$unwind": "$tipo"},
        {"$group": {
            "_id": None,
            "total": {"$sum": "$tipo.valor"}
        }}
    ]
    
    receita_total = 0
    async for result in db.ingressos_emitidos.aggregate(pipeline):
        receita_total = result.get("total", 0)
    
    # Get upcoming events
    proximos_eventos = []
    cursor = db.eventos.find(
        {"data_evento": {"$gte": datetime.utcnow()}, "ativo": True}
    ).sort("data_evento", 1).limit(5)
    
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        doc["id"] = doc["_id"]
        proximos_eventos.append(doc)
    
    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "active_page": "dashboard",
            "stats": {
                "total_eventos": total_eventos,
                "eventos_ativos": eventos_ativos,
                "total_ingressos": total_ingressos,
                "receita_total": receita_total
            },
            "proximos_eventos": proximos_eventos
        }
    )


@router.get("/eventos", response_class=HTMLResponse)
async def admin_eventos_list(
    request: Request,
    busca: Optional[str] = None,
    status: Optional[str] = None,
    periodo: Optional[str] = None
):
    """List eventos with filters"""
    redirect = check_admin_session(request)
    if redirect:
        return redirect
    
    db = get_database()
    
    # Build query
    query = {}
    
    if busca:
        query["nome"] = {"$regex": busca, "$options": "i"}
    
    if status == "ativo":
        query["ativo"] = True
    elif status == "inativo":
        query["ativo"] = False
    
    if periodo == "futuros":
        query["data_evento"] = {"$gte": datetime.utcnow()}
    elif periodo == "passados":
        query["data_evento"] = {"$lt": datetime.utcnow()}
    
    # Get events
    eventos = []
    cursor = db.eventos.find(query).sort("data_evento", -1)
    
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        doc["id"] = doc["_id"]
        eventos.append(doc)
    
    return templates.TemplateResponse(
        "admin/eventos_list.html",
        {
            "request": request,
            "active_page": "eventos",
            "eventos": eventos,
            "busca": busca or "",
            "status": status or "",
            "periodo": periodo or ""
        }
    )


@router.get("/eventos/novo", response_class=HTMLResponse)
async def admin_evento_novo_page(request: Request):
    """New evento form"""
    redirect = check_admin_session(request)
    if redirect:
        return redirect
    
    return templates.TemplateResponse(
        "admin/evento_novo.html",
        {"request": request, "active_page": "eventos"}
    )


@router.post("/eventos/novo")
async def admin_evento_criar(
    request: Request,
    nome: str = Form(...),
    descricao: str = Form(...),
    data_evento: str = Form(...),
    ativo: Optional[str] = Form(None),
    logo: Optional[UploadFile] = File(None)
):
    """Create new evento"""
    redirect = check_admin_session(request)
    if redirect:
        return redirect
    
    db = get_database()
    
    # Process logo if uploaded
    logo_base64 = None
    if logo and logo.filename:
        # Validate file type
        if not logo.content_type in ["image/png", "image/jpeg"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formato de imagem inválido. Use PNG ou JPG."
            )
        
        # Read file
        contents = await logo.read()
        
        # Validate size (200KB)
        if len(contents) > 200 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Arquivo muito grande. Máximo: 200KB"
            )
        
        # Resize image using Pillow
        try:
            image = Image.open(io.BytesIO(contents))
            
            # Resize maintaining aspect ratio
            max_size = (400, 400)
            image.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Convert to RGB if needed
            if image.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background
            
            # Save to bytes
            output = io.BytesIO()
            image.save(output, format='JPEG', quality=85)
            output.seek(0)
            
            # Encode to base64
            logo_base64 = base64.b64encode(output.read()).decode()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Erro ao processar imagem: {str(e)}"
            )
    
    # Create evento
    evento_dict = {
        "nome": nome,
        "descricao": descricao,
        "data_evento": datetime.fromisoformat(data_evento),
        "ativo": ativo == "on",
        "data_criacao": datetime.utcnow(),
        "token_bilheteria": base64.b64encode(f"bilheteria_{nome}_{datetime.utcnow()}".encode()).decode()[:32],
        "token_portaria": base64.b64encode(f"portaria_{nome}_{datetime.utcnow()}".encode()).decode()[:32],
        "layout_ingresso": {
            "canvas": {"width": 80, "height": 120, "unit": "mm"},
            "elements": []
        }
    }
    
    if logo_base64:
        evento_dict["logo_base64"] = logo_base64
    
    await db.eventos.insert_one(evento_dict)
    
    return RedirectResponse(url="/admin/eventos", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/eventos/layout/{evento_id}", response_class=HTMLResponse)
async def admin_evento_layout_page(request: Request, evento_id: str):
    """Ticket layout editor"""
    redirect = check_admin_session(request)
    if redirect:
        return redirect
    
    db = get_database()
    
    try:
        evento = await db.eventos.find_one({"_id": ObjectId(evento_id)})
        if not evento:
            raise HTTPException(status_code=404, detail="Evento não encontrado")
        
        evento["_id"] = str(evento["_id"])
        evento["id"] = evento["_id"]
        
        return templates.TemplateResponse(
            "admin/ticket_layout.html",
            {"request": request, "active_page": "eventos", "evento": evento}
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/eventos/layout/{evento_id}")
async def admin_evento_layout_salvar(
    evento_id: str,
    request: Request,
    dependencies=[Depends(verify_admin_access)]
):
    """Save ticket layout"""
    db = get_database()
    
    try:
        data = await request.json()
        layout_ingresso = data.get("layout_ingresso")
        
        if not layout_ingresso:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Layout inválido"
            )
        
        result = await db.eventos.update_one(
            {"_id": ObjectId(evento_id)},
            {"$set": {"layout_ingresso": layout_ingresso}}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Evento não encontrado")
        
        return {"message": "Layout salvo com sucesso"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/eventos/limpar-passados")
async def admin_limpar_eventos_passados(request: Request):
    """Soft delete past events"""
    redirect = check_admin_session(request)
    if redirect:
        return redirect
    
    db = get_database()
    
    # Soft delete: set ativo = False for past events
    result = await db.eventos.update_many(
        {"data_evento": {"$lt": datetime.utcnow()}},
        {"$set": {"ativo": False}}
    )
    
    return RedirectResponse(
        url=f"/admin/eventos?periodo=passados",
        status_code=status.HTTP_303_SEE_OTHER
    )


@router.get("/financeiro", response_class=HTMLResponse)
async def admin_financeiro(request: Request):
    """Financial page (placeholder)"""
    redirect = check_admin_session(request)
    if redirect:
        return redirect
    
    return templates.TemplateResponse(
        "admin/base.html",
        {
            "request": request,
            "active_page": "financeiro"
        }
    )


@router.get("/configuracoes", response_class=HTMLResponse)
async def admin_configuracoes(request: Request):
    """Settings page (placeholder)"""
    redirect = check_admin_session(request)
    if redirect:
        return redirect
    
    return templates.TemplateResponse(
        "admin/base.html",
        {
            "request": request,
            "active_page": "configuracoes"
        }
    )
