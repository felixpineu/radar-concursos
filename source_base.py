# -*- coding: utf-8 -*-
"""
source_base.py — Fonte 2 (ATIVA): Portal BASE — secção "Anúncios DR".

Os "Anúncios DR" do Portal BASE incluem os anúncios de procedimento publicados no
Diário da República — ou seja, os concursos públicos NACIONAIS, incluindo os pequenos
abaixo dos limiares europeus (muitas vezes < 20.000 €) em comunicação, eventos,
formação, educação, design, conteúdos, websites, audiovisual e consultoria.

Estratégia (verificada manualmente no fluxo do BASE):
  1. Abrir https://www.base.gov.pt/Base4/pt/pesquisa/?type=anuncios
  2. Preencher o formulário avançado de "Anúncios DR" e clicar em "Pesquisar"
     (navegar com parâmetros no URL NÃO dispara a pesquisa). É OBRIGATÓRIO definir
     uma data "Desde" (últimos dias), senão o servidor responde
     "Não foi possível obter os dados do servidor".
       - Tipo de contrato = "Aquisição de serviços"
       - Tipo de ato = "Anúncio de procedimento"
       - "Anúncios ativos" marcado
       - Data da publicação "Desde" = hoje − DIAS_RETROATIVOS (DD-MM-AAAA)
  3. Percorrer todas as páginas de resultados (25 linhas/página) e recolher as linhas.
  4. Abrir a ficha de detalhe SÓ das linhas cujo "Tipo de procedimento" é
     "Concurso público" ou "Concurso limitado por prévia qualificação" (permitem
     candidatura espontânea) E cujo "Objeto do contrato" contém uma palavra-chave core
     (para limitar o nº de fichas, que são lentas). A relevância final é decidida por
     filters.interessa — aqui só normalizamos.

NÃO filtra por perfil de interesse (isso é do filters.py). Em caso de falha (timeout,
mudança de layout, sem resultados), fetch() devolve ([], "aviso/erro ...") e não
rebenta — o radar.py continua a enviar a parte do TED.
"""

import re
import datetime as dt

NOME = "BASE — Concursos nacionais (inclui abaixo dos limiares)"
ATIVA = True

ESTADO = "Fonte ativa — raspagem da secção 'Anúncios DR' do Portal BASE via navegador."

# ---- Parâmetros ----
URL_PESQUISA = "https://www.base.gov.pt/Base4/pt/pesquisa/?type=anuncios"
URL_DETALHE = "https://www.base.gov.pt/Base4/pt/detalhe/?type=anuncios&id={id}"
DIAS_RETROATIVOS = 4
MAX_PAGINAS = 25          # trava de segurança (25 páginas ≈ 625 linhas)
MAX_FICHAS = 80           # trava de segurança ao nº de fichas de detalhe abertas
ATRASO_FICHA_MS = 400     # ser educado entre fichas

# Só estes tipos de modelo permitem candidatura espontânea — ignora os restantes.
MODELOS_OK = {"concurso público", "concurso limitado por prévia qualificação"}

# Palavras-chave "core" para decidir que linhas valem a pena abrir em detalhe.
# Propositadamente abrangente (a relevância final é do filters.py).
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

MESES_VAZIOS = "Não foi possível obter os dados do servidor"


# --------------------------------------------------------------------------- #
# Helpers de parsing                                                          #
# --------------------------------------------------------------------------- #
def _tem_core(texto):
    t = (texto or "").lower()
    return any(k in t for k in CORE)


def _data_iso(ddmmaaaa):
    """'25-06-2026' -> '2026-06-25'. Devolve '' se não der."""
    m = re.search(r"(\d{2})-(\d{2})-(\d{4})", ddmmaaaa or "")
    if not m:
        return ""
    d, mth, y = m.groups()
    return f"{y}-{mth}-{d}"


def _cpvs(valor):
    """Extrai todos os códigos CPV (NNNNNNNN-N) do texto da célula 'CPVs'."""
    out, vistos = [], set()
    for c in re.findall(r"\d{8}-\d", valor or ""):
        if c not in vistos:
            vistos.add(c)
            out.append(c)
    return out


