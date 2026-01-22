from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Dict, Any
from datetime import datetime, timezone
from bson import ObjectId
from app.models.participante import Participante, ParticipanteCreate
from app.models.ingresso_emitido import IngressoEmitido, IngressoEmitidoCreate
from app.config.database import get_database
from app.config.auth import verify_token_bilheteria, generate_qrcode_hash
from app.utils.validations import validate_cpf
from pydantic import BaseModel

router = APIRouter()


class EmissaoIngressoRequest(BaseModel):
    """Request para emissão de ingresso"""
    tipo_ingresso_id: str
    participante_id: str


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
    
    # Busca tipos de ingresso do evento
    tipos_ingresso = []
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
        data_evento=evento["data_evento"].strftime("%d/%m/%Y %H:%M") if isinstance(evento["data_evento"], datetime) else str(evento["data_evento"]),
        tipos_ingresso=tipos_ingresso
    )


@router.post("/participantes", response_model=Participante, status_code=status.HTTP_201_CREATED)
async def criar_participante(
    participante: ParticipanteCreate,
    evento_id: str = Depends(verify_token_bilheteria)
):
    """Cadastro rápido de participantes (botão 'Adicionar Participante')"""
    db = get_database()
    
    # Verifica se já existe participante com este email
    existing = await db.participantes.find_one({"email": participante.email})
    if existing:
        # Retorna o participante existente
        existing["_id"] = str(existing["_id"])
        return Participante(**existing)
    
    participante_dict = participante.model_dump()
    result = await db.participantes.insert_one(participante_dict)
    
    created_participante = await db.participantes.find_one({"_id": result.inserted_id})
    created_participante["_id"] = str(created_participante["_id"])
    
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
    
    # Verifica se o tipo de ingresso existe e pertence ao evento
    try:
        tipo_ingresso = await db.tipos_ingresso.find_one({
            "_id": ObjectId(emissao.tipo_ingresso_id),
            "evento_id": evento_id
        })
        if not tipo_ingresso:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tipo de ingresso não encontrado para este evento"
            )
    except Exception as e:
        if "not a valid ObjectId" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID de tipo de ingresso inválido"
            )
        raise
    
    # Verifica se o participante existe
    try:
        participante = await db.participantes.find_one({"_id": ObjectId(emissao.participante_id)})
        if not participante:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Participante não encontrado"
            )
    except Exception as e:
        if "not a valid ObjectId" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID de participante inválido"
            )
        raise
    
    participante_cpf = await _ensure_participante_cpf_unico(
        db,
        evento_id,
        emissao.participante_id,
        participante
    )
    
    # Busca o evento para pegar o layout
    evento = await db.eventos.find_one({"_id": ObjectId(evento_id)})
    if not evento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evento não encontrado"
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
    
    result = await db.ingressos_emitidos.insert_one(ingresso_dict)
    
    created_ingresso = await db.ingressos_emitidos.find_one({"_id": result.inserted_id})
    created_ingresso["_id"] = str(created_ingresso["_id"])
    
    # Escolhe o layout do tipo de ingresso se existir, senão usa o layout do evento
    layout_source = tipo_ingresso.get("layout_ingresso") if tipo_ingresso and tipo_ingresso.get("layout_ingresso") else evento.get("layout_ingresso")

    # Preenche o layout com os dados
    layout_preenchido = preencher_layout(
        layout_source,
        {
            "participante_nome": participante["nome"],
            "qrcode_hash": qrcode_hash,
            "tipo_ingresso": tipo_ingresso["descricao"],
            "evento_nome": evento["nome"],
            "data_evento": evento["data_evento"].strftime("%d/%m/%Y %H:%M") if isinstance(evento["data_evento"], datetime) else str(evento["data_evento"])
        }
    )
    
    return EmissaoIngressoResponse(
        ingresso=IngressoEmitido(**created_ingresso),
        layout_preenchido=layout_preenchido
    )


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
    except Exception as e:
        if "not a valid ObjectId" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID de participante inválido"
            )
        raise
    
    participante["_id"] = str(participante["_id"])
    return Participante(**participante)


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
        query["cpf"] = {"$regex": cpf, "$options": "i"}
    
    if not query:
        return []
    
    participantes = []
    cursor = db.participantes.find(query).limit(20)
    async for participante in cursor:
        participante["_id"] = str(participante["_id"])
        participantes.append(Participante(**participante))
    
    return participantes


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
        
        # Busca ingressos deste participante para este evento
        ingressos = []
        ingresso_cursor = db.ingressos_emitidos.find({
            "participante_id": participante_id,
            "evento_id": evento_id
        })
        
        async for ingresso in ingresso_cursor:
            # Busca tipo de ingresso
            tipo = await db.tipos_ingresso.find_one({"_id": ObjectId(ingresso["tipo_ingresso_id"])})
            
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
                "nome": participante["nome"],
                "email": participante["email"],
                "telefone": participante.get("telefone", ""),
                "empresa": participante.get("empresa", ""),
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
    
    # Busca o ingresso
    try:
        ingresso = await db.ingressos_emitidos.find_one({
            "_id": ObjectId(ingresso_id),
            "evento_id": evento_id
        })
        if not ingresso:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ingresso não encontrado para este evento"
            )
    except Exception as e:
        if "not a valid ObjectId" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID de ingresso inválido"
            )
        raise
    
    # Busca dados relacionados
    participante = await db.participantes.find_one({"_id": ObjectId(ingresso["participante_id"])})
    tipo_ingresso = await db.tipos_ingresso.find_one({"_id": ObjectId(ingresso["tipo_ingresso_id"])})
    evento = await db.eventos.find_one({"_id": ObjectId(evento_id)})
    
    if not all([participante, tipo_ingresso, evento]):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao buscar dados do ingresso"
        )
    
    # Escolhe layout do tipo se existir, senão usa o do evento
    layout_source = tipo_ingresso.get("layout_ingresso") if tipo_ingresso and tipo_ingresso.get("layout_ingresso") else evento.get("layout_ingresso")

    # Preenche o layout
    layout_preenchido = preencher_layout(
        layout_source,
        {
            "participante_nome": participante["nome"],
            "qrcode_hash": ingresso["qrcode_hash"],
            "tipo_ingresso": tipo_ingresso["descricao"],
            "evento_nome": evento["nome"],
            "data_evento": evento["data_evento"].strftime("%d/%m/%Y %H:%M") if isinstance(evento["data_evento"], datetime) else str(evento["data_evento"])
        }
    )
    
    ingresso["_id"] = str(ingresso["_id"])
    
    return EmissaoIngressoResponse(
        ingresso=IngressoEmitido(**ingresso),
        layout_preenchido=layout_preenchido
    )
