"""
Integration test for complete event creation and layout workflow
"""
import pytest
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from app.routers import admin_web, admin_management
from tests.conftest import FakeCollection


@pytest.mark.asyncio
async def test_complete_event_to_layout_flow():
    """
    Integration test: Create event → Set layout → Save layout → Verify
    This tests the complete workflow from event creation to layout persistence
    """
    
    # Step 1: Setup mock database
    mock_db = MagicMock()
    mock_db.eventos = FakeCollection([])
    mock_db.tipos_ingresso = FakeCollection([])
    mock_db.ingressos_emitidos = FakeCollection([])
    mock_db.participantes = FakeCollection([])
    
    # Step 2: Create an event
    evento_data = {
        "nome": "Workshop de Python Avançado",
        "data_evento": datetime.now(timezone.utc) + timedelta(days=30),
        "local": "Centro de Convenções",
        "descricao": "Workshop intensivo de Python",
        "capacidade_maxima": 100,
        "link_imagem": "https://example.com/image.jpg",
        "categorias": ["Tecnologia", "Educação"],
        "organizador": "Tech Academy",
        "layout_ingresso": {
            "canvas": {"width": 62, "height": 120, "orientation": "portrait", "padding": 5, "dpi": 300},
            "elements": []
        }
    }
    
    # Mock the evento creation
    with patch.object(admin_web, 'get_database', return_value=mock_db):
        # Insert evento directly to simulate creation
        result = await mock_db.eventos.insert_one(evento_data)
        evento_id = str(result.inserted_id)
    
    # Verify event was created
    evento = await mock_db.eventos.find_one({"_id": ObjectId(evento_id)})
    assert evento is not None
    assert evento["nome"] == "Workshop de Python Avançado"
    assert "layout_ingresso" in evento
    
    # Step 3: Load a default template
    template = await admin_web.get_layout_template("padrao")
    assert template is not None
    assert "canvas" in template
    assert "elements" in template
    
    # Step 4: Customize the layout
    custom_layout = {
        "canvas": template["canvas"],
        "elements": [
            {
                "type": "text",
                "x": 31,
                "y": 10,
                "value": "{EVENTO_NOME}",
                "size": 16,
                "font": "Arial",
                "align": "center",
                "bold": True,
                "z_index": 1
            },
            {
                "type": "qrcode",
                "x": 16,
                "y": 35,
                "value": "{qrcode_hash}",
                "size_mm": 30,
                "align": "left",
                "z_index": 2
            },
            {
                "type": "text",
                "x": 31,
                "y": 75,
                "value": "{NOME}",
                "size": 12,
                "font": "Arial",
                "align": "center",
                "bold": False,
                "z_index": 3
            },
            {
                "type": "text",
                "x": 5,
                "y": 95,
                "value": "{TIPO_INGRESSO}",
                "size": 10,
                "font": "Arial",
                "align": "left",
                "z_index": 4
            },
            {
                "type": "text",
                "x": 57,
                "y": 95,
                "value": "{DATA_EVENTO}",
                "size": 10,
                "font": "Arial",
                "align": "right",
                "z_index": 5
            }
        ]
    }
    
    # Step 5: Save the layout
    mock_request = MagicMock()
    mock_request.json = AsyncMock(return_value={"layout_ingresso": custom_layout})
    
    with patch.object(admin_web, 'get_database', return_value=mock_db):
        save_result = await admin_web.admin_evento_layout_salvar(
            evento_id=evento_id,
            request=mock_request,
            dependencies=None
        )
    
    # Verify save was successful
    assert save_result is not None
    # Extract content from JSONResponse
    import json
    result_body = save_result.body.decode('utf-8')
    result_data = json.loads(result_body)
    assert result_data.get("success") is True
    
    # Step 6: Retrieve the saved layout
    evento_updated = await mock_db.eventos.find_one({"_id": ObjectId(evento_id)})
    assert evento_updated is not None
    assert "layout_ingresso" in evento_updated
    
    saved_layout = evento_updated["layout_ingresso"]
    assert "canvas" in saved_layout
    assert "elements" in saved_layout
    assert len(saved_layout["elements"]) == 5
    
    # Verify each element type
    element_types = [el["type"] for el in saved_layout["elements"]]
    assert "text" in element_types
    assert "qrcode" in element_types
    
    # Verify text elements have proper structure
    text_elements = [el for el in saved_layout["elements"] if el["type"] == "text"]
    assert len(text_elements) == 4
    for el in text_elements:
        assert "value" in el
        assert "size" in el
        assert "align" in el
        assert "x" in el
        assert "y" in el
    
    # Verify QR code element
    qr_elements = [el for el in saved_layout["elements"] if el["type"] == "qrcode"]
    assert len(qr_elements) == 1
    assert qr_elements[0]["value"] == "{qrcode_hash}"
    assert "size_mm" in qr_elements[0]
    
    # Step 7: Verify canvas dimensions
    canvas = saved_layout["canvas"]
    assert canvas["width"] == 62
    assert canvas["height"] == 120
    assert canvas["orientation"] == "portrait"
    assert canvas["dpi"] == 300
    
    print("✓ Complete integration test passed: Event creation → Layout saving → Verification")


