#!/usr/bin/env python3
"""
Script de migração: Adiciona campo 'impresso': False aos ing ressos que não têm este campo.
"""
import os
from pymongo import MongoClient

def main():
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://admin:password@mongodb:27017/?authSource=admin")
    client = MongoClient(mongodb_url)
    db = client["ticket_manager"]
    
    print("=" * 70)
    print("MIGRAÇÃO: Adicionar campo 'impresso' aos ingressos")
    print("=" * 70)
    
    # Buscar todos os participantes
    participantes = list(db.participantes.find({}))
    
    total_participantes = len(participantes)
    total_ingressos_verificados = 0
    total_ingressos_sem_impresso = 0
    total_ingressos_atualizados = 0
    
    print(f"\n✓ Encontrados {total_participantes} participantes no banco\n")
    
    for p in participantes:
        participante_id = p["_id"]
        participante_nome = p.get("nome", "Sem nome")
        ingressos = p.get("ingressos", [])
        
        if not ingressos:
            continue
        
        ingressos_sem_campo = []
        
        for idx, ing in enumerate(ingressos):
            total_ingressos_verificados += 1
            ingresso_id = ing.get("_id", f"index-{idx}")
            
            # Verificar se o campo 'impresso' existe
            if "impresso" not in ing:
                total_ingressos_sem_impresso += 1
                ingressos_sem_campo.append((idx, ingresso_id))
                print(f"  ✗ Participante: {participante_nome}")
                print(f"    Ingresso ID: {ingresso_id}")
                print(f"    Campos presentes: {list(ing.keys())}")
                print(f"    'impresso' in campos: False")
                print(f"    → Adicionando 'impresso': False\n")
        
        # Atualizar os ingressos que não têm o campo
        if ingressos_sem_campo:
            for idx, ingresso_id in ingressos_sem_campo:
                result = db.participantes.update_one(
                    {"_id": participante_id, f"ingressos.{idx}._id": ingresso_id},
                    {"$set": {f"ingressos.{idx}.impresso": False}}
                )
                
                if result.modified_count > 0:
                    total_ingressos_atualizados += 1
                    print(f"    ✓ Atualizado ingresso {ingresso_id}")
                else:
                    # Tentar sem usar índice (caso _id seja string)
                    result = db.participantes.update_one(
                        {"_id": participante_id, "ingressos._id": ingresso_id},
                        {"$set": {"ingressos.$.impresso": False}}
                    )
                    if result.modified_count > 0:
                        total_ingressos_atualizados += 1
                        print(f"    ✓ Atualizado ingresso {ingresso_id} (método alternativo)")
    
    print("\n" + "=" * 70)
    print("RESUMO DA MIGRAÇÃO")
    print("=" * 70)
    print(f"Participantes verificados: {total_participantes}")
    print(f"Ingressos verificados: {total_ingressos_verificados}")
    print(f"Ingressos SEM campo 'impresso': {total_ingressos_sem_impresso}")
    print(f"Ingressos atualizados: {total_ingressos_atualizados}")
    print("=" * 70)
    
    if total_ingressos_sem_impresso == 0:
        print("\n✓ Todos os ingressos já possuem o campo 'impresso'!")
    elif total_ingressos_atualizados == total_ingressos_sem_impresso:
        print("\n✓ Migração concluída com sucesso!")
    else:
        print(f"\n⚠ ATENÇÃO: {total_ingressos_sem_impresso - total_ingressos_atualizados} ingressos não foram atualizados!")
    
    # Verificar um participante específico após migração
    print("\n" + "=" * 70)
    print("VERIFICAÇÃO PÓS-MIGRAÇÃO (primeiro participante com ingresso)")
    print("=" * 70)
    p = db.participantes.find_one({"ingressos.0": {"$exists": True}})
    if p and "ingressos" in p and p["ingressos"]:
        ing = p["ingressos"][0]
        print(f"Participante: {p.get('nome')}")
        print(f"Ingresso ID: {ing.get('_id')}")
        print(f"Campos no ingresso: {list(ing.keys())}")
        print(f"'impresso' in ing: {'impresso' in ing}")
        print(f"Valor de 'impresso': {ing.get('impresso')}")
    print("=" * 70)

if __name__ == "__main__":
    main()
