# -*- coding: utf-8 -*-
"""
Camada de pontuação do SITE da apuração — reusa os motores validados (bolao_engine /
score_engine) sem alterá-los, acrescentando o que a planilha resolvia por fórmula/dropdown:

1. derive_full_adv(): igual a score_engine.derive_full, MAS empate no mata-mata pode ter
   "quem passa" (pênaltis) — tanto no palpite (dropdown da planilha do palpiteiro, capturado
   em palpites.json) quanto no gabarito real (campo 'quem passa' do organizador).
   Empate SEM escolha → vencedor indefinido (ramo em branco, como na planilha — caso JAM J73).
2. Seções B/C/D em variantes que recebem a derivação PRONTA (injetada), com a MESMA lógica
   do oráculo (copiada literalmente de score_engine; a paridade é provada em qa_site.py).
3. Penalidade (decisão Renato 2026-06-11): jogos anulados na Seção A por palpiteiro
   (DACA → J1), sem tocar na derivação do bracket dele (grupo A continua com o 2-0).
"""
import fixture_copa_2026 as fx
import bolao_engine as eng
import score_engine as se

GROUP_NUMS = se.GROUP_NUMS
KO_SLOTS = se.KO_SLOTS


# ---------------------------------------------------------------- derivação com pênaltis
def derive_full_adv(scores, advancers=None):
    """Bracket completo a partir dos 104 placares + 'quem passa' dos empates.
    None se a fase de grupos estiver incompleta (mesmo gate do oráculo)."""
    advancers = advancers or {}
    if not se._group_complete(scores):
        return None
    d = eng.derive({n: scores[n] for n in GROUP_NUMS})
    pos = {}
    for L, order in d["standings"].items():
        for i, t in enumerate(order):
            pos[t] = i + 1
    teams = {int(k[1:]): v for k, v in d["r32"].items()}
    win, lose = {}, {}
    for num in range(73, 105):
        if num not in teams:
            s1, s2 = KO_SLOTS[num]
            teams[num] = (se._resolve(s1, win, lose), se._resolve(s2, win, lose))
        a, b = teams[num]
        p = scores.get(num)
        if se._validpair(p) and (a or b):
            ga, gb = p
            if ga > gb:                             # decisivo: propaga o lado vencedor VERBATIM,
                win[num], lose[num] = a, b          # mesmo se o outro lado estiver indefinido
            elif gb > ga:                           # (fiel ao winner_f da planilha)
                win[num], lose[num] = b, a
            else:                                   # EMPATE: decide o 'quem passa' (pênaltis)
                adv = advancers.get(num)
                win[num] = adv if adv in (a, b) else None
                lose[num] = ((b if adv == a else a) if win[num] else None)
        else:
            win[num] = lose[num] = None

    def setof(nums):
        s = set()
        for n in nums:
            for t in teams.get(n, (None, None)):
                if t:
                    s.add(t)
        return s

    return {"pos": pos, "teams": teams, "win": win, "lose": lose,
            "standings": d["standings"], "combo": d["combo_key"],
            "R32": setof(range(73, 89)), "R16": setof(range(89, 97)),
            "QF": setof(range(97, 101)), "SF": setof(range(101, 103)),
            "DISP3": setof([103]), "FINAL": setof([104]),
            "champion": win.get(104), "vice": lose.get(104),
            "third": win.get(103), "fourth": lose.get(103)}


# ------------------------------------------------- Seções (lógica IDÊNTICA ao oráculo)
def section_A(palpite, real, anulados=()):
    """(total, {num: pontos}, pontos_descontados_pela_anulação)."""
    per, desc = {}, 0
    for num in GROUP_NUMS:
        pts = se.score_game_A(palpite.get(num), real.get(num))
        if num in anulados:
            desc += pts
            pts = 0
        per[num] = pts
    return sum(per.values()), per, desc


def section_B(pd, rd, real_groups_complete):
    per = {}
    for key, phase, full, half in se.SET_STEPS_B:
        pts = 0
        if pd and rd and (key != 1 or real_groups_complete):
            rset = rd[phase]
            for t in pd[phase]:
                if t in rset:
                    pts += full if pd["pos"].get(t) == rd["pos"].get(t) else half
        per[key] = pts
    per[6] = 0
    if pd and rd:
        for slot in ("third", "fourth"):
            if pd[slot] and pd[slot] == rd[slot]:
                per[6] += 10 if pd["pos"].get(pd[slot]) == rd["pos"].get(rd[slot]) else 5
    for key, slot, full, half in ((8, "vice", 16, 8), (9, "champion", 30, 15)):
        per[key] = 0
        if pd and rd and pd[slot] and pd[slot] == rd[slot]:
            per[key] = full if pd["pos"].get(pd[slot]) == rd["pos"].get(rd[slot]) else half
    return sum(per.values()), per


