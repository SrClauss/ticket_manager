"""
Evento Web UI — Login por evento e painel de gestão de participantes.

Aceita tanto o token de bilheteria quanto o token de portaria para autenticação.
As rotas server-side consultam o banco diretamente, independente do tipo de token.
"""
import re
import logging
from fastapi import APIRouter, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from bson import ObjectId
from typing import Optional, Tuple
from datetime import datetime, timezone

import app.config.database as database
from app.utils.validations import validate_cpf, normalize_participante_data, format_datetime_display
from app.routers.bilheteria import normalize_bson_types, _detect_search_type

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
logger = logging.getLogger(__name__)

# Cookie name for evento session
COOKIE_TOKEN = "evento_session_token"

async def _resolve_token(token: str) -> Optional[dict]:
    """Verifica se o token é de bilheteria ou portaria e retorna o documento do evento."""
    db = database.get_database()
    evento = await db.eventos.find_one({"token_bilheteria": token})
    if evento:
        return evento
    evento = await db.eventos.find_one({"token_portaria": token})
    return evento


async def _get_evento_from_cookie(request: Request) -> Optional[Tuple[dict, str]]:
    """Lê o cookie de sessão e retorna (evento_doc, token) ou None."""
    token = request.cookies.get(COOKIE_TOKEN)
    if not token:
        return None
    evento = await _resolve_token(token)
    if not evento:
        return None
    return evento, token


def _evento_id_str(evento: dict) -> str:
    return str(evento["_id"])


def _format_evento_data(evento: dict) -> str:
    try:
        return format_datetime_display(evento.get("data_evento", ""))
    except Exception:
        return str(evento.get("data_evento", ""))


# ── Login ──────────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def evento_login_page(request: Request, error: Optional[str] = None):
    """Página raiz — login por evento (bilheteria ou portaria)."""
    # Se já tem sessão válida, redireciona para o dashboard
    session = await _get_evento_from_cookie(request)
    if session:
        return RedirectResponse(url="/evento/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        "evento/login.html",
        {"request": request, "error": error}
    )


