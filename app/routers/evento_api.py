from fastapi import APIRouter, HTTPException, status, Request, Response, UploadFile, File
from fastapi.responses import StreamingResponse
from app.config.database import get_database
from bson import ObjectId
from io import BytesIO
from pathlib import Path
from datetime import datetime, timezone
from PIL import Image, ImageDraw, ImageFont
import logging

logger = logging.getLogger(__name__)
import qrcode
import hashlib

router = APIRouter()


@router.get("/{evento_id}/ingresso/{ingresso_id}/render.jpg")
async def render_ingresso_jpg(evento_id: str, ingresso_id: str, dpi: int = 300, request: Request = None):
    """Renderiza o ingresso como JPG a partir do layout do tipo de ingresso ou do evento."""
    db = get_database()

    # Validate ingresso exists and belongs to evento
    try:
        ingresso = await db.ingressos_emitidos.find_one({"_id": ObjectId(ingresso_id), "evento_id": evento_id})
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ID de ingresso inválido")

    if not ingresso:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingresso não encontrado para este evento")

    # Load related data
    tipo = None
    if ingresso.get("tipo_ingresso_id"):
        try:
            tipo = await db.tipos_ingresso.find_one({"_id": ObjectId(ingresso.get("tipo_ingresso_id"))})
        except Exception:
            tipo = await db.tipos_ingresso.find_one({"_id": ingresso.get("tipo_ingresso_id")})

    evento = await db.eventos.find_one({"_id": ObjectId(evento_id)})
    if not evento:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evento não encontrado")

    # Prepare ETag value (based on QR hash and emission time)
    etag_src = (ingresso.get('qrcode_hash', '') or '') + str(ingresso.get('data_emissao', ''))
    etag = hashlib.sha1(etag_src.encode()).hexdigest()
    # If client provided If-None-Match and it matches, return 304
    if request is not None:
        inm = request.headers.get('if-none-match')
        if inm and inm.strip('"') == etag:
            return Response(status_code=304, headers={"ETag": etag})
        # Support If-Modified-Since: if provided and resource not modified since that date, return 304
        ims_hdr = request.headers.get('if-modified-since')
        if ims_hdr:
            try:
                from email.utils import parsedate_to_datetime
                ims = parsedate_to_datetime(ims_hdr)
                de = ingresso.get('data_emissao')
                if isinstance(de, str):
                    # try to parse ISO string
                    try:
                        from dateutil import parser as _p
                        de = _p.parse(de)
                    except Exception:
                        de = None
                if ims is not None and de is not None:
                    # normalize tz
                    if ims.tzinfo is None:
                        from datetime import timezone as _tz
                        ims = ims.replace(tzinfo=_tz.utc)
                    if de.tzinfo is None:
                        from datetime import timezone as _tz
                        de = de.replace(tzinfo=_tz.utc)
                    if de <= ims:
                        return Response(status_code=304, headers={"ETag": etag})
            except Exception:
                pass

    # Choose layout
    layout = None
    if tipo and tipo.get("layout_ingresso"):
        layout = tipo.get("layout_ingresso")
    else:
        layout = evento.get("layout_ingresso") or {"canvas": {"width": 80, "height": 120, "unit": "mm"}, "elements": []}

    canvas = layout.get("canvas", {})
    width_mm = float(canvas.get("width", 80))
    height_mm = float(canvas.get("height", 120))
    # mm -> px
    px_per_mm = dpi / 25.4
    width_px = max(1, int(round(width_mm * px_per_mm)))
    height_px = max(1, int(round(height_mm * px_per_mm)))

    img = Image.new('RGB', (width_px, height_px), color='white')
    draw = ImageDraw.Draw(img)

    # Basic font fallback
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 14)
    except Exception:
        font = ImageFont.load_default()

    # Helper to convert mm coords to px
    def mm_to_px(val_mm):
        return int(round(float(val_mm) * px_per_mm))

    # Render elements
    elements = layout.get("elements", [])
    for el in elements:
        etype = el.get("type")
        if etype == "text":
            raw = el.get("value", "")
            # replace placeholders
            text = raw.replace("{NOME}", ingresso.get("participante_id", ""))
            text = text.replace("{qrcode_hash}", ingresso.get("qrcode_hash", ""))
            text = text.replace("{TIPO_INGRESSO}", tipo.get("descricao", "") if tipo else "")
            size = int(el.get("size", 12))
            try:
                f = ImageFont.truetype("DejaVuSans.ttf", size)
            except Exception:
                f = font
            x = mm_to_px(el.get("x", 0))
            y = mm_to_px(el.get("y", 0))
            draw.text((x, y), str(text), fill='black', font=f)
        elif etype == "qrcode":
            value = el.get("value", "{qrcode_hash}")
            if value == "{qrcode_hash}":
                qr_text = ingresso.get("qrcode_hash", "")
            else:
                qr_text = str(value)
            size_mm = float(el.get("size", 30))
            size_px = mm_to_px(size_mm)
            qr = qrcode.make(qr_text)
            qr = qr.resize((size_px, size_px))
            x = mm_to_px(el.get("x", 0))
            y = mm_to_px(el.get("y", 0))
            img.paste(qr, (x, y))

    # Serialize to JPEG
    bio = BytesIO()
    img.save(bio, format='JPEG', quality=85)
    bio.seek(0)

    # Cache headers: ETag based on qrcode_hash + data_emissao
    etag_src = (ingresso.get('qrcode_hash', '') or '') + str(ingresso.get('data_emissao', ''))
    etag = hashlib.sha1(etag_src.encode()).hexdigest()
    headers = {"Cache-Control": "public, max-age=86400", "ETag": etag}

    return StreamingResponse(bio, media_type='image/jpeg', headers=headers)