@pytest.mark.asyncio
async def test_event_with_tipo_ingresso_and_layout():
    """
    Test creating event with ticket types and applying layout
    """
    
    # Setup mock database
    mock_db = MagicMock()
    mock_db.eventos = FakeCollection([])
    mock_db.tipos_ingresso = FakeCollection([])
    
    # Create event
    evento_data = {
        "nome": "Conferência Tech 2026",
        "data_evento": datetime.now(timezone.utc) + timedelta(days=60),
        "local": "Auditório Central",
        "descricao": "Conferência anual de tecnologia",
        "capacidade_maxima": 500,
        "layout_ingresso": None  # No layout initially
    }
    
    with patch.object(admin_web, 'get_database', return_value=mock_db):
        result = await mock_db.eventos.insert_one(evento_data)
        evento_id = str(result.inserted_id)
    
    # Create ticket types
    tipos_data = [
        {
            "evento_id": evento_id,
            "descricao": "VIP",
            "preco": 500.0,
            "quantidade_disponivel": 50,
            "ordem": 1
        },
        {
            "evento_id": evento_id,
            "descricao": "Regular",
            "preco": 200.0,
            "quantidade_disponivel": 400,
            "ordem": 2
        },
        {
            "evento_id": evento_id,
            "descricao": "Estudante",
            "preco": 100.0,
            "quantidade_disponivel": 50,
            "ordem": 3
        }
    ]
    
    for tipo in tipos_data:
        await mock_db.tipos_ingresso.insert_one(tipo)
    
    # Verify ticket types were created
    tipos_count = await mock_db.tipos_ingresso.count_documents({"evento_id": evento_id})
    assert tipos_count == 3
    
    # Now apply a layout to the event
    layout = {
        "canvas": {"width": 80, "height": 120, "orientation": "portrait", "padding": 5, "dpi": 300},
        "elements": [
            {
                "type": "text",
                "x": 40,
                "y": 10,
                "value": "{EVENTO_NOME}",
                "size": 18,
                "font": "Arial",
                "align": "center",
                "bold": True,
                "z_index": 1
            },
            {
                "type": "text",
                "x": 40,
                "y": 30,
                "value": "{TIPO_INGRESSO}",
                "size": 14,
                "font": "Arial",
                "align": "center",
                "bold": True,
                "z_index": 2
            },
            {
                "type": "qrcode",
                "x": 25,
                "y": 45,
                "value": "{qrcode_hash}",
                "size_mm": 30,
                "align": "left",
                "z_index": 3
            },
            {
                "type": "text",
                "x": 40,
                "y": 85,
                "value": "{NOME}",
                "size": 12,
                "font": "Arial",
                "align": "center",
                "z_index": 4
            }
        ]
    }
    
    mock_request = MagicMock()
    mock_request.json = AsyncMock(return_value={"layout_ingresso": layout})
    
    with patch.object(admin_web, 'get_database', return_value=mock_db):
        save_result = await admin_web.admin_evento_layout_salvar(
            evento_id=evento_id,
            request=mock_request,
            dependencies=None
        )
    
    import json
    result_body = save_result.body.decode('utf-8')
    result_data = json.loads(result_body)
    assert result_data.get("success") is True
    
    # Verify the layout was saved
    evento = await mock_db.eventos.find_one({"_id": ObjectId(evento_id)})
    assert evento["layout_ingresso"] is not None
    assert len(evento["layout_ingresso"]["elements"]) == 4
    
    # Verify it includes ticket type placeholder
    tipo_elements = [el for el in evento["layout_ingresso"]["elements"] if "{TIPO_INGRESSO}" in el.get("value", "")]
    assert len(tipo_elements) == 1
    
    print("✓ Event with ticket types and layout test passed")


