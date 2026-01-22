"""
Testes para autenticação e autorização.
Cobre JWT, tokens de bilheteria, portaria e admin.
"""
import pytest
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from fastapi import HTTPException
from jose import jwt

from app.config import auth
from tests.conftest import FakeDB


class TestJWTAuthentication:
    """Testes para autenticação JWT de administradores."""
    
    def test_create_access_token(self):
        """Testa criação de token JWT."""
        data = {"sub": "admin_user", "type": "admin"}
        token = auth.create_access_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_create_access_token_with_expiration(self):
        """Testa criação de token JWT com expiração customizada."""
        data = {"sub": "admin_user", "type": "admin"}
        expires_delta = timedelta(minutes=15)
        token = auth.create_access_token(data, expires_delta=expires_delta)
        
        assert isinstance(token, str)
        
        # Decodifica para verificar expiração
        decoded = jwt.decode(
            token,
            auth.JWT_SECRET_KEY,
            algorithms=[auth.JWT_ALGORITHM]
        )
        assert "exp" in decoded
    
    def test_verify_token_valid(self):
        """Testa verificação de token válido."""
        data = {"sub": "admin_user", "type": "admin"}
        token = auth.create_access_token(data)
        
        payload = auth.verify_token(token)
        
        assert payload["sub"] == "admin_user"
        assert payload["type"] == "admin"
    
    def test_verify_token_expired(self):
        """Testa verificação de token expirado."""
        data = {"sub": "admin_user", "type": "admin"}
        expires_delta = timedelta(seconds=-1)  # Token já expirado
        token = auth.create_access_token(data, expires_delta=expires_delta)
        
        with pytest.raises(Exception):
            auth.verify_token(token)
    
    def test_verify_token_invalid(self):
        """Testa verificação de token inválido."""
        invalid_token = "invalid.token.here"
        
        with pytest.raises(Exception):
            auth.verify_token(invalid_token)


class TestTokenGeneration:
    """Testes para geração de tokens de eventos."""
    
    def test_generate_token_format(self):
        """Testa formato do token gerado."""
        token = auth.generate_token()
        
        assert isinstance(token, str)
        assert len(token) > 20  # Token deve ter tamanho razoável
    
    def test_generate_token_unique(self):
        """Testa que tokens gerados são únicos."""
        token1 = auth.generate_token()
        token2 = auth.generate_token()
        
        assert token1 != token2
    
    def test_generate_multiple_tokens(self):
        """Testa geração de múltiplos tokens."""
        tokens = set()
        for _ in range(100):
            token = auth.generate_token()
            tokens.add(token)
        
        # Todos devem ser únicos
        assert len(tokens) == 100


class TestTokenBilheteria:
    """Testes para autenticação de bilheteria."""
    
    @pytest.mark.asyncio
    async def test_verify_token_bilheteria_valid(self, fake_db, mock_get_database, sample_evento):
        """Testa verificação de token de bilheteria válido."""
        fake_db.eventos.docs.append(sample_evento)
        
        evento_id = await auth.verify_token_bilheteria(sample_evento["token_bilheteria"])
        
        assert evento_id == str(sample_evento["_id"])
    
    @pytest.mark.asyncio
    async def test_verify_token_bilheteria_invalid(self, fake_db, mock_get_database):
        """Testa verificação de token de bilheteria inválido."""
        with pytest.raises(HTTPException) as exc_info:
            await auth.verify_token_bilheteria("token_invalido")
        
        assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_verify_token_bilheteria_empty(self, fake_db, mock_get_database):
        """Testa verificação sem token."""
        with pytest.raises(HTTPException) as exc_info:
            await auth.verify_token_bilheteria("")
        
        assert exc_info.value.status_code == 401


class TestTokenPortaria:
    """Testes para autenticação de portaria."""
    
    @pytest.mark.asyncio
    async def test_verify_token_portaria_valid(self, fake_db, mock_get_database, sample_evento):
        """Testa verificação de token de portaria válido."""
        fake_db.eventos.docs.append(sample_evento)
        
        evento_id = await auth.verify_token_portaria(sample_evento["token_portaria"])
        
        assert evento_id == str(sample_evento["_id"])
    
    @pytest.mark.asyncio
    async def test_verify_token_portaria_invalid(self, fake_db, mock_get_database):
        """Testa verificação de token de portaria inválido."""
        with pytest.raises(HTTPException) as exc_info:
            await auth.verify_token_portaria("token_invalido")
        
        assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_verify_token_portaria_empty(self, fake_db, mock_get_database):
        """Testa verificação sem token."""
        with pytest.raises(HTTPException) as exc_info:
            await auth.verify_token_portaria("")
        
        assert exc_info.value.status_code == 401


