from fastapi import APIRouter, HTTPException, status
from bson import ObjectId
from app.config.database import get_database
from app.models.lead_interacao import LeadInteracao, LeadInteracaoCreate
from datetime import datetime, timezone

router = APIRouter()


@router.post("/coletar", response_model=LeadInteracao, status_code=status.HTTP_201_CREATED)
async def coletar_lead(interacao: LeadInteracaoCreate):
    """
    Lê o QR Code de um participante e salva a interação 
    para posterior exportação pelo organizador
    """
    db = get_database()
    
    # Busca o ingresso pelo QR code
    ingresso = await db.ingressos_emitidos.find_one({
        "qrcode_hash": interacao.qrcode_hash
    })
    
    if not ingresso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="QR Code não encontrado"
        )
    
    # Verifica se o ingresso está ativo
    if ingresso["status"] != "Ativo":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ingresso não está ativo"
        )
    
    # Cria a interação
    interacao_dict = {
        "evento_id": ingresso["evento_id"],
        "participante_id": ingresso["participante_id"],
        "qrcode_hash": interacao.qrcode_hash,
        "data_interacao": datetime.now(timezone.utc),
        "origem": interacao.origem
    }
    
    result = await db.lead_interacoes.insert_one(interacao_dict)
    
    created_interacao = await db.lead_interacoes.find_one({"_id": result.inserted_id})
    created_interacao["_id"] = str(created_interacao["_id"])
    
    return LeadInteracao(**created_interacao)


@router.get("/interacoes/{evento_id}")
async def listar_interacoes(evento_id: str, origem: str = None):
    """Lista todas as interações de um evento, opcionalmente filtradas por origem"""
    db = get_database()
    
    query = {"evento_id": evento_id}
    if origem:
        query["origem"] = origem
    
    interacoes = []
    cursor = db.lead_interacoes.find(query).sort("data_interacao", -1)
    
    async for document in cursor:
        # Busca participante
        try:
            participante = await db.participantes.find_one({"_id": ObjectId(document["participante_id"])})
            participante_info = {
                "nome": participante["nome"] if participante else "Desconhecido",
                "email": participante["email"] if participante else "",
                "empresa": participante.get("empresa", "") if participante else ""
            }
        except:
            participante_info = {"nome": "Desconhecido", "email": "", "empresa": ""}
        
        interacoes.append({
            "id": str(document["_id"]),
            "participante": participante_info,
            "origem": document["origem"],
            "data_interacao": document["data_interacao"]
        })
    
    return interacoes


@router.get("/estatisticas/{evento_id}")
async def estatisticas_leads(evento_id: str):
    """Retorna estatísticas de coleta de leads"""
    db = get_database()
    
    # Total de interações
    total = await db.lead_interacoes.count_documents({"evento_id": evento_id})
    
    # Interações por origem
    pipeline = [
        {"$match": {"evento_id": evento_id}},
        {"$group": {
            "_id": "$origem",
            "total": {"$sum": 1}
        }},
        {"$sort": {"total": -1}}
    ]
    
    por_origem = []
    async for doc in db.lead_interacoes.aggregate(pipeline):
        por_origem.append({
            "origem": doc["_id"],
            "total": doc["total"]
        })
    
    # Participantes únicos
    pipeline_unicos = [
        {"$match": {"evento_id": evento_id}},
        {"$group": {
            "_id": "$participante_id"
        }},
        {"$count": "total"}
    ]
    
    participantes_unicos = 0
    async for doc in db.lead_interacoes.aggregate(pipeline_unicos):
        participantes_unicos = doc["total"]
    
    return {
        "total_interacoes": total,
        "participantes_unicos": participantes_unicos,
        "interacoes_por_origem": por_origem
    }
