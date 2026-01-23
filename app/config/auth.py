import secrets
import hashlib
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from fastapi import Header, HTTPException, status, Depends, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
import app.config.database as database
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

# Password hashing - support multiple schemes for compatibility with test fixtures
pwd_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")

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
def _admin_collection(db):
    return getattr(db, 'administradores', None) or getattr(db, 'admins', None)


async def get_admin_by_username(username: str) -> Optional[Admin]:
    """Get admin by username"""
    db = database.get_database()
    col = _admin_collection(db)
    admin_data = await col.find_one({"username": username, "ativo": True})
    if admin_data:
        try:
            return Admin.from_mongo(admin_data)
        except Exception:
            # Fallback: return a lightweight object for authentication purposes when data is incomplete
            from types import SimpleNamespace
            admin_clone = dict(admin_data)
            if "_id" in admin_clone and isinstance(admin_clone["_id"], ObjectId):
                admin_clone["_id"] = str(admin_clone["_id"])
            admin_clone.setdefault("nome", "")
            admin_clone.setdefault("ativo", True)
            return SimpleNamespace(
                username=admin_clone.get("username"),
                email=admin_clone.get("email"),
                nome=admin_clone.get("nome"),
                ativo=admin_clone.get("ativo"),
                password_hash=admin_clone.get("password_hash"),
                id=admin_clone.get("_id")
            )
    return None


async def get_admin_by_id(admin_id: str) -> Optional[Admin]:
    """Get admin by ID"""
    db = database.get_database()
    col = _admin_collection(db)
    admin_data = await col.find_one({"_id": ObjectId(admin_id), "ativo": True})
    if admin_data:
        return Admin.from_mongo(admin_data)
    return None


async def get_all_admins() -> List[Admin]:
    """Get all active admins"""
    db = database.get_database()
    col = _admin_collection(db)
    admins_data = await col.find({"ativo": True}).to_list(length=None)
    return [Admin.from_mongo(admin) for admin in admins_data]


async def create_admin(admin_data: AdminCreate) -> Admin:
    """Create a new admin"""
    db = database.get_database()
    col = _admin_collection(db)

    # Check if username already exists
    existing = await col.find_one({"username": admin_data.username})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username já existe"
        )

    # Check if email already exists
    existing_email = await col.find_one({"email": admin_data.email})
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email já existe"
        )

    admin_dict = admin_data.model_dump()
    admin_dict["password_hash"] = hash_password(admin_dict.pop("password"))
    admin_dict["data_criacao"] = datetime.now(timezone.utc)

    result = await col.insert_one(admin_dict)
    admin_dict["_id"] = str(result.inserted_id)

    return Admin.from_mongo(admin_dict)


async def update_admin(admin_id: str, admin_data: AdminUpdate) -> Admin:
    """Update an admin"""
    db = database.get_database()
    col = _admin_collection(db)

    update_data = {}
    if admin_data.username:
        # Check if username already exists for another admin
        existing = await col.find_one({
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
        existing_email = await col.find_one({
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

    result = await col.update_one(
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
    db = database.get_database()
    col = _admin_collection(db)

    result = await col.update_one(
        {"_id": ObjectId(admin_id)},
        {"$set": {"ativo": False}}
    )

    return result.modified_count > 0


async def create_initial_admin():
    """Create initial admin if none exists"""
    db = database.get_database()
    col = _admin_collection(db)

    # Check if any admin exists
    count = await col.count_documents({"ativo": True})
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


def verify_token(token: str) -> dict:
    """Compatibilidade: wrapper para verificar token JWT como `verify_token` nos testes"""
    return verify_jwt_token(token)


async def authenticate_admin(username: str, password: str):
    """Compatibilidade: wrapper que retorna o admin dict se credenciais válidas ou None"""
    admin = await get_admin_by_username(username)
    if not admin:
        return None
    if verify_password(password, admin.password_hash):
        # Return a plain dict to match tests
        return {
            "username": admin.username,
            "email": admin.email,
            "nome": admin.nome,
            "ativo": admin.ativo
        }
    return None


def get_password_hash(password: str) -> str:
    """Compatibilidade: alias para hash_password"""
    return hash_password(password)


async def verify_token_bilheteria(
    x_token_bilheteria: str = Header(..., description="Token de acesso da bilheteria")
):
    """
    Middleware para verificar token de bilheteria
    """
    db = database.get_database()
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
    db = database.get_database()
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
    Logs detalhes mínimos para depuração de autenticação.
    Aceita também ser chamado diretamente com um `Request` (usado em alguns testes).
    """
    # If called directly with a Request object (test helpers), extract cookie token
    try:
        from fastapi import Request
        if isinstance(x_admin_key, Request) or hasattr(x_admin_key, "cookies"):
            request = x_admin_key
            token = request.cookies.get("admin_jwt") if hasattr(request, "cookies") else None
            if token:
                try:
                    payload = verify_jwt_token(token)
                    # Accept 'role' or legacy 'type' claim
                    if payload.get("role") == "admin" or payload.get("type") == "admin":
                        return True
                except HTTPException:
                    pass
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Acesso administrativo negado.")
    except Exception:
        # not a Request, continue with normal flow
        pass

    # Debug prints to help identify why requests are unauthorized
    print(f"verify_admin_access: x_admin_key present={bool(x_admin_key)} credentials present={bool(credentials)}")

    # Try JWT first (preferred method)
    if credentials and hasattr(credentials, "credentials"):
        token = credentials.credentials
        if token:
            try:
                print(f"verify_admin_access: received token (truncated)={token[:20]}... len={len(token)}")
            except Exception:
                print("verify_admin_access: received token (unprintable)")
        try:
            payload = verify_jwt_token(token)
            print(f"verify_admin_access: jwt payload keys={list(payload.keys())}")
            # Accept 'role' or legacy 'type' claim
            if payload.get("role") == "admin" or payload.get("type") == "admin":
                return payload
        except HTTPException as e:
            # Token invalid or expired
            print(f"verify_admin_access: jwt verification failed: {getattr(e, 'detail', str(e))}")

    # Fallback to legacy admin key for backward compatibility
    if x_admin_key and x_admin_key == ADMIN_PASSWORD:
        print("verify_admin_access: legacy x_admin_key accepted")
        return {"role": "admin", "username": "admin_legacy"}

    print("verify_admin_access: denying access")
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
        db = database.get_database()
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
