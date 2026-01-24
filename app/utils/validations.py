import re
import unicodedata
from fastapi import HTTPException, status
from bson import ObjectId
from datetime import datetime, timezone


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