def _prazo(valor_prazo, data_pub_iso):
    """'12 dias.' + data de publicação -> data-limite ISO. Fallback: 'N dias'."""
    m = re.search(r"(\d+)\s*dias", valor_prazo or "", re.I)
    if not m:
        return (valor_prazo or "—").strip().rstrip(".") or "—"
    n = int(m.group(1))
    if data_pub_iso:
        try:
            base = dt.date.fromisoformat(data_pub_iso)
            return (base + dt.timedelta(days=n)).isoformat()
        except ValueError:
            pass
    return f"{n} dias"


# --------------------------------------------------------------------------- #
# Interação com a página                                                      #
# --------------------------------------------------------------------------- #
def _fazer_pesquisa(pg, desde_ddmmaaaa):
    """Preenche o formulário avançado de Anúncios DR e dispara a pesquisa.
    Devolve o nº total de resultados (int). Repete uma vez se o servidor
    responder com o erro de 'não foi possível obter os dados'."""
    F = "#form_anuncios "
    for tentativa in (1, 2):
        pg.goto(URL_PESQUISA, wait_until="networkidle", timeout=60000)
        pg.wait_for_timeout(1500)
        # Abrir a pesquisa avançada (revela os selects/checkbox/data)
        try:
            pg.click("#advanced_anuncios")
            pg.wait_for_timeout(600)
        except Exception:
            pass
        pg.select_option(F + "select[name=tipocontrato]", label="Aquisição de serviços")
        pg.select_option(F + "select[name=tipoacto]", label="Anúncio de procedimento")
        cb = pg.query_selector(F + "input[name=activo]")
        if cb and not cb.is_checked():
            cb.check()
        campo_data = pg.query_selector(F + "input[name=desdedatapublicacao]")
        campo_data.fill(desde_ddmmaaaa)
        pg.keyboard.press("Escape")  # fecha o datepicker
        pg.wait_for_timeout(300)
        # Botão "Pesquisar" do formulário avançado
        pg.click("#search_anuncios2")
        # Esperar a tabela (ajax lento) ou a mensagem de total
        total = _esperar_resultados(pg)
        if total is not None:
            return total
        # erro do servidor -> tenta outra vez
        pg.wait_for_timeout(1500)
    return 0


def _esperar_resultados(pg, timeout_ms=45000):
    """Espera o ajax renderizar. Devolve total (int) ou None se deu erro de servidor."""
    alvo = dt.datetime.now() + dt.timedelta(milliseconds=timeout_ms)
    while dt.datetime.now() < alvo:
        corpo = pg.inner_text("body")
        if MESES_VAZIOS in corpo:
            return None
        m = re.search(r"Número de resultados:\s*([0-9]+)", corpo)
        if m:
            return int(m.group(1))
        pg.wait_for_timeout(700)
    # Sem mensagem de total mas talvez com tabela — tenta contar
    if pg.query_selector("table tbody tr"):
        return len(pg.query_selector_all("table tbody tr"))
    return None


def _extrair_linhas(pg):
    """Lê as linhas da página atual de resultados -> lista de dicts com
    objeto, tipo_proc e o id da ficha de detalhe."""
    linhas = []
    for tr in pg.query_selector_all("table tbody tr"):
        tds = tr.query_selector_all("td")
        if len(tds) < 6:
            continue
        objeto = tds[0].inner_text().strip()
        tipo_proc = tds[2].inner_text().strip()
        a = tr.query_selector("a[href*='detalhe']")
        href = a.get_attribute("href") if a else ""
        m = re.search(r"[?&]id=(\d+)", href or "")
        if not m:
            continue
        linhas.append({"objeto": objeto, "tipo_proc": tipo_proc, "det_id": m.group(1)})
    return linhas


