from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import Response
from typing import List, Dict, Any
from datetime import datetime, timezone
from io import BytesIO
from bson import ObjectId
from bson.errors import InvalidId
from bson.int64 import Int64
from app.models.participante import Participante, ParticipanteCreate
from app.models.ingresso_emitido import IngressoEmitido, IngressoEmitidoCreate
import app.config.database as database

def get_database():
    """Runtime indirection to allow tests to monkeypatch `get_database` on this module."""
    return database.get_database()
import logging
from app.config.auth import verify_token_bilheteria, generate_qrcode_hash
from app.utils.validations import validate_cpf, format_datetime_display, normalize_participante_data
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)
router = APIRouter()


def normalize_bson_types(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize BSON types to Python native types for Pydantic compatibility.
    Converts Int64/Long to string, ObjectId to string, empty strings to None.
    """
    if not doc:
        return doc
    
    for key, value in doc.items():
        # Convert ObjectId to string
        if isinstance(value, ObjectId):
            doc[key] = str(value)
        # Check for BSON Long/Int64 by type name (more robust than isinstance)
        elif type(value).__name__ in ('Int64', 'Long') or isinstance(value, Int64):
            # Convert BSON Long/Int64 to string
            doc[key] = str(value)
            logger.debug(f"Converted {key}={value} from {type(value).__name__} to string")
        elif value == '':
            # Convert empty strings to None for Optional fields
            doc[key] = None
        elif isinstance(value, dict):
            # Recursively normalize nested documents
            doc[key] = normalize_bson_types(value)
        elif isinstance(value, list):
            # Normalize items in arrays
            doc[key] = [
                normalize_bson_types(item) if isinstance(item, dict) else 
                str(item) if isinstance(item, ObjectId) else
                str(item) if type(item).__name__ in ('Int64', 'Long') or isinstance(item, Int64) else 
                None if item == '' else
                item
                for item in value
            ]
    
    return doc


class CompatResponse(dict):
    """Compatibility response that supports both dict access and attribute access."""
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)
    def __setattr__(self, name, value):
        self[name] = value


class EmissaoIngressoRequest(BaseModel):
    """Request para emissão de ingresso"""
    tipo_ingresso_id: str
    participante_id: str


# Backwards compatibility alias
EmissaoRequest = EmissaoIngressoRequest


class EmissaoIngressoResponse(BaseModel):
    """Response com ingresso emitido e layout preenchido"""
    ingresso: IngressoEmitido
    layout_preenchido: Dict[str, Any]


class EventoInfo(BaseModel):
    """Informações do evento para o módulo bilheteria"""
    evento_id: str
    nome: str
    descricao: str = None
    data_evento: str
    tipos_ingresso: List[Dict[str, Any]]


@router.get("/evento", response_model=EventoInfo)
async def get_evento_info(
    evento_id: str = Depends(verify_token_bilheteria)
):
    """Retorna informações do evento e tipos de ingresso disponíveis"""
    db = get_database()
    
    # Busca o evento
    evento = await db.eventos.find_one({"_id": ObjectId(evento_id)})
    if not evento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evento não encontrado"
        )
    
    # Preferir tipos embutidos no evento
    tipos_ingresso = []
    tipos_from_evento = evento.get("tipos_ingresso", [])
    if tipos_from_evento:
        for tipo in tipos_from_evento:
            tipos_ingresso.append({
                "tipo_ingresso_id": str(tipo.get("_id") or tipo.get("id") or tipo.get("numero")),
                "descricao": tipo.get("descricao"),
                "valor": tipo.get("valor", 0),
                "permissoes": tipo.get("permissoes", [])
            })
    else:
        cursor = db.tipos_ingresso.find({"evento_id": evento_id})
        async for tipo in cursor:
            tipos_ingresso.append({
                "tipo_ingresso_id": str(tipo["_id"]),
                "descricao": tipo["descricao"],
                "valor": tipo.get("valor", 0),
                "permissoes": tipo.get("permissoes", [])
            })
    
    return EventoInfo(
        evento_id=str(evento["_id"]),
        nome=evento["nome"],
        descricao=evento.get("descricao"),
        data_evento=format_datetime_display(evento["data_evento"]),
        tipos_ingresso=tipos_ingresso
    )


@router.get("/tipos", response_model=List[Dict[str, Any]])
async def get_tipos(evento_id: str = Depends(verify_token_bilheteria)):
    """Retorna os tipos de ingresso disponíveis para o evento (para mobile)."""
    db = get_database()
    # tenta por ObjectId primeiro, mas aceita string também
    try:
        evento = await db.eventos.find_one({"_id": ObjectId(evento_id)})
    except Exception:
        evento = await db.eventos.find_one({"_id": evento_id})

    if not evento:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evento não encontrado")

    tipos = []
    tipos_from_evento = evento.get("tipos_ingresso", [])
    if tipos_from_evento:
        for tipo in tipos_from_evento:
            tipos.append({
                "tipo_ingresso_id": str(tipo.get("_id") or tipo.get("id") or tipo.get("numero")),
                "descricao": tipo.get("descricao"),
                "valor": tipo.get("valor", 0),
                "permissoes": tipo.get("permissoes", [])
            })
    else:
        cursor = db.tipos_ingresso.find({"evento_id": evento_id})
        async for tipo in cursor:
            tipos.append({
                "tipo_ingresso_id": str(tipo["_id"]),
                "descricao": tipo.get("descricao"),
                "valor": tipo.get("valor", 0),
                "permissoes": tipo.get("permissoes", [])
            })

    return tipos


@router.get("/evento/campos-obrigatorios")
async def get_evento_campos_obrigatorios(evento_id: str = Depends(verify_token_bilheteria)):
    """Retorna os campos obrigatórios configurados para o evento (útil para clientes mobile montar UI de cadastro)."""
    db = get_database()
    # tenta por ObjectId primeiro, mas aceita string também
    try:
        evento = await db.eventos.find_one({"_id": ObjectId(evento_id)})
    except Exception:
        evento = await db.eventos.find_one({"_id": evento_id})

    if not evento:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evento não encontrado")

    campos = evento.get("campos_obrigatorios_planilha") or []
    return {"campos_obrigatorios": campos}


@router.post("/participantes", response_model=Participante, status_code=status.HTTP_201_CREATED)
async def criar_participante(
    participante: ParticipanteCreate,
    evento_id: str = Depends(verify_token_bilheteria)
):
    """Cadastro rápido de participantes (botão 'Adicionar Participante').

    Se um evento for fornecido via token, cria também um ingresso usando o tipo
    de ingresso marcado como `padrao` para o evento (requisito solicitado pelo cliente).
    """
    db = get_database()
    
    # Normalize and validate CPF if provided
    from app.utils.validations import validate_cpf
    participante_dict = participante.model_dump()
    if participante_dict.get("cpf"):
        try:
            participante_dict["cpf"] = validate_cpf(participante_dict.get("cpf"))
        except Exception:
            # Let validation errors propagate via model validators where appropriate
            pass
    
    # Normalizar dados antes de inserir (converte ''->None, etc)
    participante_dict = normalize_participante_data(participante_dict)

    # Verifica se já existe participante com este email
    existing = await db.participantes.find_one({"email": participante.email})
    if existing:
        # Retorna o participante existente
        existing["_id"] = str(existing["_id"])
        existing = normalize_bson_types(existing)
        return Participante(**existing)
    
    result = await db.participantes.insert_one(participante_dict)
    
    created_participante = await db.participantes.find_one({"_id": result.inserted_id})
    created_participante["_id"] = str(created_participante["_id"])
    created_participante = normalize_bson_types(created_participante)

    # Se veio um evento via token, tenta emitir ingresso padrão para o participante
    if evento_id:
        try:
            evento = await db.eventos.find_one({"_id": ObjectId(evento_id)})
        except Exception:
            evento = await db.eventos.find_one({"_id": evento_id})

        if evento:
            # procura tipo padrao embutido no evento
            tipo = None
            for t in evento.get("tipos_ingresso", []) or []:
                if t.get("padrao"):
                    tipo = t
                    break
            # fallback: procura na coleção de tipos
            if not tipo:
                tipo = await db.tipos_ingresso.find_one({"evento_id": str(evento.get("_id") or evento_id), "padrao": True})

            if tipo:
                try:
                    # garante CPF único por evento quando possível
                    participante_cpf = created_participante.get("cpf")
                    try:
                        participante_cpf = await _ensure_participante_cpf_unico(db, str(evento.get("_id") or evento_id), created_participante.get("_id"), created_participante)
                    except Exception:
                        # ignore uniqueness enforcement failures here (still create ingresso)
                        participante_cpf = participante_cpf

                    qrcode_hash = generate_qrcode_hash()
                    tipo_id = str(tipo.get("_id") or tipo.get("id") or tipo.get("numero"))

                    ingresso_dict = {
                        "evento_id": str(evento.get("_id") or evento_id),
                        "tipo_ingresso_id": tipo_id,
                        "participante_id": created_participante.get("_id"),
                        "participante_cpf": participante_cpf,
                        "status": "Ativo",
                        "qrcode_hash": qrcode_hash,
                        "data_emissao": datetime.now(timezone.utc)
                    }

                    try:
                        res = await db.ingressos_emitidos.insert_one(ingresso_dict)
                        ingresso_dict["_id"] = res.inserted_id
                    except Exception:
                        pass
                    
                    # Normalizar ingresso antes de embedar (converter ObjectId->str)
                    ingresso_dict = normalize_participante_data(ingresso_dict)

                    # também armazena embutido no participante
                    try:
                        await db.participantes.update_one({"_id": ObjectId(created_participante.get("_id"))}, {"$push": {"ingressos": ingresso_dict}})
                    except Exception:
                        await db.participantes.update_one({"_id": created_participante.get("_id")}, {"$push": {"ingressos": ingresso_dict}})
                except Exception:
                    # não bloquear criação de participante por falha na emissão automática
                    pass

    return Participante(**created_participante)


@router.post("/emitir", response_model=EmissaoIngressoResponse, status_code=status.HTTP_201_CREATED)
async def emitir_ingresso(
    emissao: EmissaoIngressoRequest,
    evento_id: str = Depends(verify_token_bilheteria)
):
    """
    Vincula um participante a um tipo de ingresso, 
    gera o qrcode_hash e retorna o JSON de layout preenchido para impressão
    """
    db = get_database()
    
    # Busca o evento para pegar o layout e tipos embutidos
    evento = await db.eventos.find_one({"_id": ObjectId(evento_id)})
    if not evento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evento não encontrado"
        )

    # Verifica se o tipo de ingresso existe (procura primeiro em evento embutido)
    tipo_ingresso = None
    if evento.get("tipos_ingresso"):
        for t in evento.get("tipos_ingresso", []):
            if str(t.get("_id") or t.get("id")) == emissao.tipo_ingresso_id or str(t.get("numero")) == emissao.tipo_ingresso_id:
                tipo_ingresso = t
                break
    if not tipo_ingresso:
        try:
            tipo_ingresso = await db.tipos_ingresso.find_one({"_id": ObjectId(emissao.tipo_ingresso_id), "evento_id": evento_id})
        except InvalidId:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID de tipo de ingresso inválido"
            )
        if not tipo_ingresso:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tipo de ingresso não encontrado para este evento"
            )

    # Verifica se o participante existe
    try:
        participante = await db.participantes.find_one({"_id": ObjectId(emissao.participante_id)})
        if not participante:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Participante não encontrado"
            )
    except InvalidId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID de participante inválido"
        )
    
    participante_cpf = await _ensure_participante_cpf_unico(
        db,
        evento_id,
        emissao.participante_id,
        participante
    )
    
    # Cria o ingresso
    qrcode_hash = generate_qrcode_hash()

    ingresso_dict = {
        "evento_id": evento_id,
        "tipo_ingresso_id": emissao.tipo_ingresso_id,
        "participante_id": emissao.participante_id,
        "participante_cpf": participante_cpf,
        "status": "Ativo",
        "qrcode_hash": qrcode_hash,
        "data_emissao": datetime.now(timezone.utc)
    }

    # Insere primeiro na coleção antiga para compatibilidade e obter _id
    try:
        res = await db.ingressos_emitidos.insert_one(ingresso_dict)
        ingresso_dict["_id"] = res.inserted_id
    except Exception:
        pass
    
    # Normalizar ingresso antes de embedar (converter ObjectId->str)
    ingresso_dict = normalize_participante_data(ingresso_dict)

    # Também armazena o ingresso embutido dentro do participante (atomic push)
    try:
        await db.participantes.update_one({"_id": ObjectId(emissao.participante_id)}, {"$push": {"ingressos": ingresso_dict}})
    except Exception:
        # fallback se participante._id é string
        await db.participantes.update_one({"_id": emissao.participante_id}, {"$push": {"ingressos": ingresso_dict}})

    # Recupera representação criada (prioriza documento na coleção antiga para compatibilidade)
    created_ingresso = None
    if ingresso_dict.get("_id"):
        created_ingresso = await db.ingressos_emitidos.find_one({"_id": ingresso_dict.get("_id")})
        if created_ingresso:
            created_ingresso["_id"] = str(created_ingresso["_id"])
    if not created_ingresso:
        created_ingresso = ingresso_dict
    
    # Use always the event layout; tipos não possuem layout anymore
    layout_source = evento.get("layout_ingresso")

    # Preenche o layout com os dados (para retorno ao cliente)
    layout_preenchido = preencher_layout(
        layout_source,
        {
            "participante_nome": participante["nome"],
            "qrcode_hash": qrcode_hash,
            "tipo_ingresso": tipo_ingresso["descricao"],
            "evento_nome": evento["nome"],
            "data_evento": format_datetime_display(evento["data_evento"])
        }
    )

    # Also embed the resolved layout into the ingresso document so render uses exact layout stored on the ingresso
    try:
        from app.utils.layouts import embed_layout
        embedded = embed_layout(layout_source, participante, tipo_ingresso, evento, created_ingresso)
        # store as layout_ingresso in the ingresso document
        await db.ingressos_emitidos.update_one({"_id": ObjectId(created_ingresso["_id"])}, {"$set": {"layout_ingresso": embedded}})
        # update the returned object to include layout
        created_ingresso["layout_ingresso"] = embedded
    except Exception:
        # non-fatal: if embedding fails, continue returning the prefilled layout
        pass

    # Normalize created_ingresso _id to string if present
    if created_ingresso and created_ingresso.get("_id"):
        try:
            created_ingresso["_id"] = str(created_ingresso["_id"])
        except Exception:
            pass

    # Return a Pydantic response object so tests calling the function directly can access attributes
    try:
        ingresso_model = IngressoEmitido(**created_ingresso) if isinstance(created_ingresso, dict) else created_ingresso
    except Exception:
        # Fallback: wrap minimal fields
        ingresso_model = IngressoEmitido(**{
            "_id": str(created_ingresso.get("_id")) if created_ingresso and created_ingresso.get("_id") else "",
            "evento_id": ingresso_dict.get("evento_id"),
            "tipo_ingresso_id": ingresso_dict.get("tipo_ingresso_id"),
            "participante_id": ingresso_dict.get("participante_id"),
            "participante_cpf": ingresso_dict.get("participante_cpf"),
            "status": ingresso_dict.get("status"),
            "qrcode_hash": ingresso_dict.get("qrcode_hash"),
            "data_emissao": ingresso_dict.get("data_emissao")
        })

    # Return compatibility response: behaves like dict and object
    resp = CompatResponse({
        "participante_nome": participante["nome"],
        "tipo_ingresso": tipo_ingresso["descricao"],
        "qrcode_hash": qrcode_hash,
        "ingresso": ingresso_model,
        "layout_preenchido": layout_preenchido
    })
    return resp


async def _ensure_participante_cpf_unico(db, evento_id: str, participante_id: str, participante: dict) -> str:
    from app.utils.validations import ensure_cpf_unique
    cpf_raw = participante.get('cpf')
    return await ensure_cpf_unique(db, evento_id, participante_id=participante_id, cpf_raw=cpf_raw)


def preencher_layout(layout: Dict[str, Any], dados: Dict[str, str]) -> Dict[str, Any]:
    """Preenche o template de layout com os dados reais"""
    import json
    layout_str = json.dumps(layout)
    
    for key, value in dados.items():
        layout_str = layout_str.replace(f"{{{key}}}", str(value))
    
    return json.loads(layout_str)


@router.get("/participante/{participante_id}", response_model=Participante)
async def get_participante(
    participante_id: str,
    evento_id: str = Depends(verify_token_bilheteria)
):
    """Obtém um participante específico por ID"""
    db = get_database()
    
    try:
        participante = await db.participantes.find_one({"_id": ObjectId(participante_id)})
        if not participante:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Participante não encontrado"
            )
    except InvalidId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID de participante inválido"
        )
    
    participante["_id"] = str(participante["_id"])
    participante = normalize_bson_types(participante)
    return Participante(**participante)


class ParticipantesListResponse(BaseModel):
    """Response model for paginated participants list"""
    participantes: List[Participante]
    total_count: int
    total_pages: int
    current_page: int
    per_page: int


@router.get("/participantes/list", response_model=ParticipantesListResponse)
async def listar_participantes(
    page: int = 1,
    per_page: int = 20,
    nome: str = None,
    evento_id: str = Depends(verify_token_bilheteria)
):
    """
    Retorna uma lista paginada de participantes do evento.
    
    Query parameters:
    - page: número da página (padrão: 1)
    - per_page: itens por página (padrão: 20, máximo: 100)
    - nome: filtro opcional por nome (case insensitive regex)
    """
    db = get_database()
    
    # Validate and clamp per_page to valid range
    per_page = max(1, min(per_page, 100))
    
    # Validate page number
    if page < 1:
        page = 1
    
    # Build query
    query = {}
    if nome and nome.strip():
        query["nome"] = {"$regex": nome, "$options": "i"}
    
    # Get total count
    total_count = await db.participantes.count_documents(query)
    
    # Calculate total pages
    total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1
    
    # Ensure page is within valid range
    if page > total_pages and total_pages > 0:
        page = total_pages
    
    # Calculate skip
    skip = (page - 1) * per_page
    
    # Fetch participants with pagination
    participantes = []
    cursor = db.participantes.find(query).skip(skip).limit(per_page)
    async for participante in cursor:
        # Ensure _id is a string for the Pydantic model
        participante["_id"] = str(participante.get("_id"))
        # Normalize BSON types (Long/Int64 -> str) to prevent serialization failures
        participante = normalize_bson_types(participante)
        
        # IMPORTANT: Filter ingressos to only include tickets for current event
        # Business rule: A CPF can only have ONE ticket per event
        if participante.get("ingressos"):
            participante["ingressos"] = [
                ing for ing in participante["ingressos"] 
                if ing.get("evento_id") == evento_id
            ]
        
        try:
            participantes.append(Participante(**participante))
        except ValidationError as e:
            # Skip malformed participant documents instead of raising 500
            logger.warning("Skipping invalid participante document (id=%s): %s", participante.get("_id"), e)
            continue
    
    return ParticipantesListResponse(
        participantes=participantes,
        total_count=total_count,
        total_pages=total_pages,
        current_page=page,
        per_page=per_page
    )


@router.get("/participantes/buscar", response_model=List[Participante])
async def buscar_participantes(
    nome: str = None,
    email: str = None,
    cpf: str = None,
    evento_id: str = Depends(verify_token_bilheteria)
):
    """Busca participantes por filtros (nome, email ou CPF)"""
    db = get_database()
    
    query = {}
    if nome:
        query["nome"] = {"$regex": nome, "$options": "i"}
    if email:
        query["email"] = {"$regex": email, "$options": "i"}
    if cpf:
        # normalize CPF filter when possible
        try:
            from app.utils.validations import validate_cpf
            cpf_clean = validate_cpf(cpf)
            query["cpf"] = cpf_clean
        except Exception:
            query["cpf"] = {"$regex": cpf, "$options": "i"}
    
    if not query:
        return []
    
    participantes = []
    cursor = db.participantes.find(query).limit(20)
    async for participante in cursor:
        participante["_id"] = str(participante["_id"])
        participante = normalize_bson_types(participante)
        participantes.append(Participante(**participante))
    
    return participantes


# Capture route function reference so we can provide compatibility wrapper below
buscar_participantes_route = buscar_participantes


@router.get("/busca-credenciamento", response_model=List[Dict[str, Any]])
async def buscar_credenciamento(
    nome: str = None,
    email: str = None,
    evento_id: str = Depends(verify_token_bilheteria)
):
    """
    Busca otimizada por nome/email para reimpressão de credenciais
    """
    db = get_database()
    
    if not nome and not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Informe pelo menos um filtro (nome ou email)"
        )
    
    # Busca participantes
    query = {}
    if nome:
        query["nome"] = {"$regex": nome, "$options": "i"}  # Case insensitive
    if email:
        query["email"] = {"$regex": email, "$options": "i"}
    
    participantes = []
    cursor = db.participantes.find(query).limit(10)
    async for participante in cursor:
        participante_id = str(participante["_id"])
        
        # Busca ingressos embutidos neste participante para este evento (prefere embutido)
        ingressos = []
        for ing in participante.get("ingressos", []):
            if str(ing.get("evento_id")) == str(evento_id):
                # tipo pode vir embutido no evento
                tipo_descr = "Desconhecido"
                # procura em tipos embutidos
                for t in evento.get("tipos_ingresso", []):
                    if str(t.get("_id") or t.get("id")) == str(ing.get("tipo_ingresso_id")) or str(t.get("numero")) == str(ing.get("tipo_ingresso_id")):
                        tipo_descr = t.get("descricao")
                        break
                # fallback para coleção tipos
                if tipo_descr == "Desconhecido":
                    try:
                        tipo = await db.tipos_ingresso.find_one({"_id": ObjectId(ing.get("tipo_ingresso_id"))})
                        tipo_descr = tipo["descricao"] if tipo else tipo_descr
                    except Exception:
                        pass

                ingressos.append({
                    "ingresso_id": str(ing.get("_id") or ing.get("qrcode_hash")),
                    "tipo": tipo_descr,
                    "status": ing.get("status"),
                    "qrcode_hash": ing.get("qrcode_hash"),
                    "data_emissao": ing.get("data_emissao")
                })
        # fallback: se não encontrou nada, consulta coleção antiga
        if not ingressos:
            ingresso_cursor = db.ingressos_emitidos.find({
                "participante_id": participante_id,
                "evento_id": evento_id
            })
            async for ingresso in ingresso_cursor:
                try:
                    tipo = await db.tipos_ingresso.find_one({"_id": ObjectId(ingresso["tipo_ingresso_id"])})
                except Exception:
                    tipo = await db.tipos_ingresso.find_one({"_id": ingresso.get("tipo_ingresso_id")})
                ingressos.append({
                    "ingresso_id": str(ingresso["_id"]),
                    "tipo": tipo["descricao"] if tipo else "Desconhecido",
                    "status": ingresso["status"],
                    "qrcode_hash": ingresso["qrcode_hash"],
                    "data_emissao": ingresso["data_emissao"]
                })
        
        if ingressos:  # Só retorna participantes que têm ingressos neste evento
            participantes.append({
                "participante_id": participante_id,
                "participante": {
                    "nome": participante["nome"],
                    "email": participante.get("email", ""),
                    "telefone": participante.get("telefone", ""),
                    "empresa": participante.get("empresa", "")
                },
                "ingressos": ingressos
            })
    
    return participantes


@router.post("/reimprimir/{ingresso_id}", response_model=EmissaoIngressoResponse)
async def reimprimir_ingresso(
    ingresso_id: str,
    evento_id: str = Depends(verify_token_bilheteria)
):
    """Reimprime um ingresso existente"""
    db = get_database()
    try:
        print(f"reimprimir_ingresso: module database.get_database={database.get_database}")
        print(f"reimprimir_ingresso: module get_database={get_database}")
        print(f"reimprimir_ingresso: db_from_get={db} id={id(db)}")
    except Exception:
        pass
    
    # Tenta localizar ingresso embutido dentro de participantes pelo _id
    ingresso = None
    participante = None  # Initialize to avoid UnboundLocalError
    try:
        participante = await db.participantes.find_one({"ingressos._id": ObjectId(ingresso_id)}, {"ingressos": {"$elemMatch": {"_id": ObjectId(ingresso_id)}}})
        if participante and participante.get("ingressos"):
            ingresso = participante["ingressos"][0]
    except Exception:
        ingresso = None

    # Se não encontrou embutido, fallback para coleção antiga
    if not ingresso:
        # Try to find by ObjectId in the legacy collection first
        try:
            ingresso = await db.ingressos_emitidos.find_one({"_id": ObjectId(ingresso_id), "evento_id": evento_id})
            if not ingresso:
                # If not found by ObjectId, fall through to try qrcode_hash lookup
                ingresso = None
        except InvalidId:
            # ingresso_id is not a valid ObjectId -> try lookup by qrcode_hash instead of returning 400
            ingresso = None

        # If still not found, attempt to resolve by qrcode_hash (support QR contents)
        if not ingresso:
            # look for embedded ingresso in participantes by qrcode_hash
            participante_q = await db.participantes.find_one(
                {"ingressos.qrcode_hash": ingresso_id},
                {"ingressos": {"$elemMatch": {"qrcode_hash": ingresso_id}}}
            )
            if participante_q and participante_q.get("ingressos"):
                ingresso = participante_q["ingressos"][0]
            else:
                # fallback to ingressos_emitidos collection by qrcode_hash
                ingresso = await db.ingressos_emitidos.find_one({"qrcode_hash": ingresso_id, "evento_id": evento_id})
                if not ingresso:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Ingresso não encontrado para este evento"
                    )
    
    # Busca dados relacionados
    # participante pode já estar disponível quando o ingresso é embutido
    if not participante:
        participante = None
        pid = ingresso.get("participante_id")
        if pid:
            try:
                participante = await db.participantes.find_one({"_id": ObjectId(pid)})
            except Exception:
                participante = await db.participantes.find_one({"_id": pid})
        # fallback: search participants by ingressos.qrcode_hash
        if not participante:
            try:
                cursor = db.participantes.find({"ingressos.qrcode_hash": ingresso.get("qrcode_hash")})
                async for p in cursor:
                    participante = p
                    break
            except Exception:
                pass


    evento = await db.eventos.find_one({"_id": ObjectId(evento_id)})
    tipo_ingresso = None
    if evento:
        for t in evento.get("tipos_ingresso", []):
            if str(t.get("_id") or t.get("id")) == str(ingresso.get("tipo_ingresso_id")) or str(t.get("numero")) == str(ingresso.get("tipo_ingresso_id")):
                tipo_ingresso = t
                break
    if not tipo_ingresso:
        try:
            tipo_ingresso = await db.tipos_ingresso.find_one({"_id": ObjectId(ingresso.get("tipo_ingresso_id"))})
        except Exception:
            tipo_ingresso = await db.tipos_ingresso.find_one({"_id": ingresso.get("tipo_ingresso_id")})
    
    # Allow reprint even if participante or tipo_ingresso are missing (use fallbacks)
    if not evento:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro ao buscar dados do ingresso")
    if not participante:
        participante = {"nome": "Desconhecido"}
    if not tipo_ingresso:
        tipo_ingresso = {"descricao": "Desconhecido"}
    
    # Always use event layout for printing/reprinting
    layout_source = evento.get("layout_ingresso")

    # Preenche o layout
    layout_preenchido = preencher_layout(
        layout_source,
        {
            "participante_nome": participante["nome"],
            "qrcode_hash": ingresso["qrcode_hash"],
            "tipo_ingresso": tipo_ingresso["descricao"],
            "evento_nome": evento["nome"],
            "data_evento": format_datetime_display(evento["data_evento"])
        }
    )
    
    ingresso["_id"] = str(ingresso["_id"])
    
    # Return as plain dict for test compatibility
    return {
        "ingresso": ingresso,
        "layout_preenchido": layout_preenchido,
        "qrcode_hash": ingresso.get("qrcode_hash")
    }


# Backwards-compatible wrapper names expected by tests
async def create_participante(participante: ParticipanteCreate, evento_id: str = None):
    """Compat: English-named alias for criar_participante"""
    return await criar_participante(participante, evento_id=evento_id)


async def buscar_participantes_query(query: str = None, evento_id: str = None):
    """Compat: accept a single 'query' parameter and map to nome/email/cpf heuristically"""
    if not query:
        return []
    if "@" in query:
        return await buscar_participantes_route(nome=None, email=query, cpf=None, evento_id=evento_id)
    # simple CPF detection (digits or dots/dashes)
    import re
    if re.search(r"\d", query):
        return await buscar_participantes_route(nome=None, email=None, cpf=query, evento_id=evento_id)
    return await buscar_participantes_route(nome=query, email=None, cpf=None, evento_id=evento_id)

# expose compatibility name
buscar_participantes = buscar_participantes_query


async def busca_credenciamento(query: str = None, evento_id: str = None):
    """Compat: alias for buscar_credenciamento (tests expect this name)"""
    if not query:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Informe pelo menos um filtro (nome ou email)")
    if "@" in query:
        return await buscar_credenciamento(nome=None, email=query, evento_id=evento_id)


@router.get("/render/{qrcode_hash}")
async def render_ingresso_by_qrcode(
    qrcode_hash: str,
    evento_id: str,
    token: str = Depends(verify_token_bilheteria),
    dpi: int = 300
):
    """
    Renderiza ingresso como JPG usando qrcode_hash.
    Endpoint alternativo que funciona com hash ao invés de ObjectId.
    """
    db = get_database()
    
    # Busca ingresso pelo qrcode_hash (embedded ou standalone)
    participante = await db.participantes.find_one(
        {"ingressos.qrcode_hash": qrcode_hash},
        {"ingressos": {"$elemMatch": {"qrcode_hash": qrcode_hash}}, "nome": 1, "email": 1, "cpf": 1}
    )
    
    ingresso = None
    if participante and participante.get("ingressos"):
        ingresso = participante["ingressos"][0]
    else:
        # Fallback para ingressos_emitidos
        ingresso = await db.ingressos_emitidos.find_one(
            {"qrcode_hash": qrcode_hash, "evento_id": evento_id}
        )
    
    if not ingresso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ingresso não encontrado"
        )
    
    # Busca evento para logo_path/logo_blob
    evento = await db.eventos.find_one({"_id": ObjectId(evento_id)})
    logo_path = evento.get("logo_path") if evento else None
    logo_blob = evento.get("logo_blob") if evento else None
    
    # Importa funções de renderização
    from app.routers.evento_api import _get_or_create_embedded_layout, _render_layout_to_image
    
    # Get or create layout
    from_participante = participante is not None
    layout = await _get_or_create_embedded_layout(
        db, ingresso, evento_id, from_participante, participante
    )
    
    # Render to image
    img = _render_layout_to_image(layout, dpi, logo_path=logo_path, logo_blob=logo_blob)
    
    # Serialize to JPEG
    bio = BytesIO()
    img.save(bio, format='JPEG', quality=85)
    bio.seek(0)
    
    return Response(content=bio.read(), media_type="image/jpeg")
    return await buscar_credenciamento(nome=query, email=None, evento_id=evento_id)
