from fastapi import APIRouter, HTTPException, status, Request, Response, UploadFile, File
from fastapi.responses import StreamingResponse, RedirectResponse
import app.config.database as database

def get_database():
    """Runtime indirection to allow tests to monkeypatch `get_database` on this module."""
    return database.get_database()
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
    
    print(f"\n{'='*80}")
    print(f"RENDER REQUEST: evento_id={evento_id}, ingresso_id={ingresso_id}")
    print(f"{'='*80}")

    # Quick debug: write a small tick file so we can see handler was reached even if logs are not visible
    try:
        debug_dir = Path('app') / 'static' / 'ingressos'
        debug_dir.mkdir(parents=True, exist_ok=True)
        debug_file = debug_dir / f"{ingresso_id}.hit.txt"
        debug_file.write_text('handler reached')
    except Exception as _e:
        print(f"Failed to write debug hit file: {_e}")

    # Tenta localizar ingresso embutido dentro de participantes pelo _id
    ingresso = None
    participante = None
    from_participante = False
    try:
        try:
            oid = ObjectId(ingresso_id)
        except Exception:
            oid = ingresso_id
        participante = await db.participantes.find_one({"ingressos._id": oid}, {"ingressos": {"$elemMatch": {"_id": oid}}, "nome": 1, "email": 1, "telefone": 1})
        if participante and participante.get("ingressos"):
            ingresso = participante["ingressos"][0]
            from_participante = True
    except Exception:
        ingresso = None

    if not ingresso:
        # Fallback para coleção antiga
        try:
            ingresso = await db.ingressos_emitidos.find_one({"_id": ObjectId(ingresso_id), "evento_id": evento_id})
        except Exception:
            try:
                ingresso = await db.ingressos_emitidos.find_one({"_id": ingresso_id, "evento_id": evento_id})
            except Exception:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ID de ingresso inválido")

    if not ingresso:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingresso não encontrado para este evento")

    print(f"✓ Ingresso found: {ingresso.get('_id')}")

    # Load related data
    # participante pode já estar disponível quando ingresso veio de participante embutido
    if not participante:
        participante = None
        if ingresso.get("participante_id"):
            try:
                participante = await db.participantes.find_one({"_id": ObjectId(ingresso.get("participante_id"))})
            except Exception:
                try:
                    participante = await db.participantes.find_one({"_id": ingresso.get("participante_id")})
                except Exception:
                    participante = None

    if participante:
        print(f"✓ Participante found: {participante.get('nome')}")
    else:
        print(f"⚠ Participante NOT found for ID: {ingresso.get('participante_id')}")
    
    tipo = None
    if ingresso.get("tipo_ingresso_id"):
        try:
            tipo = await db.tipos_ingresso.find_one({"_id": ObjectId(ingresso.get("tipo_ingresso_id"))})
        except Exception:
            tipo = await db.tipos_ingresso.find_one({"_id": ingresso.get("tipo_ingresso_id")})
    
    if tipo:
        print(f"✓ Tipo ingresso found: {tipo.get('descricao')}")
    else:
        print(f"⚠ Tipo ingresso NOT found")

    evento = await db.eventos.find_one({"_id": ObjectId(evento_id)})
    if not evento:
        print(f"ERROR: Evento not found")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evento não encontrado")
    
    print(f"✓ Evento found: {evento.get('nome')}")

    # If ingresso does not already contain an embedded layout, create and persist one now
    layout = ingresso.get("layout_ingresso")
    if not layout:
        try:
            from app.utils.layouts import embed_layout
            # Always use event layout as base
            base_layout = evento.get("layout_ingresso")
            embedded = embed_layout(base_layout, participante or {}, tipo or {}, evento or {}, ingresso)
            layout = embedded
            # persist embedded layout: update either participante.ingressos.$.layout_ingresso or ingressos_emitidos
            try:
                if from_participante and participante:
                    pid = participante.get("_id")
                    try:
                        ing_oid = ObjectId(ingresso.get("_id"))
                    except Exception:
                        ing_oid = ingresso.get("_id")
                    await db.participantes.update_one({"_id": pid, "ingressos._id": ing_oid}, {"$set": {"ingressos.$.layout_ingresso": embedded}})
                else:
                    try:
                        oid = ObjectId(ingresso.get("_id"))
                    except Exception:
                        oid = ingresso.get("_id")
                    await db.ingressos_emitidos.update_one({"_id": oid}, {"$set": {"layout_ingresso": embedded}})
            except Exception as e:
                print(f"Failed to persist embedded layout: {e}")
            print("✓ Embedded layout into ingresso")
        except Exception as e:
            print(f"Failed to embed layout into ingresso: {e}")
            # fallback to existing sources
            layout = evento.get("layout_ingresso")
    else:
        print("✓ Using embedded layout from ingresso")

    print(f"Layout: {layout}")

    canvas = layout.get("canvas", {})
    width_mm = float(canvas.get("width", 80))
    height_mm = float(canvas.get("height", 120))
    # mm -> px
    px_per_mm = dpi / 25.4
    width_px = max(1, int(round(width_mm * px_per_mm)))
    height_px = max(1, int(round(height_mm * px_per_mm)))
    
    print(f"Canvas: {width_mm}x{height_mm}mm = {width_px}x{height_px}px @ {dpi}dpi")

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
    print(f"Rendering {len(elements)} elements...")
    
    def coord_to_mm(coord_val, canvas_mm):
        """Convert various possible stored coordinate formats to mm.
        Supported formats:
        - numeric mm (e.g. 33.3)
        - fraction (0.0-1.0) -> fraction * canvas_mm
        - percent (0-100) -> percent/100 * canvas_mm
        """
        try:
            if coord_val is None:
                return 0.0
            # if already a number
            v = float(coord_val)
            # heuristics
            if abs(v) <= 1.0:
                # treat as fraction
                return max(0.0, min(v * canvas_mm, canvas_mm))
            if 0.0 <= v <= 100.0 and v > canvas_mm:
                # likely percent (0-100)
                return max(0.0, min((v / 100.0) * canvas_mm, canvas_mm))
            # otherwise treat as mm
            return v
        except Exception:
            # fallback
            return 0.0
    
    for idx, el in enumerate(elements):
        etype = el.get("type")
        raw_x = el.get('x')
        raw_y = el.get('y')
        print(f"\nElement {idx}: type={etype}, raw_x={raw_x}, raw_y={raw_y}")
        
        # determine coordinates in mm using robust conversion
        x_mm = coord_to_mm(raw_x, width_mm)
        y_mm = coord_to_mm(raw_y, height_mm)
        
        if etype == "text":
            raw = el.get("value", "")
            print(f"  Raw value: {raw}")

            # Replace placeholders with actual data
            text = raw
            text = text.replace("{NOME}", participante.get("nome", "") if participante else "")
            text = text.replace("{CPF}", participante.get("cpf", "") if participante else "")
            text = text.replace("{EMAIL}", participante.get("email", "") if participante else "")
            text = text.replace("{qrcode_hash}", ingresso.get("qrcode_hash", ""))
            text = text.replace("{TIPO_INGRESSO}", tipo.get("descricao", "") if tipo else "")
            text = text.replace("{EVENTO_NOME}", evento.get("nome", ""))

            # Format data_evento if it exists
            data_evento_str = ""
            if evento.get("data_evento"):
                from datetime import datetime
                de = evento.get("data_evento")
                if isinstance(de, datetime):
                    data_evento_str = de.strftime("%d/%m/%Y %H:%M")
                else:
                    data_evento_str = str(de)
            text = text.replace("{DATA_EVENTO}", data_evento_str)

            print(f"  Replaced text: {text}")

            size = int(el.get("size", 12))
            try:
                f = ImageFont.truetype("DejaVuSans.ttf", size)
            except Exception:
                f = font

            # Clamp coordinates to canvas bounds (in mm)
            x_mm_clamped = max(0, min(x_mm, width_mm))
            y_mm_clamped = max(0, min(y_mm, height_mm))

            if x_mm != x_mm_clamped or y_mm != y_mm_clamped:
                print(f"  ⚠ Clamped from ({x_mm},{y_mm})mm to ({x_mm_clamped},{y_mm_clamped})mm")

            x = mm_to_px(x_mm_clamped)
            y = mm_to_px(y_mm_clamped)

            print(f"  Drawing at ({x},{y})px, size={size}, text='{text}'")
            draw.text((x, y), str(text), fill='black', font=f)

        elif etype == "qrcode":
            value = el.get("value", "{qrcode_hash}")
            if value == "{qrcode_hash}":
                qr_text = ingresso.get("qrcode_hash", "")
            else:
                qr_text = str(value)

            print(f"  QR text: {qr_text[:50]}...")

            size_mm = float(el.get("size", 30))
            size_px = mm_to_px(size_mm)
            qr = qrcode.make(qr_text)
            qr = qr.resize((size_px, size_px))

            # Clamp QR coordinates so QR fits inside canvas
            x_mm_clamped = max(0, min(x_mm, width_mm - size_mm))
            y_mm_clamped = max(0, min(y_mm, height_mm - size_mm))

            if x_mm != x_mm_clamped or y_mm != y_mm_clamped:
                print(f"  ⚠ QR clamped from ({x_mm},{y_mm})mm to ({x_mm_clamped},{y_mm_clamped})mm")

            x = mm_to_px(x_mm_clamped)
            y = mm_to_px(y_mm_clamped)

            print(f"  Drawing QR at ({x},{y})px, size={size_px}px")
            img.paste(qr, (x, y))

    print(f"\n✓ Rendering complete, saving to JPEG...")
    # Serialize to JPEG
    bio = BytesIO()
    img.save(bio, format='JPEG', quality=85)
    bio.seek(0)

    # Persist rendered image to disk for debugging/caching (filename = ingresso_id.jpg)
    try:
        out_dir = Path('app') / 'static' / 'ingressos'
        out_dir.mkdir(parents=True, exist_ok=True)
        file_path = out_dir / f"{ingresso_id}.jpg"
        with open(file_path, 'wb') as f:
            f.write(bio.getvalue())
        logger.info(f"Saved rendered ingresso image to {file_path}")
    except Exception as e:
        logger.exception(f"Failed to save rendered image: {e}")

    # Cache headers: compute ETag based on qrcode_hash + data_emissao to match test expectations
    # and include Last-Modified from data_emissao
    from email.utils import format_datetime, parsedate_to_datetime
    etag_src = (ingresso.get('qrcode_hash', '') or '') + str(ingresso.get('data_emissao', ''))
    etag = hashlib.sha1(etag_src.encode()).hexdigest()

    # Check conditional request headers (tests pass a FakeRequest with .headers dict)
    try:
        if request and hasattr(request, 'headers') and request.headers:
            # support lowercase header keys used by FakeRequest
            req_headers = {k.lower(): v for k, v in request.headers.items()}
            # If-None-Match
            inm = req_headers.get('if-none-match')
            if inm and inm == etag:
                return Response(status_code=304, headers={"ETag": etag})
            # If-Modified-Since
            ims = req_headers.get('if-modified-since')
            if ims and ingresso.get('data_emissao'):
                try:
                    ims_dt = parsedate_to_datetime(ims)
                    # if ims is >= data_emissao, resource not modified
                    if ims_dt.tzinfo is None:
                        ims_dt = ims_dt.replace(tzinfo=timezone.utc)
                    de = ingresso.get('data_emissao')
                    if isinstance(de, str):
                        # attempt parse
                        de = parsedate_to_datetime(de)
                    if de.tzinfo is None:
                        de = de.replace(tzinfo=timezone.utc)
                    if ims_dt >= de:
                        return Response(status_code=304, headers={"ETag": etag, "Last-Modified": format_datetime(de)})
                except Exception:
                    pass
    except Exception:
        pass

    # Force revalidation so updated layouts force fresh render
    headers = {"Cache-Control": "public, max-age=0, must-revalidate", "ETag": etag}
    # include Last-Modified when data_emissao available
    if ingresso.get('data_emissao'):
        try:
            headers["Last-Modified"] = format_datetime(ingresso.get('data_emissao'))
        except Exception:
            pass

    print(f"✓ Returning JPEG image with ETag: {etag}")
    print(f"{'='*80}\n")

    # Reset buffer position for streaming
    bio.seek(0)
    # Return the image inline as StreamingResponse (tests expect inline image)
    return StreamingResponse(bio, media_type='image/jpeg', headers=headers)


