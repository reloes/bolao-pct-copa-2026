# -*- coding: utf-8 -*-
"""
QA do SITE da apuração — prova que a camada scoring.py é FIEL ao oráculo validado:

1. PARIDADE × score_engine: para palpites/reais DECISIVOS (sem empate no mata-mata),
   as Seções A/B/C/D do site têm de bater EXATAMENTE com o oráculo (que foi validado
   contra a planilha no QA da apuração). Cenários: sintético 2x1 + os 2 palpites sem
   empates (Busnito, PB) cruzados entre si.
2. AUTO-TESTE 1236: cada palpiteiro contra o próprio palpite (com seus 'quem passa')
   tem de cravar o MÁXIMO A+B+C = 1236 — exceto JAM (ramo indefinido no J73, vale menos).
3. PENALIDADE DACA: real = só J1 (México 2-0) → A do DACA = 0 (descontado 6); demais
   palpiteiros pontuam o J1 normalmente; B/C de todos = 0 (grupos reais incompletos).
4. EMPATES/pênaltis: vencedores derivados = 'quem passa' registrado, para os 5 palpites
   com empates; gabarito real com empate+avanço propaga certo.

Uso: python3 qa_site.py   (na pasta site/; sai 0 se tudo OK)
"""
import sys
import score_engine as se
import scoring
import data as D

fails = []


def check(desc, cond, extra=""):
    print(f"  [{'OK ' if cond else 'FAIL'}] {desc}" + (f" — {extra}" if extra and not cond else ""))
    if not cond:
        fails.append(desc)


meta, PALPS = D.load_palpites()
PEN = meta["penalidades"]
byname = {p["nome"]: p for p in PALPS}
DECISIVOS = [p["nome"] for p in PALPS if not any(p["scores"][n][0] == p["scores"][n][1]
                                                 for n in range(73, 105))]
print(f"Palpiteiros: {[p['nome'] for p in PALPS]}")
print(f"Sem empates no mata-mata (usáveis na paridade × oráculo): {DECISIVOS}")

# ---------- 0) Regra do gol-exato INDEPENDENTE do resultado (organização, 12/jun/2026)
print("\n0) Regra do +1 independente (Seções A e C):")
for p_, r_, exp in [((1, 1), (2, 1), 1),   # errou o resultado, cravou o gol da Tcheca → 1 (caso do grupo)
                    ((2, 0), (2, 1), 4), ((3, 1), (2, 1), 4), ((1, 0), (2, 1), 3),
                    ((2, 5), (2, 1), 1),   # errou o resultado, cravou os 2 da Coreia → 1
                    ((0, 0), (2, 1), 0), ((0, 0), (1, 1), 3), ((2, 1), (2, 1), 6)]:
    got = se.score_game_A(p_, r_)
    check(f"Seção A: palpite {p_[0]}x{p_[1]} × real {r_[0]}x{r_[1]} → {exp}", got == exp, str(got))
_sint = {n: (2, 1) for n in range(1, 105)}
_rd0 = scoring.derive_full_adv(_sint, {})
_psc = dict(_sint); _psc[104] = (1, 1)
_pd0 = scoring.derive_full_adv(_psc, {104: _rd0["teams"][104][0]})
_, _, _pern = scoring.section_C(_pd0, _rd0, _psc, _sint)
check("Seção C: final real 2x1 × palpite 1x1 → 8 (gol independente, fase F)",
      _pern.get(104) == 8, str(_pern.get(104)))

# ---------- 1) PARIDADE × score_engine (cenários decisivos)
print("\n1) Paridade site × oráculo (A/B/C/D) em cenários decisivos:")
sint = {n: (2, 1) for n in range(1, 105)}
cenarios = [("sintético 2x1", sint, sint)]
for a in DECISIVOS:
    for b in DECISIVOS:
        cenarios.append((f"{a} × real={b}", byname[a]["scores"], byname[b]["scores"]))
npar = 0
for nome, p_sc, r_sc in cenarios:
    pd_ = scoring.derive_full_adv(p_sc, {})
    rd_ = scoring.derive_full_adv(r_sc, {})
    okA = scoring.section_A(p_sc, r_sc)[0] == se.section_A(p_sc, r_sc)[0]
    okB = scoring.section_B(pd_, rd_, se._group_complete(r_sc))[:1] == se.section_B(p_sc, r_sc)[:1]
    okC = scoring.section_C(pd_, rd_, p_sc, r_sc)[0] == se.section_C(p_sc, r_sc)[0]
    okD = scoring.section_D(pd_, rd_, p_sc, r_sc)[0] == se.section_D(p_sc, r_sc)[0]
    npar += all((okA, okB, okC, okD))
    if not all((okA, okB, okC, okD)):
        check(f"paridade {nome}", False, f"A{okA} B{okB} C{okC} D{okD}")
check(f"paridade em {npar}/{len(cenarios)} cenários", npar == len(cenarios))

# ---------- 2) Auto-teste: palpite × ele mesmo = máximo 1236
# (regressão do caso JAM: 'Suiça' digitado sem acento no quem-passa do J73 TEM de ser
#  reconhecido pelo matching tolerante → sem_escolha vazio → 1236 como todo mundo)
print("\n2) Auto-teste (cada um contra o próprio palpite → máx 1236):")
for p in PALPS:
    r = scoring.avaliar(p, p["scores"], p["advancers"], {})
    if p["sem_escolha"]:
        check(f"{p['nome']} (ramo indefinido {p['sem_escolha']}) < 1236 e sem erro",
              0 < r["total"] < 1236, f"{r['total']}")
    else:
        check(f"{p['nome']}: total = 1236", r["total"] == 1236, f"{r['total']}")
check("nenhum palpiteiro com empate-sem-escolha (todos os 'quem passa' reconhecidos)",
      not any(p["sem_escolha"] for p in PALPS),
      str([(p["nome"], p["sem_escolha"]) for p in PALPS if p["sem_escolha"]]))

# ---------- 3) Penalidade DACA com o gabarito real atual (J1 = México 2-0)
print("\n3) Penalidade DACA (real = só J1 México 2-0):")
real = {1: (2, 0)}
rows = scoring.ranking(PALPS, real, {}, PEN)
daca = next(r for r in rows if r["nome"] == "DACA")
check("DACA: A = 0 no J1 anulado", daca["A"] == 0 and daca["perA"][1] == 0)
check("DACA: descontado = 6 (tinha cravado 2-0)", daca["descontado"] == 6, str(daca["descontado"]))
outros = [r for r in rows if r["nome"] != "DACA"]
check("B/C de todos = 0 (grupos reais incompletos)",
      all(r["B"] == 0 and r["C"] == 0 for r in rows))
check("alguém pontuou no J1 sem penalidade",
      any(r["perA"][1] > 0 for r in outros))
sem_pen = scoring.ranking(PALPS, real, {}, {})
d2 = next(r for r in sem_pen if r["nome"] == "DACA")
check("sem a penalidade, DACA teria 6 no J1", d2["perA"][1] == 6, str(d2["perA"][1]))
# posições: empate por TOTAL (decisão Renato 14/jun) — desempate NÃO afeta a posição até o fim
ok_pos = all(r["pos"] == 1 + sum(1 for o in rows if o["total"] > r["total"]) for r in rows)
check("posição = 1 + nº com total estritamente maior (só o total)", ok_pos)
ok_tie = all((r["pos"] == o["pos"]) == (r["total"] == o["total"]) for r in rows for o in rows)
check("mesma posição ⇔ MESMO total (desempate não muda a posição)", ok_tie)
# cenário do bug reportado: dois com total igual e dkey diferente DEVEM dividir a posição
real_emp = {n: (2, 0) for n in range(1, 9)}                       # 8 jogos p/ separar dkeys (jogo EUA J4)
rows_e = scoring.ranking(PALPS, real_emp, {}, PEN)
from collections import defaultdict
by_total = defaultdict(set)
for r in rows_e:
    by_total[r["total"]].add(r["pos"])
