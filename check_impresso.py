#!/usr/bin/env python3
from pymongo import MongoClient
from bson import ObjectId

client = MongoClient("mongodb://localhost:27017/")
db = client["ticket_manager"]

# Buscar um participante específico
p = db["participantes"].find_one(
    {"evento_id": "69a501bcfafd8b3c03ee7230"},
    {"nome": 1, "ingressos": 1}
)

if p and "ingressos" in p and p["ingressos"]:
    ing = p["ingressos"][0]
    print("=== ESTRUTURA DO INGRESSO NO MONGODB ===")
    print(f"Nome do participante: {p.get('nome')}")
    print(f"ID do ingresso: {ing.get('_id')}")
    print(f"\nCampos presentes no ingresso:")
    for key in sorted(ing.keys()):
        valor = ing[key]
        if isinstance(valor, dict) and len(str(valor)) > 100:
            print(f"  - {key}: {type(valor).__name__} (dict com {len(valor)} campos)")
        else:
            print(f"  - {key}: {type(valor).__name__} = {valor}")
    print(f"\n'impresso' in ing: {'impresso' in ing}")
    print(f"ing.get('impresso'): {ing.get('impresso')}")
else:
    print("Nenhum participante ou ingresso encontrado")
