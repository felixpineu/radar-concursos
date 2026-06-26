# Radar de Concursos — Fórum Estudante

Programa que corre **sozinho na nuvem** (GitHub Actions), procura concursos públicos
nas áreas da Fórum Estudante e envia um **email diário** com o briefing. Não depende
do teu computador estar ligado.

## Arquitetura (modular — uma fonte por ficheiro)

- `radar.py` — orquestrador. Junta as fontes, aplica o perfil, monta o briefing,
  gere a memória dos concursos já vistos e escreve `briefing.html`.
- `filters.py` — perfil de interesse da Fórum Estudante (CPV + palavras-chave +
  exclusões + score em estrelas). **Partilhado por todas as fontes.**
- `source_ted.py` — **Fonte 1 (ATIVA): TED**, Radar Europeu / acima dos limiares.
- `source_base.py` — **Fonte 2 (Fase 2, por ativar): Portal BASE**, concursos
  nacionais, incluindo abaixo dos limiares europeus.
- `source_dre.py` — **Fonte 3 (Fase 2, por ativar): Diário da República**.
- `seen.json` — memória dos concursos já reportados (para enviar só os novos).
- `.github/workflows/radar.yml` — agendador (dias úteis ~12h de Portugal) + email.

Para acrescentar uma fonte nova no futuro, basta implementar o seu `fetch()` (que
devolve oportunidades normalizadas) e ativá-la — o filtro e o briefing já a integram.

## O briefing é sempre separado por fonte

1. Concursos encontrados no **TED**
2. Concursos **nacionais / BASE / DR** (quando estas fontes estiverem ativas)
3. **Limitações de cobertura** — aviso explícito de que, enquanto só o TED está
   ativo, o relatório pode não incluir concursos nacionais abaixo dos limiares.

## "Mapear tudo, depois só os novos"

Na 1ª execução, tudo o que está aberto é considerado novo (mapa inicial). A partir
daí, `seen.json` regista o que já foi reportado e o briefing destaca **apenas os
novos** concursos de cada dia.

## Instalação dos segredos de email (uma vez)

Em **Settings → Secrets and variables → Actions**, criar:
- `MAIL_USERNAME` = `felixpineu@gmail.com`
- `MAIL_PASSWORD` = uma **App Password do Gmail** (16 caracteres, sem espaços;
  requer verificação em 2 passos ativa).

## Como afinar

- Áreas/palavras-chave/exclusões: `filters.py`.
- Janela de dias e país do TED: `source_ted.py`.
- Hora: `cron` em `.github/workflows/radar.yml` (em UTC).

## Fase 2 — cobertura nacional

Para incluir os concursos nacionais (sobretudo os pequenos, < 20.000 €), é preciso
ativar `source_base.py` / `source_dre.py`. A via mais fiável é a **API do Portal
BASE (IMPIC)**, que requer registo + autorização. Depois disso, implementa-se o
`fetch()` real nesses ficheiros e o briefing passa a juntar as três fontes.
