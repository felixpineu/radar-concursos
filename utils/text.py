# -*- coding: utf-8 -*-
"""
utils/text.py — normalização de texto, datas, valores e hash de deduplicação.
Funções puras e testáveis (sem dependências de BD).
"""

import re
import hashlib
import unicodedata
import datetime as dt


def strip_accents(s):
    s = s or ""
    return "".join(c for c in unicodedata.normalize("NFKD", s)
                   if not unicodedata.combining(c))


def normalize(s):
    """minúsculas, sem acentos, só [a-z0-9 ], espaços colapsados."""
    s = strip_accents((s or "").lower())
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def parse_date(v):
    """Aceita date, 'YYYY-MM-DD', 'DD-MM-YYYY', 'DD/MM/YYYY'... -> date | None."""
    if not v:
        return None
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    s = str(v).strip()
    m = re.search(r"\d{4}-\d{2}-\d{2}", s)
    if m:
        try:
            return dt.date.fromisoformat(m.group(0))
        except ValueError:
            pass
    m = re.search(r"(\d{2})[-/](\d{2})[-/](\d{4})", s)
    if m:
        d, mth, y = m.groups()
        try:
            return dt.date(int(y), int(mth), int(d))
        except ValueError:
            pass
    return None


def parse_value(v):
    """Aceita número ou strings tipo '20.000,00 €', '1.883.441,25', '20000.00'
    -> float | None. Formato PT: ponto = milhares, vírgula = decimal."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = re.sub(r"[^\d,.\-]", "", str(v))
    if not s or s in ("-", ".", ","):
        return None
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def dedup_hash(entity_name, title, base_value, deadline):
    """sha256 de normalizar(entidade + objeto + valor + prazo). Estável e portátil."""
    valor = "" if base_value in (None, "") else f"{float(base_value):.2f}"
    partes = [
        normalize(entity_name or ""),
        normalize(title or ""),
        valor,
        str(parse_date(deadline) or ""),
    ]
    raw = "|".join(partes)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def extrair_nif(texto):
    """Extrai o primeiro NIF (9 dígitos) de 'Nome (514310774)' -> '514310774'."""
    m = re.search(r"\b(\d{9})\b", texto or "")
    return m.group(1) if m else None
