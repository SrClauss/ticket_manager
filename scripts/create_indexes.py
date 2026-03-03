from pymongo import MongoClient
from app.config.database import settings

def main():
    client = MongoClient(settings.mongodb_url)
    db = client[settings.database_name]

    print("Criando índices para participantes.ingressos...")
    try:
        db.participantes.create_index([("ingressos.qrcode_hash", 1)], unique=True, sparse=True)
        db.participantes.create_index([("ingressos.evento_id", 1)])
        print("Índices de participantes criados")
    except Exception as e:
        print("Falha ao criar índices de participantes:", e)

    print("Criando índices em eventos...")
    try:
        db.eventos.create_index([("tipos_ingresso.numero", 1)])
        db.eventos.create_index([("token_bilheteria", 1)], unique=True)
        db.eventos.create_index([("token_portaria", 1)], unique=True)
        print("Índices de eventos criados")
    except Exception as e:
        print("Falha ao criar índices de eventos:", e)

    print("Criando índices de compatibilidade para ingressos_emitidos (se existir)")
    try:
        db.ingressos_emitidos.create_index([("qrcode_hash", 1)], unique=True)
        db.ingressos_emitidos.create_index([("evento_id", 1), ("participante_id", 1)], unique=True)
        db.ingressos_emitidos.create_index([("evento_id", 1), ("participante_cpf", 1)], unique=True, sparse=True)
        print("Índices de ingressos_emitidos criados")
    except Exception as e:
        print("Falha ao criar índices de ingressos_emitidos:", e)

    print("Concluído")

if __name__ == '__main__':
    main()
