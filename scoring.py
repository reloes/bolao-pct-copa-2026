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
_KO_FASE = {num: fase for num, fase, _, _, _, _ in fx.KO_MATCHES}   # nº do jogo → fase (R32/R16/QF/SF/3P/F)


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


def derive_partial(scores, advancers=None):
    """Como derive_full_adv, mas SEM o gate de 72 grupos: usa a CLASSIFICAÇÃO DE MOMENTO (provisória)
    dos grupos a partir dos jogos já preenchidos. Os 16-avos saem com os classificados de momento;
    as rodadas seguintes ficam indefinidas (None) até haver placar de mata-mata. SÓ p/ EXIBIR o
    chaveamento (não para pontuar — a pontuação segue gated em derive_full_adv)."""
    advancers = advancers or {}
    gs = {n: scores[n] for n in GROUP_NUMS if n in scores}
    if not gs:
        return None
    d = eng.derive(gs, partial=True)
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
            if ga > gb:
                win[num], lose[num] = a, b
            elif gb > ga:
                win[num], lose[num] = b, a
            else:
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


def n_grupos_fechados(scores):
    """Quantos dos 12 grupos têm os 6 jogos preenchidos/válidos (1º/2º já definidos)."""
    return sum(1 for L in fx.GROUPS
               if all(se._validpair(scores.get(n)) for n, _, _ in eng.GROUP_FIXT[L]))


def _real_r32_decided(real_scores, rd):
    """{time: posição 1/2/3} dos times JÁ CONFIRMADOS nos 16-avos pela REALIDADE.
    - rd pronto (12 grupos reais fechados): todos os 32, com posição (inclui os 8 melhores 3ºs, pos 3).
    - senão: 1º (pos 1) e 2º (pos 2) de cada grupo real JÁ FECHADO (6/6 jogos válidos). 3ºs ficam
      PENDENTES (dependem dos 8 melhores) e 4ºs ficam de fora — nenhum dos dois entra aqui.
    A posição 1º/2º de um grupo fechado é intra-grupo (Art.13) e não muda com os outros grupos."""
    if rd:
        return {t: rd["pos"][t] for t in rd["R32"]}
    decided = {}
    for L, teams in fx.GROUPS.items():
        nums = [n for n, _, _ in eng.GROUP_FIXT[L]]
        if all(se._validpair(real_scores.get(n)) for n in nums):     # grupo L inteiro jogado
            ms = [(t1, t2, *real_scores[n]) for n, t1, t2 in eng.GROUP_FIXT[L]]
            order, *_ = eng.rank_group(teams, ms)
            decided[order[0]] = 1
            decided[order[1]] = 2
    return decided


_B1_FULL, _B1_HALF = next((f, h) for k, _, f, h in se.SET_STEPS_B if k == 1)   # 4 / 2 (sem hardcode)


def section_B(pd, rd, real_scores):
    """(total, {degrau: pts}). Degrau 1 (16-avos) é PARCIAL: credita os classificados confirmados
    conforme os grupos REAIS fecham — 1º/2º de cada grupo fechado já contam; os 8 melhores 3ºs só
    entram quando os 12 grupos fecharem (rd pronto). Com rd pronto, colapsa no cálculo original
    (paridade × oráculo preservada). pd está sempre completo (palpite congelado). Degraus 2–9 seguem
    gated no bracket real completo (precisam de resultados de mata-mata)."""
    per = {}
    per[1] = 0                                                       # 16-avos: avaliação incremental
    if pd:
        dec = _real_r32_decided(real_scores, rd)
        for t in pd["R32"]:
            if t in dec:
                per[1] += _B1_FULL if pd["pos"].get(t) == dec[t] else _B1_HALF
    for key, phase, full, half in se.SET_STEPS_B:
        if key == 1:
            continue
        pts = 0
        if pd and rd:
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


def _pair_index(pd):
    """{degrau_C: {frozenset(par): (vaga, teams)}} dos confrontos do bracket, por FASE.
    Permite casar o confronto pelo PAR de times na MESMA fase (qualquer vaga), não pela vaga exata —
    fiel ao regulamento ('se acertou que aquele jogo aconteceria naquela fase'): um erro de posição
    de grupo roteia o mesmo par para outra vaga, mas o confronto na fase continua valendo (metade)."""
    idx = {}
    for num in range(73, 105):
        t = pd["teams"].get(num)
        if t and t[0] and t[1]:
            idx.setdefault(se._DEGRAU_C[num], {})[frozenset((t[0], t[1]))] = (num, t)
    return idx


