# -*- coding: utf-8 -*-
"""
Motor de derivação do bolão (fundação da apuração e da planilha integrada).
A partir dos PLACARES dos 72 jogos de grupo, deriva:
  - classificação 1º–4º de cada grupo (desempate FIFA: pontos → confronto direto → saldo → gols);
  - os 8 melhores terceiros (pontos → saldo → gols);
  - os confrontos dos 32-avos, usando a matriz oficial (fifa_thirds_matrix.json).

Observação de fidelidade: fair-play e ranking FIFA (últimos critérios) não se aplicam a
palpites (não há cartões previstos); o desempate final usa uma ordem estável determinística.
"""
import os
import json
from itertools import groupby
import fixture_copa_2026 as fx

HERE = os.path.dirname(os.path.abspath(__file__))
MATRIX = json.load(open(os.path.join(HERE, "fifa_thirds_matrix.json")))["matriz"]

# colunas da matriz: mandante e jogo correspondentes
COL_WINNER = ["A", "B", "D", "E", "G", "I", "K", "L"]
COL_MATCH = ["M79", "M85", "M81", "M74", "M82", "M77", "M87", "M80"]

# confrontos diretos dos 32-avos (24 vagas de 1º/2º), do regulamento (pág. 23)
DIRECT_R32 = [
    ("M73", ("2", "A"), ("2", "B")), ("M75", ("1", "F"), ("2", "C")),
    ("M76", ("1", "C"), ("2", "F")), ("M78", ("2", "E"), ("2", "I")),
    ("M83", ("2", "K"), ("2", "L")), ("M84", ("1", "H"), ("2", "J")),
    ("M86", ("1", "J"), ("2", "H")), ("M88", ("2", "D"), ("2", "G")),
]
# jogos onde o mandante (1º) enfrenta um 3º
WINNER_VS_THIRD = {"M74": "E", "M77": "I", "M79": "A", "M80": "L",
                   "M81": "D", "M82": "G", "M85": "B", "M87": "K"}

# jogos de cada grupo (returno simples)
GROUP_FIXT = {L: [] for L in fx.GROUPS}
_t2g = {t: L for L, ts in fx.GROUPS.items() for t in ts}
for num, _, _, t1, t2, _ in fx.GROUP_MATCHES:
    GROUP_FIXT[_t2g[t1]].append((num, t1, t2))


def rank_group(teams, matches):
    """matches: lista (t1,t2,g1,g2). Retorna (ordem 1º..4º, pts, gd, gf)."""
    pts = {t: 0 for t in teams}; gd = {t: 0 for t in teams}; gf = {t: 0 for t in teams}
    for t1, t2, g1, g2 in matches:
        gf[t1] += g1; gf[t2] += g2; gd[t1] += g1 - g2; gd[t2] += g2 - g1
        if g1 > g2: pts[t1] += 3
        elif g2 > g1: pts[t2] += 3
        else: pts[t1] += 1; pts[t2] += 1

    def h2h(subset):
        hp = {t: 0 for t in subset}; hg = {t: 0 for t in subset}; hf = {t: 0 for t in subset}
        for t1, t2, g1, g2 in matches:
            if t1 in subset and t2 in subset:
                hf[t1] += g1; hf[t2] += g2; hg[t1] += g1 - g2; hg[t2] += g2 - g1
                if g1 > g2: hp[t1] += 3
                elif g2 > g1: hp[t2] += 3
                else: hp[t1] += 1; hp[t2] += 1
        return hp, hg, hf

    def order_cluster(cl):                              # Art. 13 recursivo (Step 1 → Step 2)
        if len(cl) == 1:
            return cl
        hp, hg, hf = h2h(cl)
        cl2 = sorted(cl, key=lambda t: (-hp[t], -hg[t], -hf[t]))
        subs = [list(g) for _, g in groupby(cl2, key=lambda t: (hp[t], hg[t], hf[t]))]
        if len(subs) == 1:                              # Step 1 não progrediu → saldo/gols → ranking FIFA
            return sorted(cl, key=lambda t: (-gd[t], -gf[t], fx.TEAM_FIFA_RANK[t]))
        res = []
        for s in subs:                                  # re-aplica entre os que sobraram empatados
            res += s if len(s) == 1 else order_cluster(s)
        return res

    order = []
    for _, grp in groupby(sorted(teams, key=lambda t: -pts[t]), key=lambda t: pts[t]):
        order += order_cluster(list(grp))
    return order, pts, gd, gf


def derive(scores):
    """scores: {match_num: (g1,g2)} dos 72 jogos de grupo.
    Retorna dict com standings, terceiros, combinação e confrontos dos 32-avos."""
    standings = {}; stats = {}; thirds = []
    for L, teams in fx.GROUPS.items():
        ms = [(t1, t2, *scores[num]) for num, t1, t2 in GROUP_FIXT[L]]
        order, pts, gd, gf = rank_group(teams, ms)
        standings[L] = order
        for t in teams:
            stats[t] = (pts[t], gd[t], gf[t])
        third_team = order[2]
        thirds.append((L, third_team, pts[third_team], gd[third_team], gf[third_team]))

    # 8 melhores terceiros: pontos -> saldo -> gols -> RANKING FIFA (Art. 13)
    thirds_ranked = sorted(thirds, key=lambda x: (-x[2], -x[3], -x[4], fx.TEAM_FIFA_RANK[x[1]]))
    best8 = thirds_ranked[:8]
    best8_groups = sorted(L for L, *_ in best8)
    key = "".join(best8_groups)
    assign = MATRIX[key]                                  # 3º (por grupo) em ordem de coluna
    winner_to_third = {COL_WINNER[i]: assign[i] for i in range(8)}

    def team(pos, L):
        return standings[L][int(pos) - 1]                 # 1->idx0 ... 4->idx3

    r32 = {}
    for match, (p1, g1), (p2, g2) in DIRECT_R32:
        r32[match] = (team(p1, g1), team(p2, g2))
    for match, wgroup in WINNER_VS_THIRD.items():
        tg = winner_to_third[wgroup]                      # grupo do 3º que enfrenta o 1º{wgroup}
        r32[match] = (team("1", wgroup), team("3", tg))
    return {"standings": standings, "thirds_best8": best8_groups,
            "combo_key": key, "winner_to_third": winner_to_third, "r32": r32}


if __name__ == "__main__":
    # placares pseudo-determinísticos (sem aleatoriedade) só para EXERCITAR o motor
    scores = {}
    for num, _, _, t1, t2, _ in fx.GROUP_MATCHES:
        scores[num] = ((num * 3 + 7) % 4, (num * 2 + 5) % 4)
    d = derive(scores)
    print("Combinação dos 8 melhores 3ºs:", d["combo_key"])
    print("1º x 3º (via matriz):", {m: f"1{w}x3{t}" for w, t in d["winner_to_third"].items()
                                     for m in [COL_MATCH[COL_WINNER.index(w)]]})
    teams_r32 = [t for pair in d["r32"].values() for t in pair]
    print("\nVerificações:")
    print("  16 jogos de 32-avos:", len(d["r32"]) == 16)
    print("  32 times distintos:", len(set(teams_r32)) == 32)
    same = [(m, a, b) for m, (a, b) in d["r32"].items() if _t2g[a] == _t2g[b]]
    print("  nenhum confronto do mesmo grupo:", not same, same[:3])
    print("  combinação existe na matriz oficial:", d["combo_key"] in MATRIX)
    # amostra de classificação
    print("\nClassificação Grupo C (Brasil):", [fx.TEAM_PT[t] for t in d["standings"]["C"]])
