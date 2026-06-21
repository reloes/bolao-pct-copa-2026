# -*- coding: utf-8 -*-
"""
Carga de dados do site:
- palpites.json (gerado por build_site_data.py — congelado; chaves → int aqui);
- gabarito real: MERGE por prioridade (maior vence) —
    Sheet do organizador (override manual, st.secrets["GABARITO_CSV_URL"])
    > API football-data.org (automático, st.secrets["FOOTBALL_DATA_API_KEY"], via fonte_api)
    > gabarito_local.json (fallback de emergência).
  O botão "Atualizar resultados" do app limpa o cache e força nova busca da API.

Formato CSV esperado (ver gabarito_template.csv): colunas jogo, gols1, gols2, quem_passa
(quem_passa só em empate de mata-mata; nome do time em PT ou EN).
"""
import os
import csv
import json
import io
import tempfile
import unicodedata
import urllib.request
import fixture_copa_2026 as fx

HERE = os.path.dirname(os.path.abspath(__file__))
_REV = "gabarito-base+sheet-snap-v5"   # marca de revisão (força redeploy/pull limpo)

# Snapshot persistente do último gabarito bom da API. Resolve o bug do "jogo some": quando a
# API falha (429 do rate-limit 10/min compartilhado, ou timeout), em vez de degradar para
# "quase nada" usamos o último resultado conhecido. Resultados de jogos terminados não mudam,
# então ACUMULAR (união por jogo) é seguro e garante que o nº de jogos nunca regrida. Vive no
# disco do container (efêmero entre reboots; re-popula na 1ª busca boa).
_API_SNAP = os.path.join(tempfile.gettempdir(), "bolao_pct_api_snapshot.json")


def _read_api_snap():
    try:
        raw = json.load(open(_API_SNAP, encoding="utf-8"))
        return ({int(n): tuple(v) for n, v in raw.get("scores", {}).items()},
                {int(n): t for n, t in raw.get("advancers", {}).items()})
    except Exception:
        return {}, {}


def _write_api_snap(scores, advancers):
    try:
        json.dump({"scores": {str(n): list(v) for n, v in scores.items()},
                   "advancers": {str(n): t for n, t in advancers.items()}},
                  open(_API_SNAP, "w", encoding="utf-8"))
    except Exception:
        pass


# Snapshot do último override BOM da Sheet. Diferente do snapshot da API (que ACUMULA por união,
# porque resultado terminado não muda): o override PODE mudar/ser removido pelo organizador, então
# aqui guardamos o último estado completo e SOBRESCREVEMOS a cada leitura boa (não acumula). Serve
# só para não OSCILAR quando o CSV pisca (timeout) — sem ele, a leitura falha → override some →
# valor da API ressurge → pontuação fica indo e voltando.
_OVERRIDE_SNAP = os.path.join(tempfile.gettempdir(), "bolao_pct_override_snapshot.json")


def _read_override_snap():
    try:
        raw = json.load(open(_OVERRIDE_SNAP, encoding="utf-8"))
        return ({int(n): tuple(v) for n, v in raw.get("scores", {}).items()},
                {int(n): t for n, t in raw.get("advancers", {}).items()})
    except Exception:
        return {}, {}


def _write_override_snap(scores, advancers):
    try:
        json.dump({"scores": {str(n): list(v) for n, v in scores.items()},
                   "advancers": {str(n): t for n, t in advancers.items()}},
                  open(_OVERRIDE_SNAP, "w", encoding="utf-8"))
    except Exception:
        pass


def _norm(s):
    """Matching tolerante de nome de time: sem acentos, casefold, espaços únicos
    (organizador digitando 'Suica'/'turquia ' no celular tem que funcionar)."""
    s = unicodedata.normalize("NFD", str(s))
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return " ".join(s.casefold().split())


_NORM2EN = {}
for _en, _pt in fx.TEAM_PT.items():
    _NORM2EN[_norm(_pt)] = _en
    _NORM2EN[_norm(_en)] = _en


def _team_en(name):
    if not isinstance(name, str) or not name.strip():
        return None
    return _NORM2EN.get(_norm(name))


def _int(v):
    try:
        s = str(v).strip()
        return int(s) if s != "" else None
    except (ValueError, TypeError):
        return None


def load_palpites():
    """(meta, [palpiteiro…]) com chaves numéricas convertidas p/ int."""
    raw = json.load(open(os.path.join(HERE, "palpites.json"), encoding="utf-8"))
    palps = []
    for p in raw["palpiteiros"]:
        palps.append({
            "nome": p["nome"],
            "scores": {int(n): tuple(v) for n, v in p["scores"].items()},
            "advancers": {int(n): t for n, t in (p.get("advancers") or {}).items()},
            "sem_escolha": p.get("sem_escolha") or [],
            "combo": p.get("combo"),
        })
    return raw["_meta"], palps


def load_status(csv_url):
    """Interruptor liga/desliga do site, controlado pela MESMA Google Sheet do organizador.
    Procura a linha de controle (coluna `jogo` = STATUS/SITE/ONLINE):
      - `gols1` ∈ {0, off, nao, não, false, x, fora} → site FORA DO AR;
      - vazio / 1 / on → no ar (default).
      - `time1` dessa linha = mensagem de manutenção (opcional; senão usa o padrão do app).
    Fail-open: sem a linha, ou se a Sheet não puder ser lida, o site fica NO AR (só uma
    ação explícita na Sheet tira do ar). Retorna (online: bool, mensagem: str|None)."""
    if not csv_url:
        return True, None
    try:
        with urllib.request.urlopen(csv_url, timeout=10) as resp:
            rows = list(csv.DictReader(io.StringIO(resp.read().decode("utf-8"))))
    except Exception:
        return True, None
    for row in rows:
        if str(row.get("jogo", "")).strip().lower() in ("status", "site", "online"):
            flag = str(row.get("gols1", "")).strip().lower()
            online = flag not in ("0", "off", "nao", "não", "false", "x", "fora", "offline")
            return online, (row.get("time1") or "").strip() or None
    return True, None


def _parse_rows(rows):
    scores, advancers = {}, {}
    for row in rows:
        num = _int(row.get("jogo"))
        if not num or not (1 <= num <= 104):
            continue
        g1, g2 = _int(row.get("gols1")), _int(row.get("gols2"))
        if g1 is not None and g2 is not None and g1 >= 0 and g2 >= 0:
            scores[num] = (g1, g2)
        adv = _team_en(row.get("quem_passa"))
        if adv and num >= 73:
            advancers[num] = adv
    return scores, advancers


def _load_local():
    """gabarito_local.json (fallback de emergência)."""
    path = os.path.join(HERE, "gabarito_local.json")
    if not os.path.exists(path):
        return {}, {}
    raw = json.load(open(path, encoding="utf-8"))
    scores = {int(n): tuple(v) for n, v in (raw.get("jogos") or {}).items()
              if v and v[0] is not None and v[1] is not None}
    advancers = {int(n): _team_en(t) for n, t in (raw.get("quem_passa") or {}).items()}
    return scores, {n: t for n, t in advancers.items() if t}


def _load_sheet(csv_url):
    """Google Sheet do organizador (CSV publicado) → (scores, advancers)."""
    with urllib.request.urlopen(csv_url, timeout=10) as resp:
        text = resp.read().decode("utf-8")
    return _parse_rows(list(csv.DictReader(io.StringIO(text))))


def load_gabarito_base(api_token=None):
    """Camada AUTOMÁTICA: gabarito_local.json (fallback) + API football-data.org (snapshot
    acumulado). (scores, advancers, fonte). É a parte cara/rate-limited → cache LONGO no app."""
    fontes = []
    scores, advancers = _load_local()                       # base/fallback
    if scores:
        fontes.append(f"local ({len(scores)})")
    if api_token:                                           # automático (football-data.org)
        snap_s, snap_a = _read_api_snap()                  # último estado bom (acumulado)
        try:
            import fonte_api
            a_s, a_a, _ = fonte_api.load_api_gabarito(api_token)
            snap_s.update(a_s)                             # acumula: jogo já apurado nunca regride
            snap_a.update(a_a)
            _write_api_snap(snap_s, snap_a)
            scores.update(snap_s)
            advancers.update(snap_a)
            fontes.append(f"API football-data.org ({len(snap_s)} jogos)")
        except Exception:                                  # 429/timeout → usa o último snapshot bom
            scores.update(snap_s)
            advancers.update(snap_a)
            fontes.append(f"API instável — usando cache ({len(snap_s)} jogos)"
                          if snap_s else "API indisponível")
    return scores, advancers, " + ".join(fontes) if fontes else "vazio"


def load_sheet_override(csv_url=None):
    """Camada MANUAL: só a Sheet do organizador (override que VENCE a API). Barata (1 CSV, sem
    rate-limit) → cache CURTO no app, p/ a correção refletir em segundos. NÃO degrada: leitura boa
    SOBRESCREVE o último-bom (reflete add/alteração/remoção do override); leitura que FALHA usa o
    último-bom (não some) — senão a pontuação oscila quando o CSV pisca. (scores, advancers, fonte|None)."""
    if not csv_url:
        return {}, {}, None
    try:
        s_s, s_a = _load_sheet(csv_url)
        _write_override_snap(s_s, s_a)                       # leitura boa → vira o último-bom (wholesale)
        return s_s, s_a, (f"Sheet override ({len(s_s)})" if (s_s or s_a) else None)
    except Exception:
        snap_s, snap_a = _read_override_snap()               # falhou → segura o último-bom (sem oscilar)
        if snap_s or snap_a:
            return snap_s, snap_a, f"Sheet override (cache, {len(snap_s)})"
        return {}, {}, "Sheet indisponível"


def load_gabarito(csv_url=None, api_token=None):
    """MERGE completo (Sheet override VENCE a base local+API). Mantido p/ chamadas avulsas e QA;
    o app usa as duas camadas em caches separados (base longo, Sheet curto)."""
    scores, advancers, f_base = load_gabarito_base(api_token)
    s_s, s_a, f_sheet = load_sheet_override(csv_url)
    scores.update(s_s)                                       # override por jogo
    advancers.update(s_a)
    fontes = [f for f in (f_base if f_base != "vazio" else None, f_sheet) if f]
    return scores, advancers, " + ".join(fontes) if fontes else "vazio"
