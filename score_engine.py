# -*- coding: utf-8 -*-
"""
Motor-ORÁCULO de pontuação do bolão — referência INDEPENDENTE para o QA da apuração-mestre.
Calcula os pontos do regulamento (Seções A–D do regras.md) em Python puro, para comparar
contra as fórmulas da planilha `Apuracao_PCT_Copa_2026.xlsx` (validação via LibreOffice headless).

Princípio (lição do projeto): o oráculo NÃO reusa as fórmulas da planilha — é uma 2ª implementação.
Para a derivação de bracket (necessária a B/C/D), reusa-se `bolao_engine.derive()` + a propagação
de mata-mata (espelhando winner_f/loser_f da planilha).

ESTADO: Fase 1 = Seção A (fase de grupos). B/C/D entram nas próximas fases.
"""
import fixture_copa_2026 as fx
import bolao_engine as eng   # derive()/rank_group() — usados por B/C/D (fases futuras)

GROUP_NUMS = sorted(num for num, _, _, _, _, _ in fx.GROUP_MATCHES)   # 72 jogos de grupo


def _validint(x):
    """Espelha valid_int da planilha: inteiro >= 0 (texto/None/negativo/decimal -> inválido)."""
    return isinstance(x, int) and not isinstance(x, bool) and x >= 0


def _sign(d):
    return (d > 0) - (d < 0)


def score_game_A(p, r):
    """Pontos da Seção A de UM jogo de grupo. p, r = (g1, g2) ou None (não preenchido/ inválido).
    Exato=6; senão somam-se DOIS acertos INDEPENDENTES: resultado (vencedor/empate)=3 e
    gol exato de um dos times (comparado time a time)=+1 — o +1 vale MESMO errando o
    resultado. (Esclarecimento da organização 12/jun/2026: a redação herdada de 2022,
    "soma ao acerto do vencedor", era ambígua; vale a leitura independente.)"""
    if not p or not r:
        return 0
    p1, p2 = p
    r1, r2 = r
    if not (_validint(p1) and _validint(p2) and _validint(r1) and _validint(r2)):
        return 0
    if p1 == r1 and p2 == r2:
        return 6
    pts = 3 if _sign(p1 - p2) == _sign(r1 - r2) else 0   # resultado (vencedor/empate)
    if p1 == r1 or p2 == r2:                             # gol exato de um dos times (independente)
        pts += 1
    return pts


def section_A(palpite, real):
    """palpite/real: {num: (g1, g2)} dos jogos de grupo (parcial = jogos faltando contam 0).
    Devolve (total, {num: pontos})."""
    per = {num: score_game_A(palpite.get(num), real.get(num)) for num in GROUP_NUMS}
    return sum(per.values()), per


# ============================ Seção B — classificados por fase ============================
# Pressupõe placares DECISIVOS no mata-mata (sem empate) — suficiente para o QA.
KO_SLOTS = {num: (s1, s2) for num, _, _, _, s1, s2 in fx.KO_MATCHES}   # 89..104 usam W##/L##
SET_STEPS_B = [   # (degrau, fase, posição-certa, posição-errada)
    (1, "R32", 4, 2), (2, "R16", 6, 3), (3, "QF", 10, 5),
    (4, "SF", 14, 7), (5, "DISP3", 16, 8), (7, "FINAL", 20, 10),
]


def _validpair(p):
    return bool(p) and _validint(p[0]) and _validint(p[1])

def _group_complete(scores):
    return sum(1 for n in GROUP_NUMS if _validpair(scores.get(n))) == len(GROUP_NUMS)

def _resolve(slot, win, lose):
    k = int(slot[1:])
    return win.get(k) if slot[0] == "W" else lose.get(k)

def derive_full(scores):
    """Bracket COMPLETO a partir dos 104 placares. None se a fase de grupos estiver incompleta.
    Devolve: pos{time:1..4}, conjuntos R32/R16/QF/SF/DISP3/FINAL, e champion/vice/third/fourth."""
    if not _group_complete(scores):
        return None
    d = eng.derive({n: scores[n] for n in GROUP_NUMS})
    pos = {}
    for L, order in d["standings"].items():
        for i, t in enumerate(order):
            pos[t] = i + 1
    teams = {int(k[1:]): v for k, v in d["r32"].items()}          # 73..88 (resolvidos pelo motor)
    win, lose = {}, {}
    for num in range(73, 105):
        if num not in teams:                                       # 89..104: resolve W##/L##
            s1, s2 = KO_SLOTS[num]
            teams[num] = (_resolve(s1, win, lose), _resolve(s2, win, lose))
        a, b = teams[num]; p = scores.get(num)
        if _validpair(p) and a and b:
            ga, gb = p
            win[num] = a if ga > gb else (b if gb > ga else None)
            lose[num] = (b if win[num] == a else a) if win[num] else None
        else:
            win[num] = lose[num] = None

    def setof(nums):
        s = set()
        for n in nums:
            for t in teams.get(n, (None, None)):
                if t:
                    s.add(t)
        return s

    return {"pos": pos, "teams": teams,
            "R32": setof(range(73, 89)), "R16": setof(range(89, 97)),
            "QF": setof(range(97, 101)), "SF": setof(range(101, 103)),
            "DISP3": setof([103]), "FINAL": setof([104]),
            "champion": win.get(104), "vice": lose.get(104),
            "third": win.get(103), "fourth": lose.get(103)}


