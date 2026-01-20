import secrets
import hashlib
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from fastapi import Header, HTTPException, status, Depends, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config.database import get_database
from app.models.admin import Admin, AdminCreate, AdminUpdate
from bson import ObjectId

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET_KEY or JWT_SECRET_KEY == "your-secret-key-change-in-production":
    # In development, generate a random key; in production, raise an error
    if os.getenv("ENVIRONMENT", "development") == "production":
        raise ValueError("JWT_SECRET_KEY must be set in production environment")
    JWT_SECRET_KEY = secrets.token_urlsafe(32)
    
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Admin credentials (fallback for legacy compatibility)
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
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


# Password utilities
def hash_password(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


# Admin management functions
async def get_admin_by_username(username: str) -> Optional[Admin]:
    """Get admin by username"""
    db = get_database()
    admin_data = await db.administradores.find_one({"username": username, "ativo": True})
    if admin_data:
        return Admin(**admin_data)
    return None


async def get_admin_by_id(admin_id: str) -> Optional[Admin]:
    """Get admin by ID"""
    db = get_database()
    admin_data = await db.administradores.find_one({"_id": ObjectId(admin_id), "ativo": True})
    if admin_data:
        return Admin(**admin_data)
    return None


async def get_all_admins() -> List[Admin]:
    """Get all active admins"""
    db = get_database()
    admins_data = await db.administradores.find({"ativo": True}).to_list(length=None)
    return [Admin(**admin) for admin in admins_data]


async def create_admin(admin_data: AdminCreate) -> Admin:
    """Create a new admin"""
    db = get_database()

    # Check if username already exists
    existing = await db.administradores.find_one({"username": admin_data.username})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username já existe"
        )

    # Check if email already exists
    existing_email = await db.administradores.find_one({"email": admin_data.email})
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email já existe"
        )

    admin_dict = admin_data.model_dump()
    admin_dict["password_hash"] = hash_password(admin_dict.pop("password"))
    admin_dict["data_criacao"] = datetime.now(timezone.utc)

    result = await db.administradores.insert_one(admin_dict)
    admin_dict["_id"] = str(result.inserted_id)

    return Admin(**admin_dict)


async def update_admin(admin_id: str, admin_data: AdminUpdate) -> Admin:
    """Update an admin"""
    db = get_database()

    update_data = {}
    if admin_data.username:
        # Check if username already exists for another admin
        existing = await db.administradores.find_one({
            "username": admin_data.username,
            "_id": {"$ne": ObjectId(admin_id)}
        })
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username já existe"
            )
        update_data["username"] = admin_data.username

    if admin_data.email:
        # Check if email already exists for another admin
        existing_email = await db.administradores.find_one({
            "email": admin_data.email,
            "_id": {"$ne": ObjectId(admin_id)}
        })
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email já existe"
            )
        update_data["email"] = admin_data.email

    if admin_data.nome:
        update_data["nome"] = admin_data.nome

    if admin_data.ativo is not None:
        update_data["ativo"] = admin_data.ativo

    if admin_data.password:
        update_data["password_hash"] = hash_password(admin_data.password)

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nenhum campo para atualizar"
        )

    result = await db.administradores.update_one(
        {"_id": ObjectId(admin_id)},
        {"$set": update_data}
    )

    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Administrador não encontrado"
        )

    # Return updated admin
    updated_admin = await get_admin_by_id(admin_id)
    if not updated_admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Administrador não encontrado após atualização"
        )

    return updated_admin


async def delete_admin(admin_id: str) -> bool:
    """Soft delete an admin (deactivate)"""
    db = get_database()

    result = await db.administradores.update_one(
        {"_id": ObjectId(admin_id)},
        {"$set": {"ativo": False}}
    )

    return result.modified_count > 0


async def create_initial_admin():
    """Create initial admin if none exists"""
    db = get_database()

    # Check if any admin exists
    count = await db.administradores.count_documents({"ativo": True})
    if count == 0:
        # Create default admin
        admin_data = AdminCreate(
            username=ADMIN_USERNAME,
            email="admin@example.com",
            nome="Administrador",
            password=ADMIN_PASSWORD
        )
        await create_admin(admin_data)
        print("Administrador inicial criado com sucesso")


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


async def verify_admin_credentials(username: str, password: str) -> Optional[Admin]:
    """Verifica credenciais do administrador e retorna o admin se válido"""
    admin = await get_admin_by_username(username)
    if admin and verify_password(password, admin.password_hash):
        # Update last login
        db = get_database()
        await db.administradores.update_one(
            {"_id": ObjectId(admin.id)},
            {"$set": {"ultimo_login": datetime.now(timezone.utc)}}
        )
        return admin
    return None


def verify_admin_credentials_sync(username: str, password: str) -> bool:
    """Legacy sync version for backward compatibility"""
    # Fallback to environment variables if database check fails
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD
