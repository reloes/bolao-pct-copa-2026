# -*- coding: utf-8 -*-
"""
Carga de dados do site:
- palpites.json (gerado por build_site_data.py — congelado; chaves → int aqui);
- gabarito real: 1º a URL CSV publicada da Google Sheet do organizador (st.secrets
  ["GABARITO_CSV_URL"], cache 60s — SÓ o Renato edita a Sheet = autenticação via Google);
  fallback: gabarito_local.json (modo local / antes de publicar a Sheet).

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


def load_gabarito(csv_url=None):
    """(scores, advancers, fonte). Tenta a URL CSV publicada; senão, o JSON local."""
    if csv_url:
        try:
            with urllib.request.urlopen(csv_url, timeout=10) as resp:
                text = resp.read().decode("utf-8")
            rows = list(csv.DictReader(io.StringIO(text)))
            scores, advancers = _parse_rows(rows)
            return scores, advancers, "Google Sheet do organizador (CSV publicado)"
        except Exception as e:                       # rede/URL fora → cai no local
            err = f" (falha na Sheet: {e})"
    else:
        err = ""
    path = os.path.join(HERE, "gabarito_local.json")
    if os.path.exists(path):
        raw = json.load(open(path, encoding="utf-8"))
        scores = {int(n): tuple(v) for n, v in (raw.get("jogos") or {}).items()
                  if v and v[0] is not None and v[1] is not None}
        advancers = {int(n): _team_en(t) for n, t in (raw.get("quem_passa") or {}).items()}
        advancers = {n: t for n, t in advancers.items() if t}
        return scores, advancers, "gabarito_local.json" + err
    return {}, {}, "vazio" + err
