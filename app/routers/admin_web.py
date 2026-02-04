from fastapi import APIRouter, Request, HTTPException, status, Depends, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from datetime import datetime, timedelta, timezone
import math
from bson import ObjectId
from app.models.evento import EventoUpdate
import app.config.database as database

def get_database():
    """Runtime indirection to allow tests to monkeypatch `get_database` on this module."""
    return database.get_database()
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
import secrets
from app.utils.validations import normalize_event_name

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

PLANILHA_BASE_FIELDS = ["Nome", "Email", "CPF"]
PLANILHA_OPTIONAL_FIELDS = ["Telefone", "Empresa", "Nacionalidade"]

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
    periodo: Optional[str] = None,
    futuros_only: Optional[str] = None,
    page: int = 1,
    per_page: int = 12
):
    """List eventos with filters and pagination; switcher defaults to showing future events."""
    redirect = check_admin_session(request)
    if redirect:
        return redirect
    
    db = database.get_database()
    
    # Build query
    query = {}
    
    if busca:
        query["nome"] = {"$regex": busca, "$options": "i"}
    
    if status == "ativo":
        query["ativo"] = True
    elif status == "inativo":
        query["ativo"] = False
    
    # Determine whether to show future events by default (switcher on)
    show_futuros = False
    if periodo == "futuros":
        show_futuros = True
    elif periodo == "passados":
        show_futuros = False
    else:
        # if periodo not explicitly set, use futuros_only param if present; default to True
        if futuros_only is None:
            show_futuros = True
        else:
            show_futuros = (futuros_only == "on")

    if periodo == "passados":
        query["data_evento"] = {"$lt": datetime.now(timezone.utc)}
    elif show_futuros:
        query["data_evento"] = {"$gte": datetime.now(timezone.utc)}
    
    # Pagination
    total = await db.eventos.count_documents(query)
    total_pages = max(1, math.ceil(total / per_page))
    if page < 1:
        page = 1
    if page > total_pages:
        page = total_pages

    eventos = []
    sort_order = 1 if show_futuros else -1
    skip = (page - 1) * per_page
    cursor = db.eventos.find(query).sort("data_evento", sort_order).skip(skip).limit(per_page)
    
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
            "periodo": periodo or "",
            "futuros_only": "on" if show_futuros else "",
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "total_count": total
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
    # Normalize event name for public slug
    try:
        evento_dict["nome_normalizado"] = normalize_event_name(nome)
    except Exception:
        evento_dict["nome_normalizado"] = None
    
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

        # Ensure "Tipo Ingresso" is not treated as a public field (use the select above instead)
        if "Tipo Ingresso" in campos_atual:
            campos_atual = [c for c in campos_atual if c != "Tipo Ingresso"]

        campos_opcionais = [c for c in PLANILHA_OPTIONAL_FIELDS.copy() if c != "Tipo Ingresso"]
        for campo in campos_atual:
            if campo not in PLANILHA_BASE_FIELDS and campo not in campos_opcionais:
                # skip Tipo Ingresso if it somehow appears
                if campo == "Tipo Ingresso":
                    continue
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

        tipos_ingresso = []
        cursor = db.tipos_ingresso.find({"evento_id": evento["id"]})
        async for tipo in cursor:
            tipo["_id"] = str(tipo["_id"])
            tipo["id"] = tipo["_id"]
            tipos_ingresso.append(tipo)

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
                "tipos_ingresso": tipos_ingresso,
                "saved": request.query_params.get("saved") == "1",
                "padrao_error": request.query_params.get("padrao_error") == "1"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/eventos/{evento_id}/planilhas/empresas", response_class=HTMLResponse)
