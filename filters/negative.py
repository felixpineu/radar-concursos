# -*- coding: utf-8 -*-
"""filters/negative.py — exclusões fortes e penalizações.

Os termos negativos são radicais/expressões (ex.: 'radiolog', 'cirurg') e por isso
casam por SUBSTRING no texto em minúsculas (com acentos), tal como no filtro v2."""


def match_negativos(texto_lower, pesos_negativos):
    """Devolve lista de (termo, peso<0) presentes no texto."""
    return [(str(t), peso) for t, peso in pesos_negativos.items()
            if str(t).lower() in texto_lower]


def hard_excluido(texto_lower, termos_hard):
    """Devolve o primeiro termo de hard_exclude presente, ou None."""
    for t in termos_hard or []:
        if str(t).lower() in texto_lower:
            return str(t)
    return None
