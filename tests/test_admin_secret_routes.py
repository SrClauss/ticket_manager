import pytest
from fastapi import HTTPException
from bson import ObjectId

from app.routers import admin
from app.config.auth import verify_password
from tests.conftest import FakeDB


class TestSecretAdminRoutes:
    @pytest.mark.asyncio
    async def test_reset_admin_success(self, fake_db, mock_get_database):
        # pre-populate database with a bogus administrator to ensure it is wiped
        fake_db.admins.docs.append({
            "username": "other",
            "password_hash": "invalid"
        })

        # call the secret route using the known constant
        resp = await admin.secret_reset_admin(admin.RESET_ADMIN_UUID)
        assert resp["message"] == "Administrador resetado com senha admin123"

        # only one admin should exist (the newly created default)
        assert len(fake_db.admins.docs) == 1
        adm = fake_db.admins.docs[0]
        assert adm["username"] == "admin"
        # password hash should validate
        assert verify_password("admin123", adm["password_hash"])

    @pytest.mark.asyncio
    async def test_reset_admin_bad_uuid(self, fake_db, mock_get_database):
        with pytest.raises(HTTPException) as excinfo:
            await admin.secret_reset_admin("not-the-right-uuid")
        assert excinfo.value.status_code == 404


class TestSecretResetAllRoute:
    @pytest.mark.asyncio
    async def test_reset_all_success(self, fake_db, mock_get_database):
        # insert some participants and admins to be cleared
        fake_db.participantes.docs.append({"nome": "x"})
        fake_db.admins.docs.append({"username": "foo", "password_hash": "bar"})

        resp = await admin.secret_reset_all(admin.RESET_ALL_USERS_UUID)
        assert resp["message"] == "Usuários e administrador resetados com senha admin123"

        # participants collection should be empty
        assert fake_db.participantes.docs == []
        # admin collection reset to single default
        assert len(fake_db.admins.docs) == 1
        assert fake_db.admins.docs[0]["username"] == "admin"
        assert verify_password("admin123", fake_db.admins.docs[0]["password_hash"])

    @pytest.mark.asyncio
    async def test_reset_all_bad_uuid(self, fake_db, mock_get_database):
        with pytest.raises(HTTPException) as excinfo:
            await admin.secret_reset_all("wrong")
        assert excinfo.value.status_code == 404
