from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from datetime import datetime
from bson import ObjectId
from app.models.evento import Evento, EventoCreate, EventoUpdate
from app.models.ilha import Ilha, IlhaCreate, IlhaUpdate
from app.models.tipo_ingresso import TipoIngresso, TipoIngressoCreate, TipoIngressoUpdate
from app.config.database import get_database
from app.config.auth import verify_admin_access, generate_token
from io import BytesIO
from openpyxl import Workbook
from fastapi.responses import StreamingResponse

router = APIRouter()


# ==================== EVENTOS ====================

@router.get("/eventos", response_model=List[Evento], dependencies=[Depends(verify_admin_access)])
async def list_eventos(skip: int = 0, limit: int = 10):
    """Lista todos os eventos"""
    db = get_database()
    eventos = []
    cursor = db.eventos.find().skip(skip).limit(limit)
    async for document in cursor:
        document["_id"] = str(document["_id"])
        eventos.append(Evento(**document))
    return eventos


@router.get("/eventos/{evento_id}", response_model=Evento, dependencies=[Depends(verify_admin_access)])
async def get_evento(evento_id: str):
    """Obtém um evento específico"""
    db = get_database()
    
    try:
        document = await db.eventos.find_one({"_id": ObjectId(evento_id)})
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID de evento inválido"
        )
    
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evento não encontrado"
        )
    
    document["_id"] = str(document["_id"])
    return Evento(**document)


@router.post("/eventos", response_model=Evento, status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_admin_access)])
async def create_evento(evento: EventoCreate):
    """Cria um novo evento"""
    db = get_database()
    
    evento_dict = evento.model_dump()
    evento_dict["data_criacao"] = datetime.utcnow()
    evento_dict["token_bilheteria"] = generate_token()
    evento_dict["token_portaria"] = generate_token()
    
    result = await db.eventos.insert_one(evento_dict)
    
    created_evento = await db.eventos.find_one({"_id": result.inserted_id})
    created_evento["_id"] = str(created_evento["_id"])
    
    return Evento(**created_evento)


@router.put("/eventos/{evento_id}", response_model=Evento, dependencies=[Depends(verify_admin_access)])
async def update_evento(evento_id: str, evento_update: EventoUpdate):
    """Atualiza um evento existente"""
    db = get_database()
    
    try:
        object_id = ObjectId(evento_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID de evento inválido"
        )
    
    update_data = {k: v for k, v in evento_update.model_dump().items() if v is not None}
    
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nenhum campo para atualizar"
        )
    
    result = await db.eventos.update_one(
        {"_id": object_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evento não encontrado"
        )
    
    updated_evento = await db.eventos.find_one({"_id": object_id})
    updated_evento["_id"] = str(updated_evento["_id"])
    
    return Evento(**updated_evento)


@router.delete("/eventos/{evento_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(verify_admin_access)])
async def delete_evento(evento_id: str):
    """Deleta um evento"""
    db = get_database()
    
    try:
        object_id = ObjectId(evento_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID de evento inválido"
        )
    
    result = await db.eventos.delete_one({"_id": object_id})
    
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evento não encontrado"
        )
    
    return None


# ==================== ILHAS ====================

@router.get("/eventos/{evento_id}/ilhas", response_model=List[Ilha], dependencies=[Depends(verify_admin_access)])
async def list_ilhas(evento_id: str):
    """Lista todas as ilhas de um evento"""
    db = get_database()
    ilhas = []
    cursor = db.ilhas.find({"evento_id": evento_id})
    async for document in cursor:
        document["_id"] = str(document["_id"])
        ilhas.append(Ilha(**document))
    return ilhas


@router.post("/ilhas", response_model=Ilha, status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_admin_access)])
async def create_ilha(ilha: IlhaCreate):
    """Cria uma nova ilha"""
    db = get_database()
    
    # Verifica se o evento existe
    try:
        evento = await db.eventos.find_one({"_id": ObjectId(ilha.evento_id)})
        if not evento:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Evento não encontrado"
            )
    except Exception as e:
        if "not a valid ObjectId" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID de evento inválido"
            )
        raise
    
    ilha_dict = ilha.model_dump()
    result = await db.ilhas.insert_one(ilha_dict)
    
    created_ilha = await db.ilhas.find_one({"_id": result.inserted_id})
    created_ilha["_id"] = str(created_ilha["_id"])
    
    return Ilha(**created_ilha)


