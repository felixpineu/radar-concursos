# -*- coding: utf-8 -*-
"""
source_ted.py — Fonte 1: TED (Tenders Electronic Daily).
Radar Europeu / concursos ACIMA dos limiares europeus.
API de pesquisa anónima (sem chave): POST https://api.ted.europa.eu/v3/notices/search
"""

import json
import datetime as dt
import urllib.request
import urllib.error

NOME = "TED — Radar Europeu (acima dos limiares)"
ATIVA = True

ENDPOINT = "https://api.ted.europa.eu/v3/notices/search"
PAIS = "PRT"            # buyer-country
DIAS_RETROATIVOS = 3
MAX_RESULTADOS = 250
CAMPOS = [
    "publication-number", "notice-title", "title-proc", "buyer-name",
    "classification-cpv", "deadline-receipt-tender-date-lot",
    "estimated-value-lot", "total-value", "notice-type", "publication-date",
]


def _texto(v):
    if v is None:
        return ""
    if isinstance(v, dict):
        for k in ("por", "pt", "eng", "en", "mul", "MUL"):
            if k in v:
                return _texto(v[k])
        return " ".join(_texto(x) for x in v.values())
    if isinstance(v, list):
        return ", ".join(_texto(x) for x in v if x is not None)
    return str(v)


def _primeiro(v):
    return v[0] if isinstance(v, list) and v else (None if isinstance(v, list) else v)


def _cpvs(n):
    raw = n.get("classification-cpv") or []
    if isinstance(raw, str):
        raw = [raw]
    out, seen = [], set()
    for c in raw:
        c = str(c).strip()
        if c and c not in seen:
            seen.add(c); out.append(c)
    return out


def _valor(n):
    v = _primeiro(n.get("total-value")) or _primeiro(n.get("estimated-value-lot"))
    if not v:
        return "—"
    try:
        return f"{float(str(v)):,.2f} €".replace(",", " ")
    except ValueError:
        return str(v)


def _prazo(n):
    d = _primeiro(n.get("deadline-receipt-tender-date-lot"))
    return str(d).replace("Z", "")[:10] if d else "—"


def _titulo(n):
    return _texto(n.get("notice-title")) or _texto(n.get("title-proc")) or "(sem título)"


def _pedir(query):
    payload = {"query": query, "fields": CAMPOS, "limit": MAX_RESULTADOS,
               "scope": "ACTIVE", "paginationMode": "PAGE_NUMBER", "page": 1}
    req = urllib.request.Request(
        ENDPOINT, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch():
    """Devolve (oportunidades: list[dict], estado: str). Não filtra (isso é do filters.py)."""
    desde = dt.date.today() - dt.timedelta(days=DIAS_RETROATIVOS)
    query = f"buyer-country={PAIS} AND publication-date>={desde.strftime('%Y%m%d')}"
    try:
        dados = _pedir(query)
    except urllib.error.HTTPError as e:
        return ([], f"ERRO HTTP {e.code} ao consultar o TED.")
    except Exception as e:  # noqa
        return ([], f"ERRO ao consultar o TED: {e}")

    notices = dados.get("notices") or []
    ops = []
    for n in notices:
        nt = _texto(n.get("notice-type")).lower()
        if nt and not nt.startswith("cn"):   # cn = contract notice (concurso aberto)
            continue
        num = _texto(n.get("publication-number"))
        ops.append({
            "source": "TED",
            "id": f"TED:{num}",
            "titulo": _titulo(n),
            "entidade": _texto(n.get("buyer-name")) or "—",
            "valor": _valor(n),
            "prazo": _prazo(n),
            "cpvs": _cpvs(n),
            "link": f"https://ted.europa.eu/pt/notice/-/detail/{num}" if num else "",
            "publicacao": _texto(n.get("publication-date"))[:10],
        })
    return (ops, f"OK — {len(notices)} anúncios lidos do TED (Portugal, últimos {DIAS_RETROATIVOS} dias).")
