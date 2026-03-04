import asyncio
from io import BytesIO

from PIL import Image

from app.routers import evento_api


async def _read_all(response):
    data = b''
    async for chunk in response.body_iterator:
        data += chunk
    return data


def test_generate_label_default():
    """Basic sanity check for the label generator (portrait)."""
    resp = asyncio.run(evento_api.generate_label_png(width_mm=10, height_mm=20, dpi=100))
    assert resp.media_type == 'image/png'
    content = asyncio.run(_read_all(resp))
    img = Image.open(BytesIO(content))

    # expected pixel dims from mm->px conversion using dpi
    pxw = int(round(10 * 100 / 25.4))
    pxh = int(round(20 * 100 / 25.4))
    assert img.size == (pxw, pxh)


def test_print_label_portrait_size():
    """Printed label endpoint should produce same pixel dims in portrait."""
    resp = asyncio.run(evento_api.print_label_png(width_mm=10, height_mm=20, dpi=100))
    assert resp.media_type == 'image/png'
    content = asyncio.run(_read_all(resp))
    img = Image.open(BytesIO(content))
    pxw = int(round(10 * 100 / 25.4))
    pxh = int(round(20 * 100 / 25.4))
    assert img.size == (pxw, pxh)


def test_print_label_landscape_rotates():
    """Landscape orientation on print endpoint results in rotation but same mm size."""
    resp = asyncio.run(
        evento_api.print_label_png(width_mm=10, height_mm=20, dpi=100, orientation='landscape')
    )
    assert resp.media_type == 'image/png'
    content = asyncio.run(_read_all(resp))
    img = Image.open(BytesIO(content))
    pxw = int(round(10 * 100 / 25.4))
    pxh = int(round(20 * 100 / 25.4))
    # same pixel dims as portrait, thanks to rotation logic
    assert img.size == (pxw, pxh)


def test_print_label_orientation_case_insensitive():
    resp = asyncio.run(
        evento_api.print_label_png(width_mm=5, height_mm=8, dpi=100, orientation='LANDSCAPE')
    )
    assert resp.media_type == 'image/png'
    content = asyncio.run(_read_all(resp))
    img = Image.open(BytesIO(content))
    pxw2 = int(round(5 * 100 / 25.4))
    pxh2 = int(round(8 * 100 / 25.4))
    assert img.size == (pxw2, pxh2)


# the old orientation tests belonged to the original generate_label_png;
# orientation support has been moved to a separate endpoint.


