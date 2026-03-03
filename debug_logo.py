#!/usr/bin/env python3
"""
Script para diagnosticar problema de logo não aparecendo em ingressos renderizados
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import os

async def check_logo():
    # Conectar ao MongoDB
    mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    client = AsyncIOMotorClient(mongo_uri)
    db = client.eventix
    
    print("=" * 80)
    print("DIAGNÓSTICO: Logo em Ingressos")
    print("=" * 80)
    
    # 1. Listar todos os eventos
    eventos = await db.eventos.find({}, {"_id": 1, "nome": 1, "logo_path": 1, "logo_blob": 1}).to_list(length=100)
    
    print(f"\n📋 Total de eventos: {len(eventos)}")
    
    for evento in eventos:
        print(f"\n{'='*80}")
        print(f"Evento: {evento.get('nome')}")
        print(f"ID: {evento.get('_id')}")
        print(f"logo_path: {evento.get('logo_path', 'NÃO DEFINIDO')}")
        
        logo_blob = evento.get('logo_blob')
        if logo_blob:
            print(f"✅ logo_blob PRESENTE")
            if isinstance(logo_blob, dict):
                print(f"   - content_type: {logo_blob.get('content_type')}")
                print(f"   - filename: {logo_blob.get('filename')}")
                data = logo_blob.get('data', '')
                print(f"   - data (base64): {len(data)} caracteres")
                if len(data) > 0:
                    print(f"   - primeiros 50 chars: {data[:50]}")
            else:
                print(f"   - ERRO: logo_blob não é dict, é {type(logo_blob)}")
        else:
            print(f"❌ logo_blob AUSENTE")
        
        # Verificar layout
        layout = evento.get('layout_ingresso')
        if layout:
            elements = layout.get('elements', [])
            logo_elements = [el for el in elements if el.get('type') == 'logo']
            print(f"\n📐 Layout do evento:")
            print(f"   - Total de elementos: {len(elements)}")
            print(f"   - Elementos do tipo 'logo': {len(logo_elements)}")
            
            for i, logo_el in enumerate(logo_elements):
                print(f"\n   Logo #{i+1}:")
                print(f"      - value: {logo_el.get('value', 'N/A')}")
                print(f"      - size_mm: {logo_el.get('size_mm', 30)}")
                print(f"      - x: {logo_el.get('x', 0)}, y: {logo_el.get('y', 0)}")
                print(f"      - horizontal_position: {logo_el.get('horizontal_position', logo_el.get('align', 'center'))}")
        else:
            print(f"❌ Layout não definido no evento")
        
        # Buscar um ingresso deste evento
        ingresso = await db.participantes.find_one(
            {"ingressos.evento_id": str(evento.get('_id'))},
            {"ingressos": {"$elemMatch": {"evento_id": str(evento.get('_id'))}}}
        )
        
        if not ingresso:
            ingresso_doc = await db.ingressos_emitidos.find_one({"evento_id": str(evento.get('_id'))})
            if ingresso_doc:
                print(f"\n🎫 Ingresso encontrado (standalone): {ingresso_doc.get('_id')}")
                layout_ing = ingresso_doc.get('layout_ingresso')
        else:
            print(f"\n🎫 Ingresso encontrado (em participante): {ingresso.get('ingressos', [{}])[0].get('_id')}")
            layout_ing = ingresso.get('ingressos', [{}])[0].get('layout_ingresso')
        
        if ingresso or ingresso_doc:
            if layout_ing:
                ing_elements = layout_ing.get('elements', [])
                ing_logo_elements = [el for el in ing_elements if el.get('type') == 'logo']
                print(f"   - Layout embedded tem {len(ing_logo_elements)} elementos 'logo'")
            else:
                print(f"   ⚠️  Layout embedded não foi gerado ainda")
    
    print(f"\n{'='*80}")
    print("DIAGNÓSTICO COMPLETO")
    print(f"{'='*80}\n")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(check_logo())