def section_B(palpite, real):
    """(total, {degrau: pontos}). Degrau 1 (R32) só conta com a fase de grupos REAL completa;
    2-7 ficam 0 enquanto a fase real anterior não foi jogada (conjuntos reais vazios)."""
    pd, rd = derive_full(palpite), derive_full(real)
    gc = _group_complete(real)
    per = {}
    for key, phase, full, half in SET_STEPS_B:
        pts = 0
        if pd and rd and (key != 1 or gc):
            rset = rd[phase]
            for t in pd[phase]:
                if t in rset:
                    pts += full if pd["pos"].get(t) == rd["pos"].get(t) else half
        per[key] = pts
    per[6] = 0                                                     # 3º OU 4º (por acerto): 10/5 cada
    if pd and rd:
        for slot in ("third", "fourth"):
            if pd[slot] and pd[slot] == rd[slot]:
                per[6] += 10 if pd["pos"].get(pd[slot]) == rd["pos"].get(rd[slot]) else 5
    for key, slot, full, half in ((8, "vice", 16, 8), (9, "champion", 30, 15)):
        per[key] = 0
        if pd and rd and pd[slot] and pd[slot] == rd[slot]:
            per[key] = full if pd["pos"].get(pd[slot]) == rd["pos"].get(rd[slot]) else half
    return sum(per.values()), per


# ============================ Seção C — placares do mata-mata ============================
SCORE_C = {}
for _n in range(73, 89):
    SCORE_C[_n] = (6, 3, 1)        # 16-avos
for _n in range(89, 97):
    SCORE_C[_n] = (8, 4, 2)        # Oitavas
for _n in range(97, 101):
    SCORE_C[_n] = (14, 8, 4)       # Quartas
for _n in range(101, 103):
    SCORE_C[_n] = (20, 10, 6)      # Semi
SCORE_C[103] = (20, 10, 6)         # Disputa 3º/4º
SCORE_C[104] = (30, 16, 8)         # Final
_DEGRAU_C = {**{x: 10 for x in range(73, 89)}, **{x: 11 for x in range(89, 97)},
             **{x: 12 for x in range(97, 101)}, **{x: 13 for x in range(101, 103)}, 103: 14, 104: 15}


def section_C(palpite, real):
    """Placar do mata-mata: só pontua se o confronto previsto = real (par NÃO-ordenado) na MESMA
    fase; placar comparado POR TIME (orientação pode inverter); meia se a posição-de-grupo de
    algum dos 2 times difere. (total, {degrau 10..15: pontos})."""
    pd, rd = derive_full(palpite), derive_full(real)
    per = {d: 0 for d in range(10, 16)}
    if not pd or not rd:
        return 0, per
    for num in range(73, 105):
        EX, VE, GOL = SCORE_C[num]
        pT, rT = pd["teams"][num], rd["teams"][num]
        pg, rg = palpite.get(num), real.get(num)
        if not (pT[0] and pT[1] and rT[0] and rT[1]):          # confronto não derivado dos 2 lados
            continue
        if not (_validpair(pg) and _validpair(rg)):            # placar não previsto/jogado
            continue
        same = (pT[0] == rT[0] and pT[1] == rT[1])
        swap = (pT[0] == rT[1] and pT[1] == rT[0])
        if not (same or swap):                                 # confronto diferente -> não pontua
            continue
        pg1, pg2 = pg; rg1, rg2 = rg
        pA, pB = (pg1, pg2) if same else (pg2, pg1)            # gols do palpite alinhados à orientação real
        if pA == rg1 and pB == rg2:
            base = EX
        else:                                            # VE e GOL independentes (organização, 12/jun/2026)
            base = ((VE if _sign(pA - pB) == _sign(rg1 - rg2) else 0)
                    + (GOL if (pA == rg1 or pB == rg2) else 0))
        pos_ok = (pd["pos"].get(rT[0]) == rd["pos"].get(rT[0])
                  and pd["pos"].get(rT[1]) == rd["pos"].get(rT[1]))
        per[_DEGRAU_C[num]] += base if pos_ok else base / 2
    return sum(per.values()), per