async def admin_evento_planilhas_empresas(request: Request, evento_id: str):
    """Manage company upload links for an event"""
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

        # list existing links
        links_cursor = db.planilha_upload_links.find({"evento_id": evento["id"]})
        links = []
        async for l in links_cursor:
            links.append({"token": l.get("token"), "created": l.get("created_at_display", str(l.get("created_at")) )})

        # Use base_url to build the proper server-rooted URL (request.client.host was client IP)
        url_root = str(request.base_url).rstrip('/')

        return templates.TemplateResponse(
            "admin/evento_upload_links.html",
            {"request": request, "active_page": "eventos", "evento": evento, "links": links, "url_root": url_root}
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/eventos/{evento_id}/planilhas/empresas/generate")
async def admin_evento_planilhas_empresas_generate(request: Request, evento_id: str):
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
    descricao = form.get('descricao')
    token = secrets.token_urlsafe(20)
    created_at = datetime.now(timezone.utc)
    link_doc = {"evento_id": str(object_id), "token": token, "descricao": descricao, "created_at": created_at}
    await db.planilha_upload_links.insert_one(link_doc)

    # If the client expects JSON (AJAX), return JSON with link info; otherwise redirect
    accept = request.headers.get('accept', '')
    if 'application/json' in accept or request.headers.get('x-requested-with', '').lower() == 'xmlhttprequest':
        url_root = str(request.base_url).rstrip('/')
        return JSONResponse({
            'token': token,
            'url': f"{url_root}/upload/{token}",
            'created': created_at.isoformat()
        })

    return RedirectResponse(url=f"/admin/eventos/{evento_id}/planilhas/empresas", status_code=status.HTTP_303_SEE_OTHER)


@router.delete("/eventos/{evento_id}/planilhas/empresas/{token}")
async def admin_evento_planilhas_empresas_delete(request: Request, evento_id: str, token: str):
    """Delete an upload link by token for the given event. Returns JSON for AJAX clients or redirects for browsers."""
    redirect = check_admin_session(request)
    if redirect:
        return redirect
    db = get_database()
    try:
        # Ensure the event exists
        try:
            object_id = ObjectId(evento_id)
        except Exception:
            raise HTTPException(status_code=400, detail="ID de evento inválido")
        evento = await db.eventos.find_one({"_id": object_id})
        if not evento:
            raise HTTPException(status_code=404, detail="Evento não encontrado")

        result = await db.planilha_upload_links.delete_one({"evento_id": str(object_id), "token": token})

        accept = request.headers.get('accept', '')
        if 'application/json' in accept or request.headers.get('x-requested-with', '').lower() == 'xmlhttprequest':
            if result.deleted_count:
                return JSONResponse({"status": "ok", "deleted": True})
            else:
                return JSONResponse({"status": "not_found", "deleted": False}, status_code=404)

        # fallback: redirect back to management page
        return RedirectResponse(url=f"/admin/eventos/{evento_id}/planilhas/empresas", status_code=status.HTTP_303_SEE_OTHER)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/eventos/{evento_id}/planilhas/empresas/{token}/delete")
async def admin_evento_planilhas_empresas_delete_form(request: Request, evento_id: str, token: str):
    """Form-compatible POST endpoint to delete a link (useful for non-AJAX submits)."""
    return await admin_evento_planilhas_empresas_delete(request, evento_id, token)


@router.post("/eventos/{evento_id}/planilhas/campos")
async def admin_evento_planilhas_salvar_campos(request: Request, evento_id: str):
    """Atualiza campos obrigatórios de planilha para o evento.

    Exige que exista um tipo de ingresso marcado como `padrao` para o evento antes de salvar
    as configurações da planilha (requisito solicitado pelo cliente).
    """
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

    # Verifica se existe um tipo de ingresso padrão definido (embutido ou na coleção tipos_ingresso)
    has_padrao = False
    for t in evento.get("tipos_ingresso", []) or []:
        if t.get("padrao"):
            has_padrao = True
            break
    if not has_padrao:
        # procura na coleção legada
        padrao_doc = await db.tipos_ingresso.find_one({"evento_id": str(object_id), "padrao": True})
        if padrao_doc:
            has_padrao = True

    if not has_padrao:
        # redireciona com erro informando que é necessário definir um tipo padrão
        return RedirectResponse(url=f"/admin/eventos/{evento_id}/planilhas?padrao_error=1", status_code=status.HTTP_303_SEE_OTHER)

    form = await request.form()
    selecionados = form.getlist("campos")

    # If admin selected a default ticket type, update tipos_ingresso collection accordingly
    tipo_padrao = form.get('tipo_padrao')
    if tipo_padrao:
        try:
            # clear existing padrao flags for this event
            await db.tipos_ingresso.update_many({"evento_id": str(object_id)}, {"$set": {"padrao": False}})
            # try matching by ObjectId
            from bson import ObjectId as BsonObjectId
            try:
                await db.tipos_ingresso.update_one({"_id": BsonObjectId(tipo_padrao), "evento_id": str(object_id)}, {"$set": {"padrao": True}})
            except Exception:
                # try matching by string id or by numero
                await db.tipos_ingresso.update_one({"_id": tipo_padrao, "evento_id": str(object_id)}, {"$set": {"padrao": True}})
                try:
                    num = int(tipo_padrao)
                    await db.tipos_ingresso.update_one({"numero": num, "evento_id": str(object_id)}, {"$set": {"padrao": True}})
                except Exception:
                    pass
        except Exception:
            pass

    novos_campos = []
    for campo in PLANILHA_BASE_FIELDS:
        if campo not in novos_campos:
            novos_campos.append(campo)

    for campo in selecionados:
        campo_norm = (campo or "").strip()
        # Do not allow Tipo Ingresso to be saved as a public field — it's selected separately
        if campo_norm == "Tipo Ingresso":
            continue
        if campo_norm and campo_norm not in novos_campos:
            novos_campos.append(campo_norm)

    # Handle aceita_inscricoes checkbox
    aceita = 'aceita_inscricoes' in form
    
    await db.eventos.update_one(
        {"_id": object_id},
        {"$set": {
            "campos_obrigatorios_planilha": novos_campos,
            "aceita_inscricoes": aceita
        }}
    )

    return RedirectResponse(
        url=f"/admin/eventos/{evento_id}/planilhas?saved=1",
        status_code=status.HTTP_303_SEE_OTHER
    )


@router.post("/eventos/{evento_id}/planilhas/inscricoes")
async def admin_evento_planilhas_inscricoes(request: Request, evento_id: str):
    """Atualiza ativação de inscrições públicas e token de inscrição"""
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
    aceita = 'aceita_inscricoes' in form
    regenerate = form.get('regenerate') == '1'

    campos = evento.get("campos_obrigatorios_planilha") or []
    required = set(PLANILHA_BASE_FIELDS)
    if aceita and not required.issubset(set(campos)):
        # Não pode ativar inscrições públicas sem os campos base
        return RedirectResponse(url=f"/admin/eventos/{evento_id}/planilhas?insc_error=1", status_code=status.HTTP_303_SEE_OTHER)

    updates = {"aceita_inscricoes": aceita}
    if regenerate or (aceita and not evento.get("token_inscricao")):
        token = secrets.token_urlsafe(24)
        updates["token_inscricao"] = token

    await db.eventos.update_one({"_id": object_id}, {"$set": updates})

    return RedirectResponse(url=f"/admin/eventos/{evento_id}/planilhas?insc_saved=1", status_code=status.HTTP_303_SEE_OTHER)


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


@router.post("/eventos/layout/{evento_id}/preview")
async def admin_evento_layout_preview(
    evento_id: str,
    request: Request,
    dependencies=[Depends(verify_admin_access)]
):
    """Generate preview of ticket layout with fake data"""
    from app.routers.evento_api import _render_layout_to_image
    from io import BytesIO
    
    try:
        data = await request.json()
        layout = data.get("layout_ingresso")
        
        if not layout:
            raise HTTPException(status_code=400, detail="Layout inválido")
        
        # Embed fake data into layout
        from app.utils.layouts import embed_layout
        fake_participante = {
            "nome": "Clausemberg Rodrigues de Oliveira Neto",
            "cpf": "123.456.789-00",
            "email": "teste@example.com"
        }
        fake_tipo = {
            "descricao": "Pista Premium"
        }
        db = get_database()
        evento = await db.eventos.find_one({"_id": ObjectId(evento_id)})
        if not evento:
            raise HTTPException(status_code=404, detail="Evento não encontrado")
        
        fake_ingresso = {
            "qrcode_hash": "PREVIEW123456789",
            "data_emissao": datetime.now()
        }
        
        embedded_layout = embed_layout(layout, fake_participante, fake_tipo, evento, fake_ingresso)
        
        # Render to image
        img = _render_layout_to_image(embedded_layout, dpi=300)
        
        # Return as JPEG
        bio = BytesIO()
        img.save(bio, format='JPEG', quality=90)
        bio.seek(0)
        
        return StreamingResponse(bio, media_type='image/jpeg', headers={"Cache-Control": "no-cache"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
        
        # Load fresh evento doc
        evento_doc = await db.eventos.find_one({"_id": ObjectId(evento_id)})
        try:
            from app.utils.layouts import embed_layout
            # Update standalone ingressos_emitidos and migrate into participantes when possible
            try:
                try:
                    oid = ObjectId(evento_id)
                    filter_or = {"$or": [{"evento_id": evento_id}, {"evento_id": oid}]}
                except Exception:
                    filter_or = {"evento_id": evento_id}

                cursor = db.ingressos_emitidos.find(filter_or)
                async for ingresso in cursor:
                    participante = None
                    tipo = None
                    # fetch participante if referenced
                    pid = ingresso.get('participante_id')
                    if pid:
                        try:
                            participante = await db.participantes.find_one({"_id": ObjectId(pid)})
                        except Exception:
                            participante = await db.participantes.find_one({"_id": pid})
                    # fetch tipo
                    tid = ingresso.get('tipo_ingresso_id')
                    if tid:
                        try:
                            tipo = await db.tipos_ingresso.find_one({"_id": ObjectId(tid)})
                        except Exception:
                            tipo = await db.tipos_ingresso.find_one({"_id": tid})

                    embedded = None
                    try:
                        embedded = embed_layout(layout_ingresso, participante or {}, tipo or {}, evento_doc or {}, ingresso)
                    except Exception:
                        embedded = None

                    # update standalone doc
                    try:
                        if embedded is not None:
                            await db.ingressos_emitidos.update_one({"_id": ingresso.get("_id")}, {"$set": {"layout_ingresso": embedded}})
                    except Exception:
                        pass

                    # migrate into participante if possible, enforcing single ingresso per participant per event
                    if participante is not None:
                        try:
                            # collect existing ingressos for this participant that match the event
                            existing = []
                            for ing in participante.get('ingressos', []):
                                try:
                                    if str(ing.get('evento_id')) == str(evento_id) or (isinstance(ing.get('evento_id'), ObjectId) and str(ing.get('evento_id')) == str(evento_id)):
                                        existing.append(ing)
                                except Exception:
                                    continue

                            if existing:
                                # update the first matching ingresso's layout
                                keep = existing[0]
                                try:
                                    if embedded is not None:
                                        await db.participantes.update_one({"_id": participante.get('_id'), "ingressos._id": keep.get('_id')}, {"$set": {"ingressos.$.layout_ingresso": embedded}})
                                except Exception:
                                    pass
                                # remove additional duplicates (keep the first) to enforce one ingresso per participant per event
                                try:
                                    keep_id = keep.get('_id')
                                    await db.participantes.update_one({"_id": participante.get('_id')}, {"$pull": {"ingressos": {"evento_id": evento_id, "_id": {"$ne": keep_id}}}})
                                except Exception:
                                    pass
                            else:
                                # no existing ingresso for this event, push the migrated one
                                ing_copy = ingresso.copy()
                                if embedded is not None:
                                    ing_copy['layout_ingresso'] = embedded
                                for k in ['_id', 'participante_id', 'tipo_ingresso_id']:
                                    if isinstance(ing_copy.get(k), ObjectId):
                                        ing_copy[k] = str(ing_copy[k])
                                await db.participantes.update_one({"_id": participante.get('_id')}, {"$push": {"ingressos": ing_copy}})
                        except Exception:
                            pass
            except Exception:
                # non-fatal
                pass

            # Update any ingressos already embedded inside participantes
            try:
                p_cursor = db.participantes.find({"ingressos": {"$elemMatch": {"evento_id": evento_id}}})
                async for part in p_cursor:
                    for ing in part.get('ingressos', []):
                        if str(ing.get('evento_id')) != str(evento_id) and not (isinstance(ing.get('evento_id'), ObjectId) and str(ing.get('evento_id')) == str(evento_id)):
                            continue
                        tipo = None
                        try:
                            if ing.get('tipo_ingresso_id'):
                                try:
                                    tipo = await db.tipos_ingresso.find_one({"_id": ObjectId(ing.get('tipo_ingresso_id'))})
                                except Exception:
                                    tipo = await db.tipos_ingresso.find_one({"_id": ing.get('tipo_ingresso_id')})
                        except Exception:
                            tipo = None
                        try:
                            embedded = embed_layout(layout_ingresso, part or {}, tipo or {}, evento_doc or {}, ing)
                            await db.participantes.update_one({"_id": part.get('_id'), "ingressos._id": ing.get('_id')}, {"$set": {"ingressos.$.layout_ingresso": embedded}})
                        except Exception:
                            pass
            except Exception:
                pass
        except Exception:
            # embed_layout not available or other error - continue
            pass

        return JSONResponse({"success": True, "message": "Layout salvo com sucesso"})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Layout Templates
LAYOUT_TEMPLATES = {
    "padrao_vip": {
        "name": "Padrão VIP",
        "canvas": {"width": 62, "height": 120, "orientation": "portrait", "padding": 5, "dpi": 300},
        "elements": [
            {
                "type": "text",
                "x": 31,
                "y": 10,
                "value": "{EVENTO_NOME}",
                "size": 16,
                "font": "Arial",
                "align": "center",
                "bold": True,
                "z_index": 1
            },
            {
                "type": "qrcode",
                "x": 16,
                "y": 35,
                "value": "{qrcode_hash}",
                "size_mm": 30,
                "z_index": 2
            },
            {
                "type": "text",
                "x": 31,
                "y": 75,
                "value": "{NOME}",
                "size": 12,
                "font": "Arial",
                "align": "center",
                "bold": False,
                "z_index": 3
            },
            {
                "type": "text",
                "x": 5,
                "y": 100,
                "value": "{TIPO_INGRESSO}",
                "size": 10,
                "font": "Arial",
                "align": "left",
                "z_index": 4
            },
            {
                "type": "text",
                "x": 57,
                "y": 100,
                "value": "{DATA_EVENTO}",
                "size": 10,
                "font": "Arial",
                "align": "right",
                "z_index": 5
            }
        ]
    },
    "simples": {
        "name": "Simples",
        "canvas": {"width": 62, "height": 100, "orientation": "portrait", "padding": 5, "dpi": 300},
        "elements": [
            {
                "type": "qrcode",
                "x": 16,
                "y": 10,
                "value": "{qrcode_hash}",
                "size_mm": 30,
                "z_index": 1
            },
            {
                "type": "text",
                "x": 31,
                "y": 50,
                "value": "{NOME}",
                "size": 14,
                "font": "Arial",
                "align": "center",
                "bold": True,
                "z_index": 2
            },
            {
                "type": "text",
                "x": 31,
                "y": 70,
                "value": "{TIPO_INGRESSO}",
                "size": 10,
                "font": "Arial",
                "align": "center",
                "z_index": 3
            }
        ]
    }
}


@router.get("/templates/layout", dependencies=[Depends(verify_admin_access)])
async def get_layout_templates():
    """Get available layout templates"""
    return {
        "templates": [
            {"id": key, "name": value["name"]}
            for key, value in LAYOUT_TEMPLATES.items()
        ]
    }


@router.get("/templates/layout/{template_id}", dependencies=[Depends(verify_admin_access)])
async def get_layout_template(template_id: str):
    """Get specific layout template"""
    if template_id not in LAYOUT_TEMPLATES:
        raise HTTPException(status_code=404, detail="Template não encontrado")
    return LAYOUT_TEMPLATES[template_id]


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


# TEMPORARY COMPONENT: Exclusão definitiva via UI
# Este endpoint e o botão de exclusão no template são temporários para facilitar manutenção rápida.
# Remover/reescrever este componente assim que a operação for concluída.
@router.post("/eventos/{evento_id}/delete")
async def admin_evento_deletar(request: Request, evento_id: str):
    """Deleta um evento (via UI administrativa)."""
    redirect = check_admin_session(request)
    if redirect:
        return redirect
    db = get_database()
    try:
        object_id = ObjectId(evento_id)
    except Exception:
        return RedirectResponse(url="/admin/eventos", status_code=status.HTTP_303_SEE_OTHER)
    try:
        await db.eventos.delete_one({"_id": object_id})
    except Exception:
        pass
    return RedirectResponse(url="/admin/eventos", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/eventos/{evento_id}/participantes", response_class=HTMLResponse)
async def admin_evento_participantes(request: Request, evento_id: str, busca: Optional[str] = None, page: int = 1, per_page: int = 20):
    """Lista participantes de um evento com possibilidade de exclusão."""
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
        
        # Build query para buscar participantes com ingressos deste evento
        # Support both string and ObjectId stored evento_id
        base_query = {"$or": [
            {"ingressos.evento_id": evento["id"]},
            {"ingressos.evento_id": ObjectId(evento_id)}
        ]}

        # If a busca term is provided, require both base_query AND match on nome/email/cpf
        if busca:
            search_q = {"$or": [
                {"nome": {"$regex": busca, "$options": "i"}},
                {"email": {"$regex": busca, "$options": "i"}},
                {"cpf": {"$regex": busca, "$options": "i"}}
            ]}
            query = {"$and": [base_query, search_q]}
        else:
            query = base_query

        participantes = []
        # Pagination: try counting matching participants first
        try:
            total_count = await db.participantes.count_documents(query)
        except Exception:
            total_count = 0

        if total_count > 0:
            total_pages = max(1, math.ceil(total_count / per_page))
            if page < 1:
                page = 1
            if page > total_pages:
                page = total_pages
            skip = (page - 1) * per_page
            cursor = db.participantes.find(query).skip(skip).limit(per_page)

            async for doc in cursor:
                ingressos_count = 0
                for ing in doc.get("ingressos", []):
                    if ing.get("evento_id") == evento["id"] or ing.get("evento_id") == ObjectId(evento_id):
                        ingressos_count += 1
                participantes.append({
                    "id": str(doc["_id"]),
                    "nome": doc.get("nome", ""),
                    "email": doc.get("email", ""),
                    "cpf": doc.get("cpf", ""),
                    "ingressos_count": ingressos_count
                })
        else:
            # Diagnostics: log how many found; if none, try legacy collection ingressos_emitidos as fallback
            import logging
            logger = logging.getLogger(__name__)
            logger.info("No participants in participantes collection; checking ingressos_emitidos fallback")
            pids = set()
            try:
                cursor_ing = db.ingressos_emitidos.find({"evento_id": evento["id"]})
                async for ing in cursor_ing:
                    pid = ing.get("participante_id")
                    if pid:
                        pids.add(pid)
            except Exception:
                pass
            try:
                cursor_ing = db.ingressos_emitidos.find({"evento_id": ObjectId(evento_id)})
                async for ing in cursor_ing:
                    pid = ing.get("participante_id")
                    if pid:
                        pids.add(pid)
            except Exception:
                pass

            for pid in pids:
                try:
                    part_doc = await db.participantes.find_one({"_id": ObjectId(pid)})
                except Exception:
                    part_doc = await db.participantes.find_one({"_id": pid})
                if not part_doc:
                    continue
                ingressos_count = 0
                for ing in part_doc.get("ingressos", []):
                    if ing.get("evento_id") == evento["id"] or ing.get("evento_id") == ObjectId(evento_id):
                        ingressos_count += 1
                participantes.append({
                    "id": str(part_doc["_id"]),
                    "nome": part_doc.get("nome", ""),
                    "email": part_doc.get("email", ""),
                    "cpf": part_doc.get("cpf", ""),
                    "ingressos_count": ingressos_count
                })
            logger.info(f"admin_evento_participantes: fallback added {len(participantes)} participants from ingressos_emitidos")

            # paginate in-memory for fallback
            total_count = len(participantes)
            total_pages = max(1, math.ceil(total_count / per_page))
            if page < 1:
                page = 1
            if page > total_pages:
                page = total_pages
            start = (page - 1) * per_page
            participantes = participantes[start:start + per_page]

        # final totals/pagination vars
        try:
            total_pages
        except NameError:
            total_pages = 1
        try:
            total_count
        except NameError:
            total_count = len(participantes)

        return templates.TemplateResponse(
            "admin/evento_participantes.html",
            {
                "request": request,
                "active_page": "eventos",
                "evento": evento,
                "participantes": participantes,
                "total_participantes": total_count,
                "busca": busca or "",
                "page": page,
                "per_page": per_page,
                "total_pages": total_pages,
                "total_count": total_count
            }
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# TEMPORARY COMPONENT: Exclusão de participantes via UI administrativa
@router.post("/eventos/{evento_id}/participantes/{participante_id}/delete")
async def admin_participante_deletar(request: Request, evento_id: str, participante_id: str):
    """Deleta um participante e todos seus ingressos do evento."""
    redirect = check_admin_session(request)
    if redirect:
        return redirect
    
    db = get_database()
    
    try:
        part_oid = ObjectId(participante_id)
    except Exception:
        return RedirectResponse(
            url=f"/admin/eventos/{evento_id}/participantes",
            status_code=status.HTTP_303_SEE_OTHER
        )
    
    try:
        # Remove participante completamente
        await db.participantes.delete_one({"_id": part_oid})
        
        # Remove ingressos da coleção legada se existirem
        await db.ingressos_emitidos.delete_many({"participante_id": participante_id})
    except Exception:
        pass
    
    return RedirectResponse(
        url=f"/admin/eventos/{evento_id}/participantes",
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