@pytest.mark.asyncio
async def test_layout_with_all_element_types():
    """
    Test layout with all supported element types: text, qrcode, logo, divider
    """
    
    mock_db = MagicMock()
    mock_db.eventos = FakeCollection([])
    mock_db.ingressos_emitidos = FakeCollection([])
    mock_db.participantes = FakeCollection([])
    
    # Create event
    evento_data = {
        "nome": "Evento Completo",
        "data_evento": datetime.now(timezone.utc) + timedelta(days=15),
        "layout_ingresso": {"canvas": {}, "elements": []}
    }
    
    result = await mock_db.eventos.insert_one(evento_data)
    evento_id = str(result.inserted_id)
    
    # Create layout with all element types
    comprehensive_layout = {
        "canvas": {"width": 80, "height": 140, "orientation": "portrait", "padding": 5, "dpi": 300},
        "elements": [
            # Text element
            {
                "type": "text",
                "x": 40,
                "y": 10,
                "value": "{EVENTO_NOME}",
                "size": 16,
                "font": "Arial",
                "align": "center",
                "bold": True,
                "z_index": 1
            },
            # Divider element
            {
                "type": "divider",
                "x": 5,
                "y": 25,
                "direction": "horizontal",
                "length_mm": 70,
                "thickness": 2,
                "z_index": 2
            },
            # QR Code element
            {
                "type": "qrcode",
                "x": 25,
                "y": 35,
                "value": "{qrcode_hash}",
                "size_mm": 30,
                "align": "left",
                "z_index": 3
            },
            # Logo element
            {
                "type": "logo",
                "x": 30,
                "y": 75,
                "value": "LOGO",
                "size_mm": 20,
                "align": "left",
                "z_index": 4
            },
            # Additional text
            {
                "type": "text",
                "x": 40,
                "y": 105,
                "value": "{NOME}",
                "size": 12,
                "font": "Arial",
                "align": "center",
                "z_index": 5
            }
        ]
    }
    
    mock_request = MagicMock()
    mock_request.json = AsyncMock(return_value={"layout_ingresso": comprehensive_layout})
    
    with patch.object(admin_web, 'get_database', return_value=mock_db):
        save_result = await admin_web.admin_evento_layout_salvar(
            evento_id=evento_id,
            request=mock_request,
            dependencies=None
        )
    
    import json
    result_body = save_result.body.decode('utf-8')
    result_data = json.loads(result_body)
    assert result_data.get("success") is True
    
    # Verify all element types are saved
    evento = await mock_db.eventos.find_one({"_id": ObjectId(evento_id)})
    saved_elements = evento["layout_ingresso"]["elements"]
    
    element_types = [el["type"] for el in saved_elements]
    assert "text" in element_types
    assert "qrcode" in element_types
    assert "logo" in element_types
    assert "divider" in element_types
    
    # Verify specific element properties
    divider = next(el for el in saved_elements if el["type"] == "divider")
    assert divider["direction"] == "horizontal"
    assert divider["length_mm"] == 70
    assert divider["thickness"] == 2
    
    logo = next(el for el in saved_elements if el["type"] == "logo")
    assert logo["size_mm"] == 20
    
    print("✓ Layout with all element types test passed")
