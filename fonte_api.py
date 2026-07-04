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
    "TUR": "Türkiye", "USA": "United States", "URU": "Uruguay", "UZB": "Uzbekistan",
}
# integridade do de-para: cobre exatamente as 48 seleções do nosso fixture
assert len(TLA_TO_EN) == 48, f"de-para tem {len(TLA_TO_EN)} (esperado 48)"
_missing = set(fx.TEAM_PT) ^ set(TLA_TO_EN.values())
assert not _missing, f"de-para TLA divergente do fixture: {_missing}"
# TLAs FIFA (CHAVES) conferidos contra a API ao vivo em 2026-06-28 — trava typo de sigla, que o
# assert de NOMES acima não pega (foi assim que 'URY' passou no lugar do 'URU' real, derrubando
# os 3 jogos do Uruguai → grupos "incompletos" → mata-mata não apurava). Atualize SE a API mudar.
_TLAS_FIFA = frozenset(
    "ALG ARG AUS AUT BEL BIH BRA CAN CPV COL COD CRO CUW CZE ECU EGY ENG FRA GER GHA HAI IRN IRQ "
    "CIV JPN JOR MEX MAR NED NZL NOR PAN PAR POR QAT KSA SCO SEN RSA KOR ESP SWE SUI TUN TUR USA "
    "URU UZB".split())
assert set(TLA_TO_EN) == _TLAS_FIFA, f"TLA(s) fora do padrão FIFA da API: {set(TLA_TO_EN) ^ _TLAS_FIFA}"
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
    """Placar 'de campo' do mata-mata (resultado ao FIM DA PRORROGAÇÃO, SEM o shootout) + o score bruto.
    ⚠️ ARMADILHA confirmada nos pênaltis reais (29/jun): num jogo de PÊNALTIS a football-data.org SOMA
    o shootout no `fullTime` (GER×PAR `fullTime` 4×5 = `regularTime` 1×1 + `penalties` 3×4) — então
    fullTime NÃO é o placar de campo. Regra: se há `regularTime` (houve prorrogação/pênaltis), placar
    de campo = regularTime + extraTime (gols só da prorrogação); senão (decidido no tempo normal) =
    fullTime. `score.winner` decide quem passa (cobre os pênaltis → fica empate de campo → advancer).
    Validado: RSA 0x1 CAN (REGULAR → fullTime), GER 1x1 PAR / NED 1x1 MAR (PÊNALTIS → regularTime)."""
    s = m.get("score") or {}
    rt = s.get("regularTime") or {}
    if rt.get("home") is not None and rt.get("away") is not None:     # houve prorrogação (e talvez pênaltis)
        et = s.get("extraTime") or {}
        return rt["home"] + (et.get("home") or 0), rt["away"] + (et.get("away") or 0), s
    ft = s.get("fullTime") or {}                                      # decidido no tempo normal
    return ft.get("home"), ft.get("away"), s


def _agg_winner(s, ht, a, b):
    """Quem passou quando a API NÃO preenche `score.winner` num mata-mata FINISHED (visto no AUS×EGY,
    03/jul: pênaltis, status FINISHED, mas `winner=null`). Usa o agregado `fullTime` — que SOMA o
    shootout dos pênaltis — para desempatar o placar de campo. Orienta p/ (a,b); None se indefinido."""
    ft = s.get("fullTime") or {}
    fh, fa = ft.get("home"), ft.get("away")
    if fh is None or fa is None or fh == fa:
        return None
    ft_a, ft_b = (fh, fa) if ht == EN_TO_TLA[a] else (fa, fh)
    return a if ft_a > ft_b else b


def parse_ko(matches, group_scores):
    """{num:(g1,g2)} e {num: advancer_en} dos jogos de MATA-MATA FINISHED, mapeados aos slots
    73-104. Casa por par de times — os 16-avos vêm da derivação dos grupos (matriz oficial) e
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
        elif g_a != g_b:                             # winner ausente, mas o placar de campo já decide
            w_en = a if g_a > g_b else b
        else:                                        # empate de campo + winner ausente (a API às vezes não
            w_en = _agg_winner(s, ht, a, b)          # preenche winner nos pênaltis) → desempata pelo fullTime
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
