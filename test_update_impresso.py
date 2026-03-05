#!/usr/bin/env python3
import os
from pymongo import MongoClient
from bson import ObjectId

mongodb_url = os.getenv("MONGODB_URL", "mongodb://admin:password@mongodb:27017/?authSource=admin")
client = MongoClient(mongodb_url)
db = client["ticket_manager"]

ingresso_id = "69a8d20a7556cb0bcaa44bb5"  # Brunella

print("=" * 70)
print(f"TESTE: Atualizando ingresso {ingresso_id} para impresso=True")
print("=" * 70)

# Buscar valor ANTES
participante_antes = db.participantes.find_one(
    {"ingressos._id": ingresso_id},
    {"nome": 1, "ingressos.$": 1}
)

if participante_antes and "ingressos" in participante_antes:
    ing_antes = participante_antes["ingressos"][0]
    print(f"\n ANTES:")
    print(f"  Participante: {participante_antes.get('nome')}")
    print(f"  impresso: {ing_antes.get('impresso')}")

# Fazer UPDATE
print(f"\nExecutando UPDATE...")
result = db.participantes.update_one(
    {"ingressos._id": ingresso_id},
    {"$set": {"ingressos.$.impresso": True}}
)

print(f"  matched_count: {result.matched_count}")
print(f"  modified_count: {result.modified_count}")

# Buscar valor DEPOIS
participante_depois = db.participantes.find_one(
    {"ingressos._id": ingresso_id},
    {"nome": 1, "ingressos.$": 1}
)

if participante_depois and "ingressos" in participante_depois:
    ing_depois = participante_depois["ingressos"][0]
    print(f"\n DEPOIS:")
    print(f"  Participante: {participante_depois.get('nome')}")
    print(f"  impresso: {ing_depois.get('impresso')}")

print("\n" + "=" * 70)
