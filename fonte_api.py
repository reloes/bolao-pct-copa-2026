# -*- coding: utf-8 -*-
"""
Busca resultados REAIS da football-data.org (API v4) e mapeia aos nossos jogos.

De-para por TLA (sigla FIFA de 3 letras) — robusto à variação de nome
(ex.: a API escreve "Bosnia-Herzegovina", "Turkey", "Congo DR"; nós usamos
"Bosnia and Herzegovina", "Türkiye", "DR Congo"). Verificado contra a API em 13/jun/2026.

ENTREGA 1 (agora): fase de grupos (72 jogos, sem prorrogação/pênaltis = risco baixo).
ENTREGA 2 (~28/jun): mata-mata — placar ao fim da prorrogação + "quem passou" nos
pênaltis (a API tem `score.winner`/`score.penalties`), validado no 1º jogo real.
"""
import json
import urllib.request
import fixture_copa_2026 as fx

WC_URL = "https://api.football-data.org/v4/competitions/WC/matches"

# TLA (football-data.org) -> nome EN do nosso fixture.
TLA_TO_EN = {
    "ALG": "Algeria", "ARG": "Argentina", "AUS": "Australia", "AUT": "Austria", "BEL": "Belgium",
    "BIH": "Bosnia and Herzegovina", "BRA": "Brazil", "CAN": "Canada", "CPV": "Cape Verde",
    "COL": "Colombia", "COD": "DR Congo", "CRO": "Croatia", "CUW": "Curaçao", "CZE": "Czechia",
    "ECU": "Ecuador", "EGY": "Egypt", "ENG": "England", "FRA": "France", "GER": "Germany",
    "GHA": "Ghana", "HAI": "Haiti", "IRN": "Iran", "IRQ": "Iraq", "CIV": "Ivory Coast",
    "JPN": "Japan", "JOR": "Jordan", "MEX": "Mexico", "MAR": "Morocco", "NED": "Netherlands",
    "NZL": "New Zealand", "NOR": "Norway", "PAN": "Panama", "PAR": "Paraguay", "POR": "Portugal",
    "QAT": "Qatar", "KSA": "Saudi Arabia", "SCO": "Scotland", "SEN": "Senegal", "RSA": "South Africa",
    "KOR": "South Korea", "ESP": "Spain", "SWE": "Sweden", "SUI": "Switzerland", "TUN": "Tunisia",
    "TUR": "Türkiye", "USA": "United States", "URY": "Uruguay", "UZB": "Uzbekistan",
}
# integridade do de-para: cobre exatamente as 48 seleções do nosso fixture
assert len(TLA_TO_EN) == 48, f"de-para tem {len(TLA_TO_EN)} (esperado 48)"
_missing = set(fx.TEAM_PT) ^ set(TLA_TO_EN.values())
assert not _missing, f"de-para TLA divergente do fixture: {_missing}"
EN_TO_TLA = {en: tla for tla, en in TLA_TO_EN.items()}

# jogo de grupo (num) indexado pelo par de TLAs; guarda o TLA do time1 (orientação do fixture)
_GROUP_BY_PAIR = {}
for _num, _, _, _t1, _t2, _ in fx.GROUP_MATCHES:
    _GROUP_BY_PAIR[frozenset({EN_TO_TLA[_t1], EN_TO_TLA[_t2]})] = (_num, EN_TO_TLA[_t1])


def fetch_matches(token):
    """Baixa todos os jogos da Copa da API. Lança em erro de rede/HTTP."""
    req = urllib.request.Request(WC_URL, headers={"X-Auth-Token": token})
    with urllib.request.urlopen(req, timeout=12) as r:
        return json.load(r).get("matches", [])


def parse_group_scores(matches):
    """{num: (g1,g2)} dos jogos de GROUP_STAGE FINISHED, na orientação (time1,time2) do fixture.
    Casado por par de TLA; jogos não-terminados ou sem placar são ignorados (sem erro)."""
    out = {}
    for m in matches:
        if m.get("stage") != "GROUP_STAGE" or m.get("status") != "FINISHED":
            continue
        ht = (m.get("homeTeam") or {}).get("tla")
        at = (m.get("awayTeam") or {}).get("tla")
        ft = (m.get("score") or {}).get("fullTime") or {}
        gh, ga = ft.get("home"), ft.get("away")
        if ht not in TLA_TO_EN or at not in TLA_TO_EN or gh is None or ga is None:
            continue
        hit = _GROUP_BY_PAIR.get(frozenset({ht, at}))
        if not hit:
            continue
        num, tla_t1 = hit
        out[num] = (int(gh), int(ga)) if ht == tla_t1 else (int(ga), int(gh))
    return out


def load_api_gabarito(token):
    """(scores, advancers, n). advancers={} na entrega 1 (mata-mata = entrega 2)."""
    matches = fetch_matches(token)
    scores = parse_group_scores(matches)
    return scores, {}, len(scores)