check("empatados no total dividem a posição mesmo com desempate diferente",
      all(len(ps) == 1 for ps in by_total.values()),
      str({t: ps for t, ps in by_total.items() if len(ps) > 1}))

# ---------- 4) Empates + 'quem passa'
print("\n4) Empates no mata-mata ('quem passa' respeitado):")
nadv = nok = 0
for p in PALPS:
    pdv = scoring.derive_full_adv(p["scores"], p["advancers"])
    for num, adv in p["advancers"].items():
        nadv += 1
        nok += (pdv["win"][num] == adv)
check(f"vencedor derivado = 'quem passa' em {nok}/{nadv} empates", nok == nadv)
jam = scoring.derive_full_adv(byname["JAM"]["scores"], byname["JAM"]["advancers"])
check("JAM J73: 'Suiça' (sem acento) reconhecido → Suíça avança",
      byname["JAM"]["advancers"].get(73) == "Switzerland" and jam["win"][73] == "Switzerland",
      f"adv={byname['JAM']['advancers'].get(73)}, win={jam['win'][73]}")
check("JAM: pódio completo derivado (França campeã)", jam["champion"] == "France",
      str(jam["champion"]))
# gabarito real com empate + avanço nos pênaltis (sintético): J73 empatado, avança o time B
rsint = dict(sint)
rsint[73] = (1, 1)
rd73 = scoring.derive_full_adv(rsint, {})
a73, b73 = rd73["teams"][73]
rd73p = scoring.derive_full_adv(rsint, {73: b73})
check("real empatado sem 'quem passa' → indefinido", rd73["win"][73] is None)
check("real empatado COM 'quem passa' → avança o escolhido", rd73p["win"][73] == b73)

# ---------- 6) Automação do mata-mata (fonte_api.parse_ko) com cenário simulado
print("\n6) Automação do mata-mata (parse_ko × cenário simulado, entrega 2):")
import fonte_api
import fixture_copa_2026 as fx
EN2TLA = fonte_api.EN_TO_TLA
_b = byname["BUSNITO"]                                     # decisivo (sem empate no mata-mata)
_g = {n: _b["scores"][n] for n in range(1, 73)}
_full = scoring.derive_full_adv(_b["scores"], _b["advancers"])

def _stage(n):
    return ("LAST_32" if n <= 88 else "LAST_16" if n <= 96 else "QUARTER_FINALS" if n <= 100
            else "SEMI_FINALS" if n <= 102 else "THIRD_PLACE" if n == 103 else "FINAL")

def _mk(h, a, gh, ga, stg, winner=None):
    if winner is None:
        winner = "HOME_TEAM" if gh > ga else "AWAY_TEAM" if ga > gh else None
    return {"stage": stg, "status": "FINISHED", "homeTeam": {"tla": EN2TLA[h]},
            "awayTeam": {"tla": EN2TLA[a]}, "score": {"winner": winner, "fullTime": {"home": gh, "away": ga}}}

_ms = [_mk(t1, t2, *_g[num], "GROUP_STAGE") for num, _, _, t1, t2, _ in fx.GROUP_MATCHES]
_ms += [_mk(_full["teams"][n][0], _full["teams"][n][1], *_b["scores"][n], _stage(n)) for n in range(73, 105)]
_gp = fonte_api.parse_group_scores(_ms)
_ko, _adv = fonte_api.parse_ko(_ms, _gp)
check("grupos via API == cenário", _gp == _g)
check("mata-mata via API: 32/32 casados sem divergência (casamento+orientação+propagação)",
      len(_ko) == 32 and all(_ko.get(n) == _b["scores"][n] for n in range(73, 105)),
      f"{len(_ko)}/32")
