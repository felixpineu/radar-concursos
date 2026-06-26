# -*- coding: utf-8 -*-
"""filters/cpv.py — correspondência de CPV por prefixo."""


def match_cpvs(cpvs, pesos_cpv):
    """Para cada CPV do concurso, encontra o prefixo de maior peso que casa.
    Devolve lista de (cpv, prefixo, peso). Conta no máximo um match por CPV
    (o de maior peso), para não inflacionar com prefixos sobrepostos."""
    hits = []
    for cpv in cpvs or []:
        c = str(cpv).strip()
        melhor = None
        for prefixo, peso in pesos_cpv.items():
            if c.startswith(str(prefixo)):
                if melhor is None or peso > melhor[2]:
                    melhor = (c, str(prefixo), peso)
        if melhor:
            hits.append(melhor)
    return hits
