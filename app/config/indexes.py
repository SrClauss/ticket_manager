from app.config.database import get_database


async def create_indexes():
    """Cria índices no MongoDB para melhor performance"""
    db = get_database()
    
    # Índice para tokens de eventos
    await db.eventos.create_index("token_bilheteria", unique=True)
    await db.eventos.create_index("token_portaria", unique=True)
    
    # Índice para QR code hash
    await db.ingressos_emitidos.create_index("qrcode_hash", unique=True)
    
    # Índice para busca de participantes
    await db.participantes.create_index("email", unique=True)
    await db.participantes.create_index("nome")
    
    # Índice composto para tipo de ingresso por evento
    await db.tipos_ingresso.create_index([("evento_id", 1), ("descricao", 1)])
    
    # Índice para ilhas por evento
    await db.ilhas.create_index("evento_id")
    
    # Índice para interações de leads
    await db.lead_interacoes.create_index([("evento_id", 1), ("data_interacao", -1)])
    
    # Índices para administradores
    await db.administradores.create_index("username", unique=True)
    await db.administradores.create_index("email", unique=True)
    await db.administradores.create_index("ativo")
    
    print("Índices criados com sucesso")
