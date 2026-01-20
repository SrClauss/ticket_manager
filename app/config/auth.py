import secrets
import hashlib
import os
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Header, HTTPException, status, Depends, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from app.config.database import get_database
from bson import ObjectId

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

# Admin credentials (in production, use database with hashed passwords)
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin_key_change_in_production")

security = HTTPBearer(auto_error=False)


def generate_token() -> str:
    """Gera um token único para acesso"""
    return secrets.token_urlsafe(32)


def generate_qrcode_hash() -> str:
    """Gera um hash único para QR Code"""
    random_data = secrets.token_bytes(32)
    return hashlib.sha256(random_data).hexdigest()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Cria um token JWT de acesso"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def verify_jwt_token(token: str) -> dict:
    """Verifica e decodifica um token JWT"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )


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


async def verify_admin_access(
    x_admin_key: str = Header(None, description="Chave de acesso administrativo (deprecated)"),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Middleware para verificar acesso administrativo usando JWT
    Também aceita a chave antiga para compatibilidade
    """
    # Try JWT first (preferred method)
    if credentials:
        token = credentials.credentials
        payload = verify_jwt_token(token)
        if payload.get("role") == "admin":
            return payload
    
    # Fallback to legacy admin key for backward compatibility
    if x_admin_key and x_admin_key == ADMIN_PASSWORD:
        return {"role": "admin", "username": "admin_legacy"}
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Acesso administrativo negado. Use Bearer token JWT.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def verify_admin_credentials(username: str, password: str) -> bool:
    """Verifica credenciais do administrador"""
    # In production, check against database with hashed passwords
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD
