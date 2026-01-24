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
from typing import Dict, Any, Tuple, Optional

router = APIRouter()


# ==================== HELPER FUNCTIONS ====================

def _get_font(size: int = 14) -> ImageFont.ImageFont:
    """Get font with fallback to default."""
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except Exception:
        return ImageFont.load_default()


def _mm_to_px(val_mm: float, dpi: int) -> int:
    """Convert millimeters to pixels at given DPI."""
    px_per_mm = dpi / 25.4
    return int(round(float(val_mm) * px_per_mm))


def _render_layout_to_image(layout: Dict[str, Any], dpi: int = 300) -> Image.Image:
    """Render a layout (with already-embedded data) to an image.
    
    Args:
        layout: Layout dict with embedded data (no placeholders)
        dpi: Dots per inch for rendering
        
    Returns:
        PIL Image object
    """
    canvas = layout.get("canvas", {})
    width_mm = float(canvas.get("width", 80))
    height_mm = float(canvas.get("height", 120))

    # compute pixel dimensions at requested DPI
    width_px = max(1, _mm_to_px(width_mm, dpi))
    height_px = max(1, _mm_to_px(height_mm, dpi))

    # For print-accurate output do not auto-downscale: use requested DPI so mm->px mapping is exact
    dpi_effective = dpi

    img_width_px = width_px
    img_height_px = height_px

    img = Image.new('RGB', (img_width_px, img_height_px), color='white')
    draw = ImageDraw.Draw(img)

    elements = layout.get("elements", [])
    # honor optional canvas padding and border
    canvas_padding_mm = float(canvas.get('padding_mm', 0))
    canvas_border = bool(canvas.get('border', False))
    if canvas_border and canvas_padding_mm >= 0:
        try:
            pad_px = _mm_to_px(canvas_padding_mm, dpi_effective)
            draw.rectangle([pad_px, pad_px, img_width_px - pad_px - 1, img_height_px - pad_px - 1], outline='black', width=2)
        except Exception:
            pass

    for el in elements:
        etype = el.get("type")
        x_mm = float(el.get('x', 0))
        y_mm = float(el.get('y', 0))
        el_margin_mm = float(el.get('margin_mm', 0) or 0)
        
        # convert margin to pixels using effective dpi
        margin_px = _mm_to_px(el_margin_mm, dpi_effective) if el_margin_mm else 0
        
        if etype == "text":
            text = str(el.get("value", ""))
            # interpret size as points (pt) and convert to pixel size using DPI so font scales physically
            size_pt = float(el.get("size", 12))
            font_px = max(1, int(round(size_pt * dpi_effective / 72.0)))
            try:
                font = ImageFont.truetype("DejaVuSans.ttf", font_px)
            except Exception:
                try:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_px)
                except Exception:
                    font = ImageFont.load_default()

            x = _mm_to_px(x_mm, dpi_effective) + margin_px
            y = _mm_to_px(y_mm, dpi_effective) + margin_px
            draw.text((x, y), text, fill='black', font=font)
            
        elif etype == "qrcode":

            qr_text = str(el.get("value", ""))
            size_mm = float(el.get("size", 30))
            # reduce QR size by margin on both sides
            try:
                adj_size_mm = max(1, size_mm - (el_margin_mm * 2))
            except Exception:
                adj_size_mm = size_mm
            size_px = _mm_to_px(adj_size_mm, dpi_effective)
            
            qr = qrcode.make(qr_text)
            qr = qr.resize((size_px, size_px))
            
            x = _mm_to_px(x_mm, dpi_effective) + margin_px
            y = _mm_to_px(y_mm, dpi_effective) + margin_px
            img.paste(qr, (x, y))
    
    return img


@router.get("/labels/generate.png")
async def generate_label_png(width_mm: float = 69, height_mm: float = 99, dpi: int = 300, text: str = "", bg: str = "white", fg: str = "black"):
    """Generate a PNG label sized by millimeters converted to pixels using the requested DPI.

    Returns a PNG image with DPI metadata suitable for consumption by mobile apps and SDKs.
    """
    # compute exact pixel dimensions (no automatic downscaling here) so physical size matches when printed
    width_px = max(1, _mm_to_px(float(width_mm), int(dpi)))
    height_px = max(1, _mm_to_px(float(height_mm), int(dpi)))

    img = Image.new('RGB', (width_px, height_px), color=bg)
    draw = ImageDraw.Draw(img)

    if text:
        # choose a font size proportional to label
        font_size = max(10, int(min(width_px, height_px) * 0.12))
        try:
            font = ImageFont.truetype("DejaVuSans.ttf", font_size)
        except Exception:
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
            except Exception:
                font = ImageFont.load_default()

        lines = str(text).split("\n")
        total_h = 0
        sizes = []
        for line in lines:
            ts = draw.textsize(line, font=font)
            sizes.append(ts)
            total_h += ts[1]
        y = (height_px - total_h) // 2
        for i, line in enumerate(lines):
            tw, th = sizes[i]
            x = (width_px - tw) // 2
            draw.text((x, y), line, font=font, fill=fg)
            y += th

    bio = BytesIO()
    # write PNG with dpi metadata
    try:
        img.save(bio, format='PNG', dpi=(dpi, dpi))
    except Exception:
        img.save(bio, format='PNG')
    bio.seek(0)

    headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Content-Disposition": f'inline; filename="label_{width_mm}x{height_mm}mm.png"'
    }
    return StreamingResponse(bio, media_type='image/png', headers=headers)


async def _fetch_ingresso_data(db, evento_id: str, ingresso_id: str) -> Tuple[Optional[Dict], Optional[Dict]]:
    """Fetch ingresso from database (embedded in participante or standalone).
    
    Args:
        db: MongoDB database instance (AsyncIOMotorDatabase)
        evento_id: ID of the event
        ingresso_id: ID of the ingresso
        
    Returns:
        Tuple of (ingresso_dict or None, participante_dict or None)
    """
    # Try to find ingresso embedded in participante first
    try:
        oid = ObjectId(ingresso_id)
    except Exception:
        oid = ingresso_id
        
    participante = await db.participantes.find_one(
        {"ingressos._id": oid}, 
        {"ingressos": {"$elemMatch": {"_id": oid}}, "nome": 1, "email": 1, "cpf": 1}
    )
    
    if participante and participante.get("ingressos"):
        return participante["ingressos"][0], participante
    
    # Fallback to standalone collection
    try:
        ingresso = await db.ingressos_emitidos.find_one(
            {"_id": ObjectId(ingresso_id), "evento_id": evento_id}
        )
    except Exception:
        ingresso = await db.ingressos_emitidos.find_one(
            {"_id": ingresso_id, "evento_id": evento_id}
        )
    
    return ingresso, None


async def _get_or_create_embedded_layout(db, ingresso: Dict, evento_id: str, from_participante: bool, participante: Optional[Dict]) -> Dict:
    """Get embedded layout from ingresso or create and persist it.
    
    Args:
        db: MongoDB database instance (AsyncIOMotorDatabase)
        ingresso: Ingresso document dict
        evento_id: ID of the event
        from_participante: Whether ingresso was found embedded in participante
        participante: Participante document dict or None
        
    Returns:
        Embedded layout dict with all placeholders replaced
    """
    layout = ingresso.get("layout_ingresso")
    
    if layout:
        return layout
    
    # Need to create embedded layout
    evento = await db.eventos.find_one({"_id": ObjectId(evento_id)})
    if not evento:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evento não encontrado")
    
    # Load related data for embedding
    if not participante and ingresso.get("participante_id"):
        try:
            participante = await db.participantes.find_one({"_id": ObjectId(ingresso.get("participante_id"))})
        except Exception:
            participante = await db.participantes.find_one({"_id": ingresso.get("participante_id")})
    
    tipo = None
    if ingresso.get("tipo_ingresso_id"):
        try:
            tipo = await db.tipos_ingresso.find_one({"_id": ObjectId(ingresso.get("tipo_ingresso_id"))})
        except Exception:
            tipo = await db.tipos_ingresso.find_one({"_id": ingresso.get("tipo_ingresso_id")})
    
    # Create embedded layout
    from app.utils.layouts import embed_layout
    base_layout = evento.get("layout_ingresso")
    embedded = embed_layout(base_layout, participante or {}, tipo or {}, evento or {}, ingresso)
    
    # Persist embedded layout
    try:
        if from_participante and participante:
            pid = participante.get("_id")
            try:
                ing_oid = ObjectId(ingresso.get("_id"))
            except Exception:
                ing_oid = ingresso.get("_id")
            await db.participantes.update_one(
                {"_id": pid, "ingressos._id": ing_oid}, 
                {"$set": {"ingressos.$.layout_ingresso": embedded}}
            )
        else:
            try:
                oid = ObjectId(ingresso.get("_id"))
            except Exception:
                oid = ingresso.get("_id")
            await db.ingressos_emitidos.update_one(
                {"_id": oid}, 
                {"$set": {"layout_ingresso": embedded}}
            )
    except Exception as e:
        logger.warning(f"Failed to persist embedded layout: {e}")
    
    return embedded


@router.get("/{evento_id}/ingresso/{ingresso_id}/render.jpg")
async def render_ingresso_jpg(evento_id: str, ingresso_id: str, dpi: int = 300, request: Request = None):
    """Renderiza o ingresso como JPG usando o layout embutido nos dados do ingresso emitido."""
    db = get_database()
    
    # Fetch ingresso data (with embedded layout)
    ingresso, participante = await _fetch_ingresso_data(db, evento_id, ingresso_id)
    
    if not ingresso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Ingresso não encontrado para este evento"
        )
    
    # Get or create embedded layout
    from_participante = participante is not None
    layout = await _get_or_create_embedded_layout(
        db, ingresso, evento_id, from_participante, participante
    )
    
    # Render layout to image
    img = _render_layout_to_image(layout, dpi)
    
    # Serialize to JPEG
    bio = BytesIO()
    img.save(bio, format='JPEG', quality=85)
    bio.seek(0)
    
    # Persist rendered image to disk for caching
    try:
        out_dir = Path('app') / 'static' / 'ingressos'
        out_dir.mkdir(parents=True, exist_ok=True)
        file_path = out_dir / f"{ingresso_id}.jpg"
        with open(file_path, 'wb') as f:
            f.write(bio.getvalue())
        logger.info(f"Saved rendered ingresso image to {file_path}")
    except Exception as e:
        logger.warning(f"Failed to save rendered image: {e}")
    
    # Generate cache headers
    from email.utils import format_datetime, parsedate_to_datetime
    etag_src = (ingresso.get('qrcode_hash', '') or '') + str(ingresso.get('data_emissao', ''))
    etag = hashlib.sha1(etag_src.encode()).hexdigest()
    
    # Check conditional request headers
    if request and hasattr(request, 'headers') and request.headers:
        req_headers = {k.lower(): v for k, v in request.headers.items()}
        
        # If-None-Match
        if req_headers.get('if-none-match') == etag:
            return Response(status_code=304, headers={"ETag": etag})
        
        # If-Modified-Since
        ims = req_headers.get('if-modified-since')
        if ims and ingresso.get('data_emissao'):
            try:
                ims_dt = parsedate_to_datetime(ims)
                if ims_dt.tzinfo is None:
                    ims_dt = ims_dt.replace(tzinfo=timezone.utc)
                    
                de = ingresso.get('data_emissao')
                if isinstance(de, str):
                    de = parsedate_to_datetime(de)
                if de.tzinfo is None:
                    de = de.replace(tzinfo=timezone.utc)
                    
                if ims_dt >= de:
                    return Response(
                        status_code=304, 
                        headers={"ETag": etag, "Last-Modified": format_datetime(de)}
                    )
            except Exception:
                pass
    
    # Build response headers
    headers = {"Cache-Control": "public, max-age=0, must-revalidate", "ETag": etag}
    if ingresso.get('data_emissao'):
        try:
            headers["Last-Modified"] = format_datetime(ingresso.get('data_emissao'))
        except Exception:
            pass
    
    bio.seek(0)
    return StreamingResponse(bio, media_type='image/jpeg', headers=headers)


@router.post("/{evento_id}/ingresso/{ingresso_id}/render")
async def render_ingresso_from_payload(evento_id: str, ingresso_id: str, payload: dict = None, dpi: int = 300):
    """Renderiza ingresso a partir de um payload JSON enviado.
    
    Prioridade do layout: payload.layout_ingresso -> ingresso.layout_ingresso -> evento
    Retorna a imagem JPG gerada inline.
    """
    db = get_database()
    
    # Fetch ingresso to validate existence
    ingresso, _ = await _fetch_ingresso_data(db, evento_id, ingresso_id)
    
    if not ingresso:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingresso não encontrado")
    
    # Determine layout to use
    layout = None
    if payload and isinstance(payload, dict):
        if "layout_ingresso" in payload:
            layout = payload.get("layout_ingresso")
        elif "ingresso" in payload and isinstance(payload.get("ingresso"), dict):
            layout = payload.get("ingresso").get("layout_ingresso")
    
    # Fallback to ingresso's embedded layout
    if not layout:
        layout = ingresso.get("layout_ingresso")
    
    # Final fallback: load from tipo or evento
    if not layout:
        tipo = None
        if ingresso.get("tipo_ingresso_id"):
            try:
                tipo = await db.tipos_ingresso.find_one({"_id": ObjectId(ingresso.get("tipo_ingresso_id"))})
            except Exception:
                tipo = await db.tipos_ingresso.find_one({"_id": ingresso.get("tipo_ingresso_id")})
        
        evento = await db.eventos.find_one({"_id": ObjectId(evento_id)})
        if not evento:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evento não encontrado")
        
        if tipo and tipo.get("layout_ingresso"):
            layout = tipo.get("layout_ingresso")
        else:
            layout = evento.get("layout_ingresso") or {
                "canvas": {"width": 80, "height": 120, "unit": "mm"}, 
                "elements": []
            }
    
    # Render layout to image
    img = _render_layout_to_image(layout, dpi)
    
    # Serialize to JPEG
    bio = BytesIO()
    img.save(bio, format='JPEG', quality=85)
    bio.seek(0)
    
    # Persist file
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
    """Retorna metadados do ingresso (nome, tipo, data de emissão)."""
    db = get_database()
    
    # Fetch ingresso data
    ingresso, participante = await _fetch_ingresso_data(db, evento_id, ingresso_id)
    
    if not ingresso:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingresso não encontrado")
    
    # Load participante if not already loaded
    if not participante and ingresso.get("participante_id"):
        try:
            participante = await db.participantes.find_one({"_id": ObjectId(ingresso.get("participante_id"))})
        except Exception:
            participante = await db.participantes.find_one({"_id": ingresso.get("participante_id")})
    
    # Load tipo
    tipo = None
    if ingresso.get("tipo_ingresso_id"):
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
    """Recebe foto capturada pelo usuário e salva localmente vinculada ao ingresso."""
    db = get_database()
    
    # Fetch ingresso data
    ingresso, participante = await _fetch_ingresso_data(db, evento_id, ingresso_id)
    from_participante = participante is not None
    
    if not ingresso:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingresso não encontrado")
    
    # Save captured image
    contents = await file.read()
    out_dir = Path('app') / 'static' / 'ingressos'
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{ingresso_id}_capture.jpg"
    path = out_dir / filename
    path.write_bytes(contents)
    
    # Update database with capture info
    ts = datetime.now(timezone.utc)
    try:
        if from_participante:
            try:
                ing_oid = ObjectId(ingresso.get("_id"))
            except Exception:
                ing_oid = ingresso.get("_id")
            await db.participantes.update_one(
                {"ingressos._id": ing_oid}, 
                {"$set": {
                    "ingressos.$.captured_image_path": str(path), 
                    "ingressos.$.captured_at": ts
                }}
            )
        else:
            try:
                oid = ObjectId(ingresso.get("_id"))
            except Exception:
                oid = ingresso.get("_id")
            await db.ingressos_emitidos.update_one(
                {"_id": oid}, 
                {"$set": {
                    "captured_image_path": str(path), 
                    "captured_at": ts
                }}
            )
    except Exception as e:
        logger.warning(f"Failed to persist capture info for ingresso {ingresso_id}: {e}")
    
    logger.info(f"Captured image saved for ingresso {ingresso_id} -> {path}")
    
    return {"message": "captured", "path": str(path)}
