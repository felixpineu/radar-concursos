# -*- coding: utf-8 -*-
"""
database/repository.py — ÚNICA porta de acesso à base de dados.

Todas as queries/upserts vivem aqui. O resto do código nunca toca em SQL nem na
sessão diretamente além de a passar a estas funções. Assim, migrar para Postgres
ou trocar o esquema fica contido neste módulo.

Deduplicação (secção 7 da arquitetura): ao ingerir um registo normalizado, procura
o concurso canónico por ordem de força:
  1. procedure_number  2. source_url exato  3. dedup_hash
Se existir, acrescenta uma deteção (tender_sources) e preenche campos em falta;
senão cria um novo tender.
"""

import datetime as dt

from sqlalchemy import select

from database import models
from utils import text


def _agora():
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


# --------------------------------------------------------------------------- #
# Entidades                                                                   #
# --------------------------------------------------------------------------- #
def get_or_create_entity(sessao, nome, nif=None):
    nome = (nome or "").strip() or "—"
    nif = (nif or "").strip() or None

    if nif:
        ent = sessao.scalars(
            select(models.Entity).where(models.Entity.nif == nif)).first()
        if ent:
            if nome and ent.nome in (None, "", "—"):
                ent.nome = nome
            return ent

    # Sem NIF: tenta casar por nome normalizado entre entidades sem NIF.
    if not nif:
        alvo = text.normalize(nome)
        for ent in sessao.scalars(
                select(models.Entity).where(models.Entity.nif.is_(None))):
            if text.normalize(ent.nome) == alvo:
                return ent

    ent = models.Entity(nif=nif, nome=nome)
    sessao.add(ent)
    sessao.flush()
    return ent


# --------------------------------------------------------------------------- #
# Deduplicação / ingestão                                                     #
# --------------------------------------------------------------------------- #
def _encontrar_canonico(sessao, rec, dh):
    pn = (rec.get("source_procedure_number") or "").strip()
    if pn:
        t = sessao.scalars(
            select(models.Tender).where(models.Tender.procedure_number == pn)).first()
        if t:
            return t

    url = (rec.get("source_url") or "").strip()
    if url:
        ts = sessao.scalars(
            select(models.TenderSource).where(models.TenderSource.source_url == url)).first()
        if ts:
            return ts.tender

    return sessao.scalars(
        select(models.Tender).where(models.Tender.dedup_hash == dh)).first()


def _preencher_em_falta(tender, rec):
    """Completa campos vazios do canónico com dados desta deteção (não sobrescreve)."""
    if not tender.procedure_number and rec.get("source_procedure_number"):
        tender.procedure_number = rec["source_procedure_number"]
    if not tender.description and rec.get("description"):
        tender.description = rec["description"]
    if tender.base_value is None and rec.get("base_value") is not None:
        tender.base_value = rec["base_value"]
    if not tender.publication_date and rec.get("publication_date"):
        tender.publication_date = text.parse_date(rec["publication_date"])
    if not tender.deadline and rec.get("deadline"):
        tender.deadline = text.parse_date(rec["deadline"])
    if not tender.procedure_type and rec.get("procedure_type"):
        tender.procedure_type = rec["procedure_type"]
    if not tender.location and rec.get("location"):
        tender.location = rec["location"]


def _adicionar_fonte(sessao, tender, rec):
    """Acrescenta uma deteção (source, source_url) se ainda não existir."""
    source = rec.get("source")
    url = rec.get("source_url")
    if not url:
        return
    existe = sessao.scalars(
        select(models.TenderSource).where(
            models.TenderSource.source == source,
            models.TenderSource.source_url == url)).first()
    if existe:
        return
    tender.sources.append(models.TenderSource(
        source=source,
        source_url=url,
        source_procedure_number=rec.get("source_procedure_number"),
        raw_payload=rec.get("raw_payload"),
        detected_at=_agora(),
    ))


def _adicionar_cpvs(sessao, tender, cpvs):
    existentes = {c.cpv for c in tender.cpvs}
    for cpv in cpvs or []:
        cpv = str(cpv).strip()
        if cpv and cpv not in existentes:
            existentes.add(cpv)
            tender.cpvs.append(models.TenderCpv(cpv=cpv))


def ingest(sessao, rec):
    """Ingere um registo normalizado de uma fonte. Devolve (tender, is_new).
    Idempotente: re-ingerir o mesmo registo não duplica."""
    dh = text.dedup_hash(
        rec.get("entity_name"), rec.get("title"),
        rec.get("base_value"), rec.get("deadline"))

    tender = _encontrar_canonico(sessao, rec, dh)
    is_new = tender is None

    if is_new:
        entity = get_or_create_entity(
            sessao, rec.get("entity_name"), rec.get("entity_nif"))
        tender = models.Tender(
            procedure_number=(rec.get("source_procedure_number") or None),
            entity_id=entity.id,
            title=(rec.get("title") or "(sem título)")[:1000],
            description=rec.get("description"),
            base_value=rec.get("base_value"),
            currency=rec.get("currency") or "EUR",
            publication_date=text.parse_date(rec.get("publication_date")),
            deadline=text.parse_date(rec.get("deadline")),
            procedure_type=rec.get("procedure_type"),
            location=rec.get("location"),
            status=rec.get("status") or "open",
            dedup_hash=dh,
            first_detected_at=_agora(),
            last_processed_at=_agora(),
        )
        sessao.add(tender)
        sessao.flush()
    else:
        _preencher_em_falta(tender, rec)
        tender.last_processed_at = _agora()
        if tender.entity_id is None:
            entity = get_or_create_entity(
                sessao, rec.get("entity_name"), rec.get("entity_nif"))
            tender.entity_id = entity.id

    _adicionar_fonte(sessao, tender, rec)
    _adicionar_cpvs(sessao, tender, rec.get("cpvs"))
    sessao.flush()
    return tender, is_new


# --------------------------------------------------------------------------- #
# Runs (observabilidade)                                                      #
# --------------------------------------------------------------------------- #
def start_run(sessao, mode):
    run = models.Run(mode=mode, started_at=_agora(), status="running")
    sessao.add(run)
    sessao.flush()
    return run


def finish_run(sessao, run, status, sources_json, new_tenders,
               total_processed, emailed_count=0, notes=""):
    run.finished_at = _agora()
    run.status = status
    run.sources_json = sources_json
    run.new_tenders = new_tenders
    run.total_processed = total_processed
    run.emailed_count = emailed_count
    run.notes = notes
    sessao.flush()
    return run


# --------------------------------------------------------------------------- #
# Queries para o email (Fase E)                                               #
# --------------------------------------------------------------------------- #
def get_unemailed(sessao, excluir_classificacao=("ignorar",)):
    """Concursos ainda não enviados (emailed_at IS NULL) e não-ignorados."""
    q = select(models.Tender).where(models.Tender.emailed_at.is_(None))
    if excluir_classificacao:
        q = q.where(
            (models.Tender.classification.is_(None)) |
            (models.Tender.classification.notin_(list(excluir_classificacao))))
    return list(sessao.scalars(q.order_by(models.Tender.score.desc())))


def mark_emailed(sessao, tender_ids):
    quando = _agora()
    for tid in tender_ids:
        t = sessao.get(models.Tender, tid)
        if t:
            t.emailed_at = quando
    sessao.flush()


def get_tenders_for_scoring(sessao):
    """Todos os concursos (para (re)pontuar na Fase C)."""
    return list(sessao.scalars(select(models.Tender)))
