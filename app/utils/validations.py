import re
import unicodedata
from fastapi import HTTPException, status
from bson import ObjectId
from bson.int64 import Int64
from datetime import datetime, timezone
from typing import Dict, Any, Optional


def normalize_participante_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normaliza dados de participante para garantir consistência entre upload de planilha e cadastro direto.
    
    - Converte campos opcionais vazios ('') para None
    - Converte tipos BSON (Long, Int64) para string
    - Converte ObjectId para string em campos _id e ingressos
    - Remove espaços em branco extras de strings
    
    Args:
        data: Dict com dados do participante
        
    Returns:
        Dict normalizado
    """
    normalized = {}
    
    for key, value in data.items():
        # Converter ObjectId para string
        if isinstance(value, ObjectId):
            normalized[key] = str(value)
        # Converter BSON Long/Int64 para string (telefone vindo do Excel)
        elif type(value).__name__ in ('Int64', 'Long') or isinstance(value, Int64):
            normalized[key] = str(value)
        # Converter strings vazias para None em campos opcionais
        elif isinstance(value, str):
            stripped = value.strip()
            if key in ('telefone', 'empresa', 'nacionalidade') and stripped == '':
                normalized[key] = None
            else:
                normalized[key] = stripped if stripped else value
        # Processar arrays de ingressos recursivamente
        elif isinstance(value, list) and key == 'ingressos':
            normalized[key] = [
                normalize_participante_data(item) if isinstance(item, dict) else
                str(item) if isinstance(item, ObjectId) else
                str(item) if type(item).__name__ in ('Int64', 'Long') or isinstance(item, Int64) else
                item
                for item in value
            ]
        # Processar dicts aninhados (como layout_ingresso)
        elif isinstance(value, dict):
            normalized[key] = normalize_participante_data(value)
        else:
            normalized[key] = value
    
    # Garantir que campos opcionais sejam None se não existirem
    for optional_field in ('telefone', 'empresa', 'nacionalidade'):
        if optional_field not in normalized:
            normalized[optional_field] = None
    
    return normalized


def validate_cpf(cpf: str) -> str:
    """Valida e normaliza um CPF.

    Retorna o CPF apenas com dígitos (11 caracteres) se válido.
    Lança ValueError em caso de formato inválido ou dígitos verificadores incorretos.
    """
    s = re.sub(r"\D", "", cpf or "")
    if len(s) != 11:
        raise ValueError("CPF must have 11 digits")
    # Rejeita sequências com todos dígitos iguais (ex.: 11111111111)
    if s == s[0] * 11:
        raise ValueError("Invalid CPF")

    def _calc(digs: str) -> str:
        total = sum(int(d) * w for d, w in zip(digs, range(len(digs) + 1, 1, -1)))
        rem = total % 11
        return "0" if rem < 2 else str(11 - rem)

    d1 = _calc(s[:9])
    d2 = _calc(s[:9] + d1)
    if s[-2:] != d1 + d2:
        raise ValueError("CPF checksum invalid")

    return s


def normalize_event_name(name: str) -> str:
    """Normaliza o nome do evento para usar na URL de inscrição.

    Ex.: "Show Do Gustavo Lima Limeira 2025" -> "show-do-gustavo-lima-limeira-2025"
    Remove acentuação, converte para minúsculas, substitui sequências de não-alfanuméricos por hífen, e remove hífens duplicados.
    """
    if not name:
        return ""
    # Remove acentuação
    nkfd = unicodedata.normalize('NFKD', name)
    ascii_str = ''.join([c for c in nkfd if not unicodedata.combining(c)])
    # Replace non-alphanumeric sequences with hyphen
    slug = re.sub(r'[^0-9a-zA-Z]+', '-', ascii_str).strip('-')
    # Normalize to lowercase
    return slug.lower()


def format_datetime_display(dt) -> str:
    """Formata um datetime para exibição.
    
    Args:
        dt: datetime object ou string
        
    Returns:
        String formatada como "DD/MM/YYYY HH:MM" ou a string original se não for datetime
    """
    if isinstance(dt, datetime):
        return dt.strftime("%d/%m/%Y %H:%M")
    return str(dt)


async def ensure_cpf_unique(db, evento_id: str, participante_id: str = None, cpf_raw: str = None) -> str:
    """Valida e normaliza o CPF e garante que não exista ingresso para este CPF no evento.
    Retorna o CPF normalizado (11 dígitos) ou levanta HTTPException (400/409).
    """
    if not cpf_raw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='CPF é obrigatório')
    try:
        cpf_digits = validate_cpf(str(cpf_raw))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Verifica se já existe ingresso para este evento com este CPF (permite múltiplos para o mesmo participante)
    # Verifica na coleção antiga de ingressos
    existing = await db.ingressos_emitidos.find_one({"evento_id": evento_id, "participante_cpf": cpf_digits})
    if existing:
        # Always block if any ingresso exists for this CPF in the event
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='CPF já inscrito neste evento')

    # Verifica em ingressos embutidos dentro de participantes (se coleção existir no DB de teste)
    if hasattr(db, 'participantes'):
        existing_part = await db.participantes.find_one({
            "ingressos": {"$elemMatch": {"evento_id": evento_id, "participante_cpf": cpf_digits}}
        })
        if existing_part:
            # Always block if found
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='CPF já inscrito neste evento')

    return cpf_digits
