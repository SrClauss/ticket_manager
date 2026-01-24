from fastapi import APIRouter, Request, HTTPException, status, Depends, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from datetime import datetime, timedelta, timezone
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
    
    db = database.get_database()
    
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

        url_root = request.url.scheme + "://" + request.client.host

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
    link_doc = {"evento_id": str(object_id), "token": token, "descricao": descricao, "created_at": datetime.now(timezone.utc)}
    await db.planilha_upload_links.insert_one(link_doc)
    return RedirectResponse(url=f"/admin/eventos/{evento_id}/planilhas/empresas", status_code=status.HTTP_303_SEE_OTHER)


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

                    # migrate into participante if possible
                    if participante is not None:
                        try:
                            found = False
                            for ing in participante.get('ingressos', []):
                                if str(ing.get('_id')) == str(ingresso.get('_id')) or ing.get('_id') == ingresso.get('_id'):
                                    found = True
                                    break
                            if not found:
                                ing_copy = ingresso.copy()
                                if embedded is not None:
                                    ing_copy['layout_ingresso'] = embedded
                                for k in ['_id', 'participante_id', 'tipo_ingresso_id']:
                                    if isinstance(ing_copy.get(k), ObjectId):
                                        ing_copy[k] = str(ing_copy[k])
                                await db.participantes.update_one({"_id": participante.get('_id')}, {"$push": {"ingressos": ing_copy}})
                            else:
                                try:
                                    if embedded is not None:
                                        await db.participantes.update_one({"_id": participante.get('_id'), "ingressos._id": ingresso.get('_id')}, {"$set": {"ingressos.$.layout_ingresso": embedded}})
                                except Exception:
                                    pass
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
async def admin_evento_participantes(request: Request, evento_id: str, busca: Optional[str] = None):
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
        cursor = db.participantes.find(query)

        async for doc in cursor:
            # Contar ingressos deste evento (comparo tanto str quanto ObjectId)
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

        # Diagnostics: log how many found; if none, try legacy collection ingressos_emitidos as fallback
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"admin_evento_participantes: found {len(participantes)} participants for evento {evento_id}")

        if not participantes:
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

        return templates.TemplateResponse(
            "admin/evento_participantes.html",
            {
                "request": request,
                "active_page": "eventos",
                "evento": evento,
                "participantes": participantes,
                "total_participantes": len(participantes),
                "busca": busca or ""
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
