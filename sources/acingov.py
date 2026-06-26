# -*- coding: utf-8 -*-
"""sources/acingov.py — stub de interface. NÃO implementar nesta fase."""

from sources.base_source import BaseSource


class AcinGovSource(BaseSource):
    name = "acingov"
    active = False

    def fetch(self, mode, since):
        return ([], "Fonte acinGov não implementada (planeada).")