@router.get("/{evento_id}/ingresso/{ingresso_id}/meta")
async def meta_ingresso(evento_id: str, ingresso_id: str):
    db = get_database()
    try:
        ingresso = await db.ingressos_emitidos.find_one({"_id": ObjectId(ingresso_id), "evento_id": evento_id})
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ID de ingresso inválido")
    if not ingresso:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingresso não encontrado")

    participante = None
    try:
        participante = await db.participantes.find_one({"_id": ObjectId(ingresso.get("participante_id"))})
    except Exception:
        participante = await db.participantes.find_one({"_id": ingresso.get("participante_id")})

    tipo = None
    try:
        tipo = await db.tipos_ingresso.find_one({"_id": ObjectId(ingresso.get("tipo_ingresso_id"))})
    except Exception:
        tipo = await db.tipos_ingresso.find_one({"_id": ingresso.get("tipo_ingresso_id")})

    return {
        "nome": participante.get("nome") if participante else "",
        "tipo": tipo.get("descricao") if tipo else "",
        "data_emissao": ingresso.get("data_emissao")
    }


@router.post("/{evento_id}/ingresso/{ingresso_id}/capture")
async def capture_ingresso(evento_id: str, ingresso_id: str, file: UploadFile = File(...)):
    # Recebe foto capturada pelo usuário e salva localmente vinculada ao ingresso.
    db = get_database()
    try:
        ingresso = await db.ingressos_emitidos.find_one({"_id": ObjectId(ingresso_id), "evento_id": evento_id})
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ID de ingresso inválido")
    if not ingresso:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingresso não encontrado")

    contents = await file.read()
    out_dir = Path('app') / 'static' / 'ingressos'
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{ingresso_id}_capture.jpg"
    path = out_dir / filename
    path.write_bytes(contents)

    # update db record with path and timestamp
    await db.ingressos_emitidos.update_one({"_id": ObjectId(ingresso.get('_id'))}, {"$set": {"captured_image_path": str(path), "captured_at": datetime.now(timezone.utc)}})

    logger.info(f"Captured image saved for ingresso {ingresso_id} -> {path}")

    return {"message": "captured", "path": str(path)}
