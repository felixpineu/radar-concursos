# -*- coding: utf-8 -*-
"""
sources/ted.py — Fonte TED (Tenders Electronic Daily). ATIVA.
Radar europeu / concursos ACIMA dos limiares europeus.
API anónima (sem chave): POST https://api.ted.europa.eu/v3/notices/search

Porta a lógica validada da estrutura plana para o novo contrato (modelo normalizado,
fetch(mode, since), paginação). NÃO filtra nem pontua.
"""

import json
import datetime as dt
import urllib.request
import urllib.error

from sources.base_source import BaseSource
from utils import text

ENDPOINT = "https://api.ted.europa.eu/v3/notices/search"
PAIS = "PRT"
MAX_RESULTADOS = 250          # limite por página da API
MAX_PAGINAS = 10              # trava de segurança (10 * 250 = 2500)
CAMPOS = [
    "publication-number", "notice-title", "title-proc", "buyer-name",
    "classification-cpv", "deadline-receipt-tender-date-lot",
    "estimated-value-lot", "total-value", "notice-type", "publication-date",
    "place-of-performance",
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
    out, vistos = [], set()
    for c in raw:
        c = str(c).strip()
        if c and c not in vistos:
            vistos.add(c)
            out.append(c)
    return out


def normalize_notice(n):
    """Converte um 'notice' bruto do TED no registo normalizado. Testável sem rede.
    Devolve None se não for um concurso aberto (notice-type que não começa por 'cn')."""
    nt = _texto(n.get("notice-type")).lower()
    if nt and not nt.startswith("cn"):
        return None

    num = _texto(n.get("publication-number"))
    valor_bruto = _primeiro(n.get("total-value")) or _primeiro(n.get("estimated-value-lot"))
    deadline = _primeiro(n.get("deadline-receipt-tender-date-lot"))
    titulo = _texto(n.get("notice-title")) or _texto(n.get("title-proc")) or "(sem título)"

    return {
        "source": "ted",
        "source_url": f"https://ted.europa.eu/pt/notice/-/detail/{num}" if num else "",
        "source_procedure_number": num,
        "entity_name": _texto(n.get("buyer-name")) or "—",
        "entity_nif": None,
        "title": titulo,
        "description": "",
        "base_value": text.parse_value(valor_bruto),
        "currency": "EUR",
        "publication_date": _texto(n.get("publication-date"))[:10],
        "deadline": (str(deadline).replace("Z", "")[:10] if deadline else None),
        "cpvs": _cpvs(n),
        "procedure_type": "concurso público",
        "location": _texto(n.get("place-of-performance")) or None,
        "raw_payload": n,
    }


def _pedir(query, page):
    payload = {"query": query, "fields": CAMPOS, "limit": MAX_RESULTADOS,
               "scope": "ACTIVE", "paginationMode": "PAGE_NUMBER", "page": page}
    req = urllib.request.Request(
        ENDPOINT, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


class TedSource(BaseSource):
    name = "ted"
    active = True

    def fetch(self, mode, since):
        query = (f"buyer-country={PAIS} AND "
                 f"publication-date>={since.strftime('%Y%m%d')}")
        notices = []
        try:
            for page in range(1, MAX_PAGINAS + 1):
                dados = _pedir(query, page)
                lote = dados.get("notices") or []
                notices.extend(lote)
                if len(lote) < MAX_RESULTADOS:
                    break
        except urllib.error.HTTPError as e:
            return ([], f"ERRO HTTP {e.code} ao consultar o TED.")
        except Exception as e:  # noqa
            return ([], f"ERRO ao consultar o TED: {e}")

        registos = [r for r in (normalize_notice(n) for n in notices) if r]
        estado = (f"OK — TED: {len(notices)} anúncios lidos, {len(registos)} concursos "
                  f"abertos normalizados (Portugal, desde {since.isoformat()}).")
        return (registos, estado)
