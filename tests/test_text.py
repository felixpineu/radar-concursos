# -*- coding: utf-8 -*-
import datetime as dt
from utils import text


def test_normalize_remove_acentos_e_pontuacao():
    assert text.normalize("Comunicação & Marketing!") == "comunicacao marketing"


def test_parse_value_formato_pt():
    assert text.parse_value("20.000,00 €") == 20000.00
    assert text.parse_value("1.883.441,25") == 1883441.25
    assert text.parse_value("20000.00") == 20000.00
    assert text.parse_value("7.020,00 €") == 7020.00
    assert text.parse_value(1500) == 1500.0
    assert text.parse_value("—") is None
    assert text.parse_value(None) is None


def test_parse_date_varios_formatos():
    assert text.parse_date("2026-06-25") == dt.date(2026, 6, 25)
    assert text.parse_date("25-06-2026") == dt.date(2026, 6, 25)
    assert text.parse_date("nº 121 série 2, de 25-06-2026") == dt.date(2026, 6, 25)
    assert text.parse_date("") is None
    assert text.parse_date(None) is None


def test_dedup_hash_estavel_e_sensivel():
    a = text.dedup_hash("Câmara Municipal", "Serviços de design", 20000, "2026-07-01")
    b = text.dedup_hash("camara  municipal", "Serviços de design", 20000.0, dt.date(2026, 7, 1))
    assert a == b  # normalização torna iguais
    c = text.dedup_hash("Câmara Municipal", "Serviços de vídeo", 20000, "2026-07-01")
    assert a != c  # objeto diferente -> hash diferente


def test_extrair_nif():
    assert text.extrair_nif("Águas do Douro e Paiva, SA (514310774)") == "514310774"
    assert text.extrair_nif("Sem nif aqui") is None