def section_C(pd, rd, palpite, real):
    """(total, {degrau: pts}, {jogo: pts}) — o per-jogo alimenta o expander 'palpites por jogo'.
    Confronto casado por PAR-na-fase: para cada jogo REAL, procura no bracket do palpiteiro a vaga
    (na MESMA fase) onde ele tem o mesmo par de times; pontua com o PLACAR DELE dessa vaga. cheia se
    as posições de grupo dos 2 times batem, metade se não."""
    per = {d: 0 for d in range(10, 16)}
    per_num = {}
    if not pd or not rd:
        return 0, per, per_num
    pidx = _pair_index(pd)
    for num in range(73, 105):
        EX, VE, GOL = se.SCORE_C[num]
        rT, rg = rd["teams"][num], real.get(num)
        if not (rT[0] and rT[1] and se._validpair(rg)):
            continue
        deg = se._DEGRAU_C[num]
        hit = pidx.get(deg, {}).get(frozenset((rT[0], rT[1])))    # par previsto NESTA fase?
        if not hit:
            continue
        m, pT = hit
        pg = palpite.get(m)
        if not se._validpair(pg):
            continue
        rg1, rg2 = rg
        pA, pB = (pg[0], pg[1]) if pT[0] == rT[0] else (pg[1], pg[0])   # alinha à orientação real
        if pA == rg1 and pB == rg2:
            base = EX
        else:                                            # VE e GOL independentes (organização, 12/jun/2026)
            base = ((VE if se._sign(pA - pB) == se._sign(rg1 - rg2) else 0)
                    + (GOL if (pA == rg1 or pB == rg2) else 0))
        pos_ok = (pd["pos"].get(rT[0]) == rd["pos"].get(rT[0])
                  and pd["pos"].get(rT[1]) == rd["pos"].get(rT[1]))
        per[deg] += base if pos_ok else base / 2
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
    A, perA, desc = section_A(palp["scores"], real_scores, anulados)
    B, perB = section_B(pd, rd, real_scores)
    C, perC, perCn = section_C(pd, rd, palp["scores"], real_scores)
    Dkey, crit = section_D(pd, rd, palp["scores"], real_scores)
    return {"nome": palp["nome"], "A": A, "B": B, "C": C, "total": A + B + C,
            "dkey": Dkey, "crit": crit, "perA": perA, "perB": perB, "perC": perC,
            "perCn": perCn, "anulados": anulados, "descontado": desc, "pd": pd,
            "b_parcial": rd is None}      # B só com 16-avos parciais (faltam 3ºs/mata-mata)


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


FASES_CHEIO = ("GRUPOS", "R32", "R16", "QF", "SF", "3P", "F")   # ordem das fases p/ o placar exato


def acertos_cheios(palps, real, real_advancers=None):
    """INFORMATIVO (não pontua): conta, por palpiteiro, quantos jogos ele CRAVOU O PLACAR EXATO,
    por fase. Grupos: palpite[n] == real[n]. Mata-mata: o confronto previsto = o confronto REAL
    (mesmo par de times) E o placar exato (orientado aos times reais). Devolve
    {nome: {'GRUPOS','R32','R16','QF','SF','3P','F': int}} (mata-mata só conta com os 72 grupos reais)."""
    rd = derive_full_adv(real, real_advancers or {})            # bracket real (None até os 72 grupos)
    out = {}
    for p in palps:
        c = {k: 0 for k in FASES_CHEIO}
        for n in GROUP_NUMS:                                    # grupos: placar idêntico
            rg, pg = real.get(n), p["scores"].get(n)
            if rg is not None and pg is not None and tuple(pg) == tuple(rg):
                c["GRUPOS"] += 1
        if rd:                                                  # mata-mata: confronto (par-na-fase) + placar exato
            pdv = derive_full_adv(p["scores"], p["advancers"])
            if pdv:
                pidx = _pair_index(pdv)
                for n in range(73, 105):
                    rg, rT = real.get(n), rd["teams"].get(n)
                    if not (se._validpair(rg) and rT and rT[0] and rT[1]):
                        continue
                    hit = pidx.get(se._DEGRAU_C[n], {}).get(frozenset((rT[0], rT[1])))
                    if not hit:
                        continue
                    m, pT = hit
                    pg = p["scores"].get(m)
                    if not se._validpair(pg):
                        continue
                    pA, pB = (pg[0], pg[1]) if pT[0] == rT[0] else (pg[1], pg[0])
                    if pA == rg[0] and pB == rg[1]:
                        c[_KO_FASE[n]] += 1
        out[p["nome"]] = c
    return out


