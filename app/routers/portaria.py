from fastapi import APIRouter, HTTPException, status, Depends
from bson import ObjectId
from bson.errors import InvalidId
from app.config.database import get_database
from app.config.auth import verify_token_portaria
from app.utils.validations import format_datetime_display
from pydantic import BaseModel
from datetime import datetime, timezone
from typing import Optional

router = APIRouter()


class ValidacaoRequest(BaseModel):
    """Request para validação de QR code"""
    qrcode_hash: str
    ilha_id: str


class ValidacaoResponse(BaseModel):
    """Response da validação"""
    status: str  # "OK" ou "NEGADO"
    mensagem: str
    participante_nome: str = None
    tipo_ingresso: str = None


class IngressoDetalhes(BaseModel):
    """Detalhes completos de um ingresso"""
    ingresso_id: str
    participante_nome: str
    participante_email: Optional[str] = None
    participante_telefone: Optional[str] = None
    tipo_ingresso: str
    evento_nome: str
    status: str
    qrcode_hash: str
    data_emissao: datetime
    permissoes: list  # Lista de IDs de ilhas permitidas


class EventoInfoPortaria(BaseModel):
    """Informações do evento para o módulo portaria"""
    evento_id: str
    nome: str
    descricao: Optional[str] = None
    data_evento: str


@router.get("/evento", response_model=EventoInfoPortaria)
async def get_evento_info(
    evento_id: str = Depends(verify_token_portaria)
):
    """Retorna informações do evento para o módulo portaria"""
    db = get_database()
    
    # Busca o evento
    evento = await db.eventos.find_one({"_id": ObjectId(evento_id)})
    if not evento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evento não encontrado"
        )
    
    return EventoInfoPortaria(
        evento_id=str(evento["_id"]),
        nome=evento["nome"],
        descricao=evento.get("descricao"),
        data_evento=format_datetime_display(evento["data_evento"])
    )


@router.get("/ingresso/{qrcode_hash}", response_model=IngressoDetalhes)
async def get_ingresso_by_qrcode(
    qrcode_hash: str,
    evento_id: str = Depends(verify_token_portaria)
):
    """
    Obtém detalhes completos de um ingresso pelo QR code hash
    Útil para o módulo de portaria mostrar informações do ingresso antes da validação
    """
    db = get_database()
    
    # Busca o ingresso pelo QR code
    ingresso = await db.ingressos_emitidos.find_one({
        "qrcode_hash": qrcode_hash
    })
    
    if not ingresso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ingresso não encontrado"
        )
    
    # Verifica se o ingresso pertence ao evento do token
    if ingresso["evento_id"] != evento_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ingresso não pertence a este evento"
        )
    
    # Busca dados relacionados
    participante = await db.participantes.find_one({"_id": ObjectId(ingresso["participante_id"])})
    tipo_ingresso = await db.tipos_ingresso.find_one({"_id": ObjectId(ingresso["tipo_ingresso_id"])})
    evento = await db.eventos.find_one({"_id": ObjectId(evento_id)})
    
    if not all([participante, tipo_ingresso, evento]):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao buscar dados do ingresso"
        )
    
    return IngressoDetalhes(
        ingresso_id=str(ingresso["_id"]),
        participante_nome=participante["nome"],
        participante_email=participante.get("email"),
        participante_telefone=participante.get("telefone"),
        tipo_ingresso=tipo_ingresso["descricao"],
        evento_nome=evento["nome"],
        status=ingresso["status"],
        qrcode_hash=ingresso["qrcode_hash"],
        data_emissao=ingresso["data_emissao"],
        permissoes=tipo_ingresso.get("permissoes", [])
    )


