from fastapi import APIRouter, HTTPException, status, Depends
from bson import ObjectId
from bson.errors import InvalidId
import app.config.database as database

def get_database():
    """Runtime indirection to allow tests to monkeypatch `get_database` on this module."""
    return database.get_database()
from app.config.auth import verify_token_portaria
from app.utils.validations import format_datetime_display
from pydantic import BaseModel
from datetime import datetime, timezone
from typing import Optional

router = APIRouter()

# Minimal in-memory collection to use when tests provide FakeDB without certain collections
class _LocalColl:
    def __init__(self):
        self.docs = []

    async def insert_one(self, doc):
        from types import SimpleNamespace
        new_doc = dict(doc)
        self.docs.append(new_doc)
        return SimpleNamespace(inserted_id=new_doc.get("_id"))

    async def count_documents(self, query=None):
        query = query or {}
        count = 0
        for d in self.docs:
            match = True
            for k, v in query.items():
                if d.get(k) != v:
                    match = False
                    break
            if match:
                count += 1
        return count

    def find(self, query=None, sort=None):
        class _C:
            def __init__(self, docs):
                self.docs = docs
                self._limit = None

            def sort(self, *args, **kwargs):
                return self

            def limit(self, n):
                self._limit = n
                return self

            def __aiter__(self):
                self._iter = iter(self.docs[: self._limit] if self._limit else self.docs)
                return self

            async def __anext__(self):
                try:
                    return next(self._iter)
                except StopIteration:
                    raise StopAsyncIteration

        query = query or {}
        matching = [d for d in self.docs if all(d.get(k) == v for k, v in query.items())]
        return _C(matching)

    async def aggregate(self, pipeline):
        # very small support for pipelines used in app: $match then $group by a single field
        match = {}
        group_field = None
        for stage in pipeline:
            if "$match" in stage:
                match = stage["$match"]
            if "$group" in stage:
                group_spec = stage["$group"]
                gid = group_spec.get("_id")
                if isinstance(gid, str) and gid.startswith("$"):
                    group_field = gid[1:]
        counts = {}
        for d in self.docs:
            ok = True
            for k, v in match.items():
                if d.get(k) != v:
                    ok = False
                    break
            if not ok:
                continue
            key = d.get(group_field)
            counts[key] = counts.get(key, 0) + 1
        for k, v in counts.items():
            yield {"_id": k, "total": v}


