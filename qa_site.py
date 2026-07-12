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
    okB = scoring.section_B(pd_, rd_, r_sc)[:1] == se.section_B(p_sc, r_sc)[:1]
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
# regressão dos PÊNALTIS reais (29/jun): a API SOMA o shootout no fullTime (GER×PAR fullTime 4x5 =
# regularTime 1x1 + penalties 3x4) → _ko_field_score DEVE usar regularTime+extraTime (placar de campo).
_pen = {"score": {"winner": "AWAY_TEAM", "duration": "PENALTY_SHOOTOUT",
                  "fullTime": {"home": 4, "away": 5}, "regularTime": {"home": 1, "away": 1},
                  "extraTime": {"home": 0, "away": 0}, "penalties": {"home": 3, "away": 4}}}
check("pênaltis: placar de campo = regularTime+extraTime (1x1), NÃO o fullTime 4x5 (soma o shootout)",
      fonte_api._ko_field_score(_pen)[:2] == (1, 1))
_et = {"score": {"winner": "HOME_TEAM", "duration": "EXTRA_TIME", "fullTime": {"home": 2, "away": 1},
                 "regularTime": {"home": 1, "away": 1}, "extraTime": {"home": 1, "away": 0}}}
check("prorrogação decidida em campo: regularTime+extraTime (2x1) = fullTime",
      fonte_api._ko_field_score(_et)[:2] == (2, 1))
_reg = {"score": {"winner": "AWAY_TEAM", "duration": "REGULAR", "fullTime": {"home": 0, "away": 1}}}
check("tempo normal (sem regularTime): usa fullTime (0x1)", fonte_api._ko_field_score(_reg)[:2] == (0, 1))
# regressão do WINNER=NULL (AUS×EGY, 03/jul): a API deixou `winner`=null num mata-mata FINISHED de
# PÊNALTIS → o advancer deve vir do agregado fullTime (que SOMA o shootout), nunca ficar vazio (senão o
# time some das fases seguintes). JSON real: regularTime 1x1, fullTime 3x5 (Egito/away passou).
_j88 = {"winner": None, "duration": "PENALTY_SHOOTOUT", "fullTime": {"home": 3, "away": 5},
        "regularTime": {"home": 1, "away": 1}, "extraTime": {"home": 0, "away": 0},
        "penalties": {"home": 4, "away": 4}}
check("winner=null nos pênaltis: advancer pelo fullTime agregado (AUS 3 / EGY 5 → Egito passa)",
      fonte_api._agg_winner(_j88, EN2TLA["Australia"], "Australia", "Egypt") == "Egypt")
check("winner=null: orientação p/ (a,b) independe de quem a API põe como home",
      fonte_api._agg_winner({**_j88, "fullTime": {"home": 5, "away": 3}},
                            EN2TLA["Egypt"], "Australia", "Egypt") == "Egypt")
check("winner=null: placar de campo continua o regularTime (1x1), não o fullTime somado",
      fonte_api._ko_field_score({"score": _j88})[:2] == (1, 1))
_tA, _tB = _full["teams"][80]                               # end-to-end: 16-avos com winner=null propaga
_mpen = {"stage": "LAST_32", "status": "FINISHED", "homeTeam": {"tla": EN2TLA[_tA]},
         "awayTeam": {"tla": EN2TLA[_tB]},
         "score": {"winner": None, "duration": "PENALTY_SHOOTOUT", "regularTime": {"home": 1, "away": 1},
                   "extraTime": {"home": 0, "away": 0}, "fullTime": {"home": 3, "away": 5}}}
_msP = [m for m in _ms if not (m["stage"] == "LAST_32"
        and {m["homeTeam"]["tla"], m["awayTeam"]["tla"]} == {EN2TLA[_tA], EN2TLA[_tB]})] + [_mpen]
_koP, _advP = fonte_api.parse_ko(_msP, _gp)
check("parse_ko: 16-avos winner=null → placar (1,1) e advancer = quem venceu no fullTime (não bloqueia)",
      _koP.get(80) == (1, 1) and _advP.get(80) == _tB)
