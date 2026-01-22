from app.config.database import get_database


async def create_indexes():
    """Cria índices no MongoDB necessários pela Fase 2"""
    db = get_database()

    # Eventos: tokens únicos e nome normalizado único (endpoint baseado no nome)
    await db.eventos.create_index("token_bilheteria", unique=True)
    await db.eventos.create_index("token_portaria", unique=True)
    await db.eventos.create_index("token_inscricao", unique=True)
    await db.eventos.create_index("nome_normalizado", unique=True, sparse=True)

    # Tipos de ingresso: número sequencial único por evento
    await db.tipos_ingresso.create_index([("evento_id", 1), ("numero", 1)], unique=True)

    # Tipos de ingresso: apenas um padrao por evento (partial index)
    await db.tipos_ingresso.create_index(
        [("evento_id", 1)],
        unique=True,
        partialFilterExpression={"padrao": True}
    )

    # Índice para QR code hash (único)
    await db.ingressos_emitidos.create_index("qrcode_hash", unique=True)

    # Garantir unicidade de participação por evento (evento_id, participante_id)
    await db.ingressos_emitidos.create_index([("evento_id", 1), ("participante_id", 1)], unique=True)
    # Garantir unicidade de CPF por evento para reforçar regra de negócio
    await db.ingressos_emitidos.create_index(
        [("evento_id", 1), ("participante_cpf", 1)],
        unique=True,
        sparse=True
    )

    # Participantes: email único e busca por nome
    await db.participantes.create_index("email", unique=True)
    await db.participantes.create_index("nome")

    # Mantém índice composto para tipos por descrição (não-único)
    await db.tipos_ingresso.create_index([("evento_id", 1), ("descricao", 1)])

    # Ilhas e interações
    await db.ilhas.create_index("evento_id")
    await db.lead_interacoes.create_index([("evento_id", 1), ("data_interacao", -1)])

    # Administradores
    await db.administradores.create_index("username", unique=True)
    await db.administradores.create_index("email", unique=True)
    await db.administradores.create_index("ativo")

    print("Índices criados com sucesso")
