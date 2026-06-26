# -*- coding: utf-8 -*-
"""
sources/base.py — Fonte BASE (Portal BASE, secção "Anúncios DR"). ATIVA.
Concursos públicos NACIONAIS, incluindo abaixo dos limiares europeus (< 20.000 €).

Porta a lógica de raspagem (Playwright/Chromium headless) já validada para o novo
contrato (modelo normalizado, fetch(mode, since)). NÃO filtra nem pontua — só recolhe
e normaliza. Fluxo do BASE verificado manualmente (ver secção 6.2 da arquitetura):
form avançado de "Anúncios DR" (Aquisição de serviços + Anúncio de procedimento +
Anúncios ativos + data Desde OBRIGATÓRIA), paginação, e ficha de detalhe só das linhas
de Concurso público / limitado por prévia qualificação com objeto na área core.
"""

import re
import datetime as dt

from sources.base_source import BaseSource
from utils import text

URL_PESQUISA = "https://www.base.gov.pt/Base4/pt/pesquisa/?type=anuncios"
URL_DETALHE = "https://www.base.gov.pt/Base4/pt/detalhe/?type=anuncios&id={id}"
MAX_PAGINAS = 40          # trava de segurança
MAX_FICHAS = 120          # trava ao nº de fichas de detalhe abertas
ATRASO_FICHA_MS = 400     # ser educado entre fichas
MSG_ERRO_SERVIDOR = "Não foi possível obter os dados do servidor"

# Só estes tipos de modelo permitem candidatura espontânea.
MODELOS_OK = {"concurso público", "concurso limitado por prévia qualificação"}

# Palavras-chave "core" para decidir que linhas vale a pena abrir em detalhe
# (abrangente de propósito; a relevância final é decidida no scoring, Fase C).
CORE = [
    "comunica", "campanha", "marketing", "publicidade", "evento", "congress",
    "conferênc", "conferenc", "seminár", "seminar", "workshop", "bootcamp",
    "academia", "formaç", "formac", "ensino", "educa", "vídeo", "video",
    "audiovisual", "produç", "produc", "conteúdo", "conteudo", "design",
    "branding", "imagem", "redes sociais", "website", "web site", "sítio",
    "sitio", "portal", "plataforma", "aplicaç", "aplicac", "software", "digital",
    "literacia", "juventude", "jovens", "empregabilidade", "assessoria",
    "relações públicas", "relacoes publicas", "fotograf", "consultor", "estudo",
    "feira", "exposiç", "exposic", "stand", "divulgaç", "divulgac", "promoç",
    "promoc", "informaç", "informac", "edição", "edicao", "impress", "gráfic",
    "grafic",
]


# --------------------------------------------------------------------------- #
# Helpers de parsing                                                          #
# --------------------------------------------------------------------------- #
def _tem_core(texto_):
    t = (texto_ or "").lower()
    return any(k in t for k in CORE)


def _cpvs(valor):
    out, vistos = [], set()
    for c in re.findall(r"\d{8}-\d", valor or ""):
        if c not in vistos:
            vistos.add(c)
            out.append(c)
    return out


def _deadline(valor_prazo, data_pub_iso):
    """'12 dias.' + data de publicação -> data-limite ISO. Devolve None se não der."""
    m = re.search(r"(\d+)\s*dias", valor_prazo or "", re.I)
    if not m:
        return None
    pub = text.parse_date(data_pub_iso)
    if not pub:
        return None
    return (pub + dt.timedelta(days=int(m.group(1)))).isoformat()


def normalize_detalhe(dados, url):
    """Constrói o registo normalizado a partir do dict de campos da ficha de detalhe.
    Devolve None se faltar o nº de anúncio ou se o tipo de modelo não for elegível.
    Testável sem rede."""
    num = (dados.get("Nº do anúncio DR") or "").strip()
    if not num:
        return None
    modelo = (dados.get("Tipo de modelo") or "").strip()
    if modelo.lower() not in MODELOS_OK:
        return None

    data_pub = text.parse_date(dados.get("Diário da república", ""))
    data_pub_iso = data_pub.isoformat() if data_pub else ""
    entidade = (dados.get("Entidade emissora") or "—").strip()

    return {
        "source": "base",
        "source_url": url,
        "source_procedure_number": num,
        "entity_name": entidade,
        "entity_nif": text.extrair_nif(entidade),
        "title": (dados.get("Descrição") or "(sem descrição)").strip(),
        "description": (dados.get("Descrição") or "").strip(),
        "base_value": text.parse_value(dados.get("Preço base")),
        "currency": "EUR",
        "publication_date": data_pub_iso,
        "deadline": _deadline(dados.get("Prazo para apresentação de propostas"), data_pub_iso),
        "cpvs": _cpvs(dados.get("CPVs")),
        "procedure_type": modelo,
        "location": None,
        "raw_payload": dict(dados),
    }


# --------------------------------------------------------------------------- #
# Interação com a página                                                      #
# --------------------------------------------------------------------------- #
def _abrir_avancada(pg):
    """Garante que o painel de 'Pesquisa avançada' está aberto (o select de tipo de
    contrato visível). Tolera a animação do accordion / handlers tardios."""
    sel = "#form_anuncios select[name=tipocontrato]"
    for _ in range(4):
        el = pg.query_selector(sel)
        if el and el.is_visible():
            return True
        try:
            pg.click("#advanced_anuncios")
        except Exception:
            pass
        try:
            pg.wait_for_selector(sel, state="visible", timeout=5000)
            return True
        except Exception:
            pg.wait_for_timeout(600)
    return False


