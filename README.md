# Radar de Concursos — Fórum Estudante (versão cloud)

Programa que corre **sozinho na nuvem** (GitHub Actions), consulta o **TED**
(concursos públicos europeus) filtrado pelas áreas da Fórum Estudante, e envia-te
um **email diário** com o briefing. Não depende do teu computador estar ligado.

> **Cobertura:** o TED só inclui concursos **acima dos limiares europeus**. Os
> concursos nacionais mais pequenos (abaixo do limiar) não entram nesta fonte —
> esses continuam a precisar do BASE/DRE. Ver secção "Passo seguinte".

---

## O que está nesta pasta

- `radar_ted.py` — o programa (Python, sem instalar nada).
- `.github/workflows/radar.yml` — o agendador (corre dias úteis ~12h de Portugal).
- `README.md` — este guia.

---

## Instalação (uma vez, ~10 minutos)

**1. Cria uma conta GitHub** (grátis) em https://github.com, se ainda não tiveres.

**2. Cria um repositório novo** (botão "+" → "New repository"). Nome à escolha,
ex.: `radar-concursos`. Podes deixá-lo privado.

**3. Carrega estes ficheiros** para o repositório, mantendo a estrutura de pastas:
- `radar_ted.py` na raiz
- `.github/workflows/radar.yml` dentro da pasta `.github/workflows`

(Podes arrastar os ficheiros na página do repositório com "Add file → Upload files".)

**4. Cria uma "App Password" do Gmail** (para o programa poder enviar o email):
- Tens de ter a verificação em 2 passos ativa na conta Google.
- Vai a https://myaccount.google.com/apppasswords, cria uma password de aplicação
  (ex.: nome "Radar"). Copia os 16 caracteres gerados.

**5. Guarda os segredos no repositório:**
- No repositório: **Settings → Secrets and variables → Actions → New repository secret**.
- Cria `MAIL_USERNAME` = `felixpineu@gmail.com`
- Cria `MAIL_PASSWORD` = a App Password de 16 caracteres do passo 4.

**6. Pronto.** Vai ao separador **Actions**, escolhe "Radar Concursos Fórum
Estudante" e clica **Run workflow** para testar já. Deves receber o email.
A partir daí corre automaticamente todos os dias úteis.

---

## Como afinar

Abre `radar_ted.py` e edita no topo:
- `CPV_INCLUIR` — famílias de CPV a captar.
- `TERMOS_INTERESSE` / `TERMOS_EXCLUIR` — palavras que sobem/excluem.
- `DIAS_RETROATIVOS` — janela de dias a varrer.
- A hora está em `radar.yml` (`cron`, em UTC).

---

## Passo seguinte (cobertura nacional completa)

Para apanhar também os concursos **nacionais abaixo do limiar** de forma cloud,
é preciso pedir acesso à **API do Portal BASE (IMPIC)** — gratuito, mas sujeito a
autorização. Quando tiveres o acesso, junta-se um segundo módulo a este programa.
Enquanto isso, o radar via Chrome (no teu computador) cobre esses concursos.