@router.post("/{evento_id}/ingresso/{ingresso_id}/render")
async def render_ingresso_from_payload(evento_id: str, ingresso_id: str, payload: dict = None, dpi: int = 300):
    """Renderiza ingresso a partir de um payload JSON enviado (ex: o próprio ingresso com layout_ingresso).
    Prioridade do layout: payload.layout_ingresso -> ingresso.layout_ingresso -> evento
    Retorna a imagem JPG gerada inline."""
    db = get_database()

    # fetch ingresso from DB to validate existence (support embedded ingressos)
    db = get_database()
    ingresso_db = None
    try:
        oid = ObjectId(ingresso_id)
    except Exception:
        oid = ingresso_id
    try:
        participante = await db.participantes.find_one({"ingressos._id": oid}, {"ingressos": {"$elemMatch": {"_id": oid}}})
        if participante and participante.get("ingressos"):
            ingresso_db = participante["ingressos"][0]
    except Exception:
        ingresso_db = None

    if not ingresso_db:
        try:
            ingresso_db = await db.ingressos_emitidos.find_one({"_id": ObjectId(ingresso_id), "evento_id": evento_id})
        except Exception:
            ingresso_db = await db.ingressos_emitidos.find_one({"_id": ingresso_id, "evento_id": evento_id})

    if not ingresso_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingresso não encontrado")

    # prefer layout from payload if provided
    layout = None
    if payload and isinstance(payload, dict):
        if "layout_ingresso" in payload:
            layout = payload.get("layout_ingresso")
        # if payload contains full ingresso doc with layout
        elif "ingresso" in payload and isinstance(payload.get("ingresso"), dict):
            layout = payload.get("ingresso").get("layout_ingresso")

    # if no payload layout, prefer layout on ingresso document itself
    if not layout:
        layout = ingresso_db.get("layout_ingresso")

    # load tipo and evento for fallback
    tipo = None
    if ingresso_db.get("tipo_ingresso_id"):
        try:
            tipo = await db.tipos_ingresso.find_one({"_id": ObjectId(ingresso_db.get("tipo_ingresso_id"))})
        except Exception:
            tipo = await db.tipos_ingresso.find_one({"_id": ingresso_db.get("tipo_ingresso_id")})

    evento = await db.eventos.find_one({"_id": ObjectId(evento_id)})
    if not evento:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evento não encontrado")

    # final fallback
    if not layout:
        if tipo and tipo.get("layout_ingresso"):
            layout = tipo.get("layout_ingresso")
        else:
            layout = evento.get("layout_ingresso") or {"canvas": {"width": 80, "height": 120, "unit": "mm"}, "elements": []}

    # Now generate image using same logic as GET handler
    canvas = layout.get("canvas", {})
    width_mm = float(canvas.get("width", 80))
    height_mm = float(canvas.get("height", 120))
    px_per_mm = dpi / 25.4
    width_px = max(1, int(round(width_mm * px_per_mm)))
    height_px = max(1, int(round(height_mm * px_per_mm)))

    img = Image.new('RGB', (width_px, height_px), color='white')
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 14)
    except Exception:
        font = ImageFont.load_default()

    def mm_to_px(val_mm):
        return int(round(float(val_mm) * px_per_mm))

    # get participante
    participante = None
    if ingresso_db.get("participante_id"):
        try:
            participante = await db.participantes.find_one({"_id": ObjectId(ingresso_db.get("participante_id"))})
        except Exception:
            participante = await db.participantes.find_one({"_id": ingresso_db.get("participante_id")})

    elements = layout.get("elements", [])
    for idx, el in enumerate(elements):
        etype = el.get("type")
        # reuse coord conversion helper logic
        def coord_to_mm(coord_val, canvas_mm):
            try:
                if coord_val is None:
                    return 0.0
                v = float(coord_val)
                if abs(v) <= 1.0:
                    return max(0.0, min(v * canvas_mm, canvas_mm))
                if 0.0 <= v <= 100.0 and v > canvas_mm:
                    return max(0.0, min((v / 100.0) * canvas_mm, canvas_mm))
                return v
            except Exception:
                return 0.0

        x_mm = coord_to_mm(el.get('x'), width_mm)
        y_mm = coord_to_mm(el.get('y'), height_mm)

        if etype == 'text':
            raw = el.get('value', '')
            text = raw
            text = text.replace('{NOME}', participante.get('nome', '') if participante else '')
            text = text.replace('{CPF}', participante.get('cpf', '') if participante else '')
            text = text.replace('{EMAIL}', participante.get('email', '') if participante else '')
            text = text.replace('{qrcode_hash}', ingresso_db.get('qrcode_hash', ''))
            text = text.replace('{TIPO_INGRESSO}', tipo.get('descricao', '') if tipo else '')
            text = text.replace('{EVENTO_NOME}', evento.get('nome', ''))
            data_evento_str = ''
            if evento.get('data_evento'):
                from datetime import datetime
                de = evento.get('data_evento')
                if isinstance(de, datetime):
                    data_evento_str = de.strftime('%d/%m/%Y %H:%M')
                else:
                    data_evento_str = str(de)
            text = text.replace('{DATA_EVENTO}', data_evento_str)

            size = int(el.get('size', 12))
            try:
                f = ImageFont.truetype('DejaVuSans.ttf', size)
            except Exception:
                f = font

            x_mm_clamped = max(0, min(x_mm, width_mm))
            y_mm_clamped = max(0, min(y_mm, height_mm))
            x = mm_to_px(x_mm_clamped)
            y = mm_to_px(y_mm_clamped)
            draw.text((x, y), str(text), fill='black', font=f)

        elif etype == 'qrcode':
            value = el.get('value', '{qrcode_hash}')
            qr_text = ingresso_db.get('qrcode_hash', '') if value == '{qrcode_hash}' else str(value)
            size_mm = float(el.get('size', 30))
            size_px = mm_to_px(size_mm)
            qr = qrcode.make(qr_text)
            qr = qr.resize((size_px, size_px))
            x_mm_clamped = max(0, min(x_mm, width_mm - size_mm))
            y_mm_clamped = max(0, min(y_mm, height_mm - size_mm))
            x = mm_to_px(x_mm_clamped)
            y = mm_to_px(y_mm_clamped)
            img.paste(qr, (x, y))

    bio = BytesIO()
    img.save(bio, format='JPEG', quality=85)
    bio.seek(0)

    # persist file
    try:
        out_dir = Path('app') / 'static' / 'ingressos'
        out_dir.mkdir(parents=True, exist_ok=True)
        file_path = out_dir / f"{ingresso_id}.jpg"
        with open(file_path, 'wb') as f:
            f.write(bio.getvalue())
    except Exception:
        pass

    bio.seek(0)
    headers = {"Cache-Control": "no-cache, no-store, must-revalidate"}
    return StreamingResponse(bio, media_type='image/jpeg', headers=headers)