_a104, _c104 = _full["teams"][104]                          # pênaltis: final empatada + winner = away
_ms2 = [m for m in _ms if m["stage"] != "FINAL"] + [_mk(_a104, _c104, 1, 1, "FINAL", "AWAY_TEAM")]
_ko2, _adv2 = fonte_api.parse_ko(_ms2, _gp)
check("final empate 1x1 + pênaltis → placar (1,1) e advancer = quem a API marcou",
      _ko2.get(104) == (1, 1) and _adv2.get(104) == _c104)
check("mata-mata NÃO deriva sem os 72 grupos completos (gate)",
      fonte_api.parse_ko(_ms, {1: (1, 0)}) == ({}, {}))

# ---------- 7) Imagem dos palpites do dia (imagem.py): cor 1-X-2 + intensidade por gols
print("\n7) Imagem dos palpites do dia (imagem.py):")
import imagem
# matiz = coluna da aposta via sign(g1-g2) — casos do mockup de 16/jun
check("2x1 → coluna 1 (vence a esquerda)", imagem.cor_palpite(2, 1)[1] == "1")
check("1x1 → coluna X (empate)", imagem.cor_palpite(1, 1)[1] == "X")
check("1x2 → coluna 2 (vence a direita)", imagem.cor_palpite(1, 2)[1] == "2")
check("0x3 (todos cravaram a Noruega) → coluna 2", imagem.cor_palpite(0, 3)[1] == "2")
_b1 = imagem.cor_palpite(2, 1)[0]; _g2 = imagem.cor_palpite(1, 2)[0]; _x = imagem.cor_palpite(1, 1)[0]
check("coluna 1 puxa AZUL (B > R)", _b1[2] > _b1[0])
check("coluna 2 puxa VERDE (G dominante)", _g2[1] > _g2[0] and _g2[1] > _g2[2])
check("coluna X puxa VERMELHO (R dominante)", _x[0] > _x[1] and _x[0] > _x[2])
# intensidade cresce com o total de gols (mesma coluna) e satura em 6


def _forca(rgb):
    return sum(255 - c for c in rgb)   # distância do branco = quão forte é o tom


check("intensidade: 4x0 > 2x0 > 1x0 (mais gols, tom mais forte)",
      _forca(imagem.cor_palpite(4, 0)[0]) > _forca(imagem.cor_palpite(2, 0)[0])
      > _forca(imagem.cor_palpite(1, 0)[0]))
check("intensidade satura em 6 gols (6x0 == 7x0)",
      imagem.cor_palpite(6, 0)[0] == imagem.cor_palpite(7, 0)[0])
# PNG válido e não-trivial p/ um dia de 4 e de 6 jogos
_jg = lambda n: [(100 + i, "AAA", "BBB", [(p["nome"], 2, 1) for p in PALPS]) for i in range(n)]
png4 = imagem.palpites_grid_png("16/jun", _jg(4))
png6 = imagem.palpites_grid_png("25/jun", _jg(6))
check("PNG (4 jogos) é PNG válido e não-trivial",
      png4[:8] == b"\x89PNG\r\n\x1a\n" and len(png4) > 2000, str(len(png4)))
check("PNG (6 jogos) é PNG válido e não-trivial",
      png6[:8] == b"\x89PNG\r\n\x1a\n" and len(png6) > 2000, str(len(png6)))
try:
    imagem.palpites_grid_png("x", [])
    _empty_ok = False
except Exception:
    _empty_ok = True
check("dia sem jogos → erro explícito (não gera imagem vazia)", _empty_ok)

print("\n" + ("✅ QA DO SITE PASSOU — pontuação fiel ao oráculo validado"
              if not fails else f"❌ QA FALHOU: {fails}"))
sys.exit(0 if not fails else 1)
