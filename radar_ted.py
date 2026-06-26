#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Radar de Contratação Pública — Fórum Estudante (componente cloud TED)
--------------------------------------------------------------------
Consulta a Search API do TED (Tenders Electronic Daily), anónima e gratuita,
filtra os anúncios pelas áreas de interesse da Fórum Estudante e produz um
briefing HTML (briefing.html). Pensado para correr na cloud (GitHub Actions),
sem depender do computador do utilizador.

- Sem dependências externas (só biblioteca-padrão do Python).
- A Search API do TED NÃO exige chave: POST https://api.ted.europa.eu/v3/notices/search
  (validado: query "buyer-country=PRT AND publication-date>=YYYYMMDD" devolve JSON).
- O envio de email é feito pelo workflow do GitHub Actions (ver radar.yml).

Limite conhecido: o TED só cobre concursos ACIMA dos limiares europeus.
Concursos nacionais abaixo do limiar não aparecem aqui (ficam no BASE/DRE).
"""

import json
import sys
import datetime as dt
import urllib.request
import urllib.error

TED_ENDPOINT = "https://api.ted.europa.eu/v3/notices/search"

# ---------------------------------------------------------------------------
# CONFIGURAÇÃO — áreas de interesse da Fórum Estudante (prefixos CPV)
# ---------------------------------------------------------------------------
CPV_INCLUIR = [
    # Eventos, congressos, seminários, feiras
    "79952", "79951", "79956", "79950",
    # Comunicação, publicidade, marketing, RP, design gráfico, fotografia
    "79340", "79341", "79342", "79416", "79822", "79961", "79970",
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
    "seminário", "workshop", "bootcamp", "academia", "formação", "vídeo",
    "audiovisual", "produção", "conteúdos", "design", "branding", "redes sociais",
    "website", "plataforma", "digital", "literacia", "juventude", "empregabilidade",
    "assessoria", "relações públicas", "fotografia", "publicidade",
]

TERMOS_EXCLUIR = [
    "obras", "construção", "empreitada", "engenharia", "arquitetura", "limpeza",
    "vigilância", "segurança", "alimentação", "catering", "refeições", "hospitalar",
    "clínico", "medicament", "viatura", "combustível", "mobiliário", "agrícola",
    "florestal", "resíduos", "saneamento", "abastecimento de água", "seguro",
]

PAIS = "PRT"          # Portugal (ISO-3, campo buyer-country do TED)
DIAS_RETROATIVOS = 2  # janela de publicação a varrer (em dias)
MAX_RESULTADOS = 250

CAMPOS = [
    "publication-number", "notice-title", "title-proc", "buyer-name",
    "classification-cpv", "deadline-receipt-tender-date-lot",
    "estimated-value-lot", "total-value", "notice-type",
    "place-of-performance", "publication-date", "links",
]


def construir_query():
    desde = dt.date.today() - dt.timedelta(days=DIAS_RETROATIVOS)
    return f"buyer-country={PAIS} AND publication-date>={desde.strftime('%Y%m%d')}"


def pedir_ted(query):
    payload = {
        "query": query, "fields": CAMPOS, "limit": MAX_RESULTADOS,
        "scope": "ACTIVE", "paginationMode": "PAGE_NUMBER", "page": 1,
    }
    req = urllib.request.Request(
        TED_ENDPOINT, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST")
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def texto(v):
    """Normaliza campos multilingues/listas do TED para texto simples (prefere PT)."""
    if v is None:
        return ""
    if isinstance(v, dict):
        for k in ("por", "pt", "eng", "en", "mul", "MUL"):
            if k in v:
                return texto(v[k])
        return " ".join(texto(x) for x in v.values())
    if isinstance(v, list):
        return ", ".join(texto(x) for x in v if x is not None)
    return str(v)


def primeiro(v):
    if isinstance(v, list):
        return v[0] if v else None
    return v


def cpvs_do(n):
    raw = n.get("classification-cpv") or []
    if isinstance(raw, str):
        raw = [raw]
    seen, out = set(), []
    for c in raw:
        c = str(c).strip()
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return out


def formata_valor(n):
    v = primeiro(n.get("total-value")) or primeiro(n.get("estimated-value-lot"))
    if not v:
        return "—"
    try:
        return f"{float(str(v)):,.2f} €".replace(",", " ")
    except ValueError:
        return str(v)


def formata_prazo(n):
    d = primeiro(n.get("deadline-receipt-tender-date-lot"))
    if not d:
        return "—"
    s = str(d).replace("Z", "")
    return s[:10]


def link_de(n):
    num = texto(n.get("publication-number"))
    return f"https://ted.europa.eu/en/notice/{num}" if num else ""


def titulo_de(n):
    return texto(n.get("notice-title")) or texto(n.get("title-proc")) or "(sem título)"


def interessa(n):
    """Devolve (incluir, score, motivos). Só anúncios de concurso (cn-*)."""
    nt = texto(n.get("notice-type")).lower()
    if nt and not nt.startswith("cn"):   # cn = contract notice (oportunidade aberta)
        return (False, 0, [])

    titulo = titulo_de(n).lower()
    for t in TERMOS_EXCLUIR:
        if t in titulo:
            return (False, 0, [])

    cpvs = cpvs_do(n)
    score, motivos = 0, []

    cpv_hit = any(any(c.startswith(p) for p in CPV_INCLUIR) for c in cpvs)
    if cpv_hit:
        score += 2
        motivos.append("CPV na área de interesse")

    termos = sorted({t for t in TERMOS_INTERESSE if t in titulo})
    if termos:
        score += len(termos)
        motivos.append("Palavras-chave: " + ", ".join(termos[:5]))

    return (cpv_hit or bool(termos), score, motivos)


def estrelas(score):
    if score >= 4:
        return "⭐⭐⭐ Concorrer"
    if score >= 2:
        return "⭐⭐ Analisar"
    return "⭐ Apenas acompanhar"


def render_html(itens, query, total_lidos):
    hoje = dt.date.today().strftime("%d-%m-%Y")
    recomendados = [i for i in itens if i["score"] >= 2]
    top3 = sorted(itens, key=lambda i: -i["score"])[:3]
    L = ["<html><head><meta charset='utf-8'></head><body style='font-family:Arial,sans-serif;max-width:760px'>"]
    L.append(f"<h1>Radar Concursos Fórum Estudante — {hoje}</h1>")
    L.append("<h2>Resumo Executivo</h2><ul>")
    L.append(f"<li><b>Anúncios analisados (TED / Portugal):</b> {total_lidos}</li>")
    L.append(f"<li><b>Relevantes:</b> {len(itens)} &nbsp;|&nbsp; <b>Recomendados (⭐⭐+):</b> {len(recomendados)}</li>")
    if top3:
        L.append("<li><b>Top 3 do dia:</b><ol>")
        for i in top3:
            L.append(f"<li>{i['titulo']} — {i['entidade']} <i>({i['estrelas']})</i></li>")
        L.append("</ol></li>")
    L.append("<li style='color:#666'><b>Nota de cobertura:</b> esta fonte (TED) só inclui "
             "concursos europeus/acima do limiar. Os nacionais abaixo do limiar não constam.</li></ul>")
    if not itens:
        L.append("<p>Sem anúncios TED relevantes nesta janela. Dia provavelmente sem publicações "
                 "acima do limiar nas áreas-alvo.</p>")
    for i in sorted(itens, key=lambda x: -x["score"]):
        L.append("<hr>")
        L.append(f"<h3>{i['titulo']}</h3><ul>")
        L.append(f"<li><b>Entidade adjudicante:</b> {i['entidade']}</li>")
        L.append(f"<li><b>Valor base:</b> {i['valor']}</li>")
        L.append(f"<li><b>Prazo de propostas:</b> {i['prazo']}</li>")
        L.append(f"<li><b>CPV:</b> {', '.join(i['cpvs']) or '—'}</li>")
        L.append(f"<li><b>Link:</b> <a href='{i['link']}'>{i['link']}</a></li>")
        L.append(f"<li><b>Probabilidade de interesse:</b> {i['estrelas']}</li>")
        if i["motivos"]:
            L.append(f"<li><b>Porque pode interessar:</b> {'; '.join(i['motivos'])}</li>")
        L.append("</ul>")
    L.append(f"<hr><p style='color:#999;font-size:12px'>Fonte: TED Search API (anónima). Query: {query}</p>")
    L.append("</body></html>")
    return "\n".join(L)


def main():
    query = construir_query()
    try:
        dados = pedir_ted(query)
    except urllib.error.HTTPError as e:
        msg = e.read().decode("utf-8", "ignore")[:500]
        print(f"ERRO HTTP {e.code}: {msg}", file=sys.stderr)
        open("briefing.html", "w", encoding="utf-8").write(
            f"<html><body><h1>Radar TED — erro</h1><p>HTTP {e.code} ao consultar o TED.</p>"
            f"<p>Query: {query}</p><pre>{msg}</pre></body></html>")
        return

    notices = dados.get("notices") or dados.get("results") or []
    total = dados.get("totalNoticeCount") or len(notices)
    itens = []
    for n in notices:
        incluir, score, motivos = interessa(n)
        if not incluir:
            continue
        itens.append({
            "titulo": titulo_de(n), "entidade": texto(n.get("buyer-name")) or "—",
            "valor": formata_valor(n), "prazo": formata_prazo(n),
            "cpvs": cpvs_do(n), "link": link_de(n),
            "score": score, "estrelas": estrelas(score), "motivos": motivos,
        })
    open("briefing.html", "w", encoding="utf-8").write(render_html(itens, query, total))
    print(f"OK — {len(notices)} anúncios lidos (total PT: {total}), {len(itens)} relevantes.")


if __name__ == "__main__":
    main()