class TestAdminAuthentication:
    """Testes para autenticação de administradores."""
    
    @pytest.mark.asyncio
    async def test_authenticate_admin_success(self, fake_db, mock_get_database):
        """Testa autenticação de admin com credenciais válidas."""
        from passlib.context import CryptContext
        
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        admin = {
            "_id": ObjectId(),
            "username": "admin",
            "email": "admin@example.com",
            "nome": "Administrador",
            "password_hash": pwd_context.hash("password123"),
            "ativo": True,
            "data_criacao": datetime.now(timezone.utc),
            "ultimo_login": None
        }
        fake_db.admins.docs.append(admin)
        
        result = await auth.authenticate_admin("admin", "password123")
        
        assert result is not None
        assert result["username"] == "admin"
    
    @pytest.mark.asyncio
    async def test_authenticate_admin_wrong_password(self, fake_db, mock_get_database):
        """Testa autenticação com senha incorreta."""
        from passlib.context import CryptContext
        
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        admin = {
            "_id": ObjectId(),
            "username": "admin",
            "email": "admin@example.com",
            "password_hash": pwd_context.hash("password123"),
            "ativo": True,
            "data_criacao": datetime.now(timezone.utc)
        }
        fake_db.admins.docs.append(admin)
        
        result = await auth.authenticate_admin("admin", "wrong_password")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_authenticate_admin_user_not_found(self, fake_db, mock_get_database):
        """Testa autenticação com usuário inexistente."""
        result = await auth.authenticate_admin("inexistente", "password123")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_authenticate_admin_inactive(self, fake_db, mock_get_database):
        """Testa autenticação de admin inativo."""
        from passlib.context import CryptContext
        
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        admin = {
            "_id": ObjectId(),
            "username": "admin",
            "email": "admin@example.com",
            "password_hash": pwd_context.hash("password123"),
            "ativo": False,  # Admin inativo
            "data_criacao": datetime.now(timezone.utc)
        }
        fake_db.admins.docs.append(admin)
        
        result = await auth.authenticate_admin("admin", "password123")
        
        assert result is None


class TestPasswordHashing:
    """Testes para hashing de senhas."""
    
    def test_hash_password(self):
        """Testa criação de hash de senha."""
        password = "my_secure_password"
        hashed = auth.get_password_hash(password)
        
        assert hashed != password
        assert len(hashed) > 0
    
    def test_verify_password_correct(self):
        """Testa verificação de senha correta."""
        password = "my_secure_password"
        hashed = auth.get_password_hash(password)
        
        result = auth.verify_password(password, hashed)
        
        assert result is True
    
    def test_verify_password_incorrect(self):
        """Testa verificação de senha incorreta."""
        password = "my_secure_password"
        hashed = auth.get_password_hash(password)
        
        result = auth.verify_password("wrong_password", hashed)
        
        assert result is False
    
    def test_hash_different_each_time(self):
        """Testa que hash é diferente a cada vez (devido ao salt)."""
        password = "my_secure_password"
        hash1 = auth.get_password_hash(password)
        hash2 = auth.get_password_hash(password)
        
        # Hashes devem ser diferentes devido ao salt
        assert hash1 != hash2
        
        # Mas ambos devem ser válidos para a mesma senha
        assert auth.verify_password(password, hash1)
        assert auth.verify_password(password, hash2)


class TestInitialAdminCreation:
    """Testes para criação automática de admin inicial."""
    
    @pytest.mark.asyncio
    async def test_create_initial_admin(self, fake_db, mock_get_database):
        """Testa criação de admin inicial."""
        await auth.create_initial_admin()
        
        # Verifica que admin foi criado
        assert len(fake_db.admins.docs) == 1
        admin = fake_db.admins.docs[0]
        assert admin["username"] is not None
        assert admin["ativo"] is True
    
    @pytest.mark.asyncio
    async def test_create_initial_admin_already_exists(self, fake_db, mock_get_database):
        """Testa que não cria admin se já existe um."""
        # Adiciona admin existente
        admin = {
            "_id": ObjectId(),
            "username": "existing_admin",
            "email": "admin@example.com",
            "password_hash": "hash",
            "ativo": True,
            "data_criacao": datetime.now(timezone.utc)
        }
        fake_db.admins.docs.append(admin)
        
        await auth.create_initial_admin()
        
        # Não deve criar novo admin
        assert len(fake_db.admins.docs) == 1


class TestAuthorizationMiddleware:
    """Testes para middleware de autorização."""
    
    @pytest.mark.asyncio
    async def test_verify_admin_access_valid(self, fake_db, mock_get_database):
        """Testa verificação de acesso admin válido."""
        from fastapi import Request
        from unittest.mock import MagicMock
        
        # Cria token JWT válido
        token = auth.create_access_token({"sub": "admin", "type": "admin"})
        
        # Mock de request com token
        request = MagicMock(spec=Request)
        request.cookies = {"admin_jwt": token}
        
        # Deve passar sem exceção
        result = await auth.verify_admin_access(request)
        assert result is True or result is None
    
    @pytest.mark.asyncio
    async def test_verify_admin_access_no_token(self):
        """Testa acesso admin sem token."""
        from fastapi import Request
        from unittest.mock import MagicMock
        
        request = MagicMock(spec=Request)
        request.cookies = {}
        
        with pytest.raises(HTTPException) as exc_info:
            await auth.verify_admin_access(request)
        
        assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_verify_admin_access_invalid_token(self):
        """Testa acesso admin com token inválido."""
        from fastapi import Request
        from unittest.mock import MagicMock
        
        request = MagicMock(spec=Request)
        request.cookies = {"admin_jwt": "invalid_token"}
        
        with pytest.raises(HTTPException) as exc_info:
            await auth.verify_admin_access(request)
        
        assert exc_info.value.status_code == 401