# ============================ Seção D — desempate (chave lexicográfica i..xiii) ============================
_US_CODE = next((c for c, n in fx.TEAM_PT.items() if n == "Estados Unidos"), None)
US_GROUP_GAMES = sorted(num for num, _, _, t1, t2, _ in fx.GROUP_MATCHES if _US_CODE in (t1, t2))
D_ORDER = ["i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x", "xi", "xii", "xiii"]   # i = mais significativo
D_MAX = {"i": 2, "ii": 2, "iii": 2, "iv": 4, "v": 2, "vi": 2, "vii": 2, "viii": 4,
         "ix": 8, "x": 16, "xi": 32, "xii": 64, "xiii": 18}

def _d_weights():
    w = {}; acc = 1
    for k in reversed(D_ORDER):           # peso = produto dos (max+1) dos critérios menos significativos
        w[k] = acc; acc *= (D_MAX[k] + 1)
    return w
D_WEIGHTS = _d_weights()                  # acc final (módulo) ~1.1e11 << 2^53


def section_D(palpite, real):
    """Chave de desempate (i mais significativo → xiii). Não soma ao total — ordena empates.
    'posição certa > errada' embutido (2 = time certo na posição certa; 1 = posição errada; 0 = errou)."""
    pd, rd = derive_full(palpite), derive_full(real)
    crit = {k: 0 for k in D_ORDER}
    if pd and rd:
        def tp(slot):                                       # critério de 1 time -> 2/1/0
            pt, rt = pd[slot], rd[slot]
            return (2 if pd["pos"].get(pt) == rd["pos"].get(rt) else 1) if (pt and pt == rt) else 0

        def wc(phase):                                      # contagem ponderada (2 pos certa, 1 errada)
            return sum(2 if pd["pos"].get(t) == rd["pos"].get(t) else 1 for t in pd[phase] if t in rd[phase])

        def jogo(num):                                      # confronto+placar -> 2 (exato) / 1 (confronto) / 0
            pT, rT = pd["teams"][num], rd["teams"][num]; pg, rg = palpite.get(num), real.get(num)
            if not (pT[0] and pT[1] and rT[0] and rT[1] and _validpair(pg) and _validpair(rg)):
                return 0
            same = (pT[0] == rT[0] and pT[1] == rT[1]); swap = (pT[0] == rT[1] and pT[1] == rT[0])
            if not (same or swap):
                return 0
            pg1, pg2 = pg; rg1, rg2 = rg
            pA, pB = (pg1, pg2) if same else (pg2, pg1)
            return 2 if (pA == rg1 and pB == rg2) else 1

        crit["i"] = tp("champion"); crit["iii"] = tp("vice"); crit["v"] = tp("third"); crit["vii"] = tp("fourth")
        crit["iv"] = wc("FINAL"); crit["viii"] = wc("DISP3"); crit["ix"] = wc("SF")
        crit["x"] = wc("QF"); crit["xi"] = wc("R16"); crit["xii"] = wc("R32")
        crit["ii"] = jogo(104); crit["vi"] = jogo(103)
    # xiii é pontuação de JOGOS DE GRUPO (independe do bracket) -> conta sempre que os jogos dos EUA forem jogados
    crit["xiii"] = sum(score_game_A(palpite.get(n), real.get(n)) for n in US_GROUP_GAMES)
    key = sum(crit[k] * D_WEIGHTS[k] for k in D_ORDER)
    return key, crit


def total_points(palpite, real):
    """Total do palpiteiro (A + B + C). A Seção D é DESEMPATE (chave), não soma ao total."""
    return section_A(palpite, real)[0] + section_B(palpite, real)[0] + section_C(palpite, real)[0]


if __name__ == "__main__":
    real = {n: (2, 1) for n in range(1, 105)}      # cenário decisivo (grupo 2x1; mata-mata 2x1)
    print("== A ==", "igual:", section_A(real, real)[0], "(esp", 6 * 72, ")  vazio:", section_A({}, real)[0])
    print("== B ==", "igual:", section_B(real, real)[0], "(máx 498)  vazio:", section_B({}, real)[0])
    tc, perc = section_C(real, real)
    print("== C ==", "igual:", tc, "por degrau:", perc, "(máx 306)  vazio:", section_C({}, real)[0])
    print("TOTAL igual:", total_points(real, real), "(máx A+B+C = 432+498+306 = 1236)")
    kd, crit = section_D(real, real)
    print("== D ==", "jogos EUA:", US_GROUP_GAMES, "| critérios igual:", crit)
    print("chave igual ao real:", kd, "| chave vazio:", section_D({}, real)[0],
          "| < 2^53?", kd < 2**53, "(2^53 =", 2**53, ")")