# ============================================================ Views do mata-mata (UI)
# Conferência de CLASSIFICADOS por fase (Seção B) e CONCORRÊNCIA por jogo (Seção C).
# Tudo reusa a MESMA lógica de section_B/section_C — só reorganiza para exibição. Não pontua nada novo.
FASES_B = [(1, "R32", "16-avos"), (2, "R16", "Oitavas"), (3, "QF", "Quartas"),
           (4, "SF", "Semifinal"), (5, "DISP3", "Disputa de 3º"), (7, "FINAL", "Final")]
_B_PESOS = {k: (f, h) for k, _, f, h in se.SET_STEPS_B}     # {degrau: (posição certa, errada)}


def membros_fase_real(real_scores, real_adv, rd, set_key):
    """{time: posição de grupo 1/2/3} dos times que a REALIDADE colocou na fase set_key.
    R32 (16-avos) é PARCIAL por grupo fechado; demais precisam de rd (bracket real) e refletem os já
    decididos pelos resultados de mata-mata até agora (jogos não jogados não entram no conjunto)."""
    if set_key == "R32":
        return _real_r32_decided(real_scores, rd)
    if not rd:
        return {}
    return {t: rd["pos"][t] for t in rd[set_key]}


def conferencia_fase(pdv, membros_real, set_key, degrau):
    """Linhas [(time, pos_real, previu, pos_palpite, pontos)] de UMA fase — soma == degrau da Seção B.
    Para cada time que a realidade colocou na fase, vê se o palpiteiro o tem NESTA fase e em que posição
    de grupo (cheio se a posição bate, metade se não; 0 se não previu o time nesta fase)."""
    full, half = _B_PESOS[degrau]
    out = []
    for t in membros_real:
        previu = t in pdv[set_key]
        ppos = pdv["pos"].get(t)
        pts = (full if ppos == membros_real[t] else half) if previu else 0
        out.append((t, membros_real[t], previu, ppos, pts))
    return out


def podio_conferencia(pdv, rd):
    """Linhas do pódio [(rótulo, time_real, time_palpite, pontos)] — degraus 9/8/6 (campeão 30/15,
    vice 16/8, 3º e 4º 10/5 cada). [] se rd indefinido (bracket real ainda incompleto)."""
    if not rd:
        return []

    def pts(slot, full, half):
        pt, rt = pdv[slot], rd[slot]
        if rt and pt == rt:
            return full if pdv["pos"].get(pt) == rd["pos"].get(rt) else half
        return 0
    return [("Campeão", rd["champion"], pdv["champion"], pts("champion", 30, 15)),
            ("Vice", rd["vice"], pdv["vice"], pts("vice", 16, 8)),
            ("3º lugar", rd["third"], pdv["third"], pts("third", 10, 5)),
            ("4º lugar", rd["fourth"], pdv["fourth"], pts("fourth", 10, 5))]


def concorrencia_jogo(pdv, rd, num):
    """Status de concorrência de UM palpiteiro num jogo de mata-mata, computável SEM o placar:
    'cheia' (confronto certo + posições de grupo certas → placar pontua 100%), 'metade' (confronto
    certo, posição de grupo de 1+ time trocada → placar vale metade), 'fora' (não previu esse par na
    fase), ou None (confronto real ainda indefinido). Casa por PAR-na-fase (qualquer vaga), igual à
    section_C: o palpiteiro concorre se previu esses 2 times se enfrentando NESTA fase."""
    if not rd:
        return None
    rT = rd["teams"].get(num)
    if not (rT and rT[0] and rT[1]):
        return None
    par = frozenset((rT[0], rT[1]))
    deg = se._DEGRAU_C[num]
    tem = any(pdv["teams"].get(m) and pdv["teams"][m][0] and pdv["teams"][m][1]
              and frozenset(pdv["teams"][m]) == par
              for m in range(73, 105) if se._DEGRAU_C[m] == deg)   # previu o par NESTA fase?
    if not tem:
        return "fora"
    pos_ok = (pdv["pos"].get(rT[0]) == rd["pos"].get(rT[0])
              and pdv["pos"].get(rT[1]) == rd["pos"].get(rT[1]))
    return "cheia" if pos_ok else "metade"