# regressão do STATUS MALFORMADO (MEX×ENG oitavas, 06/jul): a API devolveu `status` = um timestamp em
# vez de 'FINISHED' → o jogo sumia e a Inglaterra não subia p/ as quartas (NOR×ENG não encaixava).
# _match_done conta se NÃO está pendente E tem resultado; mas um IN_PLAY com winner (líder do momento,
# ARG×SUI 1×0 ao vivo) NÃO pode contar — por isso o status pendente é checado ANTES do winner.
check("status malformado + placar → conta (MEX×ENG: status=timestamp, winner preenchido)",
      fonte_api._match_done({"status": "2026-07-06 01:00:00Z",
                             "score": {"winner": "AWAY_TEAM", "fullTime": {"home": 2, "away": 3}}}))
check("IN_PLAY com winner (líder do momento) NÃO conta (ARG×SUI 1×0 ao vivo)",
      not fonte_api._match_done({"status": "IN_PLAY",
                                 "score": {"winner": "HOME_TEAM", "fullTime": {"home": 1, "away": 0}}}))
check("FINISHED com winner=null mas fullTime completo conta (Egito)",
      fonte_api._match_done({"status": "FINISHED",
                             "score": {"winner": None, "fullTime": {"home": 3, "away": 5}}}))
check("TIMED / malformado SEM resultado (ainda não jogado) NÃO conta",
      not fonte_api._match_done({"status": "TIMED", "score": {"winner": None, "fullTime": {}}})
      and not fonte_api._match_done({"status": "2026-07-20", "score": {"winner": None, "fullTime": {}}}))
_eA, _eB = _full["teams"][92]                               # end-to-end: oitava com status malformado entra
_jmal = {"stage": "LAST_16", "status": "2026-07-06 01:00:00Z",
         "homeTeam": {"tla": EN2TLA[_eA]}, "awayTeam": {"tla": EN2TLA[_eB]},
         "score": {"winner": "AWAY_TEAM", "duration": "REGULAR", "fullTime": {"home": 0, "away": 1}}}
_msM = [m for m in _ms if not (m["stage"] == "LAST_16"
        and {m["homeTeam"]["tla"], m["awayTeam"]["tla"]} == {EN2TLA[_eA], EN2TLA[_eB]})] + [_jmal]
_koM, _advM = fonte_api.parse_ko(_msM, _gp)
check("parse_ko: oitava com status malformado NÃO é mais descartada (placar 0x1 mapeado)",
      _koM.get(92) == (0, 1))

# ---------- 7) Imagem dos palpites do dia (imagem.py): cor 1-X-2 + intensidade por gols
print("\n7) Imagem dos palpites do dia (imagem.py):")
import imagem
from PIL import ImageFont
# FONTE: tem de carregar uma TrueType REAL (a DejaVu embarcada) — não o default do
# Pillow (sem glifos 'Ã'/'—' → caixas □ em produção). Regressão do deploy de 16/jun.
check("fonte embarcada carrega como TrueType (não o default sem acento)",
      isinstance(imagem._font(imagem._FONTES_BOLD, 40), ImageFont.FreeTypeFont)
      and isinstance(imagem._font(imagem._FONTES, 40), ImageFont.FreeTypeFont))
check("1ª opção de fonte é a embarcada no repo (fonts/DejaVuSans*.ttf)",
      imagem._FONTES[0].endswith("fonts/DejaVuSans.ttf")
      and imagem._FONTES_BOLD[0].endswith("fonts/DejaVuSans-Bold.ttf")
      and __import__("os").path.isfile(imagem._FONTES[0])
      and __import__("os").path.isfile(imagem._FONTES_BOLD[0]))
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