def section_C(pd, rd, palpite, real):
    """(total, {degrau: pts}, {jogo: pts}) — o per-jogo alimenta o expander 'palpites por jogo'."""
    per = {d: 0 for d in range(10, 16)}
    per_num = {}
    if not pd or not rd:
        return 0, per, per_num
    for num in range(73, 105):
        EX, VE, GOL = se.SCORE_C[num]
        pT, rT = pd["teams"][num], rd["teams"][num]
        pg, rg = palpite.get(num), real.get(num)
        if not (pT[0] and pT[1] and rT[0] and rT[1]):
            continue
        if not (se._validpair(pg) and se._validpair(rg)):
            continue
        same = (pT[0] == rT[0] and pT[1] == rT[1])
        swap = (pT[0] == rT[1] and pT[1] == rT[0])
        if not (same or swap):
            continue
        pg1, pg2 = pg
        rg1, rg2 = rg
        pA, pB = (pg1, pg2) if same else (pg2, pg1)
        if pA == rg1 and pB == rg2:
            base = EX
        else:                                            # VE e GOL independentes (organização, 12/jun/2026)
            base = ((VE if se._sign(pA - pB) == se._sign(rg1 - rg2) else 0)
                    + (GOL if (pA == rg1 or pB == rg2) else 0))
        pos_ok = (pd["pos"].get(rT[0]) == rd["pos"].get(rT[0])
                  and pd["pos"].get(rT[1]) == rd["pos"].get(rT[1]))
        per[se._DEGRAU_C[num]] += base if pos_ok else base / 2
        per_num[num] = base if pos_ok else base / 2
    return sum(per.values()), per, per_num


def section_D(pd, rd, palpite, real):
    crit = {k: 0 for k in se.D_ORDER}
    if pd and rd:
        def tp(slot):
            pt, rt = pd[slot], rd[slot]
            return (2 if pd["pos"].get(pt) == rd["pos"].get(rt) else 1) if (pt and pt == rt) else 0

        def wc(phase):
            return sum(2 if pd["pos"].get(t) == rd["pos"].get(t) else 1
                       for t in pd[phase] if t in rd[phase])

        def jogo(num):
            pT, rT = pd["teams"][num], rd["teams"][num]
            pg, rg = palpite.get(num), real.get(num)
            if not (pT[0] and pT[1] and rT[0] and rT[1] and se._validpair(pg) and se._validpair(rg)):
                return 0
            same = (pT[0] == rT[0] and pT[1] == rT[1])
            swap = (pT[0] == rT[1] and pT[1] == rT[0])
            if not (same or swap):
                return 0
            pg1, pg2 = pg
            rg1, rg2 = rg
            pA, pB = (pg1, pg2) if same else (pg2, pg1)
            return 2 if (pA == rg1 and pB == rg2) else 1

        crit["i"] = tp("champion"); crit["iii"] = tp("vice"); crit["v"] = tp("third"); crit["vii"] = tp("fourth")
        crit["iv"] = wc("FINAL"); crit["viii"] = wc("DISP3"); crit["ix"] = wc("SF")
        crit["x"] = wc("QF"); crit["xi"] = wc("R16"); crit["xii"] = wc("R32")
        crit["ii"] = jogo(104); crit["vi"] = jogo(103)
    crit["xiii"] = sum(se.score_game_A(palpite.get(n), real.get(n)) for n in se.US_GROUP_GAMES)
    key = sum(crit[k] * se.D_WEIGHTS[k] for k in se.D_ORDER)
    return key, crit


# ---------------------------------------------------------------- avaliação + ranking
def avaliar(palp, real_scores, real_advancers, penalidades):
    """Pontuação completa de UM palpiteiro contra o gabarito. palp = dict do palpites.json
    (chaves já em int). Retorna dict com totais, quebras por seção e chave de desempate."""
    anulados = tuple(penalidades.get(palp["nome"], {}).get("jogos_anulados_secao_A", ()))
    pd = derive_full_adv(palp["scores"], palp["advancers"])
    rd = derive_full_adv(real_scores, real_advancers)
    rgc = se._group_complete(real_scores)
    A, perA, desc = section_A(palp["scores"], real_scores, anulados)
    B, perB = section_B(pd, rd, rgc)
    C, perC, perCn = section_C(pd, rd, palp["scores"], real_scores)
    Dkey, crit = section_D(pd, rd, palp["scores"], real_scores)
    return {"nome": palp["nome"], "A": A, "B": B, "C": C, "total": A + B + C,
            "dkey": Dkey, "crit": crit, "perA": perA, "perB": perB, "perC": perC,
            "perCn": perCn, "anulados": anulados, "descontado": desc, "pd": pd}


def ranking(palps, real_scores, real_advancers, penalidades):
    """Avalia todos e devolve a lista ordenada. **A POSIÇÃO depende SÓ do total** (decisão Renato
    2026-06-14): quem empata no total DIVIDE a mesma posição durante a Copa (ex.: 1,2,2,4,4,6…),
    fiel ao regulamento ('desempate no caso de empate na pontuação FINAL'). A chave de desempate
    (i–xiii) ainda ordena a EXIBIÇÃO entre os empatados (quem está à frente aparece em cima) e
    decide o campeão/pódio só no fim — mas NÃO altera o número da posição."""
    rows = [avaliar(p, real_scores, real_advancers, penalidades) for p in palps]
    rows.sort(key=lambda r: (-r["total"], -r["dkey"], r["nome"].lower()))   # exibição
    for r in rows:
        r["pos"] = 1 + sum(1 for o in rows if o["total"] > r["total"])      # posição: só o total
    return rows
