#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
radar.py — Orquestrador do Radar de Concursos da Fórum Estudante.

- Junta várias FONTES (TED ativa; BASE e DR planeadas para a Fase 2).
- Aplica o perfil de interesse (filters.py) de forma uniforme.
- Mantém memória dos concursos já reportados (seen.json) para enviar SÓ OS NOVOS.
- Produz briefing.html sempre SEPARADO por fonte, com aviso de cobertura explícito.

Objetivo: na 1ª execução mapeia tudo o que está aberto (tudo é "novo");
nas seguintes, destaca apenas os concursos novos desde a última corrida.
"""

import json
import datetime as dt

import filters
import source_ted
import source_base
import source_dre

FONTES = [source_ted, source_base, source_dre]
SEEN_FILE = "seen.json"


def carregar_seen():
    try:
        with open(SEEN_FILE, encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()


def guardar_seen(ids):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(ids), f, ensure_ascii=False, indent=1)


def recolher():
    """Corre todas as fontes. Devolve lista de blocos (um por fonte)."""
    seen = carregar_seen()
    blocos = []
    for fonte in FONTES:
        nome = getattr(fonte, "NOME", fonte.__name__)
        ativa = getattr(fonte, "ATIVA", True)
        ops, estado = fonte.fetch()
        relevantes = []
        for op in ops:
            incluir, score, motivos = filters.interessa(op)
            if not incluir:
                continue
            relevantes.append(dict(
                op, score=score, motivos=motivos,
                estrelas=filters.estrelas(score),
                novo=(op.get("id") not in seen),
            ))
        relevantes.sort(key=lambda o: (not o["novo"], -o["score"]))
        blocos.append({
            "nome": nome, "ativa": ativa, "estado": estado,
            "relevantes": relevantes,
            "novos": [o for o in relevantes if o["novo"]],
        })
    return seen, blocos


def card(op):
    L = ["<div style='border:1px solid #e1e4e8;border-radius:8px;padding:12px;margin:10px 0'>"]
    etiqueta = " &nbsp;<span style='background:#1f6feb;color:#fff;border-radius:4px;padding:1px 6px;font-size:11px'>NOVO</span>" if op.get("novo") else ""
    L.append(f"<h4 style='margin:0 0 6px'>{op['titulo']}{etiqueta}</h4><ul style='margin:0;padding-left:18px'>")
    L.append(f"<li><b>Entidade:</b> {op['entidade']}</li>")
    L.append(f"<li><b>Valor base:</b> {op['valor']} &nbsp;|&nbsp; <b>Prazo:</b> {op['prazo']}</li>")
    L.append(f"<li><b>CPV:</b> {', '.join(op['cpvs']) or '—'}</li>")
    L.append(f"<li><b>Interesse:</b> {op['estrelas']}{('  —  ' + '; '.join(op['motivos'])) if op['motivos'] else ''}</li>")
    if op.get("link"):
        L.append(f"<li><a href='{op['link']}'>{op['link']}</a></li>")
    L.append("</ul></div>")
    return "\n".join(L)


def render(blocos):
    hoje = dt.date.today().strftime("%d-%m-%Y")
    total_novos = sum(len(b["novos"]) for b in blocos)
    todos_novos = [o for b in blocos for o in b["novos"]]
    top3 = sorted(todos_novos, key=lambda o: -o["score"])[:3]

    L = ["<html><head><meta charset='utf-8'></head>",
         "<body style='font-family:Arial,Helvetica,sans-serif;max-width:780px;color:#24292f'>"]
    L.append(f"<h1>Radar Concursos Fórum Estudante — {hoje}</h1>")

    # Resumo executivo
    L.append("<h2>Resumo Executivo</h2><ul>")
    L.append(f"<li><b>Novos concursos relevantes hoje:</b> {total_novos}</li>")
    for b in blocos:
        if b["ativa"]:
            L.append(f"<li>{b['nome']}: <b>{len(b['novos'])}</b> novos &nbsp;(<i>{len(b['relevantes'])} relevantes abertos</i>)</li>")
    if top3:
        L.append("<li><b>Top 3 novos:</b><ol>")
        for o in top3:
            L.append(f"<li>{o['titulo']} — {o['entidade']} <i>({o['estrelas']})</i></li>")
        L.append("</ol></li>")
    L.append("</ul>")

    # Secções por fonte
    for i, b in enumerate(blocos, 1):
        L.append(f"<hr><h2>{i}. {b['nome']}</h2>")
        L.append(f"<p style='color:#57606a;font-size:13px'>{b['estado']}</p>")
        if not b["ativa"]:
            continue
        if b["novos"]:
            L.append(f"<p><b>{len(b['novos'])} novo(s):</b></p>")
            for o in b["novos"]:
                L.append(card(o))
        else:
            L.append(f"<p>Sem concursos novos nesta fonte hoje. "
                     f"({len(b['relevantes'])} relevantes ainda abertos.)</p>")

    # Limitações de cobertura — SEMPRE explícito
    L.append("<hr><h2>Limitações de cobertura</h2>")
    inativas = [b["nome"] for b in blocos if not b["ativa"]]
    L.append("<p style='background:#fff8c5;border:1px solid #d4a72c;border-radius:6px;padding:10px'>"
             "<b>⚠️ Cobertura atual: apenas TED</b> (concursos europeus / acima dos limiares). "
             "Este relatório <b>pode não incluir concursos nacionais abaixo dos limiares europeus</b> "
             "(ex.: &lt; 20.000 €) em comunicação, eventos, formação, educação, design, conteúdos, "
             "websites, audiovisual e consultoria.</p>")
    if inativas:
        L.append("<p>Fontes planeadas (Fase 2), ainda não ativas: " + "; ".join(inativas) + ".</p>")
    L.append("</body></html>")
    return "\n".join(L)


def main():
    seen, blocos = recolher()
    html = render(blocos)
    with open("briefing.html", "w", encoding="utf-8") as f:
        f.write(html)

    novos_ids = {o["id"] for b in blocos for o in b["novos"] if o.get("id")}
    seen |= novos_ids
    guardar_seen(seen)

    total_novos = sum(len(b["novos"]) for b in blocos)
    print(f"OK — {total_novos} concursos novos. Estado atualizado ({len(seen)} ids memorizados).")


if __name__ == "__main__":
    main()
