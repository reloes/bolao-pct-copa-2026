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
import unicodedata
import urllib.request
import fixture_copa_2026 as fx

HERE = os.path.dirname(os.path.abspath(__file__))


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


def load_gabarito(csv_url=None, api_token=None):
    """(scores, advancers, fonte) com MERGE por prioridade (maior vence):
    Sheet do organizador (override manual) > API football-data.org (automático) >
    gabarito_local.json (fallback). Cada camada sobrescreve a anterior POR JOGO."""
    fontes = []
    scores, advancers = _load_local()                       # base/fallback
    if scores:
        fontes.append(f"local ({len(scores)})")
    if api_token:                                           # automático (football-data.org)
        try:
            import fonte_api
            a_s, a_a, n = fonte_api.load_api_gabarito(api_token)
            scores.update(a_s)
            advancers.update(a_a)
            fontes.append(f"API football-data.org ({n} jogos)")
        except Exception:
            fontes.append("API indisponível")
    if csv_url:                                             # override do organizador (vence)
        try:
            s_s, s_a = _load_sheet(csv_url)
            scores.update(s_s)
            advancers.update(s_a)
            if s_s or s_a:
                fontes.append(f"Sheet override ({len(s_s)})")
        except Exception:
            fontes.append("Sheet indisponível")
    return scores, advancers, " + ".join(fontes) if fontes else "vazio"
