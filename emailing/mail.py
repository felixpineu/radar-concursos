# -*- coding: utf-8 -*-
"""
emailing/mail.py — render do briefing diário (a partir da BD) + envio por smtplib.

Seleciona os concursos ainda não enviados (emailed_at IS NULL) e não-ignorados,
ordena por score, agrupa por classificação, e envia um email HTML. Depois marca
emailed_at, para não reenviar. Inclui sempre a secção "Limitações de cobertura".

Chama-se 'emailing' (não 'email') de propósito: um pacote 'email' na raiz faria
shadow ao módulo 'email' da stdlib que o smtplib usa.
"""

import ssl
import smtplib
import datetime as dt
from email.mime.text import MIMEText
from email.utils import formataddr

import config
from database import repository
from filters.scoring import CLASSIF_ESTRELAS

ORDEM_CLASSIF = ["concorrer", "analisar", "acompanhar"]
TITULO_CLASSIF = {
    "concorrer": "⭐⭐⭐ Concorrer",
    "analisar": "⭐⭐ Analisar",
    "acompanhar": "⭐ Acompanhar",
}


def _fmt_valor(t):
    if t.base_value is None:
        return "—"
    try:
        return f"{float(t.base_value):,.2f} {t.currency}".replace(",", " ")
    except (TypeError, ValueError):
        return f"{t.base_value} {t.currency}"


def _card(t):
    fontes = ", ".join(sorted({s.source.upper() for s in t.sources})) or "—"
    link = t.sources[0].source_url if t.sources else ""
    cpvs = ", ".join(c.cpv for c in t.cpvs) or "—"
    L = ["<div style='border:1px solid #e1e4e8;border-radius:8px;padding:12px;margin:10px 0'>"]
    L.append(f"<h4 style='margin:0 0 6px'>{t.title}</h4><ul style='margin:0;padding-left:18px'>")
    L.append(f"<li><b>Entidade:</b> {t.entity.nome if t.entity else '—'}</li>")
    L.append(f"<li><b>Valor base:</b> {_fmt_valor(t)} &nbsp;|&nbsp; "
             f"<b>Prazo:</b> {t.deadline or '—'} &nbsp;|&nbsp; <b>Fonte:</b> {fontes}</li>")
    L.append(f"<li><b>CPV:</b> {cpvs} &nbsp;|&nbsp; <b>Score:</b> {t.score} "
             f"({CLASSIF_ESTRELAS.get(t.classification, t.classification)})</li>")
    if link:
        L.append(f"<li><a href='{link}'>{link}</a></li>")
    if t.ai_summary:
        L.append("<li style='margin-top:6px;color:#24292f'>"
                 f"<b>Resumo (IA):</b> {t.ai_summary}</li>")
    if t.ai_why:
        L.append(f"<li><b>Porque interessa (IA):</b> {t.ai_why}</li>")
    if t.ai_opportunities:
        L.append(f"<li><b>Oportunidades (IA):</b> {t.ai_opportunities}</li>")
    if t.ai_risks:
        L.append(f"<li><b>Riscos (IA):</b> {t.ai_risks}</li>")
    L.append("</ul></div>")
    return "\n".join(L)


def render(tenders):
    """Constrói o HTML do briefing a partir de uma lista de Tender."""
    hoje = dt.date.today().strftime("%d-%m-%Y")
    por_classe = {c: [] for c in ORDEM_CLASSIF}
    for t in tenders:
        if t.classification in por_classe:
            por_classe[t.classification].append(t)

    L = ["<html><head><meta charset='utf-8'></head>",
         "<body style='font-family:Arial,Helvetica,sans-serif;max-width:780px;color:#24292f'>"]
    L.append(f"<h1>Radar Concursos Fórum Estudante — {hoje}</h1>")
    total = sum(len(v) for v in por_classe.values())
    L.append(f"<p><b>{total}</b> concurso(s) novo(s) relevante(s) hoje.</p>")

    if total == 0:
        L.append("<p>Sem concursos novos relevantes nesta execução.</p>")
    for classe in ORDEM_CLASSIF:
        grupo = por_classe[classe]
        if not grupo:
            continue
        L.append(f"<hr><h2>{TITULO_CLASSIF[classe]} ({len(grupo)})</h2>")
        for t in grupo:
            L.append(_card(t))

    # Limitações de cobertura — sempre explícito
    L.append("<hr><h2>Limitações de cobertura</h2>")
    L.append("<p style='background:#fff8c5;border:1px solid #d4a72c;border-radius:6px;padding:10px'>"
             "Cobertura atual: <b>TED</b> (concursos europeus) e <b>BASE — Anúncios DR</b> "
             "(concursos nacionais, incluindo abaixo dos limiares, ex.: &lt; 20.000 €). "
             "Fontes Vortal/acinGov/Saphety ainda não integradas.</p>")
    L.append("</body></html>")
    return "\n".join(L)


def _enviar_smtp(html, assunto):
    if not (config.MAIL_USERNAME and config.MAIL_PASSWORD):
        return (False, "AVISO: sem MAIL_USERNAME/MAIL_PASSWORD — email não enviado.")
    msg = MIMEText(html, "html", "utf-8")
    msg["Subject"] = assunto
    msg["From"] = formataddr(("Radar Concursos", config.MAIL_FROM or config.MAIL_USERNAME))
    msg["To"] = config.MAIL_TO
    contexto = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=contexto) as s:
        s.login(config.MAIL_USERNAME, config.MAIL_PASSWORD)
        s.sendmail(config.MAIL_USERNAME, [config.MAIL_TO], msg.as_string())
    return (True, "OK — email enviado.")


def enviar_briefing(sessao, mode):
    """Envia o briefing diário dos concursos novos relevantes e marca emailed_at.
    Devolve (emailed_count:int, estado:str). Só envia em modo 'daily'."""
    if mode != "daily":
        return (0, "Modo backfill — email não enviado.")

    tenders = repository.get_unemailed(sessao)
    tenders = [t for t in tenders if t.classification in ORDEM_CLASSIF]

    html = render(tenders)
    assunto = "Radar Concursos Fórum Estudante"
    enviado, estado = _enviar_smtp(html, assunto)
    if not enviado:
        return (0, estado)

    repository.mark_emailed(sessao, [t.id for t in tenders])
    return (len(tenders), f"{estado} ({len(tenders)} concursos)")
