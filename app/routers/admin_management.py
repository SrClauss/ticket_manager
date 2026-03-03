from fastapi import APIRouter, HTTPException, status, Depends, Request, Body
from typing import List
from app.models.admin import Admin, AdminCreate, AdminUpdate
from app.config.auth import (
    verify_admin_access,
    get_all_admins,
    create_admin,
    update_admin,
    delete_admin,
    get_admin_by_id
)

router = APIRouter()


@router.get("/admins", response_model=List[Admin], dependencies=[Depends(verify_admin_access)])
async def list_admins():
    """Lista todos os administradores ativos"""
    return await get_all_admins()


@router.post("/admins", response_model=Admin, dependencies=[Depends(verify_admin_access)])
async def create_new_admin(admin_data: AdminCreate):
    """Cria um novo administrador"""
    return await create_admin(admin_data)


@router.get("/admins/{admin_id}", response_model=Admin, dependencies=[Depends(verify_admin_access)])
async def get_admin(admin_id: str):
    """Obtém um administrador específico"""
    admin = await get_admin_by_id(admin_id)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Administrador não encontrado"
        )
    return admin


@router.put("/admins/{admin_id}", response_model=Admin, dependencies=[Depends(verify_admin_access)])
async def update_existing_admin(admin_id: str, request: Request, admin_payload: dict = Body(...)):
    """Atualiza um administrador. Loga payload recebido para depuração e valida depois com Pydantic."""
    # Print payload to stdout to ensure visibility in uvicorn logs
    print(f"PUT /admins/{admin_id} payload: {admin_payload}")
    # Validate payload using Pydantic model and return clear 422 on validation error
    from pydantic import ValidationError
    try:
        admin_data = AdminUpdate(**admin_payload)
    except ValidationError as e:
        print(f"Validation error for /admins/{admin_id}: {e}")
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.errors())
    return await update_admin(admin_id, admin_data)


@router.delete("/admins/{admin_id}", dependencies=[Depends(verify_admin_access)])
async def delete_existing_admin(admin_id: str):
    """Remove um administrador (desativa)"""
    success = await delete_admin(admin_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Administrador não encontrado"
        )
    return {"message": "Administrador removido com sucesso"}