@router.put("/ilhas/{ilha_id}", response_model=Ilha, dependencies=[Depends(verify_admin_access)])
async def update_ilha(ilha_id: str, ilha_update: IlhaUpdate):
    """Atualiza uma ilha existente"""
    db = get_database()
    
    try:
        object_id = ObjectId(ilha_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID de ilha inválido"
        )
    
    update_data = {k: v for k, v in ilha_update.model_dump().items() if v is not None}
    
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nenhum campo para atualizar"
        )
    
    result = await db.ilhas.update_one(
        {"_id": object_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ilha não encontrada"
        )
    
    updated_ilha = await db.ilhas.find_one({"_id": object_id})
    updated_ilha["_id"] = str(updated_ilha["_id"])
    
    return Ilha(**updated_ilha)


@router.delete("/ilhas/{ilha_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(verify_admin_access)])
async def delete_ilha(ilha_id: str):
    """Deleta uma ilha"""
    db = get_database()
    
    try:
        object_id = ObjectId(ilha_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID de ilha inválido"
        )
    
    result = await db.ilhas.delete_one({"_id": object_id})
    
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ilha não encontrada"
        )
    
    return None


# ==================== TIPOS DE INGRESSO ====================

@router.get("/eventos/{evento_id}/tipos-ingresso", response_model=List[TipoIngresso], dependencies=[Depends(verify_admin_access)])
async def list_tipos_ingresso(evento_id: str):
    """Lista todos os tipos de ingresso de um evento"""
    db = get_database()
    tipos = []
    cursor = db.tipos_ingresso.find({"evento_id": evento_id})
    async for document in cursor:
        document["_id"] = str(document["_id"])
        tipos.append(TipoIngresso(**document))
    return tipos


@router.post("/tipos-ingresso", response_model=TipoIngresso, status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_admin_access)])
async def create_tipo_ingresso(tipo_ingresso: TipoIngressoCreate):
    """Cria um novo tipo de ingresso"""
    db = get_database()
    
    # Verifica se o evento existe
    try:
        evento = await db.eventos.find_one({"_id": ObjectId(tipo_ingresso.evento_id)})
        if not evento:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Evento não encontrado"
            )
    except Exception as e:
        if "not a valid ObjectId" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID de evento inválido"
            )
        raise
    
    tipo_dict = tipo_ingresso.model_dump()
    result = await db.tipos_ingresso.insert_one(tipo_dict)
    
    created_tipo = await db.tipos_ingresso.find_one({"_id": result.inserted_id})
    created_tipo["_id"] = str(created_tipo["_id"])
    
    return TipoIngresso(**created_tipo)