@router.post("/evento/login")
async def evento_login(request: Request, token: str = Form(...)):
    """Processa o login com token de bilheteria ou portaria."""
    token = token.strip()
    evento = await _resolve_token(token)
    if not evento:
        return templates.TemplateResponse(
            "evento/login.html",
            {"request": request, "error": "Token inválido. Verifique o token de acesso do evento."},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    response = RedirectResponse(url="/evento/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key=COOKIE_TOKEN,
        value=token,
        httponly=True,
        max_age=86400,  # 24 horas
        samesite="lax",
    )
    return response


@router.get("/evento/logout")
async def evento_logout():
    """Encerra a sessão do evento."""
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(COOKIE_TOKEN)
    return response


# ── Dashboard ──────────────────────────────────────────────────────────────────

@router.get("/evento/dashboard", response_class=HTMLResponse)
async def evento_dashboard(request: Request):
    """Dashboard principal: métricas e lista de participantes."""
    session = await _get_evento_from_cookie(request)
    if not session:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    evento, token = session
    return templates.TemplateResponse(
        "evento/dashboard.html",
        {
            "request": request,
            "evento_nome": evento.get("nome", "Evento"),
            "evento_data": _format_evento_data(evento),
            "active_page": "dashboard",
            "evento_id": str(evento.get("_id")),
        },
    )


# ── Internal JSON API (cookie-auth, independent of token type) ─────────────────

@router.get("/evento/api/ilhas")
async def evento_api_ilhas(request: Request):
    """Lista ilhas do evento (autenticado por cookie)."""
    session = await _get_evento_from_cookie(request)
    if not session:
        return JSONResponse({"detail": "Não autenticado"}, status_code=401)
    evento, _ = session
    evento_id = _evento_id_str(evento)
    db = database.get_database()

    ilhas = []
    if evento.get("ilhas"):
        for ilha in evento.get("ilhas", []):
            ilhas.append({
                "ilha_id": str(ilha.get("_id") or ilha.get("id")),
                "nome_setor": ilha.get("nome_setor"),
                "capacidade_maxima": ilha.get("capacidade_maxima", 0),
            })
    else:
        cursor = db.ilhas.find({"evento_id": evento_id})
        async for ilha in cursor:
            ilhas.append({
                "ilha_id": str(ilha["_id"]),
                "nome_setor": ilha.get("nome_setor"),
                "capacidade_maxima": ilha.get("capacidade_maxima", 0),
            })
    return JSONResponse({"ilhas": ilhas})


@router.get("/evento/api/ingressos/metrics")
async def evento_api_ingresso_metrics(request: Request):
    """Retorna métricas dos ingressos emitidos para o evento.

    O JSON de retorno contém duas listas:
    - ``tipo_metrics``: agregação por tipo de ingresso (total/impressos)
    - ``ilha_metrics``: capacidade e ingressos vendidos por ilha/setor
    """
    session = await _get_evento_from_cookie(request)
    if not session:
        return JSONResponse({"detail": "Não autenticado"}, status_code=401)
    evento, _ = session
    evento_id = _evento_id_str(evento)
    db = database.get_database()

    # --- metrics por tipo ---
    pipeline = [
        {"$match": {"evento_id": evento_id}},
        {"$group": {
            "_id": "$tipo_ingresso_id",
            "total": {"$sum": 1},
            "printed": {"$sum": {"$cond": [{"$eq": ["$impresso", True]}, 1, 0]}}
        }}
    ]
    tipo_metrics = await db.ingressos_emitidos.aggregate(pipeline).to_list(length=None)
    # attach names and normalize ids
    for doc in tipo_metrics:
        tipo = await db.tipos_ingresso.find_one({"_id": ObjectId(doc["_id"])})
        doc["tipo_nome"] = tipo.get("nome") if tipo else None
        doc["tipo_id"] = str(doc["_id"])
        doc.pop("_id", None)

    # --- metrics por ilha ---
    # gather ilhas for event
    ilhas = []
    async for i in db.ilhas.find({"evento_id": evento_id}):
        ilhas.append(i)
    # build map of tipo -> permissoes (list of ilha ids)
    tipo_perms = {}
    async for t in db.tipos_ingresso.find({"evento_id": evento_id}):
        tipo_perms[str(t.get("_id"))] = t.get("permissoes", [])
    
    # count sold tickets per ilha usando ingressos embedded em participantes
    sold = {str(i.get("_id")): 0 for i in ilhas}
    
    # Agregação para contar ingressos por tipo do evento
    pipeline = [
        {"$match": {"ingressos.evento_id": evento_id}},
        {"$unwind": "$ingressos"},
        {"$match": {"ingressos.evento_id": evento_id}},
        {"$group": {"_id": "$ingressos.tipo_ingresso_id", "count": {"$sum": 1}}}
    ]
    
    async for result in db.participantes.aggregate(pipeline):
        tipo_id = str(result["_id"])
        count = result["count"]
        for ilha_id in tipo_perms.get(tipo_id, []):
            if ilha_id in sold:
                sold[ilha_id] += count
    ilha_metrics = []
    for i in ilhas:
        ilha_metrics.append({
            "ilha_id": str(i.get("_id")),
            "nome_setor": i.get("nome_setor"),
            "capacidade": i.get("capacidade_maxima", 0),
            "vendidos": sold.get(str(i.get("_id")), 0),
        })

    return JSONResponse({"tipo_metrics": tipo_metrics, "ilha_metrics": ilha_metrics})


@router.get("/evento/api/ilhas/{ilha_id}/stats")
async def evento_api_ilha_stats(request: Request, ilha_id: str):
    """Estatísticas de uma ilha (autenticado por cookie)."""
    session = await _get_evento_from_cookie(request)
    if not session:
        return JSONResponse({"detail": "Não autenticado"}, status_code=401)
    evento, _ = session
    evento_id = _evento_id_str(evento)
    db = database.get_database()

    capacidade = None
    if evento.get("ilhas"):
        for ilh in evento.get("ilhas", []):
            if str(ilh.get("_id") or ilh.get("id")) == ilha_id:
                capacidade = ilh.get("capacidade_maxima", 0)
                break
    if capacidade is None:
        try:
            ilh = await db.ilhas.find_one({"_id": ObjectId(ilha_id)})
        except Exception:
            ilh = None
        if ilh:
            capacidade = ilh.get("capacidade_maxima", 0)
    if capacidade is None:
        return JSONResponse({"detail": "Ilha não encontrada"}, status_code=404)

    from app.routers.bilheteria import _count_ingressos_affecting_ilha
    total = await _count_ingressos_affecting_ilha(db, evento_id, ilha_id)
    return JSONResponse({"ilha_id": ilha_id, "capacidade_maxima": capacidade, "ingressos_emitidos": total})


@router.get("/evento/api/participantes")
async def evento_api_participantes(request: Request, page: int = 1, per_page: int = 20):
    """Lista paginada de participantes do evento (autenticado por cookie), ordenada por nome."""
    session = await _get_evento_from_cookie(request)
    if not session:
        return JSONResponse({"detail": "Não autenticado"}, status_code=401)
    evento, _ = session
    evento_id = _evento_id_str(evento)
    db = database.get_database()

    per_page = max(1, min(per_page, 100))
    if page < 1:
        page = 1

    # Filtra participantes que possuem ingressos neste evento
    pipeline = [
        {"$match": {"ingressos.evento_id": evento_id}},
        {"$sort": {"nome": 1}},
        {"$facet": {
            "total": [{"$count": "count"}],
            "data": [{"$skip": (page - 1) * per_page}, {"$limit": per_page}],
        }},
    ]
    result = await db.participantes.aggregate(pipeline).to_list(length=1)
    total_count = 0
    docs = []
    if result:
        total_count = (result[0].get("total") or [{}])[0].get("count", 0)
        docs = result[0].get("data", [])

    # Fallback: se não há ingressos embutidos, lista todos ordenados por nome
    if total_count == 0:
        total_count = await db.participantes.count_documents({})
        total_pages = max(1, (total_count + per_page - 1) // per_page)
        skip = (page - 1) * per_page
        cursor = db.participantes.find({}).sort("nome", 1).skip(skip).limit(per_page)
        docs = await cursor.to_list(length=per_page)

    total_pages = max(1, (total_count + per_page - 1) // per_page)

    participantes = []
    for p in docs:
        p["_id"] = str(p.get("_id"))
        p = normalize_bson_types(p)
        if p.get("ingressos"):
            # Filtra ingressos deste evento e normaliza cada ingresso
            filtered_ingressos = []
            for ing in p["ingressos"]:
                if ing.get("evento_id") == evento_id:
                    # DEBUG: Log do valor impresso ANTES da normalização
                    impresso_original = ing.get("impresso")
                    print(f"[BACKEND-LOAD] Ingresso {ing.get('_id')}: impresso_original={impresso_original}, tipo={type(impresso_original)}, 'impresso' in ing={('impresso' in ing)}")
                    
                    # Garante que _id do ingresso é string
                    if ing.get("_id") and not isinstance(ing["_id"], str):
                        ing["_id"] = str(ing["_id"])
                    # Normaliza campo impresso como booleano
                    impresso = ing.get("impresso")
                    if impresso is None or impresso == "":
                        ing["impresso"] = False
                    elif isinstance(impresso, str):
                        ing["impresso"] = impresso.lower() in ("true", "1", "yes")
                    else:
                        ing["impresso"] = bool(impresso)
                    
                    print(f"[BACKEND-LOAD] Ingresso {ing.get('_id')}: impresso_normalizado={ing['impresso']}")
                    filtered_ingressos.append(ing)
            p["ingressos"] = filtered_ingressos
        participantes.append(p)

    return JSONResponse({
        "participantes": participantes,
        "total_count": total_count,
        "total_pages": total_pages,
        "current_page": page,
        "per_page": per_page,
    })


@router.get("/evento/api/participantes/busca-smart")
async def evento_api_busca_smart(request: Request, q: str = ""):
    """Busca inteligente de participantes por CPF, nome, empresa, tipo de ingresso ou token.

    Autenticado por cookie (evento)."""
    session = await _get_evento_from_cookie(request)
    if not session:
        return JSONResponse({"detail": "Não autenticado"}, status_code=401)
    if not q.strip():
        return JSONResponse([])
    evento, _ = session
    evento_id = _evento_id_str(evento)
    db = database.get_database()

    tipo = _detect_search_type(q)
    participantes = []

    if tipo == "cpf":
        try:
            cpf_clean = validate_cpf(q)
            query = {"cpf": cpf_clean}
        except Exception:
            digits = re.sub(r"\D", "", q)
            query = {"cpf": {"$regex": digits, "$options": "i"}}
        # only participants with an ingresso for this evento
        query["ingressos.evento_id"] = evento_id
        cursor = db.participantes.find(query).limit(20)
        async for p in cursor:
            p["_id"] = str(p["_id"])
            p = normalize_bson_types(p)
            if p.get("ingressos"):
                filtered_ingressos = []
                for ing in p["ingressos"]:
                    if ing.get("evento_id") == evento_id:
                        # DEBUG: Log do valor impresso ANTES da normalização
                        impresso_original = ing.get("impresso")
                        print(f"[BACKEND-SEARCH-CPF] Ingresso {ing.get('_id')}: impresso_original={impresso_original}, tipo={type(impresso_original)}, 'impresso' in ing={('impresso' in ing)}")
                        
                        # Normaliza campo impresso como booleano
                        impresso = ing.get("impresso")
                        if impresso is None or impresso == "":
                            ing["impresso"] = False
                        elif isinstance(impresso, str):
                            ing["impresso"] = impresso.lower() in ("true", "1", "yes")
                        else:
                            ing["impresso"] = bool(impresso)
                        
                        print(f"[BACKEND-SEARCH-CPF] Ingresso {ing.get('_id')}: impresso_normalizado={ing['impresso']}")
                        filtered_ingressos.append(ing)
                p["ingressos"] = filtered_ingressos
            # append only if there remains at least one ingresso
            if p.get("ingressos"):
                participantes.append(p)

    elif tipo == "token":
        qrcode_hash = q.strip()
        p_doc = await db.participantes.find_one(
            {"ingressos.qrcode_hash": qrcode_hash, "ingressos.evento_id": evento_id},
            {"ingressos": {"$elemMatch": {"qrcode_hash": qrcode_hash, "evento_id": evento_id}}},
        )
        
        if p_doc:
            p_doc["_id"] = str(p_doc["_id"])
            p_doc = normalize_bson_types(p_doc)
            if p_doc.get("ingressos"):
                filtered_ingressos = []
                for ing in p_doc.get("ingressos", []):
                    if ing.get("evento_id") == evento_id:
                        # Normaliza campo impresso como booleano
                        impresso = ing.get("impresso")
                        if impresso is None or impresso == "":
                            ing["impresso"] = False
                        elif isinstance(impresso, str):
                            ing["impresso"] = impresso.lower() in ("true", "1", "yes")
                        else:
                            ing["impresso"] = bool(impresso)
                        filtered_ingressos.append(ing)
                p_doc["ingressos"] = filtered_ingressos
            participantes.append(p_doc)

    else:
        # texto livre: nome/email/empresa ou tipo_ingresso
        regex = {"$regex": q, "$options": "i"}
        # buscar tipos que correspondam
        tipo_ids = []
        async for t in db.tipos_ingresso.find({"nome": regex}):
            tipo_ids.append(str(t.get("_id")))
        or_clauses = [{"nome": regex}, {"email": regex}, {"empresa": regex}, {"cpf": regex}]
        if tipo_ids:
            or_clauses.append({"ingressos.tipo_ingresso_id": {"$in": tipo_ids}})
        # require at least one ingresso for this evento in the query results
        query = {"$and": [{"ingressos.evento_id": evento_id}, {"$or": or_clauses}]}
        cursor = db.participantes.find(query).limit(20)
        async for p in cursor:
            p["_id"] = str(p["_id"])
            p = normalize_bson_types(p)
            if p.get("ingressos"):
                filtered_ingressos = []
                for ing in p["ingressos"]:
                    if ing.get("evento_id") == evento_id:
                        # Normaliza campo impresso como booleano
                        impresso = ing.get("impresso")
                        if impresso is None or impresso == "":
                            ing["impresso"] = False
                        elif isinstance(impresso, str):
                            ing["impresso"] = impresso.lower() in ("true", "1", "yes")
                        else:
                            ing["impresso"] = bool(impresso)
                        filtered_ingressos.append(ing)
                p["ingressos"] = filtered_ingressos
            if p.get("ingressos"):
                participantes.append(p)
    return JSONResponse(participantes)


# ── Participante Edit ──────────────────────────────────────────────────────────

@router.get("/evento/participante/{participante_id}/editar", response_class=HTMLResponse)
async def evento_participante_editar_page(request: Request, participante_id: str):
    """Página de edição de dados do participante."""
    session = await _get_evento_from_cookie(request)
    if not session:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    evento, token = session
    evento_id = _evento_id_str(evento)

    db = database.get_database()
    try:
        participante = await db.participantes.find_one({"_id": ObjectId(participante_id)})
    except Exception:
        participante = await db.participantes.find_one({"_id": participante_id})

    if not participante:
        return RedirectResponse(url="/evento/dashboard", status_code=status.HTTP_303_SEE_OTHER)

    participante["_id"] = str(participante["_id"])
    participante = normalize_bson_types(participante)
    participante["id"] = participante["_id"]

    ingressos = await _get_participante_ingressos(db, participante_id, evento_id, evento)

    return templates.TemplateResponse(
        "evento/participante_editar.html",
        {
            "request": request,
            "participante": participante,
            "ingressos": ingressos,
            "evento_nome": evento.get("nome", "Evento"),
            "active_page": "dashboard",
        },
    )


@router.post("/evento/participante/{participante_id}/editar")
async def evento_participante_editar_save(
    request: Request,
    participante_id: str,
    nome: str = Form(...),
    email: str = Form(...),
    cpf: str = Form(...),
    telefone: str = Form(""),
    empresa: str = Form(""),
    nacionalidade: str = Form(""),
):
    """Salva as alterações do participante."""
    session = await _get_evento_from_cookie(request)
    if not session:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    evento, token = session
    evento_id = _evento_id_str(evento)

    db = database.get_database()
    error = None

    # Normaliza CPF
    try:
        cpf_clean = validate_cpf(cpf)
    except Exception as e:
        cpf_clean = None
        error = f"CPF inválido: {e}"

    if not error:
        update_data = {
            "nome": nome.strip(),
            "email": email.strip(),
            "cpf": cpf_clean,
            "telefone": telefone.strip() or None,
            "empresa": empresa.strip() or None,
            "nacionalidade": nacionalidade.strip() or None,
        }
        # Remove None values
        update_data = {k: v for k, v in update_data.items() if v is not None}
        try:
            await db.participantes.update_one(
                {"_id": ObjectId(participante_id)},
                {"$set": update_data},
            )
        except Exception as exc:
            error = f"Erro ao salvar: {exc}"

    # Reload participant for rendering
    try:
        participante = await db.participantes.find_one({"_id": ObjectId(participante_id)})
    except Exception:
        participante = await db.participantes.find_one({"_id": participante_id})

    if not participante:
        return RedirectResponse(url="/evento/dashboard", status_code=status.HTTP_303_SEE_OTHER)

    participante["_id"] = str(participante["_id"])
    participante = normalize_bson_types(participante)
    participante["id"] = participante["_id"]

    ingressos = await _get_participante_ingressos(db, participante_id, evento_id, evento)

    return templates.TemplateResponse(
        "evento/participante_editar.html",
        {
            "request": request,
            "participante": participante,
            "ingressos": ingressos,
            "evento_nome": evento.get("nome", "Evento"),
            "active_page": "dashboard",
            "success": error is None,
            "error": error,
        },
    )



# ── Tipos de Ingresso ──────────────────────────────────────────────────────────

async def _get_tipos_ingresso(db, evento: dict) -> list:
    """Retorna os tipos de ingresso do evento como lista de dicts {id, descricao}."""
    tipos = []
    # allow calling without a real database (e.g. during unit tests)
    if db is None:
        return tipos

    if evento.get("tipos_ingresso"):
        for t in evento.get("tipos_ingresso", []):
            tipos.append({
                "id": str(t.get("_id") or t.get("id") or t.get("numero", "")),
                "descricao": t.get("descricao", "Ingresso"),
            })
    else:
        evento_id = _evento_id_str(evento)
        cursor = db.tipos_ingresso.find({"evento_id": evento_id})
        async for t in cursor:
            tipos.append({
                "id": str(t["_id"]),
                "descricao": t.get("descricao", "Ingresso"),
            })
    return tipos


@router.get("/evento/api/tipos-ingresso")
async def evento_api_tipos_ingresso(request: Request):
    """Lista os tipos de ingresso do evento (autenticado por cookie)."""
    session = await _get_evento_from_cookie(request)
    if not session:
        return JSONResponse({"detail": "Não autenticado"}, status_code=401)
    evento, _ = session
    db = database.get_database()
    tipos = await _get_tipos_ingresso(db, evento)
    return JSONResponse({"tipos_ingresso": tipos})


@router.get("/evento/participante/novo", response_class=HTMLResponse)
async def evento_participante_novo_page(request: Request):
    """Página de cadastro de novo participante."""
    session = await _get_evento_from_cookie(request)
    if not session:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    evento, _ = session
    db = database.get_database()
    tipos = await _get_tipos_ingresso(db, evento)

    # determine which fields are required according to event settings
    campos = evento.get("campos_obrigatorios_planilha", []) or []
    # always include the base fields so form makes sense
    base = {"Nome", "Email", "CPF"}
    required_fields = list(set(campos) | base)

    return templates.TemplateResponse(
        "evento/participante_novo.html",
        {
            "request": request,
            "tipos_ingresso": tipos,
            "evento_nome": evento.get("nome", "Evento"),
            "active_page": "dashboard",
            "required_fields": required_fields,
        },
    )


@router.post("/evento/participante/novo")
async def evento_participante_novo_save(
    request: Request,
    nome: str = Form(...),
    email: str = Form(...),
    cpf: str = Form(...),
    telefone: str = Form(""),
    empresa: str = Form(""),
    nacionalidade: str = Form(""),
    tipo_ingresso_id: str = Form(""),
):
    """Cria um novo participante e emite ingresso opcional."""
    session = await _get_evento_from_cookie(request)
    if not session:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    evento, _ = session
    evento_id = _evento_id_str(evento)
    db = database.get_database()

    error = None
    cpf_clean = None
    try:
        cpf_clean = validate_cpf(cpf)
    except Exception as e:
        error = f"CPF inválido: {e}"

    participante_id = None
    if not error:
        participante_dict = {
            "nome": nome.strip(),
            "email": email.strip(),
            "cpf": cpf_clean,
            "telefone": telefone.strip() or None,
            "empresa": empresa.strip() or None,
            "nacionalidade": nacionalidade.strip() or None,
        }
        existing = await db.participantes.find_one({"email": participante_dict["email"]})
        if existing:
            participante_id = str(existing["_id"])
        else:
            result = await db.participantes.insert_one(participante_dict)
            participante_id = str(result.inserted_id)

    if not error and tipo_ingresso_id.strip() and participante_id:
        from app.config.auth import generate_qrcode_hash
        qrcode_hash = generate_qrcode_hash()
        ingresso_dict = {
            "evento_id": evento_id,
            "tipo_ingresso_id": tipo_ingresso_id.strip(),
            "participante_id": participante_id,
            "participante_cpf": cpf_clean,
            "status": "Ativo",
            "qrcode_hash": qrcode_hash,
            "data_emissao": datetime.now(timezone.utc).isoformat(),
        }
        try:
            await db.ingressos_emitidos.insert_one(dict(ingresso_dict))
        except Exception as exc:
            logger.error("Erro ao inserir ingresso em ingressos_emitidos: %s", exc)
            error = "Erro ao emitir ingresso. Participante cadastrado, mas ingresso não emitido."
        if not error:
            try:
                await db.participantes.update_one(
                    {"_id": ObjectId(participante_id)},
                    {"$push": {"ingressos": ingresso_dict}},
                )
            except Exception as exc:
                logger.error("Erro ao embedar ingresso no participante: %s", exc)

    tipos = await _get_tipos_ingresso(db, evento)

    if error:
        return templates.TemplateResponse(
            "evento/participante_novo.html",
            {
                "request": request,
                "tipos_ingresso": tipos,
                "evento_nome": evento.get("nome", "Evento"),
                "active_page": "dashboard",
                "error": error,
            },
        )

    if participante_id:
        return RedirectResponse(
            url=f"/evento/participante/{participante_id}/editar",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    return RedirectResponse(url="/evento/dashboard", status_code=status.HTTP_303_SEE_OTHER)


# ── Internal helpers ───────────────────────────────────────────────────────────

async def _get_participante_ingressos(db, participante_id: str, evento_id: str, evento: dict) -> list:
    """Retorna os ingressos do participante para o evento, com descrição do tipo."""
    ingressos = []

    try:
        p = await db.participantes.find_one({"_id": ObjectId(participante_id)}, {"ingressos": 1})
    except Exception:
        p = await db.participantes.find_one({"_id": participante_id}, {"ingressos": 1})

    embedded = []
    if p:
        embedded = [ing for ing in (p.get("ingressos") or []) if str(ing.get("evento_id")) == str(evento_id)]

    for ing in embedded:
        tipo_descr = _resolve_tipo_descricao(ing.get("tipo_ingresso_id"), evento)
        ingressos.append({
            "qrcode_hash": ing.get("qrcode_hash", ""),
            "status": ing.get("status", ""),
            "tipo_descricao": tipo_descr,
        })

    return ingressos


def _resolve_tipo_descricao(tipo_ingresso_id, evento: dict) -> str:
    """Tenta resolver a descrição do tipo de ingresso a partir dos dados embutidos no evento."""
    if not tipo_ingresso_id:
        return "Ingresso"
    tid = str(tipo_ingresso_id)
    for t in (evento.get("tipos_ingresso") or []):
        if str(t.get("_id") or t.get("id") or t.get("numero")) == tid:
            return t.get("descricao", "Ingresso")
    return "Ingresso"
