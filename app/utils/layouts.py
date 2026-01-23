from typing import Dict, Any


def embed_layout(layout_template: Dict[str, Any], participante: Dict[str, Any], tipo: Dict[str, Any], evento: Dict[str, Any], ingresso: Dict[str, Any]) -> Dict[str, Any]:
    """Return a deep-copied layout with element values replaced by provided data.

    Supports placeholder variants: {NOME}, {participante_nome}, {CPF}, {EMAIL}, {qrcode_hash},
    {TIPO_INGRESSO}, {EVENTO_NOME}, {DATA_EVENTO}.
    Coordinates are left untouched.
    """
    import copy
    from datetime import datetime

    if not layout_template:
        return {"canvas": {"width": 80, "height": 120, "unit": "mm"}, "elements": []}

    layout = copy.deepcopy(layout_template)

    # derive replacement values (ensure all are strings)
    nome = str(participante.get("nome", "") if participante else "")
    cpf = str(participante.get("cpf", "") if participante else "")
    email = str(participante.get("email", "") if participante else "")
    qrcode = str(ingresso.get("qrcode_hash", "") if ingresso else "")
    tipo_desc = str(tipo.get("descricao", "") if tipo else "")
    evento_nome = str(evento.get("nome", "") if evento else "")
    data_evento_str = ""
    de = evento.get("data_evento") if evento else None
    if de:
        if isinstance(de, datetime):
            data_evento_str = de.strftime("%d/%m/%Y %H:%M")
        else:
            data_evento_str = str(de)

    def replace_vals(s: str) -> str:
        if not isinstance(s, str):
            return s
        out = s
        out = out.replace("{NOME}", nome)
        out = out.replace("{participante_nome}", nome)
        out = out.replace("{CPF}", cpf)
        out = out.replace("{EMAIL}", email)
        out = out.replace("{qrcode_hash}", qrcode)
        out = out.replace("{TIPO_INGRESSO}", tipo_desc)
        out = out.replace("{EVENTO_NOME}", evento_nome)
        out = out.replace("{DATA_EVENTO}", data_evento_str)
        return out

    elements = layout.get("elements", [])
    for el in elements:
        if el.get("type") == "text":
            el["value"] = replace_vals(el.get("value", ""))
        elif el.get("type") == "qrcode":
            # qrcode elements may have value placeholders too
            el["value"] = replace_vals(el.get("value", "{qrcode_hash}"))
    return layout