# ---------- 8) Incidente 17/jun (Espanha×Arábia J38): Seção A correta + override da Sheet vence
print("\n8) Incidente J38 — Seção A (+2, não +3) e override da Sheet:")
# (a) Seção A: real 5x0 (errado) × palpite 4x0 → 4 (resultado + gol exato do time que fez 0);
#     corrigido p/ 4x0 → 6 (exato). Delta = +2. (O +1 extra que apareceu veio de OUTRO jogo.)
check("4x0 × real 5x0 = 4 (resultado + gol exato do time que fez 0)", se.score_game_A((4, 0), (5, 0)) == 4)
check("4x0 × real 4x0 = 6 (exato)", se.score_game_A((4, 0), (4, 0)) == 6)
check("delta 5x0→4x0 = +2 (não +3)", se.score_game_A((4, 0), (4, 0)) - se.score_game_A((4, 0), (5, 0)) == 2)
check("gol exato do time que fez 0 conta ganhando (1x0 × 2x0 = 4)", se.score_game_A((1, 0), (2, 0)) == 4)
check("gol exato do time que fez 0 conta perdendo (0x0 × 0x1 = 1)", se.score_game_A((0, 0), (0, 1)) == 1)
# (b) override da Sheet VENCE a base por jogo, e NÃO oscila quando o CSV pisca (segura o último-bom)
import tempfile, os as _os
_p = _os.path.join(tempfile.gettempdir(), "qa_override.csv")
open(_p, "w", encoding="utf-8").write("jogo,gols1,gols2,quem_passa\n38,4,0,\n17,2,1,\n")
_so, _sa, _sf = D.load_sheet_override("file://" + _p)        # leitura boa → snapshot do último-bom
check("Sheet override lê J38 = (4,0)", _so.get(38) == (4, 0), str(_so.get(38)))
check("merge: Sheet (4,0) VENCE a base (5,0) no J38", {**{38: (5, 0), 19: (1, 0)}, **_so}.get(38) == (4, 0))
check("merge: jogo não-sobrescrito da base permanece (J19)", {**{38: (5, 0), 19: (1, 0)}, **_so}.get(19) == (1, 0))
_so2, _sa2, _sf2 = D.load_sheet_override("file:///___inexistente___.csv")   # CSV falha de propósito
check("anti-flap: CSV falhou → segura o último-bom (J38 ainda 4,0, não some)", _so2.get(38) == (4, 0), str(_so2.get(38)))
check("override vazio (sem url) não quebra", D.load_sheet_override(None) == ({}, {}, None))
for _f in (_p, D._OVERRIDE_SNAP):
    try:
        _os.remove(_f)
    except Exception:
        pass

# ---------- 9) Chaveamento (bracket) do Simulador: ordem da ÁRVORE + imagem
print("\n9) Chaveamento do Simulador (bracket):")
import imagem
import fonte_api as _fa
import fixture_copa_2026 as _fx
_KO = {n: (s1, s2) for n, _, _, _, s1, s2 in _fx.KO_MATCHES}
_kids = lambda n: [int(s[1:]) for s in _KO[n] if s and s[0] == "W"]
_lv, _cur = [], [104]
while _cur:
    _lv.append(_cur)
    _nx = []
    for n in _cur:
        _nx += _kids(n)
    _cur = _nx
_lv.reverse()                                                  # [R32(16),R16(8),QF(4),SF(2),F(1)]
check("ordem da árvore por rodada = 16/8/4/2/1", [len(x) for x in _lv] == [16, 8, 4, 2, 1], str([len(x) for x in _lv]))
_b = byname[DECISIVOS[0]]                                      # bracket COMPLETO (sem empate em aberto)
_sd = scoring.derive_full_adv(_b["scores"], _b["advancers"])


def _adj(parent_lv, child_lv):                                 # cada chave = vencedores das 2 chaves anteriores
    for j, pg in enumerate(parent_lv):
        a, b = _sd["teams"][pg]
        if {a, b} != {_sd["win"][child_lv[2 * j]], _sd["win"][child_lv[2 * j + 1]]}:
            return False
    return True


check("adjacência da árvore (R16<-R32, QF<-R16, SF<-QF, F<-SF) — pega o bug do bracket consecutivo",
      all(_adj(_lv[i + 1], _lv[i]) for i in range(4)))
