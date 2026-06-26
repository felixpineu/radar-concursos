# -*- coding: utf-8 -*-
"""
filters.py — Perfil de interesse da Fórum Estudante.
Partilhado por TODAS as fontes (TED, BASE, DR), para o critério ser uniforme.
Cada fonte devolve oportunidades normalizadas; aqui decide-se relevância e score.
"""

# Prefixos CPV de interesse (match por prefixo: "79952" apanha 79952000, 79952100, ...)
CPV_INCLUIR = [
    # Eventos, congressos, seminários, feiras
    "79952", "79951", "79956", "79950",
    # Comunicação, publicidade, marketing, RP, design gráfico, fotografia
    "79340", "79341", "79342", "79416", "79822", "79961", "79970", "79413",
    # Produção audiovisual, vídeo, conteúdos, cultura
    "92111", "92112", "92211", "92400",
    # Educação e formação
    "80400", "80500", "80510", "80520", "80521", "80522", "80530",
    # TI, desenvolvimento web, software, internet, CRM
    "72200", "72210", "72212", "72400", "72410", "72413", "72420",
    "48000", "48445", "48700",
]

TERMOS_INTERESSE = [
    "comunicação", "campanha", "marketing", "evento", "congresso", "conferência",
    "seminário", "workshop", "bootcamp", "academia", "formação", "educa",
    "vídeo", "audiovisual", "produção", "conteúdos", "design", "branding",
    "redes sociais", "website", "site", "plataforma", "digital", "literacia",
    "juventude", "empregabilidade", "assessoria", "relações públicas",
    "fotografia", "publicidade", "consultoria",
]

TERMOS_EXCLUIR = [
    "obras", "construção", "empreitada", "engenharia", "arquitetura", "limpeza",
    "vigilância", "segurança", "alimentação", "catering", "refeições", "hospitalar",
    "clínico", "medicament", "viatura", "combustível", "mobiliário", "agrícola",
    "florestal", "resíduos", "saneamento", "abastecimento de água", "seguro",
]


def interessa(op):
    """op normalizada: precisa de 'titulo' (str) e 'cpvs' (lista de str).
    Devolve (incluir: bool, score: int, motivos: list[str])."""
    titulo = (op.get("titulo") or "").lower()
    for t in TERMOS_EXCLUIR:
        if t in titulo:
            return (False, 0, [])

    cpvs = op.get("cpvs") or []
    cpv_hit = any(any(str(c).startswith(p) for p in CPV_INCLUIR) for c in cpvs)
    termos = sorted({t for t in TERMOS_INTERESSE if t in titulo})

    score = (2 if cpv_hit else 0) + len(termos)
    motivos = []
    if cpv_hit:
        motivos.append("CPV na área de interesse")
    if termos:
        motivos.append("Palavras-chave: " + ", ".join(termos[:5]))
    return (cpv_hit or bool(termos), score, motivos)


def estrelas(score):
    if score >= 4:
        return "⭐⭐⭐ Concorrer"
    if score >= 2:
        return "⭐⭐ Analisar"
    return "⭐ Apenas acompanhar"
