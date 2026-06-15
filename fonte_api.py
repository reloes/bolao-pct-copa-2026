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
import time
import urllib.request
import fixture_copa_2026 as fx
import bolao_engine as eng

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

# slots do mata-mata (89+ usam W##/L##; 73-88 vêm da derivação dos grupos)
KO_SLOTS = {num: (s1, s2) for num, _, _, _, s1, s2 in fx.KO_MATCHES}
KO_STAGES = {"LAST_32", "LAST_16", "QUARTER_FINALS", "SEMI_FINALS", "THIRD_PLACE", "FINAL"}


def fetch_matches(token, retries=1):
    """Baixa todos os jogos da Copa da API. 1 retry curto p/ erro transitório (rede/timeout);
    lança se persistir (ex.: 429 de rate-limit) — o chamador trata caindo no snapshot."""
    last = None
    for i in range(retries + 1):
        try:
            req = urllib.request.Request(WC_URL, headers={"X-Auth-Token": token})
            with urllib.request.urlopen(req, timeout=12) as r:
                return json.load(r).get("matches", [])
        except Exception as e:
            last = e
            if i < retries:
                time.sleep(2)
    raise last


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


def _ko_field_score(m):
    """Placar 'de campo' do mata-mata (vale o fim da prorrogação; pênaltis NÃO contam) + o score bruto.
    Prioriza extraTime/regularTime se a API os expuser; senão fullTime.
    ⚠️ AJUSTAR/confirmar no 1º jogo real (28/jun): a estrutura de prorrogação/pênaltis só
    aparece quando há um jogo de mata-mata jogado; hoje só dá p/ testar com cenário simulado."""
    s = m.get("score") or {}
    for campo in ("extraTime", "regularTime"):     # placar de campo, sem o shootout
        v = s.get(campo) or {}
        if v.get("home") is not None and v.get("away") is not None:
            return v["home"], v["away"], s
    ft = s.get("fullTime") or {}
    return ft.get("home"), ft.get("away"), s


def parse_ko(matches, group_scores):
    """{num:(g1,g2)} e {num: advancer_en} dos jogos de MATA-MATA FINISHED, mapeados aos slots
    73-104. Casa por par de times — os 32-avos vêm da derivação dos grupos (matriz oficial) e
    as fases seguintes da propagação dos vencedores REAIS. 'quem passou' (inclui pênaltis) vem
    do campo `winner` da API. Só roda com os 72 grupos completos."""
    if len(group_scores) != 72:
        return {}, {}
    api = {}                                        # par de TLAs -> match (mata-mata FINISHED, 2 times definidos)
    for m in matches:
        if m.get("stage") not in KO_STAGES or m.get("status") != "FINISHED":
            continue
        ht = (m.get("homeTeam") or {}).get("tla")
        at = (m.get("awayTeam") or {}).get("tla")
        if ht in TLA_TO_EN and at in TLA_TO_EN:
            api[frozenset({ht, at})] = m
    if not api:
        return {}, {}

    slot = {int(k[1:]): v for k, v in eng.derive(group_scores)["r32"].items()}   # 73-88 (chaves "M73"..)
    scores, advancers, win, lose = {}, {}, {}, {}
    for num in range(73, 105):
        if num not in slot:                          # 89+: resolve W##/L## com os vencedores já apurados
            s1, s2 = KO_SLOTS[num]
            a = win.get(int(s1[1:])) if s1[0] == "W" else lose.get(int(s1[1:]))
            b = win.get(int(s2[1:])) if s2[0] == "W" else lose.get(int(s2[1:]))
            slot[num] = (a, b)
        a, b = slot[num]
        if not (a and b):
            continue                                 # confronto ainda indefinido (fase anterior não apurada)
        m = api.get(frozenset({EN_TO_TLA[a], EN_TO_TLA[b]}))
        if not m:
            continue                                 # jogo ainda não realizado
        gh, ga, s = _ko_field_score(m)
        if gh is None or ga is None:
            continue
        ht = (m["homeTeam"]).get("tla")
        g_a, g_b = (int(gh), int(ga)) if ht == EN_TO_TLA[a] else (int(ga), int(gh))   # orienta p/ (a,b)
        scores[num] = (g_a, g_b)
        wside = s.get("winner")
        if wside == "HOME_TEAM":
            w_en = TLA_TO_EN.get(ht)
        elif wside == "AWAY_TEAM":
            w_en = TLA_TO_EN.get((m["awayTeam"]).get("tla"))
        else:
            w_en = a if g_a > g_b else (b if g_b > g_a else None)
        win[num] = w_en
        lose[num] = (b if w_en == a else a) if w_en else None
        if g_a == g_b and w_en:                      # empate de campo -> decidido nos pênaltis -> quem passou
            advancers[num] = w_en
    return scores, advancers


def load_api_gabarito(token):
    """(scores, advancers, n). Grupos + mata-mata (este só com os 72 grupos completos)."""
    matches = fetch_matches(token)
    g = parse_group_scores(matches)
    ko_s, ko_a = parse_ko(matches, g)
    return {**g, **ko_s}, ko_a, len(g) + len(ko_s)