def _fazer_pesquisa(pg, desde_ddmmaaaa):
    F = "#form_anuncios "
    for _ in (1, 2):
        pg.goto(URL_PESQUISA, wait_until="networkidle", timeout=60000)
        pg.wait_for_timeout(1500)
        if not _abrir_avancada(pg):
            pg.wait_for_timeout(1500)
            continue   # volta a carregar a página e tenta de novo
        pg.select_option(F + "select[name=tipocontrato]", label="Aquisição de serviços")
        pg.select_option(F + "select[name=tipoacto]", label="Anúncio de procedimento")
        cb = pg.query_selector(F + "input[name=activo]")
        if cb and not cb.is_checked():
            cb.check()
        pg.query_selector(F + "input[name=desdedatapublicacao]").fill(desde_ddmmaaaa)
        pg.keyboard.press("Escape")
        pg.wait_for_timeout(300)
        pg.click("#search_anuncios2")
        total = _esperar_resultados(pg)
        if total is not None:
            return total
        pg.wait_for_timeout(1500)
    return 0


def _esperar_resultados(pg, timeout_ms=45000):
    alvo = dt.datetime.now() + dt.timedelta(milliseconds=timeout_ms)
    while dt.datetime.now() < alvo:
        corpo = pg.inner_text("body")
        if MSG_ERRO_SERVIDOR in corpo:
            return None
        m = re.search(r"Número de resultados:\s*([0-9]+)", corpo)
        if m:
            return int(m.group(1))
        pg.wait_for_timeout(700)
    if pg.query_selector("table tbody tr"):
        return len(pg.query_selector_all("table tbody tr"))
    return None


def _extrair_linhas(pg):
    linhas = []
    for tr in pg.query_selector_all("table tbody tr"):
        tds = tr.query_selector_all("td")
        if len(tds) < 6:
            continue
        a = tr.query_selector("a[href*='detalhe']")
        href = a.get_attribute("href") if a else ""
        m = re.search(r"[?&]id=(\d+)", href or "")
        if not m:
            continue
        linhas.append({
            "objeto": tds[0].inner_text().strip(),
            "tipo_proc": tds[2].inner_text().strip(),
            "det_id": m.group(1),
        })
    return linhas


def _paginar(pg, total):
    todas = []
    nr_pags = max(1, -(-total // 25))
    page = 0
    while True:
        todas.extend(_extrair_linhas(pg))
        if page + 1 >= nr_pags or page + 1 >= MAX_PAGINAS:
            break
        nxt = pg.query_selector(f"#page_{page + 1}")
        if not nxt:
            break
        nxt.click()
        try:
            pg.wait_for_selector(
                f"li.page-item.active span#page_{page + 1}", timeout=20000)
        except Exception:
            pg.wait_for_timeout(2500)
        pg.wait_for_timeout(400)
        page += 1
    return todas


def _ler_detalhe(pg, det_id):
    url = URL_DETALHE.format(id=det_id)
    pg.goto(url, wait_until="domcontentloaded", timeout=45000)
    pg.wait_for_timeout(900)
    dados = {}
    for tr in pg.query_selector_all("table tr"):
        tds = tr.query_selector_all("td, th")
        if len(tds) >= 2:
            chave = tds[0].inner_text().strip().rstrip(":")
            valor = tds[1].inner_text().strip()
            if chave and chave not in dados:
                dados[chave] = valor
    return normalize_detalhe(dados, url)


# --------------------------------------------------------------------------- #
# Fonte                                                                       #
# --------------------------------------------------------------------------- #
class BaseGovSource(BaseSource):
    name = "base"
    active = True

    def fetch(self, mode, since):
        try:
            from playwright.sync_api import sync_playwright
        except Exception as e:
            return ([], f"AVISO: Playwright indisponível ({e}). Secção BASE ignorada.")

        desde = since.strftime("%d-%m-%Y")
        registos, vistos = [], set()
        candidatos = []
        total = 0

        try:
            with sync_playwright() as p:
                navegador = p.chromium.launch(headless=True)
                pg = navegador.new_page()
                pg.set_default_timeout(45000)

                total = _fazer_pesquisa(pg, desde)
                if not total:
                    navegador.close()
                    return ([], "AVISO: BASE sem resultados (sem dados ou erro do servidor).")

                linhas = _paginar(pg, total)
                ids_cand = set()
                for ln in linhas:
                    if ln["tipo_proc"].strip().lower() not in MODELOS_OK:
                        continue
                    if not _tem_core(ln["objeto"]):
                        continue
                    if ln["det_id"] in ids_cand:
                        continue
                    ids_cand.add(ln["det_id"])
                    candidatos.append(ln)

                for ln in candidatos[:MAX_FICHAS]:
                    try:
                        rec = _ler_detalhe(pg, ln["det_id"])
                    except Exception:
                        continue
                    if rec and rec["source_url"] not in vistos:
                        vistos.add(rec["source_url"])
                        registos.append(rec)
                    pg.wait_for_timeout(ATRASO_FICHA_MS)

                navegador.close()
        except Exception as e:  # noqa
            return (registos, f"AVISO: BASE interrompido ({type(e).__name__}: {e}). "
                              f"{len(registos)} registos antes da falha.")

        estado = (f"OK — BASE: {total} anúncios (Aquisição de serviços, desde {since.isoformat()}); "
                  f"{len(candidatos)} candidatos; {len(registos)} concursos públicos/limitados "
                  f"normalizados.")
        return (registos, estado)