@router.post("/validar", response_model=ValidacaoResponse)
async def validar_acesso(
    validacao: ValidacaoRequest,
    evento_id: str = Depends(verify_token_portaria)
):
    """
    Valida o QR code e verifica se o ingresso tem permissão para acessar a ilha
    
    Retorna:
    - 200 (Verde/OK): Acesso permitido
    - 403 (Vermelho/Negado): Acesso negado
    """
    db = get_database()
    
    # Busca o ingresso pelo QR code
    ingresso = await db.ingressos_emitidos.find_one({
        "qrcode_hash": validacao.qrcode_hash
    })
    
    if not ingresso:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="QR Code inválido"
        )
    
    # Verifica se o ingresso pertence ao evento do token
    if ingresso["evento_id"] != evento_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ingresso não pertence a este evento"
        )
    
    # Verifica se o ingresso está ativo
    if ingresso["status"] != "Ativo":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ingresso cancelado ou inválido"
        )
    
    # Busca o tipo de ingresso para verificar permissões
    try:
        tipo_ingresso = await db.tipos_ingresso.find_one({
            "_id": ObjectId(ingresso["tipo_ingresso_id"])
        })
        if not tipo_ingresso:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Tipo de ingresso não encontrado"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao buscar tipo de ingresso"
        )
    
    # Verifica se a ilha solicitada está nas permissões do tipo de ingresso
    if validacao.ilha_id not in tipo_ingresso.get("permissoes", []):
        # Busca nome da ilha para mensagem mais informativa
        try:
            ilha = await db.ilhas.find_one({"_id": ObjectId(validacao.ilha_id)})
            ilha_nome = ilha["nome_setor"] if ilha else "Setor desconhecido"
        except:
            ilha_nome = "Setor desconhecido"
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Acesso negado: ingresso não tem permissão para {ilha_nome}"
        )
    
    # Busca o participante para retornar informações
    try:
        participante = await db.participantes.find_one({
            "_id": ObjectId(ingresso["participante_id"])
        })
        participante_nome = participante["nome"] if participante else "Desconhecido"
    except:
        participante_nome = "Desconhecido"
    
    # Registra a validação (log de acesso)
    await db.validacoes_acesso.insert_one({
        "ingresso_id": str(ingresso["_id"]),
        "evento_id": evento_id,
        "ilha_id": validacao.ilha_id,
        "participante_id": ingresso["participante_id"],
        "data_validacao": datetime.now(timezone.utc),
        "status": "OK"
    })
    
    # Tudo OK, acesso permitido
    return ValidacaoResponse(
        status="OK",
        mensagem="Acesso permitido",
        participante_nome=participante_nome,
        tipo_ingresso=tipo_ingresso["descricao"]
    )


@router.get("/ilhas")
async def get_ilhas(
    evento_id: str = Depends(verify_token_portaria)
):
    """Retorna todas as ilhas (setores) do evento para seleção na portaria"""
    db = get_database()
    
    ilhas = []
    cursor = db.ilhas.find({"evento_id": evento_id})
    async for ilha in cursor:
        ilhas.append({
            "ilha_id": str(ilha["_id"]),
            "nome_setor": ilha["nome_setor"],
            "capacidade_maxima": ilha.get("capacidade_maxima", 0)
        })
    
    return {"ilhas": ilhas}


@router.get("/estatisticas")
async def estatisticas_portaria(
    evento_id: str = Depends(verify_token_portaria)
):
    """Retorna estatísticas de validações para o evento"""
    db = get_database()
    
    # Total de validações
    total_validacoes = await db.validacoes_acesso.count_documents({
        "evento_id": evento_id
    })
    
    # Validações por ilha
    pipeline = [
        {"$match": {"evento_id": evento_id}},
        {"$group": {
            "_id": "$ilha_id",
            "total": {"$sum": 1}
        }}
    ]
    
    validacoes_por_ilha = []
    async for doc in db.validacoes_acesso.aggregate(pipeline):
        # Busca nome da ilha
        try:
            ilha = await db.ilhas.find_one({"_id": ObjectId(doc["_id"])})
            ilha_nome = ilha["nome_setor"] if ilha else "Desconhecido"
        except:
            ilha_nome = "Desconhecido"
        
        validacoes_por_ilha.append({
            "ilha_id": doc["_id"],
            "ilha_nome": ilha_nome,
            "total_validacoes": doc["total"]
        })
    
    # Últimas validações
    ultimas_validacoes = []
    cursor = db.validacoes_acesso.find({"evento_id": evento_id}).sort("data_validacao", -1).limit(10)
    async for validacao in cursor:
        # Busca participante
        try:
            participante = await db.participantes.find_one({"_id": ObjectId(validacao["participante_id"])})
            participante_nome = participante["nome"] if participante else "Desconhecido"
        except:
            participante_nome = "Desconhecido"
        
        # Busca ilha
        try:
            ilha = await db.ilhas.find_one({"_id": ObjectId(validacao["ilha_id"])})
            ilha_nome = ilha["nome_setor"] if ilha else "Desconhecido"
        except:
            ilha_nome = "Desconhecido"
        
        ultimas_validacoes.append({
            "participante_nome": participante_nome,
            "ilha_nome": ilha_nome,
            "data_validacao": validacao["data_validacao"],
            "status": validacao["status"]
        })
    
    return {
        "total_validacoes": total_validacoes,
        "validacoes_por_ilha": validacoes_por_ilha,
        "ultimas_validacoes": ultimas_validacoes
    }