def _ensure_validacoes(db):
    if not hasattr(db, "validacoes_acesso"):
        db.validacoes_acesso = _LocalColl()



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
    
    # Primeiro tenta localizar ingresso embutido dentro de participantes
    participante = await db.participantes.find_one(
        {"ingressos.qrcode_hash": qrcode_hash},
        {"ingressos": {"$elemMatch": {"qrcode_hash": qrcode_hash}}, "nome": 1, "email": 1, "telefone": 1}
    )

    ingresso = None
    evento = await db.eventos.find_one({"_id": ObjectId(evento_id)})

    if participante and participante.get("ingressos"):
        ingresso = participante["ingressos"][0]
    else:
        # Fallback para coleção antiga `ingressos_emitidos` (compatibilidade)
        ingresso = await db.ingressos_emitidos.find_one({"qrcode_hash": qrcode_hash})
        if not ingresso:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ingresso não encontrado"
            )
        try:
            participante = await db.participantes.find_one({"_id": ObjectId(ingresso["participante_id"])})
        except Exception:
            participante = await db.participantes.find_one({"_id": ingresso.get("participante_id")})

    # Verifica se o ingresso pertence ao evento do token
    if ingresso.get("evento_id") != evento_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ingresso não pertence a este evento"
        )

    # Busca tipo de ingresso no evento (embutido) ou fallback para coleção
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

    if not all([participante, tipo_ingresso, evento]):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao buscar dados do ingresso"
        )

    ingresso_id = str(ingresso.get("_id") or ingresso.get("qrcode_hash"))

    return IngressoDetalhes(
        ingresso_id=ingresso_id,
        participante_nome=participante["nome"],
        participante_email=participante.get("email"),
        participante_telefone=participante.get("telefone"),
        tipo_ingresso=tipo_ingresso["descricao"],
        evento_nome=evento["nome"],
        status=ingresso.get("status"),
        qrcode_hash=ingresso["qrcode_hash"],
        data_emissao=ingresso.get("data_emissao"),
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
    
    # Primeiro tenta localizar ingresso embutido dentro de participantes
    participante = await db.participantes.find_one(
        {"ingressos.qrcode_hash": validacao.qrcode_hash},
        {"ingressos": {"$elemMatch": {"qrcode_hash": validacao.qrcode_hash}}, "nome": 1}
    )

    ingresso = None
    if participante and participante.get("ingressos"):
        ingresso = participante["ingressos"][0]
    else:
        # Fallback para coleção antiga `ingressos_emitidos`
        ingresso = await db.ingressos_emitidos.find_one({"qrcode_hash": validacao.qrcode_hash})

    if not ingresso:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="QR Code inválido"
        )

    # Verifica se o ingresso pertence ao evento do token
    if ingresso.get("evento_id") != evento_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ingresso não pertence a este evento"
        )

    # Verifica se o ingresso está ativo
    if ingresso.get("status") != "Ativo":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ingresso cancelado ou inválido"
        )

    # Busca tipo de ingresso no evento (embutido) ou fallback para coleção
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

    if not tipo_ingresso:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Tipo de ingresso não encontrado"
        )

    # Verifica se a ilha solicitada está nas permissões do tipo de ingresso
    if validacao.ilha_id not in tipo_ingresso.get("permissoes", []):
        # Busca nome da ilha para mensagem mais informativa: procura nas ilhas embutidas do evento, fallback para coleção
        ilha_nome = "Setor desconhecido"
        try:
            if evento:
                for il in evento.get("ilhas", []):
                    if str(il.get("_id") or il.get("id")) == str(validacao.ilha_id):
                        ilha_nome = il.get("nome_setor", "Setor desconhecido")
                        break
            else:
                il = await db.ilhas.find_one({"_id": ObjectId(validacao.ilha_id)})
                ilha_nome = il["nome_setor"] if il else "Setor desconhecido"
        except Exception:
            ilha_nome = "Setor desconhecido"

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Acesso negado: ingresso não tem permissão para {ilha_nome}"
        )

    # Busca o participante para retornar informações (caso não já tenhamos)
    try:
        if not participante:
            participante = await db.participantes.find_one({"_id": ObjectId(ingresso.get("participante_id"))})
        participante_nome = participante["nome"] if participante else "Desconhecido"
    except:
        participante_nome = "Desconhecido"

    # Ensure the validacoes_acesso collection exists (for tests using FakeDB)
    _ensure_validacoes(db)

    # Registra a validação (log de acesso)
    await db.validacoes_acesso.insert_one({
        "ingresso_id": str(ingresso.get("_id") or ingresso.get("qrcode_hash")),
        "evento_id": evento_id,
        "ilha_id": validacao.ilha_id,
        "participante_id": ingresso.get("participante_id") or (str(participante.get("_id")) if participante else None),
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
    
    # Preferir ilhas embutidas no evento
    evento = await db.eventos.find_one({"_id": ObjectId(evento_id)})
    ilhas = []
    if evento and evento.get("ilhas"):
        for ilha in evento.get("ilhas", []):
            ilhas.append({
                "ilha_id": str(ilha.get("_id") or ilha.get("id")),
                "nome_setor": ilha.get("nome_setor"),
                "capacidade_maxima": ilha.get("capacidade_maxima", 0)
            })
        return {"ilhas": ilhas}

    # Fallback para coleção `ilhas`
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
    _ensure_validacoes(db)
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
    
    result = {
        "total_validacoes": total_validacoes,
        "validacoes_por_ilha": validacoes_por_ilha,
        "ultimas_validacoes": ultimas_validacoes
    }
    return result


# Backwards-compatible alias expected by tests
async def get_estatisticas(evento_id: str = None):
    return await estatisticas_portaria(evento_id=evento_id)
