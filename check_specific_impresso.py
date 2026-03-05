#!/usr/bin/env python3
import os
from pymongo import MongoClient
from bson import ObjectId

mongodb_url = os.getenv("MONGODB_URL", "mongodb://admin:password@mongodb:27017/?authSource=admin")
client = MongoClient(mongodb_url)
db = client["ticket_manager"]

# IDs específicos dos logs do frontend
ingresso_ids = [
    "69a8d20a7556cb0bcaa44bb5",  # Brunella
    "69a8d20a7556cb0bcaa44bb3"   # Clausemberg
]

print("=" * 70)
print("VERIFICAÇÃO DIRETA NO MONGODB")
print("=" * 70)

for ing_id in ingresso_ids:
    # Buscar o participante que contém este ingresso
    participante = db.participantes.find_one(
        {"ingressos._id": ing_id},
        {"nome": 1, "ingressos.$": 1}
    )
    
    if participante and "ingressos" in participante and participante["ingressos"]:
        ing = participante["ingressos"][0]
        print(f"\n{'='*70}")
        print(f"Participante: {participante.get('nome')}")
        print(f"Ingresso ID: {ing.get('_id')}")
        print(f"\nCAMPO IMPRESSO NO MONGODB:")
        print(f"  'impresso' in ing: {'impresso' in ing}")
        print(f"  ing.get('impresso'): {ing.get('impresso')}")
        print(f"  type(ing.get('impresso')): {type(ing.get('impresso'))}")
        print(f"\nTODOS OS CAMPOS:")
        for key, value in ing.items():
            if key != 'layout_ingresso':  # Skip large nested object
                print(f"  {key}: {value}")
        print("=" * 70)
    else:
        print(f"\n✗ Ingresso {ing_id} NÃO ENCONTRADO")

print("\n" + "=" * 70)
print("FIM DA VERIFICAÇÃO")
print("=" * 70)
