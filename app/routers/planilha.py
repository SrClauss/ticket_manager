from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import app.config.database as database
import os

def get_database():
    """Runtime indirection to allow tests to monkeypatch `get_database` on this module."""
    return database.get_database()
from app.config.auth import verify_admin_access
from app.utils.planilha import process_planilha
from datetime import datetime, timezone
from bson import ObjectId

router = APIRouter()
templates = Jinja2Templates(directory='app/templates')


@router.post("/eventos/{evento_id}/planilha-upload", dependencies=[Depends(verify_admin_access)])
async def upload_planilha(evento_id: str, file: UploadFile = File(...)):
    db = get_database()
    try:
        evento_object_id = ObjectId(evento_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ID de evento inválido")

    evento = await db.eventos.find_one({"_id": evento_object_id})
    if not evento:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evento não encontrado")

    evento_id_str = str(evento_object_id)
    content = await file.read()

    # registrar importacao como em processamento antes de começar para permitir updates de progresso
    import_doc = {
        'evento_id': evento_id_str,
        'filename': file.filename,
        'status': 'processing',
        'relatorio': {},
        'progress': {'processed': 0},
        'created_at': datetime.now(timezone.utc)
    }
    res = await db.planilha_importacoes.insert_one(import_doc)
    import_id = str(res.inserted_id)

    try:
        report = await process_planilha(content, file.filename, evento_id_str, db, import_id=import_id)
    except ValueError as exc:
        # update import_doc as failed
        try:
            await db.planilha_importacoes.update_one({'_id': ObjectId(import_id)}, {'$set': {'status': 'failed', 'relatorio': {'errors': [str(exc)]}}})
        except Exception:
            pass
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    # registrar importacao final
    if report.get('errors'):
        if report.get('created_ingressos', 0) > 0 or report.get('created_participants', 0) > 0:
            status_val = 'partial'
        else:
            status_val = 'failed'
    else:
        status_val = 'completed'

    try:
        await db.planilha_importacoes.update_one({'_id': ObjectId(import_id)}, {'$set': {'status': status_val, 'relatorio': report, 'progress': {'processed': report.get('total', 0), 'total': report.get('total', 0)}}})
    except Exception:
        pass

    return { 'message': 'Upload processed', 'report': report, 'import_id': import_id }


# Public upload via token
@router.get('/upload/{token}', response_class=HTMLResponse)
async def public_upload_form(request: Request, token: str):
    db = get_database()
    link = await db.planilha_upload_links.find_one({'token': token})
    if not link:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Link de upload inválido')
    evento = await db.eventos.find_one({'_id': ObjectId(link.get('evento_id'))})
    if not evento:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Evento não encontrado')
    evento['_id'] = str(evento['_id'])
    return templates.TemplateResponse('upload_form.html', {'request': request, 'evento': evento, 'token': token})


@router.post('/upload/{token}', response_class=HTMLResponse)
async def public_upload(request: Request, token: str, file: UploadFile = File(...)):
    db = get_database()
    link = await db.planilha_upload_links.find_one({'token': token})
    if not link:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Link de upload inválido')
    evento_id = link.get('evento_id')
    content = await file.read()
    # registrar importacao como em processamento antes de começar
    import_doc = {
        'evento_id': evento_id,
        'filename': file.filename,
        'status': 'processing',
        'relatorio': {},
        'progress': {'processed': 0},
        'created_at': datetime.now(timezone.utc)
    }
    res = await db.planilha_importacoes.insert_one(import_doc)
    import_id = str(res.inserted_id)

    try:
        # validate only first: do not persist data yet
        report = await process_planilha(content, file.filename, evento_id, db, import_id=import_id, validate_only=True)
    except ValueError as exc:
        try:
            await db.planilha_importacoes.update_one({'_id': ObjectId(import_id)}, {'$set': {'status': 'failed', 'relatorio': {'errors': [str(exc)]}}})
        except Exception:
            pass
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    # If validation failed, delete the import record and do not keep the file
    if report.get('errors'):
        try:
            await db.planilha_importacoes.delete_one({'_id': ObjectId(import_id)})
        except Exception:
            pass
        return templates.TemplateResponse('upload_result.html', {'request': request, 'status': 'failed', 'report': report})

    # Validation passed: store the uploaded file for admin review and mark as uploaded
    uploads_dir = os.path.join('app', 'static', 'uploads')
    os.makedirs(uploads_dir, exist_ok=True)
    safe_name = file.filename.replace(' ', '_')
    file_path = os.path.join(uploads_dir, f"{import_id}_" + safe_name)
    try:
        with open(file_path, 'wb') as fh:
            fh.write(content)
    except Exception:
        # failed to save file, mark import as failed
        await db.planilha_importacoes.update_one({'_id': ObjectId(import_id)}, {'$set': {'status': 'failed', 'relatorio': {'errors': ['Erro ao salvar arquivo no servidor']}}})
        return templates.TemplateResponse('upload_result.html', {'request': request, 'status': 'failed', 'report': {'errors': ['Erro ao salvar arquivo no servidor']}})

    status_val = 'uploaded'
    try:
        await db.planilha_importacoes.update_one({'_id': ObjectId(import_id)}, {'$set': {'status': status_val, 'relatorio': report, 'file_path': file_path, 'progress': {'processed': report.get('total', 0), 'total': report.get('total', 0)}}})
    except Exception:
        pass

    return templates.TemplateResponse('upload_result.html', {'request': request, 'status': status_val, 'report': report})


@router.get('/eventos/{evento_id}/planilha-importacao/{import_id}')
async def get_importacao(evento_id: str, import_id: str):
    db = get_database()
    try:
        doc = await db.planilha_importacoes.find_one({'_id': ObjectId(import_id), 'evento_id': evento_id})
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Importacao não encontrada')
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Importacao não encontrada')
    # serializar _id para string
    doc['_id'] = str(doc['_id'])
    return doc


# Admin action: accept an uploaded (validated) import and persist participants/ingressos
@router.post('/admin/eventos/{evento_id}/planilha-importacao/{import_id}/accept', dependencies=[Depends(verify_admin_access)])
async def accept_importacao(evento_id: str, import_id: str):
    db = get_database()
    try:
        doc = await db.planilha_importacoes.find_one({'_id': ObjectId(import_id), 'evento_id': evento_id})
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Importacao não encontrada')
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Importacao não encontrada')
    # require that file_path exists
    file_path = doc.get('file_path')
    if not file_path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Nenhum arquivo associado a esta importacao')
    try:
        with open(file_path, 'rb') as fh:
            content = fh.read()
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Falha ao ler arquivo no servidor')

    # process and persist
    try:
        report = await process_planilha(content, doc.get('filename'), evento_id, db, import_id=import_id, validate_only=False)
    except ValueError as exc:
        await db.planilha_importacoes.update_one({'_id': ObjectId(import_id)}, {'$set': {'status': 'failed', 'relatorio': {'errors': [str(exc)]}}})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    # update import status based on report
    if report.get('errors'):
        status_val = 'partial' if (report.get('created_ingressos', 0) > 0 or report.get('created_participants', 0) > 0) else 'failed'
    else:
        status_val = 'completed'

    await db.planilha_importacoes.update_one({'_id': ObjectId(import_id)}, {'$set': {'status': status_val, 'relatorio': report, 'progress': {'processed': report.get('total', 0), 'total': report.get('total', 0)}}})

    return {'status': status_val, 'report': report}