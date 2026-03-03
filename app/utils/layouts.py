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

    # If layout defines groups, compile them into flattened elements for backward compatibility
    def compile_groups(layout_obj: Dict[str, Any]) -> list:
        """Compile `groups` into a flat list of elements with absolute coordinates.

        Expected group format (non-strict):
        {
            "x": <mm>, "y": <mm>, "elements": [ {..element..}, ... ],
            "direction": "horizontal"|"vertical" (optional), "spacing_mm": <mm> (optional)
        }

        This function is conservative: it only adjusts element coordinates by group's x/y
        and preserves element attributes. If element already has absolute x/y it will be
        offset by the group's origin.
        """
        out = []
        groups = layout_obj.get("groups") or []
        for g in groups:
            gx = float(g.get("x", 0) or 0)
            gy = float(g.get("y", 0) or 0)
            elems = g.get("elements") or []
            for el in elems:
                # copy to avoid mutating original
                el_copy = copy.deepcopy(el)
                try:
                    rel_x = float(el_copy.get("x", 0) or 0)
                except Exception:
                    rel_x = 0
                try:
                    rel_y = float(el_copy.get("y", 0) or 0)
                except Exception:
                    rel_y = 0

                # set absolute coords
                el_copy["x"] = gx + rel_x
                el_copy["y"] = gy + rel_y

                # propagate group-level align/size defaults if not present on element
                for key in ("align", "size_mm", "size", "margin_mm"):
                    if key in g and el_copy.get(key) is None:
                        el_copy[key] = g.get(key)

                out.append(el_copy)
        return out

    # derive replacement values (ensure all are strings)
    nome = str(participante.get("nome", "") if participante else "")
    cpf = str(participante.get("cpf", "") if participante else "")
    email = str(participante.get("email", "") if participante else "")
    qrcode = str(ingresso.get("qrcode_hash", "") if ingresso else "")
    tipo_desc = str(tipo.get("descricao", "") if tipo else "")
    evento_nome = str(evento.get("nome", "") if evento else "")
    data_evento_str = ""
    data_str = ""
    horario_str = ""
    data_hora_str = ""
    de = evento.get("data_evento") if evento else None
    if de:
        if isinstance(de, datetime):
            data_evento_str = de.strftime("%d/%m/%Y %H:%M")
            data_str = de.strftime("%d/%m/%Y")
            horario_str = de.strftime("%H:%M")
            data_hora_str = de.strftime("%d/%m/%Y %H:%M")
        else:
            data_evento_str = str(de)
            data_str = str(de)
            horario_str = ""
            data_hora_str = str(de)

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
        out = out.replace("{DATA}", data_str)
        out = out.replace("{HORARIO}", horario_str)
        out = out.replace("{DATA_HORA}", data_hora_str)
        return out

    elements = layout.get("elements", [])
    # merge compiled groups into elements for rendering/embedding
    if layout.get("groups"):
        try:
            compiled = compile_groups(layout)
            # Maintain original elements order first, then group elements
            elements = elements + compiled
            layout["elements"] = elements
        except Exception:
            # on any failure fall back to original elements
            pass
    # If elements reference groups by `groupId`, convert their coords to absolute using group's origin
    groups_map = {}
    try:
        for g in layout.get("groups", []) or []:
            gid = g.get("id")
            if gid:
                groups_map[gid] = g
    except Exception:
        groups_map = {}

    if groups_map:
        for el in elements:
            gid = el.get("groupId")
            if gid and gid in groups_map:
                g = groups_map[gid]
                try:
                    gx = float(g.get("x", 0) or 0)
                except Exception:
                    gx = 0
                try:
                    gy = float(g.get("y", 0) or 0)
                except Exception:
                    gy = 0
                try:
                    rel_x = float(el.get("x", 0) or 0)
                except Exception:
                    rel_x = 0
                try:
                    rel_y = float(el.get("y", 0) or 0)
                except Exception:
                    rel_y = 0

                el["x"] = gx + rel_x
                el["y"] = gy + rel_y
    for el in elements:
        if el.get("type") == "text":
            el["value"] = replace_vals(el.get("value", ""))
        elif el.get("type") == "qrcode":
            # qrcode elements may have value placeholders too
            el["value"] = replace_vals(el.get("value", "{qrcode_hash}"))
    return layout