def _paginar(pg, total):
    """Percorre todas as páginas de resultados e devolve todas as linhas."""
    todas = []
    nr_pags = max(1, -(-total // 25))  # ceil(total/25)
    page = 0
    while True:
        todas.extend(_extrair_linhas(pg))
        if page + 1 >= nr_pags or page + 1 >= MAX_PAGINAS:
            break
        nxt = pg.query_selector(f"#page_{page + 1}")
        if not nxt:
            break
        nxt.click()
        # Esperar a nova página ficar ativa (re-render do ajax)
        try:
            pg.wait_for_selector(
                f"li.page-item.active span#page_{page + 1}", timeout=20000)
        except Exception:
            pg.wait_for_timeout(2500)
        pg.wait_for_timeout(400)
        page += 1
    return todas


def _ler_detalhe(pg, det_id):
    """Abre a ficha de detalhe e devolve uma op normalizada (ou None se não
    interessar / não der para ler)."""
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

    num = dados.get("Nº do anúncio DR", "").strip()
    if not num:
        return None

    modelo = dados.get("Tipo de modelo", "").strip().lower()
    if modelo not in MODELOS_OK:
        return None  # só concurso público / limitado por prévia qualificação

    data_pub = _data_iso(dados.get("Diário da república", ""))
    titulo = dados.get("Descrição", "").strip() or "(sem descrição)"
    entidade = dados.get("Entidade emissora", "").strip() or "—"
    valor = dados.get("Preço base", "").strip() or "—"
    cpvs = _cpvs(dados.get("CPVs", ""))
    prazo = _prazo(dados.get("Prazo para apresentação de propostas", ""), data_pub)

    return {
        "source": "BASE",
        "id": f"BASE:{num}",
        "titulo": titulo,
        "entidade": entidade,
        "valor": valor,
        "prazo": prazo,
        "cpvs": cpvs,
        "link": url,
        "publicacao": data_pub,
    }


# --------------------------------------------------------------------------- #
# Ponto de entrada                                                            #
# --------------------------------------------------------------------------- #
def fetch():
    """Devolve (oportunidades: list[dict], estado: str). Não filtra por perfil."""
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        return ([], f"AVISO: Playwright não disponível ({e}). Secção BASE ignorada.")

    desde = (dt.date.today() - dt.timedelta(days=DIAS_RETROATIVOS)).strftime("%d-%m-%Y")
    ops, vistos = [], set()

    try:
        with sync_playwright() as p:
            navegador = p.chromium.launch(headless=True)
            pg = navegador.new_page()
            pg.set_default_timeout(45000)

            total = _fazer_pesquisa(pg, desde)
            if not total:
                navegador.close()
                return ([], "AVISO: BASE não devolveu resultados (sem dados ou erro do servidor).")

            linhas = _paginar(pg, total)

            # Candidatos: tipo de procedimento permitido + objeto com palavra-chave core
            candidatos, ids_cand = [], set()
            for ln in linhas:
                if ln["tipo_proc"].strip().lower() not in MODELOS_OK:
                    continue
                if not _tem_core(ln["objeto"]):
                    continue
                if ln["det_id"] in ids_cand:
                    continue
                ids_cand.add(ln["det_id"])
                candidatos.append(ln)

            for i, ln in enumerate(candidatos[:MAX_FICHAS]):
                try:
                    op = _ler_detalhe(pg, ln["det_id"])
                except Exception:
                    continue
                if op and op["id"] not in vistos:
                    vistos.add(op["id"])
                    ops.append(op)
                pg.wait_for_timeout(ATRASO_FICHA_MS)

            navegador.close()
    except Exception as e:  # noqa
        return (ops, f"AVISO: BASE interrompido ({type(e).__name__}: {e}). "
                     f"{len(ops)} anúncios recolhidos antes da falha.")

    estado = (f"OK — BASE: {total} anúncios de procedimento (Aquisição de serviços, "
              f"últimos {DIAS_RETROATIVOS} dias); {len(ops)} concursos públicos/limitados "
              f"relevantes lidos em detalhe.")
    return (ops, estado)
