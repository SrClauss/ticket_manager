import app.config.database as database


async def create_indexes():
    """Cria índices no MongoDB necessários pela Fase 2"""
    db = database.get_database()

    # Eventos: tokens únicos e nome normalizado único (endpoint baseado no nome)
    await db.eventos.create_index("token_bilheteria", unique=True)
    await db.eventos.create_index("token_portaria", unique=True)
    await db.eventos.create_index("token_inscricao", unique=True, partialFilterExpression={"token_inscricao": {"$exists": True}})
    await db.eventos.create_index("nome_normalizado", unique=True, sparse=True)

    # Tipos de ingresso: número sequencial único por evento
    await db.tipos_ingresso.create_index([("evento_id", 1), ("numero", 1)], unique=True)

    # Tipos de ingresso: apenas um padrao por evento (partial index)
    await db.tipos_ingresso.create_index(
        [("evento_id", 1)],
        unique=True,
        partialFilterExpression={"padrao": True}
    )

    # Índices para suportar ingressos embutidos em participantes
    # Índice único para qrcode dentro dos ingressos embutidos
    try:
        await db.participantes.create_index([("ingressos.qrcode_hash", 1)], unique=True, sparse=True)
    except Exception:
        pass
    # Index para consultas por evento dentro dos ingressos embutidos
    try:
        await db.participantes.create_index([("ingressos.evento_id", 1)])
    except Exception:
        pass

    # Mantém índices antigos em ingressos_emitidos para compatibilidade (se coleção existir)
    try:
        await db.ingressos_emitidos.create_index("qrcode_hash", unique=True)
        await db.ingressos_emitidos.create_index([("evento_id", 1), ("participante_id", 1)], unique=True)
        await db.ingressos_emitidos.create_index([("evento_id", 1), ("participante_cpf", 1)], unique=True, sparse=True)
    except Exception:
        pass

    # Participantes: email único e busca por nome
    await db.participantes.create_index("email", unique=True)
    await db.participantes.create_index("nome")

    # Mantém índice composto para tipos por descrição (não-único)
    await db.tipos_ingresso.create_index([("evento_id", 1), ("descricao", 1)])

    # Ilhas e interações
    await db.ilhas.create_index("evento_id")

    # Administradores
    await db.administradores.create_index("username", unique=True)
    await db.administradores.create_index("email", unique=True)
    await db.administradores.create_index("ativo")

    print("Índices criados com sucesso")