@router.put("/tipos-ingresso/{tipo_id}", response_model=TipoIngresso, dependencies=[Depends(verify_admin_access)])
async def update_tipo_ingresso(tipo_id: str, tipo_update: TipoIngressoUpdate):
    """Atualiza um tipo de ingresso existente"""
    db = get_database()
    
    try:
        object_id = ObjectId(tipo_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID de tipo de ingresso inválido"
        )
    
    update_data = {k: v for k, v in tipo_update.model_dump().items() if v is not None}
    
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nenhum campo para atualizar"
        )
    
    result = await db.tipos_ingresso.update_one(
        {"_id": object_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tipo de ingresso não encontrado"
        )
    
    updated_tipo = await db.tipos_ingresso.find_one({"_id": object_id})
    updated_tipo["_id"] = str(updated_tipo["_id"])
    
    return TipoIngresso(**updated_tipo)


@router.delete("/tipos-ingresso/{tipo_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(verify_admin_access)])
async def delete_tipo_ingresso(tipo_id: str):
    """Deleta um tipo de ingresso"""
    db = get_database()
    
    try:
        object_id = ObjectId(tipo_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID de tipo de ingresso inválido"
        )
    
    result = await db.tipos_ingresso.delete_one({"_id": object_id})
    
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tipo de ingresso não encontrado"
        )
    
    return None


# ==================== RELATÓRIOS ====================

@router.get("/eventos/{evento_id}/relatorio-vendas", dependencies=[Depends(verify_admin_access)])
async def relatorio_vendas(evento_id: str):
    """Gera relatório de vendas de um evento"""
    db = get_database()
    
    # Verifica se o evento existe
    try:
        evento = await db.eventos.find_one({"_id": ObjectId(evento_id)})
        if not evento:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Evento não encontrado"
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID de evento inválido"
        )
    
    # Conta ingressos emitidos por tipo
    pipeline = [
        {"$match": {"evento_id": evento_id}},
        {"$group": {
            "_id": "$tipo_ingresso_id",
            "quantidade": {"$sum": 1},
            "ativos": {
                "$sum": {"$cond": [{"$eq": ["$status", "Ativo"]}, 1, 0]}
            },
            "cancelados": {
                "$sum": {"$cond": [{"$eq": ["$status", "Cancelado"]}, 1, 0]}
            }
        }}
    ]
    
    vendas_por_tipo = []
    async for doc in db.ingressos_emitidos.aggregate(pipeline):
        # Busca informações do tipo de ingresso
        tipo = await db.tipos_ingresso.find_one({"_id": ObjectId(doc["_id"])})
        vendas_por_tipo.append({
            "tipo_ingresso": tipo["descricao"] if tipo else "Desconhecido",
            "valor": tipo["valor"] if tipo else 0,
            "quantidade_total": doc["quantidade"],
            "ativos": doc["ativos"],
            "cancelados": doc["cancelados"],
            "receita_total": (tipo["valor"] if tipo else 0) * doc["ativos"]
        })
    
    total_vendas = sum(v["quantidade_total"] for v in vendas_por_tipo)
    receita_total = sum(v["receita_total"] for v in vendas_por_tipo)
    
    return {
        "evento": evento["nome"],
        "total_vendas": total_vendas,
        "receita_total": receita_total,
        "detalhes_por_tipo": vendas_por_tipo
    }


@router.get("/eventos/{evento_id}/exportar-leads", dependencies=[Depends(verify_admin_access)])
async def exportar_leads(evento_id: str):
    """Exporta leads do evento em formato XLSX"""
    db = get_database()
    
    # Verifica se o evento existe
    try:
        evento = await db.eventos.find_one({"_id": ObjectId(evento_id)})
        if not evento:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Evento não encontrado"
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID de evento inválido"
        )
    
    # Busca todos os participantes do evento
    participantes_ids = set()
    cursor = db.ingressos_emitidos.find({"evento_id": evento_id})
    async for ingresso in cursor:
        participantes_ids.add(ingresso["participante_id"])
    
    # Cria o workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Leads"
    
    # Cabeçalhos
    ws.append(["Nome", "Email", "Telefone", "Empresa", "Cargo"])
    
    # Dados
    for participante_id in participantes_ids:
        participante = await db.participantes.find_one({"_id": ObjectId(participante_id)})
        if participante:
            ws.append([
                participante.get("nome", ""),
                participante.get("email", ""),
                participante.get("telefone", ""),
                participante.get("empresa", ""),
                participante.get("cargo", "")
            ])
    
    # Salva em memória
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=leads_{evento['nome']}.xlsx"}
    )
