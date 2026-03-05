#!/usr/bin/env python3
import os
from pymongo import MongoClient

mongodb_url = os.getenv("MONGODB_URL", "mongodb://admin:password@mongodb:27017/?authSource=admin")
client = MongoClient(mongodb_url)
db = client["ticket_manager"]

print("=" * 70)
print("BUSCANDO INGRESSOS COM impresso=true NO BANCO")
print("=" * 70)

# Buscar participantes com ingressos onde impresso = true
participantes = db.participantes.find(
    {"ingressos.impresso": True},
    {"nome": 1, "ingressos": 1}
).limit(10)

count = 0
for p in participantes:
    for ing in p.get("ingressos", []):
        if ing.get("impresso") is True:
            count += 1
            print(f"\n✓ Encontrado ingresso com impresso=true:")
            print(f"  Participante: {p.get('nome')}")
            print(f"  Ingresso ID: {ing.get('_id')}")
            print(f"  impresso: {ing.get('impresso')}")
            print(f"  status: {ing.get('status')}")
            print(f"  data_emissao: {ing.get('data_emissao')}")

if count == 0:
    print("\n✗ NENHUM ingresso encontrado com impresso=true")
    print("\nVerificando total de ingressos no evento 69a501bcfafd8b3c03ee7230:")
    
    pipeline = [
        {"$match": {"evento_id": "69a501bcfafd8b3c03ee7230"}},
        {"$project": {"nome": 1, "ingressos": 1}},
        {"$unwind": "$ingressos"},
        {"$group": {
            "_id": "$ingressos.impresso",
            "count": {"$sum": 1}
        }}
    ]
    
    resultado = list(db.participantes.aggregate(pipeline))
    print("\nDistribuição de valores de 'impresso':")
    for r in resultado:
        print(f"  impresso={r['_id']}: {r['count']} ingressos")
else:
    print(f"\n✓ Total: {count} ingresso(s) com impresso=true")

print("\n" + "=" * 70)
