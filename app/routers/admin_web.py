from fastapi import APIRouter, Request, HTTPException, status, Depends, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from datetime import datetime, timedelta, timezone
from bson import ObjectId
from app.models.evento import EventoUpdate
from app.config.database import get_database
from app.config.auth import (
    verify_admin_access, 
    verify_admin_credentials, 
    create_access_token,
    verify_jwt_token
)
from app.models.admin import Admin
from PIL import Image
import base64
import io

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

PLANILHA_BASE_FIELDS = ["Nome", "Email", "CPF"]
PLANILHA_OPTIONAL_FIELDS = ["Telefone", "Empresa", "Nacionalidade", "Tipo Ingresso"]

# Simple session storage (in production, use proper session management)
admin_sessions = set()


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


@router.get("/login", response_class=HTMLResponse)
async def admin_login_page(request: Request, error: Optional[str] = None):
    """Admin login page"""
    return templates.TemplateResponse(
        "admin/login.html",
        {"request": request, "error": error, "active_page": ""}
    )


@router.post("/login")
async def admin_login(
    request: Request, 
    username: str = Form(...),
    password: str = Form(...)
):
    """Process admin login with JWT"""
    admin = await verify_admin_credentials(username, password)
    if admin:
        # Create JWT token
        access_token = create_access_token(
            data={"sub": admin.username, "role": "admin", "admin_id": admin.id},
            expires_delta=timedelta(hours=24)
        )
        
        response = RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(
            key="admin_jwt", 
            value=access_token, 
            httponly=False, # Alterado para False para permitir leitura via JS
            max_age=86400,  # 24 hours
            samesite="lax"
        )
        return response
    else:
        return templates.TemplateResponse(
            "admin/login.html",
            {"request": request, "error": "Credenciais inválidas", "active_page": ""}
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
        {"data_evento": {"$gte": datetime.now(timezone.utc)}, "ativo": True}
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
        query["data_evento"] = {"$gte": datetime.now(timezone.utc)}
    elif periodo == "passados":
        query["data_evento"] = {"$lt": datetime.now(timezone.utc)}
    
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
        "data_criacao": datetime.now(timezone.utc),
        "token_bilheteria": base64.b64encode(f"bilheteria_{nome}_{datetime.now(timezone.utc).isoformat()}".encode()).decode()[:32],
        "token_portaria": base64.b64encode(f"portaria_{nome}_{datetime.now(timezone.utc).isoformat()}".encode()).decode()[:32],
        "layout_ingresso": {
            "canvas": {"width": 80, "height": 120, "unit": "mm"},
            "elements": []
        }
    }
    
    if logo_base64:
        evento_dict["logo_base64"] = logo_base64
    
    await db.eventos.insert_one(evento_dict)
    
    return RedirectResponse(url="/admin/eventos", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/eventos/{evento_id}", response_class=HTMLResponse)
async def admin_evento_detalhes(request: Request, evento_id: str):
    """Event details with ilhas and ticket types"""
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
        
        # Get ilhas
        ilhas = []
        cursor = db.ilhas.find({"evento_id": evento["id"]})
        async for ilha in cursor:
            ilha["_id"] = str(ilha["_id"])
            ilha["id"] = ilha["_id"]
            ilhas.append(ilha)
        
        # Get ticket types
        tipos_ingresso = []
        cursor = db.tipos_ingresso.find({"evento_id": evento["id"]})
        async for tipo in cursor:
            tipo["_id"] = str(tipo["_id"])
            tipo["id"] = tipo["_id"]
            tipos_ingresso.append(tipo)
        
        return templates.TemplateResponse(
            "admin/evento_detalhes.html",
            {
                "request": request,
                "active_page": "eventos",
                "evento": evento,
                "ilhas": ilhas,
                "tipos_ingresso": tipos_ingresso
            }
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/eventos/{evento_id}/planilhas", response_class=HTMLResponse)
async def admin_evento_planilhas(request: Request, evento_id: str):
    """Admin page para geração e upload de planilhas"""
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

        campos_brutos = evento.get("campos_obrigatorios_planilha") or []
        campos_atual = PLANILHA_BASE_FIELDS.copy()
        for campo in campos_brutos:
            campo_norm = (campo or "").strip()
            if campo_norm and campo_norm not in campos_atual:
                campos_atual.append(campo_norm)

        campos_opcionais = PLANILHA_OPTIONAL_FIELDS.copy()
        for campo in campos_atual:
            if campo not in PLANILHA_BASE_FIELDS and campo not in campos_opcionais:
                campos_opcionais.append(campo)

        importacoes = []
        cursor = db.planilha_importacoes.find({"evento_id": evento["id"]}).sort("created_at", -1).limit(20)
        async for doc in cursor:
            relatorio = doc.get("relatorio") or {}
            importacoes.append({
                "id": str(doc["_id"]),
                "filename": doc.get("filename") or "arquivo",
                "status": doc.get("status", "pending"),
                "created_at_display": _format_planilha_datetime(doc.get("created_at")),
                "relatorio": relatorio,
                "stats": {
                    "total": relatorio.get("total", 0),
                    "criados": relatorio.get("created_ingressos", 0),
                    "participantes": relatorio.get("created_participants", 0),
                    "erros": len(relatorio.get("errors", []))
                }
            })

        return templates.TemplateResponse(
            "admin/evento_planilhas.html",
            {
                "request": request,
                "active_page": "eventos",
                "evento": evento,
                "campos_base": PLANILHA_BASE_FIELDS,
                "campos_opcionais": campos_opcionais,
                "campos_atual": campos_atual,
                "importacoes": importacoes,
                "saved": request.query_params.get("saved") == "1"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/eventos/{evento_id}/planilhas/campos")
async def admin_evento_planilhas_salvar_campos(request: Request, evento_id: str):
    """Atualiza campos obrigatórios de planilha para o evento."""
    redirect = check_admin_session(request)
    if redirect:
        return redirect

    db = get_database()
    try:
        object_id = ObjectId(evento_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID de evento inválido")

    evento = await db.eventos.find_one({"_id": object_id})
    if not evento:
        raise HTTPException(status_code=404, detail="Evento não encontrado")

    form = await request.form()
    selecionados = form.getlist("campos")

    novos_campos = []
    for campo in PLANILHA_BASE_FIELDS:
        if campo not in novos_campos:
            novos_campos.append(campo)

    for campo in selecionados:
        campo_norm = (campo or "").strip()
        if campo_norm and campo_norm not in novos_campos:
            novos_campos.append(campo_norm)

    await db.eventos.update_one(
        {"_id": object_id},
        {"$set": {"campos_obrigatorios_planilha": novos_campos}}
    )

    return RedirectResponse(
        url=f"/admin/eventos/{evento_id}/planilhas?saved=1",
        status_code=status.HTTP_303_SEE_OTHER
    )


def _format_planilha_datetime(value):
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
    return "--"


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


@router.get("/logout", response_class=HTMLResponse)
async def admin_logout(request: Request):
    """Logout admin"""
    response = RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(key="admin_jwt")
    return response



@router.get("/configuracoes", response_class=HTMLResponse)
async def admin_configuracoes(request: Request):
    """Settings page with administrators management"""
    redirect = check_admin_session(request)
    if redirect:
        return redirect
    
    return templates.TemplateResponse(
        "admin/configuracoes.html",
        {
            "request": request,
            "active_page": "configuracoes"
        }
    )