@router.get("/{evento_id}/ingresso/{ingresso_id}/meta")
async def meta_ingresso(evento_id: str, ingresso_id: str):
    db = get_database()
    # support embedded ingressos in participantes first
    ingresso = None
    participante = None
    from_participante = False
    try:
        try:
            oid = ObjectId(ingresso_id)
        except Exception:
            oid = ingresso_id
        participante = await db.participantes.find_one({"ingressos._id": oid}, {"ingressos": {"$elemMatch": {"_id": oid}}, "nome": 1})
        if participante and participante.get("ingressos"):
            ingresso = participante["ingressos"][0]
            from_participante = True
    except Exception:
        ingresso = None

    if not ingresso:
        try:
            ingresso = await db.ingressos_emitidos.find_one({"_id": ObjectId(ingresso_id), "evento_id": evento_id})
        except Exception:
            ingresso = await db.ingressos_emitidos.find_one({"_id": ingresso_id, "evento_id": evento_id})

    if not ingresso:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingresso não encontrado")

    # participante might already be available when ingresso is embedded
    if not participante:
        participante = None
        if ingresso.get("participante_id"):
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
    # support embedded ingressos in participantes first
    ingresso = None
    participante = None
    from_participante = False
    try:
        try:
            oid = ObjectId(ingresso_id)
        except Exception:
            oid = ingresso_id
        participante = await db.participantes.find_one({"ingressos._id": oid}, {"ingressos": {"$elemMatch": {"_id": oid}}, "nome": 1})
        if participante and participante.get("ingressos"):
            ingresso = participante["ingressos"][0]
            from_participante = True
    except Exception:
        ingresso = None

    if not ingresso:
        try:
            ingresso = await db.ingressos_emitidos.find_one({"_id": ObjectId(ingresso_id), "evento_id": evento_id})
        except Exception:
            ingresso = await db.ingressos_emitidos.find_one({"_id": ingresso_id, "evento_id": evento_id})

    if not ingresso:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingresso não encontrado")

    contents = await file.read()
    out_dir = Path('app') / 'static' / 'ingressos'
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{ingresso_id}_capture.jpg"
    path = out_dir / filename
    path.write_bytes(contents)

    # update db record with path and timestamp, either in participante.ingressos.$ or in ingressos_emitidos
    ts = datetime.now(timezone.utc)
    try:
        if from_participante:
            try:
                ing_oid = ObjectId(ingresso.get("_id"))
            except Exception:
                ing_oid = ingresso.get("_id")
            await db.participantes.update_one({"ingressos._id": ing_oid}, {"$set": {"ingressos.$.captured_image_path": str(path), "ingressos.$.captured_at": ts}})
        else:
            try:
                oid = ObjectId(ingresso.get("_id"))
            except Exception:
                oid = ingresso.get("_id")
            await db.ingressos_emitidos.update_one({"_id": oid}, {"$set": {"captured_image_path": str(path), "captured_at": ts}})
    except Exception as e:
        logger.exception(f"Failed to persist capture info for ingresso {ingresso_id}: {e}")

    logger.info(f"Captured image saved for ingresso {ingresso_id} -> {path}")

    return {"message": "captured", "path": str(path)}
