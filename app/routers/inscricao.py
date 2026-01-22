from fastapi import APIRouter, HTTPException, status, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, RedirectResponse

from app.config.database import get_database
from app.models.participante import ParticipanteCreate, Participante
from app.models.ingresso_emitido import IngressoEmitido
from app.config.auth import generate_qrcode_hash
from app.utils.validations import validate_cpf
from bson import ObjectId
from datetime import datetime, timezone

router = APIRouter()
templates = Jinja2Templates(directory='app/templates')



@router.get("/{evento_slug}")
async def get_inscricao_form(evento_slug: str):
    """Retorna metadados do evento para o formulário público de inscrição"""
    db = get_database()
    evento = await db.eventos.find_one({"nome_normalizado": evento_slug})
    if not evento:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evento não encontrado")

    # Apenas retorna formulário se evento aceitar inscrições
    if not evento.get('aceita_inscricoes'):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inscrições não estão habilitadas para este evento")

    # Retornar campos essenciais (nome, campos obrigatórios) — garantir que Nome/Email/CPF estejam presentes
    campos = evento.get("campos_obrigatorios_planilha", []) or []
    base = ['Nome', 'Email', 'CPF']
    for b in base:
        if b not in campos:
            campos.insert(0, b)

    return {
        "nome": evento.get("nome"),
        "campos_obrigatorios_planilha": campos
    }


@router.get("/{evento_slug}/meu-ingresso")
async def minha_pagina_meu_ingresso(request: Request, evento_slug: str):
    db = get_database()
    evento = await db.eventos.find_one({"nome_normalizado": evento_slug})
    if not evento:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evento não encontrado")
    evento["_id"] = str(evento.get("_id"))
    return templates.TemplateResponse('inscricao_meu_ingresso.html', {"request": request, "evento": evento})


@router.post("/{evento_slug}/buscar-ingresso")
async def buscar_ingresso_api(evento_slug: str, payload: dict):
    """API que busca ingresso por CPF para um evento público.

    Espera payload: {"cpf": "..."}
    Retorna {"ingresso_id": "...", "evento_id": "..."} ou 404/409.
    """
    cpf_raw = payload.get('cpf') if isinstance(payload, dict) else None
    if not cpf_raw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CPF é obrigatório")

    try:
        cpf_digits = validate_cpf(str(cpf_raw))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    db = get_database()
    evento = await db.eventos.find_one({"nome_normalizado": evento_slug})
    if not evento:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evento não encontrado")

    participant = await db.participantes.find_one({"cpf": cpf_digits})
    if not participant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participante não encontrado")

    ingresso = await db.ingressos_emitidos.find_one({"evento_id": str(evento.get("_id")), "participante_id": str(participant.get("_id"))})
    if not ingresso:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingresso não encontrado para este CPF neste evento")

    return JSONResponse({"ingresso_id": str(ingresso.get("_id")), "evento_id": ingresso.get("evento_id")})


@router.post("/{evento_slug}", status_code=status.HTTP_201_CREATED)
async def post_inscricao(evento_slug: str, participante: ParticipanteCreate):
    """Processa inscrição pública pelo nome normalizado do evento"""
    db = get_database()
    evento = await db.eventos.find_one({"nome_normalizado": evento_slug})
    if not evento:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evento não encontrado")

    if not evento.get('aceita_inscricoes'):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inscrições não estão habilitadas para este evento")

    # Valida CPF (levanta 400 se inválido)
    try:
        cpf_digits = validate_cpf(participante.cpf)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Verifica se participante com este CPF já tem ingresso para este evento
    existing_part = await db.participantes.find_one({"cpf": cpf_digits})
    if existing_part:
        # procura ingresso para este participante no evento
        ingressos = await db.ingressos_emitidos.find_one({"evento_id": str(evento["_id"]), "participante_id": str(existing_part.get("_id"))})
        if ingressos:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="CPF já inscrito neste evento")

    # Cria ou reutiliza participante
    if existing_part:
        participante_id = str(existing_part.get("_id"))
    else:
        part_dict = participante.model_dump()
        part_dict["cpf"] = cpf_digits
        result = await db.participantes.insert_one(part_dict)
        participante_id = str(result.inserted_id)

    # Encontra tipo padrão do evento
    tipo = await db.tipos_ingresso.find_one({"evento_id": str(evento["_id"]), "padrao": True})
    if not tipo:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Nenhum tipo de ingresso padrão definido para este evento")

    qrcode_hash = generate_qrcode_hash()
    ingresso_dict = {
        "evento_id": str(evento["_id"]),
        "tipo_ingresso_id": str(tipo.get("_id")),
        "participante_id": participante_id,
        "participante_cpf": cpf_digits,
        "status": "Ativo",
        "qrcode_hash": qrcode_hash,
        "data_emissao": datetime.now(timezone.utc)
    }

    result = await db.ingressos_emitidos.insert_one(ingresso_dict)
    created_ingresso = await db.ingressos_emitidos.find_one({"_id": result.inserted_id})
    created_ingresso["_id"] = str(created_ingresso["_id"])

    return {"message": "Inscrição realizada com sucesso", "ingresso": IngressoEmitido(**created_ingresso)}
