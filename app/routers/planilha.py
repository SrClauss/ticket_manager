from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File
from app.config.database import get_database
from app.config.auth import verify_admin_access
from app.utils.planilha import process_planilha
from datetime import datetime, timezone
from bson import ObjectId

router = APIRouter()


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
    try:
        report = await process_planilha(content, file.filename, evento_id_str, db)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    # registrar importacao
    if report.get('errors'):
        if report.get('created_ingressos', 0) > 0 or report.get('created_participants', 0) > 0:
            status = 'partial'
        else:
            status = 'failed'
    else:
        status = 'completed'

    import_doc = {
        'evento_id': evento_id_str,
        'filename': file.filename,
        'status': status,
        'relatorio': report,
        'created_at': datetime.now(timezone.utc)
    }
    await db.planilha_importacoes.insert_one(import_doc)

    return { 'message': 'Upload processed', 'report': report }