_tla = lambda t: _fa.EN_TO_TLA.get(t, "") if t else ""


def _mk(n):
    a, b = _sd["teams"].get(n, (None, None))
    sc, w = _b["scores"].get(n), _sd["win"].get(n)
    return (_tla(a), sc[0] if sc else None, w is not None and w == a,
            _tla(b), sc[1] if sc else None, w is not None and w == b)


_h = lambda l: (l[:len(l) // 2], l[len(l) // 2:])
(_r32L, _r32R), (_r16L, _r16R), (_qfL, _qfR) = _h(_lv[0]), _h(_lv[1]), _h(_lv[2])
_mkc = lambda nums: [_mk(n) for n in nums]
_left = [_mkc(c) for c in (_r32L, _r16L, _qfL, [_lv[3][0]])]
_right = [_mkc(c) for c in (_r32R, _r16R, _qfR, [_lv[3][1]])]
_pb = imagem.bracket_png(_left, _right, _mk(_lv[4][0]), _tla(_sd["champion"]), None)
check("bracket_png two-sided é PNG válido e não-trivial", _pb[:8] == b"\x89PNG\r\n\x1a\n" and len(_pb) > 5000, str(len(_pb)))
check("campeão do bracket definido (= derivação)", _tla(_sd["champion"]) != "")
# derive_partial: bracket da CLASSIFICAÇÃO DE MOMENTO (sem o gate de 72 grupos)
_gp_full = {n: _b["scores"][n] for n in range(1, 73)}
check("derive_partial com 72 grupos == derive_full_adv (standings idênticos)",
      scoring.derive_partial(_gp_full, {})["standings"] == _sd["standings"])
_gp_part = {n: _b["scores"][n] for n in range(1, 73) if n % 2 == 0}    # metade dos jogos de grupo
_dp = scoring.derive_partial(_gp_part, {})
_r32t = [t for n in range(73, 89) for t in _dp["teams"][n]]
check("derive_partial (parcial): R32 com 32 times reais distintos (classificação de momento)",
      len(_r32t) == 32 and all(_r32t) and len(set(_r32t)) == 32)
check("derive_partial (parcial): rodadas após os 16-avos ficam indefinidas sem placar de KO",
      _dp["teams"][89][0] is None and _dp["champion"] is None)

# ---------- 10) Acertos de PLACAR EXATO por fase (informativo)
print("\n10) Acertos de placar exato por fase (scoring.acertos_cheios):")
_pc = byname[DECISIVOS[0]]
_acs = scoring.acertos_cheios(PALPS, _pc["scores"], _pc["advancers"])   # real = palpite do próprio decisivo
_self = _acs[_pc["nome"]]
check(f"{_pc['nome']} × si mesmo: GRUPOS = 72 (cravou todos os grupos)", _self["GRUPOS"] == 72, str(_self["GRUPOS"]))
check(f"{_pc['nome']} × si mesmo: total = 104 (todos os jogos exatos, bracket completo)",
      sum(_self.values()) == 104, str(sum(_self.values())))
check("chaves de fase = GRUPOS + R32/R16/QF/SF/3P/F", set(_self) == set(scoring.FASES_CHEIO))
_acp = scoring.acertos_cheios(PALPS, {1: (2, 0), 2: (2, 1)}, {})         # real só com 2 grupos
check("real parcial: mata-mata todo 0 (sem os 72 grupos reais não há bracket real)",
      all(sum(v[k] for k in ("R32", "R16", "QF", "SF", "3P", "F")) == 0 for v in _acp.values()))
check("real parcial: quem cravou J1/J2 conta em GRUPOS", any(v["GRUPOS"] > 0 for v in _acp.values()))
# placar exato NÃO conta resultado-certo-placar-errado (ex.: real 2x0, palpite 1x0 não é cheio)
_acn = scoring.acertos_cheios(PALPS, {1: (99, 98)}, {})                  # placar improvável: ninguém crava
check("placar exato exige o placar IDÊNTICO (99x98 → ninguém crava o J1)",
      all(v["GRUPOS"] == 0 for v in _acn.values()))

# ---------- 11) Comparativo de grupos: NEGRITO nos classificados (1º/2º sempre; 3º só se no combo)
print("\n11) Comparativo de grupos — negrito nos classificados (regra do _comp_grupo_html):")
_full = {q["nome"]: scoring.derive_full_adv(q["scores"], q["advancers"]) for q in PALPS}
for _nome, _d in _full.items():
    assert _d is not None, f"{_nome} sem derivação (grupos incompletos)"
    _bold = set()                                          # times marcados em negrito nos 12 grupos
    for _L in "ABCDEFGHIJKL":
        _ordem = _d["standings"][_L]
        _leva3 = _L in _d["combo"]
        for _i in range(4):
            if _i in (0, 1) or (_i == 2 and _leva3):       # regra idêntica à do app
                _bold.add(_ordem[_i])
    check(f"{_nome}: 32 células em negrito (24 do 1º/2º + 8 melhores 3ºs)", len(_bold) == 32, str(len(_bold)))
    check(f"{_nome}: negrito == campo dos 16-avos do palpite (R32)", _bold == _d["R32"])
    check(f"{_nome}: exatamente 8 terceiros em negrito (= |combo|)",
          sum(1 for _L in "ABCDEFGHIJKL" if _L in _d["combo"]) == 8)

# ---------- 12) Seção B PARCIAL: degrau 1 (16-avos) creditado conforme os grupos fecham
print("\n12) Seção B parcial — degrau 1 incremental (1º/2º por grupo fechado; 3ºs só ao fechar tudo):")
_eng = scoring.eng
_GFIX = {L: [n for n, _, _ in _eng.GROUP_FIXT[L]] for L in scoring.fx.GROUPS}   # nºs de jogo por grupo
_GORD = list("ABCDEFGHIJKL")
_PD = {q["nome"]: scoring.derive_full_adv(q["scores"], {}) for q in PALPS}      # brackets dos palpites (completos)


def _decided_ref(real_sc):
    """Referência INDEPENDENTE: {time: pos 1/2/3} confirmados nos 16-avos pela realidade
    (1º/2º de grupos fechados; + 8 melhores 3ºs se TODOS fecharam). Não usa _real_r32_decided."""
    if se._group_complete(real_sc):
        rd = scoring.derive_full_adv(real_sc, {})
        return {t: rd["pos"][t] for t in rd["R32"]}
    dec = {}
    for L, teams in scoring.fx.GROUPS.items():
        if all(se._validpair(real_sc.get(n)) for n in _GFIX[L]):
            order, *_ = _eng.rank_group(teams, [(t1, t2, *real_sc[n]) for n, t1, t2 in _eng.GROUP_FIXT[L]])
            dec[order[0]] = 1
            dec[order[1]] = 2
    return dec


def _b1_site(pd, real_sc):
    return scoring.section_B(pd, scoring.derive_full_adv(real_sc, {}), real_sc)[1][1]


def _b1_ref(pd, real_sc):                                  # 4 = posição certa · 2 = time certo, posição errada
    dec = _decided_ref(real_sc)
    return sum(4 if pd["pos"].get(t) == dec[t] else 2 for t in pd["R32"] if t in dec)


# (a) paridade site × referência independente em TODA a trajetória de revelação + monotonicidade
_npar = _ntot = 0
_mono_ok = True
for rp in PALPS:                                           # cada palpite congelado como "gabarito real"
    _prev = {q["nome"]: 0 for q in PALPS}
    for k in range(1, 13):                                 # revela grupos A..k (incremental)
        part = {n: rp["scores"][n] for L in _GORD[:k] for n in _GFIX[L]}
        for q in PALPS:
            pd = _PD[q["nome"]]
            site, ref = _b1_site(pd, part), _b1_ref(pd, part)
            _ntot += 1
            _npar += (site == ref)
            if site < _prev[q["nome"]]:
                _mono_ok = False
            _prev[q["nome"]] = site
check(f"degrau-1 parcial == referência independente em {_npar}/{_ntot} (8 reais × 12 passos × 8 palpites)",
      _npar == _ntot)
check("monotonicidade: degrau-1 nunca decresce ao fechar mais grupos", _mono_ok)

# (b) convergência/invariante: 12 grupos reais fechados → degrau-1 site == oráculo (independente)
_okconv = all(_b1_site(_PD[q["nome"]], rp["scores"]) == se.section_B(q["scores"], rp["scores"])[1][1]
              for rp in PALPS for q in PALPS)
check("convergência: grupos completos → degrau-1 site == oráculo (8×8 pares)", _okconv)

# (c) fase parcial só credita 1º/2º: 11 grupos revelados (falta L) → rd None, 22 decididos, todos pos 1/2
_p11 = {n: PALPS[0]["scores"][n] for L in _GORD[:11] for n in _GFIX[L]}
check("11 grupos: gabarito ainda incompleto (rd None)", scoring.derive_full_adv(_p11, {}) is None)
_dec11 = scoring._real_r32_decided(_p11, None)
check("11 grupos: exatamente 22 classificados decididos (11×2)", len(_dec11) == 22, str(len(_dec11)))
check("11 grupos: todos decididos são 1º ou 2º (nenhum 3º pendente)", set(_dec11.values()) == {1, 2})

# (d) caso concreto: só grupo A jogado (2x1) → real-1º/2º entram, 3º/4º ficam de fora
_realA = {n: (2, 1) for n in _GFIX["A"]}
_decA = scoring._real_r32_decided(_realA, None)
_ordA, *_ = _eng.rank_group(scoring.fx.GROUPS["A"], [(t1, t2, 2, 1) for _, t1, t2 in _eng.GROUP_FIXT["A"]])
check("grupo A só: decididos = exatamente {1º:1, 2º:2} reais (3º/4º fora)",
      _decA == {_ordA[0]: 1, _ordA[1]: 2})
check("grupo A só: nenhum palpiteiro pontua por time fora dos decididos",
      all(set(t for t in _PD[q["nome"]]["R32"] if t in _decA) <= set(_decA) for q in PALPS))

# ---------- 13) Views do mata-mata: conferência por fase + pódio == Seção B; concorrência == section_C
print("\n13) Views do mata-mata (conferência por fase + concorrência):")
# (a) para cada palpite real COMPLETO, soma(conferencia_fase por fase) + pódio == Seção B do palpiteiro
_okB = True
for _rp in PALPS:
    _REAL, _RADV = _rp["scores"], _rp["advancers"]
    _rd = scoring.derive_full_adv(_REAL, _RADV)
    if not _rd:
        continue
    for _p in PALPS:
        _pdv = scoring.derive_full_adv(_p["scores"], _p["advancers"])
        _sf = 0
        for _deg, _setk, _rot in scoring.FASES_B:
            _mr = scoring.membros_fase_real(_REAL, _RADV, _rd, _setk)
            _sf += sum(x[4] for x in scoring.conferencia_fase(_pdv, _mr, _setk, _deg))
        _sp = sum(x[3] for x in scoring.podio_conferencia(_pdv, _rd))
        _B = scoring.avaliar(_p, _REAL, _RADV, {})["B"]
        if _sf + _sp != _B:
            _okB = False
check("conferência por fase + pódio == Seção B (8×8 pares completos)", _okB)

# (b) concorrência consistente com section_C: 'cheia'/'metade' em jogo jogado → está em perCn; 'fora' → não
_rpB = byname[DECISIVOS[0]]
_REAL = _rpB["scores"]
_rd = scoring.derive_full_adv(_REAL, {})
_okC = True
for _p in PALPS:
    _pdv = scoring.derive_full_adv(_p["scores"], _p["advancers"])
    _per = scoring.avaliar(_p, _REAL, {}, {})["perCn"]
    for _num in range(73, 105):
        _st = scoring.concorrencia_jogo(_pdv, _rd, _num)
        _jogado = se._validpair(_REAL.get(_num))
        if _st in ("cheia", "metade") and _jogado and _num not in _per:
            _okC = False
        if _st == "fora" and _num in _per:
            _okC = False
check("concorrência (cheia/metade/fora) consistente com section_C", _okC)

# (c) parcial: só com grupos (sem mata-mata real) → R32 tem membros, fases seguintes vazias, concorrência None
_p6 = {n: byname["BUSNITO"]["scores"][n] for _L in "ABCDEFGHIJKL" for n in
       [m for m, _, _ in scoring.eng.GROUP_FIXT[_L]]}     # 12 grupos, zero mata-mata
_rd6 = scoring.derive_full_adv(_p6, {})
check("12 grupos, sem mata-mata: rd existe (bracket real derivado)", _rd6 is not None)
check("16-avos (R32) tem 32 membros reais", len(scoring.membros_fase_real(_p6, {}, _rd6, "R32")) == 32)
_pdv6 = scoring.derive_full_adv(byname["PB"]["scores"], byname["PB"]["advancers"])
check("oitavas vazia sem resultados de mata-mata", len(scoring.membros_fase_real(_p6, {}, _rd6, "R16")) == 0)
check("concorrência nos 16-avos já definida (não-None) com bracket real",
      scoring.concorrencia_jogo(_pdv6, _rd6, 73) in ("cheia", "metade", "fora"))
check("concorrência nas oitavas ainda None (jogo real indefinido)",
      scoring.concorrencia_jogo(_pdv6, _rd6, 89) is None)

# ---------- 14) Seção C casada por PAR-NA-FASE (confronto na fase certa, vaga diferente = posição errada)
print("\n14) Seção C — confronto por par-na-fase (regulamento: 'aquele jogo naquela fase'):")
_NN = {n: (None, None) for n in range(73, 105)}
_pdT = {**_NN, 80: ("X", "Y")}                             # palpiteiro tem X×Y nos 16-avos, VAGA 80
_rdT = {**_NN, 73: ("X", "Y")}                             # real tem X×Y nos 16-avos, VAGA 73 (outra vaga)
_rd14 = {"teams": _rdT, "pos": {"X": 2, "Y": 2}}           # real: ambos 2º
# posição errada (X previsto 1º) → METADE; placar exato → 6/2 = 3 no degrau 10
_t, _p, _pn = scoring.section_C({"teams": _pdT, "pos": {"X": 1, "Y": 2}}, _rd14, {80: (2, 1)}, {73: (2, 1)})
check("par certo na fase certa, vaga diferente + posição errada + placar exato → METADE (3 de 6)",
      _p[10] == 3 and _pn.get(73) == 3)
# posição certa (em qualquer vaga da fase) → CHEIA (6)
_t2, _p2, _ = scoring.section_C({"teams": _pdT, "pos": {"X": 2, "Y": 2}}, _rd14, {80: (2, 1)}, {73: (2, 1)})
check("par certo na fase certa, posições certas → CHEIA (6)", _p2[10] == 6)
# par previsto em FASE diferente (oitavas) não casa com o real (16-avos) → 0
_t3, _p3, _ = scoring.section_C({"teams": {**_NN, 89: ("X", "Y")}, "pos": {"X": 2, "Y": 2}},
                                _rd14, {89: (2, 1)}, {73: (2, 1)})
check("par previsto em FASE diferente → não pontua (0)", sum(_p3.values()) == 0)
# concorrência (display) acompanha: par-na-fase com posição errada → 'metade'
_pdv14 = {"teams": _pdT, "pos": {"X": 1, "Y": 2}}
check("concorrência: par-na-fase, posição errada → 'metade'",
      scoring.concorrencia_jogo(_pdv14, _rd14, 73) == "metade")
check("concorrência: par NÃO previsto na fase → 'fora'",
      scoring.concorrencia_jogo({"teams": _NN, "pos": {}}, _rd14, 73) == "fora")

print("\n" + ("✅ QA DO SITE PASSOU — pontuação fiel ao oráculo validado"
              if not fails else f"❌ QA FALHOU: {fails}"))
sys.exit(0 if not fails else 1)
