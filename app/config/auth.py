import secrets
import hashlib
from fastapi import Header, HTTPException, status, Depends
from app.config.database import get_database
from bson import ObjectId


def generate_token() -> str:
    """Gera um token único para acesso"""
    return secrets.token_urlsafe(32)


def generate_qrcode_hash() -> str:
    """Gera um hash único para QR Code"""
    random_data = secrets.token_bytes(32)
    return hashlib.sha256(random_data).hexdigest()


async def verify_token_bilheteria(
    x_token_bilheteria: str = Header(..., description="Token de acesso da bilheteria")
):
    """
    Middleware para verificar token de bilheteria
    """
    db = get_database()
    evento = await db.eventos.find_one({"token_bilheteria": x_token_bilheteria})
    
    if not evento:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de bilheteria inválido"
        )
    
    return str(evento["_id"])


async def verify_token_portaria(
    x_token_portaria: str = Header(..., description="Token de acesso da portaria")
):
    """
    Middleware para verificar token de portaria
    """
    db = get_database()
    evento = await db.eventos.find_one({"token_portaria": x_token_portaria})
    
    if not evento:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de portaria inválido"
        )
    
    return str(evento["_id"])


# Simplificação para admin - em produção, use OAuth2 ou JWT
async def verify_admin_access(
    x_admin_key: str = Header(..., description="Chave de acesso administrativo")
):
    """
    Middleware para verificar acesso administrativo
    Em produção, substitua por OAuth2/JWT adequado
    """
    # TODO: Implementar autenticação real com JWT/OAuth2
    ADMIN_KEY = "admin_key_change_in_production"  # Deve vir de variável de ambiente
    
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Acesso administrativo negado"
        )
    
    return True
