# Site do Bolão PCT — Copa 2026 · guia de operação e deploy

O site é a **apuração oficial** (decisão 2026-06-11): palpites congelados + gabarito do
organizador + ranking + simulador + penalidade do DACA. Pontuação 100% fiel aos motores
validados do projeto (`qa_site.py` prova a paridade com o oráculo).

## Rodar local (teste)

Duplo clique em **`Abrir Site Bolao (local).command`** (na raiz do projeto), ou:

```bash
cd site && .venv/bin/python3 -m streamlit run app.py --server.port 8503
```

Porta **8503** = reserva deste projeto na tabela de portas do workspace D1A.

## Publicar na internet (Streamlit Community Cloud — grátis)

1. **GitHub:** crie um repositório (pode ser **privado**), ex. `bolao-pct-copa-2026`, e suba o
   **conteúdo da pasta `site/`** (sem o `.venv/`): `app.py`, `scoring.py`, `data.py`,
   `palpites.json`, `gabarito_local.json`, `fixture_copa_2026.py`, `bolao_engine.py`,
   `score_engine.py`, `fifa_thirds_matrix.json`, `regras.md`, `requirements.txt`,
   `.streamlit/config.toml`.
2. **share.streamlit.io** → faça login com o GitHub → **New app** → escolha o repositório,
   branch `main`, arquivo `app.py` → **Deploy**. Em ~2 min sai a URL pública
   (ex. `https://bolao-pct-copa-2026.streamlit.app`) — é essa que vai no grupo do zap.
3. O link é **não-listado** (decisão 11/jun): só acha quem tiver a URL.

## Gabarito oficial — como lançar resultados (só você)

**Modo recomendado (Google Sheet):**
1. Crie uma planilha no SEU Drive importando `gabarito_template.csv` (104 linhas: jogo,
   fase, data, time1, time2, gols1, gols2, quem_passa). **Não compartilhe a edição** — a
   autenticação do organizador é a permissão do Google.
2. Preencha `gols1`/`gols2` conforme os jogos acontecem (mata-mata: placar **ao fim da
   prorrogação**; se empatado, preencha também `quem_passa` com o time que avançou nos pênaltis).
3. Publique como CSV: **Arquivo → Compartilhar → Publicar na web → aba do gabarito →
   CSV** → copie a URL.
4. No Streamlit Cloud: **App → Settings → Secrets** e adicione:
   `GABARITO_CSV_URL = "https://docs.google.com/spreadsheets/d/e/…/pub?output=csv"`
   O site passa a ler a Sheet (cache de 60 s — botão “Atualizar resultados” força).

**Modo local/fallback:** edite `site/gabarito_local.json` (`"jogos": {"1": [2, 0], …}` +
`"quem_passa": {"95": "Argentina"}` para pênaltis) e suba o commit. Sem a secret, o site usa
este arquivo. *(J1 México 2-0 já está lançado.)*

## Atualizações de dados

- **Palpites:** NUNCA mudam (congelados; SHA-256 na página Regras). Se algum dia for preciso
  regenerar (ex.: correção de bug), rode `python3 build_site_data.py` na raiz do projeto e
  suba o novo `palpites.json` — os arquivos dos palpiteiros continuam intocados.
- **Penalidade DACA:** embutida em `palpites.json` (`_meta.penalidades`) e aplicada por
  `scoring.py` (J1 anulado SÓ na Seção A; tabela do grupo A do palpite dele intacta).
- **QA:** `cd site && .venv/bin/python3 qa_site.py` (paridade × oráculo, 1236, penalidade,
  pênaltis) — rode após qualquer mudança em `scoring.py`/`palpites.json`.

## A planilha-apuração aposentou?

Sim como apuração oficial; fica como **backup e oráculo de conferência** (o QA do site já
compara com os mesmos motores que validaram a planilha). Não lance resultados nela — o
gabarito vive na Sheet/JSON do site (mestre único).
