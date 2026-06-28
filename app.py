# -*- coding: utf-8 -*-
"""
🏆 Bolão PCT — Copa 2026 · site oficial da apuração (Streamlit).

Reusa os motores Python validados do projeto (bolao_engine/score_engine via scoring.py).
Palpites: congelados em palpites.json (imutáveis — auditoria por SHA-256 na página Regras).
Gabarito: Google Sheet do organizador (CSV publicado em st.secrets["GABARITO_CSV_URL"])
ou gabarito_local.json. Rode local: streamlit run app.py --server.port 8503
"""
import urllib.parse
from datetime import datetime, date
from zoneinfo import ZoneInfo
import streamlit as st
import pandas as pd
import fixture_copa_2026 as fx
import score_engine as se
import scoring
import data as D
import fonte_api
import imagem

st.set_page_config(page_title="Bolão PCT — Copa 2026", page_icon="🏆", layout="wide")

PT = fx.TEAM_PT
FLAG = {
    "Mexico": "🇲🇽", "South Africa": "🇿🇦", "South Korea": "🇰🇷", "Czechia": "🇨🇿",
    "Canada": "🇨🇦", "Bosnia and Herzegovina": "🇧🇦", "Qatar": "🇶🇦", "Switzerland": "🇨🇭",
    "Brazil": "🇧🇷", "Morocco": "🇲🇦", "Haiti": "🇭🇹", "Scotland": "🏴󠁧󠁢󠁳󠁣󠁴󠁿",
    "United States": "🇺🇸", "Paraguay": "🇵🇾", "Australia": "🇦🇺", "Türkiye": "🇹🇷",
    "Germany": "🇩🇪", "Curaçao": "🇨🇼", "Ivory Coast": "🇨🇮", "Ecuador": "🇪🇨",
    "Netherlands": "🇳🇱", "Japan": "🇯🇵", "Sweden": "🇸🇪", "Tunisia": "🇹🇳",
    "Belgium": "🇧🇪", "Egypt": "🇪🇬", "Iran": "🇮🇷", "New Zealand": "🇳🇿",
    "Spain": "🇪🇸", "Cape Verde": "🇨🇻", "Saudi Arabia": "🇸🇦", "Uruguay": "🇺🇾",
    "France": "🇫🇷", "Senegal": "🇸🇳", "Iraq": "🇮🇶", "Norway": "🇳🇴",
    "Argentina": "🇦🇷", "Algeria": "🇩🇿", "Austria": "🇦🇹", "Jordan": "🇯🇴",
    "Portugal": "🇵🇹", "DR Congo": "🇨🇩", "Uzbekistan": "🇺🇿", "Colombia": "🇨🇴",
    "England": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "Croatia": "🇭🇷", "Ghana": "🇬🇭", "Panama": "🇵🇦",
}
FASE_PT = {"R32": "16-avos", "R16": "Oitavas", "QF": "Quartas", "SF": "Semifinal",
           "3P": "3º lugar", "F": "FINAL"}
GROUP_INFO = {num: (d, t1, t2) for num, d, _, t1, t2, _ in fx.GROUP_MATCHES}
KO_INFO = {num: (fase, d, s1, s2) for num, fase, d, _, s1, s2 in fx.KO_MATCHES}


def tn(team):
    """Nome de exibição com bandeira (ou — para indefinido)."""
    return f"{FLAG.get(team, '')} {PT[team]}".strip() if team else "—"


def _comp_grupo_html(L, palps, full):
    """Tabela do Comparativo de grupos para o grupo L com os classificados de cada palpiteiro
    em NEGRITO: 1º e 2º sempre (passam direto); o 3º só fica em negrito quando entra no pool
    dos 8 melhores terceiros daquele palpite (d['combo'] = letras dos grupos cujo 3º avança)."""
    cab = "".join(f"<th>{h}</th>" for h in ("Palpiteiro", "1º", "2º", "3º", "4º"))
    linhas = []
    for q in palps:
        nome = q["nome"]
        d = full.get(nome)
        if not d:                       # grupos incompletos (não ocorre com palpites congelados)
            continue
        ordem = d["standings"][L]
        leva3 = L in d["combo"]         # o 3º deste grupo entra nos 8 melhores terceiros do palpite?
        tds = [f'<td class="nm">{nome}</td>']
        for i in range(4):
            classifica = i in (0, 1) or (i == 2 and leva3)
            tds.append(f'<td class="{"cl" if classifica else ""}">{tn(ordem[i])}</td>')
        linhas.append("<tr>" + "".join(tds) + "</tr>")
    return ("<style>"
            "table.cmpg{border-collapse:collapse;width:100%;font-size:.9rem}"
            "table.cmpg th,table.cmpg td{padding:5px 10px;text-align:left;"
            "border-bottom:1px solid rgba(128,128,128,.2);white-space:nowrap}"
            "table.cmpg th{font-weight:700;border-bottom:2px solid rgba(128,128,128,.45)}"
            "table.cmpg td.cl{font-weight:700}"
            "table.cmpg td.nm{opacity:.7}"
            "</style>"
            f'<table class="cmpg"><thead><tr>{cab}</tr></thead>'
            f"<tbody>{''.join(linhas)}</tbody></table>")


_PAN_STYLE = ("<style>"
              "table.pf{border-collapse:collapse;width:100%;font-size:.9rem}"
              "table.pf th,table.pf td{padding:5px 8px;text-align:left;"
              "border-bottom:1px solid rgba(128,128,128,.2);vertical-align:top}"
              "table.pf th{font-weight:700;border-bottom:2px solid rgba(128,128,128,.45)}"
              "table.pf td.nm{white-space:nowrap;font-weight:700}"
              "table.pf td.n{white-space:nowrap;text-align:right}"
              "table.pf .chips{line-height:1.9}"
              "table.pf .chip{display:inline-block;font-size:1.05rem;margin:1px;padding:0 3px;border-radius:4px}"
              "table.pf .chip.hit{background:rgba(40,165,90,.30);outline:1px solid rgba(40,165,90,.55)}"
              "table.pf .chip.miss{opacity:.30}"
              "table.pf td.hit{background:rgba(40,165,90,.30)}"
              "table.pf td.miss{opacity:.35}"
              "table.pf td.cel{text-align:center;font-size:1.1rem}"
              "</style>")


def _panorama_fase_html(set_key, degrau, palps, pdv_all, membros_real, t2g):
    """Grade do panorama POR FASE: linha por palpiteiro, células = bandeiras dos times que ELE tem
    nesta fase (🟢 fundo verde = avançou de verdade; apagada = não avançou) + Acertos + Pts da fase."""
    full, half = scoring._B_PESOS[degrau]
    real_set = set(membros_real)
    linhas = []
    for q in palps:
        pdv = pdv_all[q["nome"]]
        prev = sorted(pdv[set_key], key=lambda t: (t2g[t], pdv["pos"].get(t, 9)))
        chips, acertos, pts = [], 0, 0
        for t in prev:
            hit = t in real_set
            if hit:
                acertos += 1
                pts += full if pdv["pos"].get(t) == membros_real[t] else half
            chips.append(f'<span class="chip {"hit" if hit else "miss"}" title="{PT.get(t, "")}">{FLAG.get(t, "·")}</span>')
        linhas.append(f'<tr><td class="nm">{q["nome"]}</td><td class="chips">{"".join(chips)}</td>'
                      f'<td class="n">{acertos}/{len(prev)}</td><td class="n">{pts:g}</td></tr>')
    cab = "".join(f"<th>{h}</th>" for h in
                  ("Palpiteiro", "Quem ele tem nesta fase (🟢 = avançou)", "Acertos", "Pts"))
    return _PAN_STYLE + f'<table class="pf"><thead><tr>{cab}</tr></thead><tbody>{"".join(linhas)}</tbody></table>'


def _panorama_podio_html(palps, pdv_all, rd):
    """Grade do pódio previsto: campeão/vice/3º/4º de cada palpiteiro (🟢 = acertou o real) + Pts."""
    slots = [("Campeão", "champion", 30, 15), ("Vice", "vice", 16, 8),
             ("3º", "third", 10, 5), ("4º", "fourth", 10, 5)]
    linhas = []
    for q in palps:
        pdv = pdv_all[q["nome"]]
        cels, pts = [], 0
        for _rot, slot, full, half in slots:
            pt, rt = pdv[slot], rd[slot]
            hit = bool(rt) and pt == rt
            if hit:
                pts += full if pdv["pos"].get(pt) == rd["pos"].get(rt) else half
            cls = "cel hit" if hit else ("cel miss" if pt else "cel")
            cels.append(f'<td class="{cls}" title="{PT.get(pt, "")}">{FLAG.get(pt, "—")}</td>')
        linhas.append(f'<tr><td class="nm">{q["nome"]}</td>{"".join(cels)}<td class="n">{pts:g}</td></tr>')
    cab = "".join(f"<th>{h}</th>" for h in ("Palpiteiro", "Campeão", "Vice", "3º", "4º", "Pts"))
    return _PAN_STYLE + f'<table class="pf"><thead><tr>{cab}</tr></thead><tbody>{"".join(linhas)}</tbody></table>'


@st.cache_data(ttl=3600)   # palpites são congelados
def _palpites():
    return D.load_palpites()


@st.cache_data(ttl=600)    # API: cache LONGO (respeita o rate-limit 10/min compartilhado c/ Loteca)
def _gabarito_base(token):
    return D.load_gabarito_base(token)        # gabarito_local + API football-data.org (snapshot)


@st.cache_data(ttl=45)     # Sheet override: cache CURTO → correção manual do organizador reflete em ~45s
def _gabarito_sheet(url):
    return D.load_sheet_override(url)         # só a camada Sheet (VENCE a base)


def carregar():
    # camadas separadas: a base (API) fica em cache longo; o override (Sheet) em cache curto,
    # pra uma correção manual aparecer em segundos sem esperar os 10 min nem bater na API.
    meta, palps = _palpites()
    try:
        url = st.secrets["GABARITO_CSV_URL"]
    except Exception:
        url = None
    try:
        token = st.secrets["FOOTBALL_DATA_API_KEY"]
    except Exception:
        token = None
    s, a, f_base = _gabarito_base(token)
    s_s, s_a, f_sheet = _gabarito_sheet(url)
    real = {**s, **s_s}                       # Sheet override vence a base, por jogo
    radv = {**a, **s_a}
    fonte = " + ".join(x for x in (f_base if f_base != "vazio" else None, f_sheet) if x) or "vazio"
    return meta, palps, real, radv, fonte


# --- interruptor liga/desliga (controlado pela Google Sheet; cache curto p/ refletir rápido) ---
MANUTENCAO_PADRAO = "Bolão PCT fora do ar - reclamem com o Procura"


@st.cache_data(ttl=30)
def _site_status():
    try:
        url = st.secrets["GABARITO_CSV_URL"]
    except Exception:
        url = None
    return D.load_status(url)


_online, _msg = _site_status()
if not _online:
    st.markdown(
        "<div style='text-align:center; padding-top:14vh'>"
        "<div style='font-size:4.5rem'>🛠️</div>"
        f"<h1 style='margin:0.2em 0'>{_msg or MANUTENCAO_PADRAO}</h1>"
        "<p style='color:#888; font-size:1.1rem'>Bolão PCT — Copa 2026</p></div>",
        unsafe_allow_html=True)
    st.stop()

meta, PALPS, REAL, RADV, FONTE = carregar()
PEN = meta.get("penalidades", {})
JOGADOS = sorted(REAL)


@st.cache_data(ttl=3600)   # palpites são congelados → cache estável (não depende do resultado)
def _grade_png(nums, dia):
    """Bytes PNG da grade colorida de palpites (palpiteiros × jogos do dia). Ver imagem.py."""
    jogos = []
    for num in nums:
        _, t1, t2 = GROUP_INFO[num]
        tla1 = fonte_api.EN_TO_TLA.get(t1, t1[:3].upper())
        tla2 = fonte_api.EN_TO_TLA.get(t2, t2[:3].upper())
        linhas = [(q["nome"], q["scores"][num][0], q["scores"][num][1]) for q in PALPS]
        jogos.append((num, tla1, tla2, linhas))
    return imagem.palpites_grid_png(dia, jogos)


@st.cache_data(ttl=600, show_spinner=False)   # mata-mata: cache por CONTEÚDO (a chave muda com o real)
def _grade_mata_png(dia, jogos):
    """Bytes PNG da grade do dia no mata-mata (cor = concorrência). `jogos` = tupla-de-tuplas
    (fase, real_hdr, ((nome, conf_str, status), ...)) — hashable, serve de chave de cache."""
    return imagem.mata_grid_png(dia, jogos)


# ------- chaveamento (bracket) do mata-mata: estrutura compartilhada por HTML e imagem -------
def _btla(t):
    return fonte_api.EN_TO_TLA.get(t, (t or "")[:3].upper()) if t else ""


def _ko_order():
    """Ordem dos jogos por rodada SEGUINDO a árvore real (slots W## do fixture), não a numérica —
    pra cada chave ficar entre seus dois alimentadores. → [R32(16), R16(8), QF(4), SF(2), Final(1)]."""
    KO = {n: (s1, s2) for n, _, _, _, s1, s2 in fx.KO_MATCHES}
    kids = lambda n: [int(s[1:]) for s in KO[n] if s and s[0] == "W"]
    levels, cur = [], [104]
    while cur:
        levels.append(cur)
        nxt = []
        for n in cur:
            nxt += kids(n)
        cur = nxt
    levels.reverse()
    return levels


_KO_ORDER = _ko_order()


def _bracket_struct(sd, sim):
    """Estrutura TWO-SIDED do chaveamento: (left, right, final, campeão, 3º). left/right = 4 colunas de
    FORA p/ DENTRO [R32(8),R16(4),QF(2),SF(1)]. Cada chave: (a_en,b_en,a_sc,b_sc,a_win,b_win)."""
    R32, R16, QF, SF, _F = _KO_ORDER

    def mk(num):
        a, b = sd["teams"].get(num, (None, None))
        sc, w = sim.get(num), sd["win"].get(num)
        return (a, b, sc[0] if sc else None, sc[1] if sc else None,
                w is not None and w == a, w is not None and w == b)
    half = lambda lst: (lst[:len(lst) // 2], lst[len(lst) // 2:])
    (r32L, r32R), (r16L, r16R), (qfL, qfR) = half(R32), half(R16), half(QF)
    left = tuple(tuple(mk(n) for n in c) for c in (r32L, r16L, qfL, [SF[0]]))
    right = tuple(tuple(mk(n) for n in c) for c in (r32R, r16R, qfR, [SF[1]]))
    terceiro = mk(103) if sd["teams"].get(103, (None, None))[0] else None
    return left, right, mk(104), sd.get("champion"), terceiro


@st.cache_data(ttl=120)
def _bracket_png_bytes(struct):
    left, right, final, champ, ter = struct
    cv = lambda col: [(_btla(a), sa, wa, _btla(b), sb, wb) for (a, b, sa, sb, wa, wb) in col]
    cm = lambda m: (_btla(m[0]), m[2], m[4], _btla(m[1]), m[3], m[5]) if m else None
    return imagem.bracket_png([cv(c) for c in left], [cv(c) for c in right], cm(final), _btla(champ), cm(ter))


def _bracket_html(struct):
    left, right, final, champ, ter = struct
    colh = len(left[0]) * 64

    def lab(t):
        return f"{FLAG.get(t, '')} {fonte_api.EN_TO_TLA.get(t, '')}".strip() if t else "—"

    def row(t, s, win):
        return (f"<div class='bkt {'bkw' if win else ''}'><span>{lab(t)}</span>"
                f"<span class='bks'>{'' if s is None else s}</span></div>")
    box = lambda m: f"<div class='bkm'>{row(m[0], m[2], m[4])}{row(m[1], m[3], m[5])}</div>"
    col = lambda c: f"<div class='bkc' style='height:{colh}px'>" + "".join(box(m) for m in c) + "</div>"
    left_html = "".join(col(c) for c in left)
    right_html = "".join(col(c) for c in reversed(right))
    center = (f"<div class='bkc bkmid' style='height:{colh}px'>"
              "<div style='font-size:10px;opacity:.6;margin-bottom:3px'>final</div>"
              f"<div class='bkm bkfin'>{row(final[0], final[2], final[4])}{row(final[1], final[3], final[5])}</div>"
              "<div class='bkcb'><div style='font-size:10px;color:#854F0B'>campeão</div>"
              f"<div style='font-size:16px;font-weight:500;color:#633806'>{lab(champ)}</div></div>")
    if ter:
        center += ("<div style='font-size:10px;opacity:.6;margin-top:8px'>disputa de 3º</div>"
                   f"<div class='bkm'>{row(ter[0], ter[2], ter[4])}{row(ter[1], ter[3], ter[5])}</div>")
    center += "</div>"
    heads = ["16-avos", "Oitavas", "Quartas", "Semi", "Final", "Semi", "Quartas", "Oitavas", "16-avos"]
    hd = "".join(f"<div>{h}</div>" for h in heads)
    css = ("<style>"
           ".bkwrap{overflow:auto;max-height:600px;border:0.5px solid rgba(128,128,128,.25);border-radius:12px}"
           ".bkhd{display:flex;position:sticky;top:0;background:rgba(127,127,127,.12);"
           "border-bottom:0.5px solid rgba(128,128,128,.25);z-index:2}"
           ".bkhd>div{min-width:120px;padding:7px 5px;font-size:12px;font-weight:500;text-align:center;opacity:.75}"
           ".bk{display:flex;padding:6px}"
           ".bkc{display:flex;flex-direction:column;justify-content:space-around;min-width:120px}"
           ".bkmid{justify-content:center;align-items:center}"
           ".bkm{margin:3px 5px;border:0.5px solid rgba(128,128,128,.3);border-radius:8px;overflow:hidden;min-width:108px}"
           ".bkfin{border:2px solid rgba(0,146,180,.5)}"
           ".bkt{display:flex;justify-content:space-between;gap:8px;padding:4px 8px;font-size:13px;opacity:.6}"
           ".bkt.bkw{background:rgba(0,146,180,.16);font-weight:500;opacity:1}"
           ".bks{font-variant-numeric:tabular-nums;opacity:.85}"
           ".bkcb{background:#FAEEDA;border:2px solid #EF9F27;border-radius:8px;padding:6px 14px;text-align:center;margin-top:6px}"
           "</style>")
    return f"{css}<div class='bkwrap'><div class='bkhd'>{hd}</div><div class='bk'>{left_html}{center}{right_html}</div></div>"


st.sidebar.title("🏆 Bolão PCT")
st.sidebar.caption("Copa 2026 · EUA-México-Canadá")
pagina = st.sidebar.radio("Páginas", ["🏅 Ranking", "📋 Palpites", "⚽ Jogos & Gabarito",
                                       "🎮 Simulador", "📜 Regras & Auditoria"],
                          label_visibility="collapsed")
st.sidebar.divider()
st.sidebar.caption(f"**{len(JOGADOS)}/104** jogos com resultado\n\nGabarito: {FONTE}")
if st.sidebar.button("🔄 Atualizar resultados"):
    st.cache_data.clear()
    st.rerun()


# ============================================================ 🏅 RANKING
if pagina == "🏅 Ranking":
    st.title("🏅 Ranking — apuração oficial")
    rows = scoring.ranking(PALPS, REAL, RADV, PEN)
    medal = {1: "🥇", 2: "🥈", 3: "🥉"}
    # Líquido = total (já pós-punição, é o que ordena) · Bruto = líquido + punição ·
    # Punição = descontado (só Seção A hoje) · A·Grupos mostra o BRUTO (A+B+C = Bruto).
    df = pd.DataFrame([{
        "Pos": f"{medal.get(r['pos'], r['pos'])}",
        "Palpiteiro": r["nome"] + (" ⚠️" if r["anulados"] else ""),
        "Líquido": r["total"],
        "Bruto": r["total"] + r["descontado"],
        "Punição": (f"−{r['descontado']:g}" if r["descontado"] else "—"),
        "A · Grupos": r["A"] + r["descontado"],
        "B · Classificados": r["B"],
        "C · Mata-mata": r["C"],
    } for r in rows])
    st.dataframe(df, width="stretch", hide_index=True)
    if rows and rows[0].get("b_parcial") and JOGADOS:
        _nf = scoring.n_grupos_fechados(REAL)
        st.caption(f"ℹ️ **Seção B parcial** ({_nf}/12 grupos fechados): o **1º e o 2º** de cada grupo "
                   "já encerrado **já contam**; os **8 melhores 3ºs** entram quando os 12 grupos "
                   "fecharem, e os degraus de mata-mata abrem com os jogos.")
    if not JOGADOS:
        st.info("Nenhum resultado lançado ainda — todos zerados. O ranking nasce com o 1º jogo.")
    pen_rows = [r for r in rows if r["anulados"]]
    for r in pen_rows:
        info = PEN.get(r["nome"], {})
        st.warning(f"⚠️ **{r['nome']}** — jogo(s) **{', '.join('J'+str(j) for j in r['anulados'])}** "
                   f"anulado(s) na Seção A ({info.get('motivo', '')}) "
                   f"— deixou de marcar **{r['descontado']:g} pt(s)** até agora.")

    # --- exportar pro WhatsApp (pedido do grupo; SEM o link do site na msg) ---
    # na URL do wa.me NÃO usar emoji: o link_button do Streamlit mangla p/ U+FFFD (�)
    def _pun(r):   # sufixo de punição na linha (só quem tem): bruto + valor descontado
        return f" (bruto {r['total'] + r['descontado']:g} · punição −{r['descontado']:g})" if r["descontado"] else ""
    zap_url = ("BOLÃO PCT — Copa 2026\n"
               f"Ranking após {len(JOGADOS)}/104 jogos:\n"
               + "\n".join(f"{r['pos']}º {r['nome']} — {r['total']:g}{_pun(r)}" for r in rows))
    medal_txt = {1: "🥇", 2: "🥈", 3: "🥉"}
    zap = ("🏆 BOLÃO PCT — Copa 2026\n"
           f"📊 Ranking após {len(JOGADOS)}/104 jogos:\n"
           + "\n".join(f"{medal_txt.get(r['pos'], str(r['pos']) + 'º')} {r['nome']}"
                       f"{' ⚠️' if r['anulados'] else ''} — {r['total']:g}{_pun(r)}" for r in rows))
    cz1, cz2 = st.columns([1, 2])
    cz1.link_button("📲 Compartilhar no WhatsApp", "https://wa.me/?text=" + urllib.parse.quote(zap_url))
    with cz2.expander("ver/copiar o texto da mensagem (com emojis — cole no zap)"):
        st.code(zap, language=None)

    with st.expander("🎯 Placar exato por fase (informativo — não conta pro ranking)"):
        st.caption("Quantos jogos cada um **cravou o placar exato**, por fase — só curiosidade. "
                   "As fases do mata-mata preenchem quando os grupos terminarem.")
        _ac = scoring.acertos_cheios(PALPS, REAL, RADV)
        _cols = [("GRUPOS", "Grupos"), ("R32", FASE_PT["R32"]), ("R16", FASE_PT["R16"]),
                 ("QF", FASE_PT["QF"]), ("SF", "Semi"), ("3P", "3º"), ("F", "Final")]
        _lin = []
        for _nome, _c in _ac.items():
            _tot = sum(_c.values())
            _pos = 1 + sum(1 for _cc in _ac.values() if sum(_cc.values()) > _tot)
            _lin.append({"Pos": _pos, "Palpiteiro": _nome,
                         **{h: _c[code] for code, h in _cols}, "Total": _tot})
        _lin.sort(key=lambda r: (r["Pos"], r["Palpiteiro"]))
        st.dataframe(pd.DataFrame(_lin), width="stretch", hide_index=True)

    st.subheader("Detalhe por palpiteiro")
    sel = st.selectbox("Palpiteiro", [r["nome"] for r in rows])
    r = next(x for x in rows if x["nome"] == sel)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Líquido", f"{r['total']:g}",
              delta=(f"−{r['descontado']:g} punição" if r["descontado"] else None),
              delta_color="inverse")
    c2.metric("Seção A", f"{r['A'] + r['descontado']:g}")   # bruto (A+B+C = Bruto; punição no Líquido)
    c3.metric("Seção B", f"{r['B']:g}")
    c4.metric("Seção C", f"{r['C']:g}")
    if r.get("b_parcial") and JOGADOS:
        st.caption("Seção B **parcial**: contam só os classificados (1º/2º) dos grupos já fechados; "
                   "os 8 melhores 3ºs e os degraus de mata-mata entram depois.")
    psel = next((p for p in PALPS if p["nome"] == sel), None)
    ja = []
    for n in JOGADOS:
        if n > 72:
            continue
        res = f"{tn(GROUP_INFO[n][1])} {REAL[n][0]} x {REAL[n][1]} {tn(GROUP_INFO[n][2])}"
        pg = psel["scores"].get(n) if psel else None
        ja.append((f"J{n}", res,
                   f"{pg[0]} x {pg[1]}" if pg else "—",
                   "ANULADO" if n in r["anulados"] else f"{r['perA'][n]:g}"))
    if ja:
        st.caption("Pontos por jogo já realizado (Seção A):")
        st.dataframe(pd.DataFrame(ja, columns=["Jogo", "Resultado", "Palpite", "Pontos"]),
                     width="stretch", hide_index=True)

    # conferência dos classificados POR FASE (Seção B) — abas por fase + pódio
    rd_real = scoring.derive_full_adv(REAL, RADV)
    pdv = r["pd"]
    if pdv:
        t2g = {t: L for L, ts in fx.GROUPS.items() for t in ts}
        _pb = r["perB"]
        _res = " · ".join(f"{rot} {_pb.get(deg, 0):g}" for deg, _sk, rot in scoring.FASES_B)
        _pod = _pb.get(6, 0) + _pb.get(8, 0) + _pb.get(9, 0)
        st.markdown("**Conferência dos classificados por fase (Seção B)**")
        st.caption(f"Sua Seção B: **{r['B']:g}** — {_res} · pódio {_pod:g}. Em cada fase: **posição de grupo "
                   "certa** vale cheio; **time certo, posição errada** vale metade; **0** se não previu o time "
                   "naquela fase.")
        _tabs = st.tabs([rot for _d, _s, rot in scoring.FASES_B] + ["Pódio"])
        for (degrau, setk, rot), tab in zip(scoring.FASES_B, _tabs):
            with tab:
                mr = scoring.membros_fase_real(REAL, RADV, rd_real, setk)
                if not mr:
                    st.info("Esta fase ainda não foi decidida na vida real — aparece conforme os jogos acontecem.")
                    continue
                full, half = scoring._B_PESOS[degrau]
                st.caption(f"**{full:g}** = posição certa · **{half:g}** = time certo, posição errada · **0** = não previu aqui")
                linhas = []
                for t, pos_real, previu, ppos, pts in sorted(
                        scoring.conferencia_fase(pdv, mr, setk, degrau), key=lambda x: (t2g[x[0]], x[1])):
                    seu = f"{ppos}º do {t2g[t]}" if previu else "não previu nesta fase"
                    linhas.append((f"{tn(t)} — {pos_real}º do {t2g[t]}", seu, f"{pts:g}"))
                st.dataframe(pd.DataFrame(linhas, columns=["Quem chegou (real)", "Seu palpite", "Pontos"]),
                             width="stretch", hide_index=True)
        with _tabs[-1]:
            podio = scoring.podio_conferencia(pdv, rd_real)
            if not podio:
                st.info("O pódio aparece quando o mata-mata avançar (semifinais e final).")
            else:
                st.caption("Campeão **30/15** · vice **16/8** · 3º e 4º **10/5** cada (posição certa / errada).")
                st.dataframe(pd.DataFrame([(rot, tn(tr), tn(tp), f"{pts:g}") for rot, tr, tp, pts in podio],
                                          columns=["Pódio", "Real", "Seu palpite", "Pontos"]),
                             width="stretch", hide_index=True)

    with st.expander("Critérios de desempate (Seção D, i–xiii)"):
        st.caption("Usados apenas em caso de empate no total — i é o mais importante.")
        st.dataframe(pd.DataFrame([{**{"critério": k}, **{"valor": v}}
                                   for k, v in r["crit"].items()]),
                     width="stretch", hide_index=True)


# ============================================================ 📋 PALPITES
elif pagina == "📋 Palpites":
    st.title("📋 Palpites (congelados na largada)")
    st.caption("Entregues antes da abertura e consolidados em 11/jun/2026 — imutáveis. "
               "Auditoria (SHA-256) na página Regras.")

    resumo = []
    for p in PALPS:
        pdv = scoring.derive_full_adv(p["scores"], p["advancers"])
        resumo.append({"Palpiteiro": p["nome"],
                       "Campeão": tn(pdv["champion"]), "Vice": tn(pdv["vice"]),
                       "3º": tn(pdv["third"]), "4º": tn(pdv["fourth"]),
                       "Combinação 3ºs": p["combo"]})
    st.dataframe(pd.DataFrame(resumo), width="stretch", hide_index=True)

    st.subheader("Palpite completo")
    sel = st.selectbox("Palpiteiro", [p["nome"] for p in PALPS])
    p = next(x for x in PALPS if x["nome"] == sel)
    pdv = scoring.derive_full_adv(p["scores"], p["advancers"])
    if sel in PEN:
        st.warning(f"⚠️ {PEN[sel].get('motivo', '')}")
    if p["sem_escolha"]:
        st.info(f"ℹ️ {sel} deixou empate **sem escolher quem passa** no(s) jogo(s) "
                f"{', '.join('J'+str(n) for n in p['sem_escolha'])} — o ramo correspondente do "
                f"bracket dele ficou indefinido (vale como entregue).")

    t_grupos, t_mata, t_comp, t_fase = st.tabs(
        ["Fase de grupos", "Mata-mata", "Comparativo dos grupos", "Por fase (mata-mata)"])
    with t_grupos:
        for row0 in range(0, 12, 3):                      # fileiras A-B-C / D-E-F / ... (ordem de leitura)
            cols = st.columns(3)
            for j, L in enumerate("ABCDEFGHIJKL"[row0:row0 + 3]):
                with cols[j]:
                    st.markdown(f"**Grupo {L}**")
                    linhas = []
                    for num, _, _, t1, t2, _ in fx.GROUP_MATCHES:
                        if {t1, t2} <= set(fx.GROUPS[L]):
                            g1, g2 = p["scores"][num]
                            linhas.append(f"{tn(t1)} **{g1} x {g2}** {tn(t2)}")
                    ordem = pdv["standings"][L]
                    linhas.append("→ " + " · ".join(f"{j2+1}º {tn(t)}" for j2, t in enumerate(ordem)))
                    st.markdown("  \n".join(linhas))
                    st.divider()
    with t_comp:
        st.caption("A classificação prevista por cada palpiteiro, grupo a grupo, lado a lado. "
                   "**Em negrito, os classificados** de cada um — 1º e 2º sempre avançam; o "
                   "**3º fica em negrito** só quando entra no pool dos 8 melhores terceiros "
                   "daquele palpite.")
        full = {q["nome"]: scoring.derive_full_adv(q["scores"], q["advancers"]) for q in PALPS}
        tabs_g = st.tabs([f"Grupo {L}" for L in "ABCDEFGHIJKL"])
        for L, tg in zip("ABCDEFGHIJKL", tabs_g):
            with tg:
                st.html(_comp_grupo_html(L, PALPS, full))
    with t_mata:
        for fase_key in ("R32", "R16", "QF", "SF", "3P", "F"):
            nums = [n for n, (f_, *_), in KO_INFO.items() if f_ == fase_key]
            st.markdown(f"#### {FASE_PT[fase_key]}")
            for num in sorted(nums):
                a, b = pdv["teams"][num]
                g1, g2 = p["scores"][num]
                pen_txt = ""
                if g1 == g2:
                    adv = p["advancers"].get(num)
                    pen_txt = f" · pênaltis: **{tn(adv)}**" if adv else " · ⚠️ sem escolha"
                st.markdown(f"J{num}: {tn(a)} **{g1} x {g2}** {tn(b)}{pen_txt}")
        st.markdown(f"#### 🏆 Pódio previsto")
        st.markdown(f"🥇 {tn(pdv['champion'])} · 🥈 {tn(pdv['vice'])} · "
                     f"🥉 {tn(pdv['third'])} · 4º {tn(pdv['fourth'])}")
    with t_fase:
        st.caption("Quem **cada um** tem em **cada fase** do mata-mata e como pontua na Seção B. "
                   "🟢 = o time avançou de verdade (posição de grupo certa vale cheio; errada, metade).")
        rd_pan = scoring.derive_full_adv(REAL, RADV)
        pdv_all = {q["nome"]: scoring.derive_full_adv(q["scores"], q["advancers"]) for q in PALPS}
        t2g = {t: L for L, ts in fx.GROUPS.items() for t in ts}
        subtabs = st.tabs([rot for _d, _s, rot in scoring.FASES_B] + ["Pódio"])
        for (degrau, setk, rot), tb in zip(scoring.FASES_B, subtabs):
            with tb:
                mr = scoring.membros_fase_real(REAL, RADV, rd_pan, setk)
                if not mr:
                    st.info("Esta fase ainda não foi decidida na vida real.")
                    continue
                full, half = scoring._B_PESOS[degrau]
                st.caption(f"{rot}: por time, posição certa **{full:g}** · posição errada **{half:g}**.")
                st.html(_panorama_fase_html(setk, degrau, PALPS, pdv_all, mr, t2g))
        with subtabs[-1]:
            if not rd_pan:
                st.info("O pódio aparece quando o mata-mata avançar (semifinais e final).")
            else:
                st.caption("Campeão **30/15** · vice **16/8** · 3º e 4º **10/5** (posição de grupo certa / errada).")
                st.html(_panorama_podio_html(PALPS, pdv_all, rd_pan))


# ============================================================ ⚽ JOGOS & GABARITO
elif pagina == "⚽ Jogos & Gabarito":
    st.title("⚽ Jogos & gabarito oficial")
    st.caption(f"Fonte do gabarito: **{FONTE}** — só o organizador lança resultados. "
               "**Clique num jogo** para abrir os palpites de todos.")
    with st.expander("❓ Como funciona a pontuação de cada jogo"):
        st.markdown(
            "**Dois acertos independentes se somam** *(esclarecido pela organização em "
            "12/jun/2026)*: **resultado** (vencedor/empate) → **3 pts** · **gol exato de um "
            "dos times** (nº de gols, comparado **time a time**) → **+1 pt — vale mesmo "
            "errando o resultado** · **placar exato** → **6 pts** (cobre tudo).\n\n"
            "Exemplos com o real **Coreia 2x1 Tchéquia**: palpite 2x1 → **6** · 2x0 → **4** "
            "(3 + gols da Coreia) · 1x0 → **3** (só o resultado) · **1x1 → 1** (errou o "
            "resultado, mas cravou o gol da Tcheca) · 0x2 → **0**.\n\n"
            "**Mata-mata (Seção C):** mesma lógica, com valores por fase (6/3/1 nos 16-avos "
            "até 30/16/8 na final) — pontua apenas se o **confronto previsto = confronto "
            "real** na mesma fase, e vale **metade** se a posição de grupo dos times estiver "
            "trocada. Prorrogação conta no placar; pênaltis não.")
    rows = scoring.ranking(PALPS, REAL, RADV, PEN)
    perA = {r["nome"]: r["perA"] for r in rows}
    perCn = {r["nome"]: r["perCn"] for r in rows}
    anul = {r["nome"]: r["anulados"] for r in rows}
    pdvs = {q["nome"]: scoring.derive_full_adv(q["scores"], q["advancers"]) for q in PALPS}
    rd = scoring.derive_full_adv(REAL, RADV)

    # texto do WhatsApp com os jogos+palpites de um dia (só jogos + palpites; sem link do site)
    def _zap_grupos(nums_dia, dia):
        out = [f"BOLÃO PCT — palpites de {dia}", ""]
        for num in nums_dia:
            _, t1, t2 = GROUP_INFO[num]
            out.append(f"J{num} {PT[t1]} x {PT[t2]}")
            out.append(" · ".join(f"{q['nome']} {q['scores'][num][0]}x{q['scores'][num][1]}"
                                  for q in PALPS))
            out.append("")
        return "\n".join(out).strip()

    def _zap_mata(nums_dia, dia):
        out = [f"BOLÃO PCT — palpites de {dia}", ""]
        for num in nums_dia:
            out.append(f"J{num} {FASE_PT[KO_INFO[num][0]]}")
            for q in PALPS:
                qa_, qb_ = pdvs[q["nome"]]["teams"][num]
                g1, g2 = q["scores"][num]
                pen = (f" (pen {PT.get(q['advancers'].get(num), '')})"
                       if g1 == g2 and q["advancers"].get(num) else "")
                out.append(f"{q['nome']}: {PT.get(qa_, '?')} {g1}x{g2} {PT.get(qb_, '?')}{pen}")
            out.append("")
        return "\n".join(out).strip()

    def _botao_zap_dia(texto, dia):
        st.link_button(f"📲 Compartilhar palpites de {dia} no WhatsApp",
                       "https://wa.me/?text=" + urllib.parse.quote(texto))

    def _imagem_dia(nums_dia, dia):
        # imagem colorida (grade palpiteiros × jogos) p/ mandar no zap — texto não carrega cor
        with st.expander(f"🖼️ Imagem dos palpites de {dia} (p/ WhatsApp)"):
            png = _grade_png(tuple(nums_dia), dia)
            st.image(png, width="stretch")
            st.download_button(f"⬇️ Baixar imagem de {dia}", data=png,
                               file_name=f"palpites_{dia.replace('/', '-')}.png",
                               mime="image/png", key=f"img_{dia}")
            st.caption("No celular: segure na imagem (ou baixe) → **Compartilhar** → WhatsApp.")

    # dia a dia: abre no dia de HOJE com um seletor; "ver todos" abre a lista completa
    dias_g, dias_k = {}, {}
    for num in sorted(GROUP_INFO):
        dias_g.setdefault(GROUP_INFO[num][0], []).append(num)
    for num in sorted(KO_INFO):
        dias_k.setdefault(KO_INFO[num][1], []).append(num)

    _INFO_MATA = ("Os confrontos REAIS do mata-mata aparecem quando a fase de grupos terminar — "
                  "mas o palpite de cada um já está travado: abra um jogo para ver o confronto previsto.")

    def _render_grupos_dia(dia, nums_dia):
        for num in nums_dia:
            _, t1, t2 = GROUP_INFO[num]
            r = REAL.get(num)
            placar = f"{r[0]} x {r[1]}" if r else "—"
            with st.expander(f"J{num} · {FLAG.get(t1, '')} {PT[t1]}  {placar}  {PT[t2]} {FLAG.get(t2, '')}"):
                linhas = []
                for q in PALPS:
                    g1, g2 = q["scores"][num]
                    if r:
                        pts = "0 (anulado)" if num in anul[q["nome"]] else f"{perA[q['nome']][num]:g}"
                    else:
                        pts = "—"
                    linhas.append({"Palpiteiro": q["nome"], "Palpite": f"{g1} x {g2}", "Pontos": pts})
                st.dataframe(pd.DataFrame(linhas), width="stretch", hide_index=True)
        _botao_zap_dia(_zap_grupos(nums_dia, dia), dia)
        _imagem_dia(nums_dia, dia)

    _SELO = {"cheia": "🟢 cheia", "metade": "🟡 metade", "fora": "— fora", None: "—"}

    def _render_mata_dia(dia, nums_dia):
        img_jogos = []                                    # alimenta a imagem do dia (grade por concorrência)
        for num in nums_dia:
            fase_k, _, s1, s2 = KO_INFO[num]
            r = REAL.get(num)
            placar = f"{r[0]} x {r[1]}" if r else "—"
            # status de concorrência de cada um (cheia/metade/fora) — já vale ANTES do placar
            status = {q["nome"]: scoring.concorrencia_jogo(pdvs[q["nome"]], rd, num) for q in PALPS}
            n_cheia = sum(1 for s in status.values() if s == "cheia")
            n_meia = sum(1 for s in status.values() if s == "metade")
            if rd:
                a, b = rd["teams"][num]
                confronto = f"{FLAG.get(a, '')} {PT.get(a, '?')}  {placar}  {PT.get(b, '?')} {FLAG.get(b, '')}"
            else:
                a = b = None
                confronto = f"{s1} x {s2}"
            pen_real = f" · pênaltis: {tn(RADV.get(num))}" if (r and r[0] == r[1]) else ""
            conc_tit = f" · 🎯 {n_cheia + n_meia} concorrendo ({n_cheia}🟢·{n_meia}🟡)" if (a and b) else ""
            if a and b:                                   # cabeçalho real p/ a imagem
                real_hdr = f"{_btla(a)} {r[0]}x{r[1]} {_btla(b)}" if r else f"{_btla(a)} x {_btla(b)} · a jogar"
            else:
                real_hdr = "a definir"
            linhas_img = []
            with st.expander(f"J{num} · {FASE_PT[fase_k]} · {confronto}{pen_real}{conc_tit}"):
                if a and b:
                    st.caption("🟢 cheia = par de times certo **e** posições de grupo certas · 🟡 metade = par "
                               "certo, posição de grupo trocada · — fora = errou o par. O selo já vale antes do "
                               "placar (⏳ = concorrendo, jogo por jogar).")
                linhas = []
                for q in PALPS:
                    qa_, qb_ = pdvs[q["nome"]]["teams"][num]
                    g1, g2 = q["scores"][num]
                    pen_txt = ""
                    if g1 == g2:
                        adv = q["advancers"].get(num)
                        pen_txt = f" (pênaltis: {PT.get(adv, '—')})" if adv else ""
                    if r:
                        pts = perCn[q["nome"]].get(num, "—")
                        pts = f"{pts:g}" if isinstance(pts, (int, float)) else pts
                    else:
                        pts = "⏳" if status[q["nome"]] in ("cheia", "metade") else "—"
                    linhas.append({"Palpiteiro": q["nome"],
                                   "Confronto previsto": f"{tn(qa_)} {g1} x {g2} {tn(qb_)}{pen_txt}",
                                   "Acerto": _SELO[status[q["nome"]]],
                                   "Pontos": pts})
                    conf_img = f"{_btla(qa_)} {g1}x{g2} {_btla(qb_)}" if (qa_ and qb_) else "—"
                    linhas_img.append((q["nome"], conf_img, status[q["nome"]]))
                st.dataframe(pd.DataFrame(linhas), width="stretch", hide_index=True)
            img_jogos.append((FASE_PT[fase_k], real_hdr, tuple(linhas_img)))
        _botao_zap_dia(_zap_mata(nums_dia, dia), dia)
        # imagem do dia (grade colorida por concorrência) — só quando há confronto real definido
        if any(h != "a definir" for _f, h, _l in img_jogos):
            with st.expander(f"🖼️ Imagem do mata-mata de {dia} (p/ WhatsApp)"):
                png = _grade_mata_png(dia, tuple(img_jogos))
                st.image(png, width="stretch")
                st.download_button(f"⬇️ Baixar imagem de {dia}", data=png,
                                   file_name=f"mata_{dia.replace('/', '-')}.png",
                                   mime="image/png", key=f"imgk_{dia}")
                st.caption("No celular: segure na imagem (ou baixe) → **Compartilhar** → WhatsApp.")

    # lista ordenada de TODOS os dias (grupos + mata-mata), com rótulo de fase/status
    _MES = {"jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
            "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12}

    def _data(diastr):
        dd, mm = diastr.split("/")
        return date(2026, _MES[mm], int(dd))

    todos_dias = [(_data(d), d, "grupos", "G", nums) for d, nums in dias_g.items()]
    for d, nums in dias_k.items():
        fl = " / ".join(dict.fromkeys(FASE_PT[KO_INFO[n][0]] for n in nums))
        todos_dias.append((_data(d), d, fl, "K", nums))
    todos_dias.sort(key=lambda t: t[0])
    try:
        _hoje = datetime.now(ZoneInfo("America/Sao_Paulo")).date()
    except Exception:
        _hoje = datetime.now().date()
    _default = next((i for i, t in enumerate(todos_dias) if t[0] >= _hoje), len(todos_dias) - 1)

    if st.toggle("📜 Ver todos os dias (lista completa)", value=False,
                 help="Mostra grupos e mata-mata inteiros, um dia embaixo do outro."):
        st.subheader("Fase de grupos")
        for dia, nums_dia in dias_g.items():
            st.markdown(f"#### 📅 {dia}")
            _render_grupos_dia(dia, nums_dia)
        st.subheader("Mata-mata")
        if rd is None:
            st.info(_INFO_MATA)
        for dia, nums_dia in dias_k.items():
            st.markdown(f"#### 📅 {dia}")
            _render_mata_dia(dia, nums_dia)
    else:
        # opções = rótulos estáveis (dia + fase); status volátil (hoje/✓/andamento) vai na legenda
        labels = [f"{d} · {fl}" for (_, d, fl, _, _) in todos_dias]
        by_label = dict(zip(labels, todos_dias))
        sel = st.selectbox("📅 Escolha o dia", labels, index=_default, key="dia_jogos")
        data_i, dia, fl, kind, nums_dia = by_label[sel]
        nres = sum(1 for n in nums_dia if REAL.get(n))
        if data_i == _hoje:
            st.caption("🔴 jogos de hoje")
        elif nres and nres == len(nums_dia):
            st.caption("✓ resultados lançados")
        elif nres:
            st.caption("🟡 em andamento")
        elif data_i > _hoje:
            st.caption("🗓️ ainda não começou")
        if kind == "K" and rd is None:
            st.info(_INFO_MATA)
        st.markdown(f"#### {dia} · {fl}")
        (_render_grupos_dia if kind == "G" else _render_mata_dia)(dia, nums_dia)


# ============================================================ 🎮 SIMULADOR
elif pagina == "🎮 Simulador":
    st.title("🎮 Simulador — e se…?")
    st.caption("Brinque de preencher resultados fictícios e veja o ranking reagir. "
               "Nada aqui é gravado — é só diversão; o gabarito oficial continua intocado. "
               "Os jogos já realizados vêm preenchidos (pode alterá-los também).")

    if st.button("↩️ Resetar simulação (voltar ao estado real)"):
        for k in list(st.session_state):
            if k.startswith("sim_"):
                del st.session_state[k]
        st.rerun()

    sim = {}
    st.subheader("Fase de grupos")
    cols = st.columns(2)
    for i, L in enumerate("ABCDEFGHIJKL"):
        with cols[i % 2].expander(f"Grupo {L}", expanded=False):
            for num, _, _, t1, t2, _ in fx.GROUP_MATCHES:
                if {t1, t2} <= set(fx.GROUPS[L]):
                    r = REAL.get(num)
                    for suf, dv in (("1", r[0] if r else None), ("2", r[1] if r else None)):
                        st.session_state.setdefault(f"sim_{num}_{suf}", dv)
                    c1, c2, c3 = st.columns([3, 1, 1])
                    c1.markdown(f"<div style='padding-top:0.6rem'>J{num} · {tn(t1)} x {tn(t2)}</div>",
                                unsafe_allow_html=True)
                    g1 = c2.number_input("g1", min_value=0, max_value=99, step=1, value=None,
                                         key=f"sim_{num}_1",
                                         label_visibility="collapsed", placeholder="-")
                    g2 = c3.number_input("g2", min_value=0, max_value=99, step=1, value=None,
                                         key=f"sim_{num}_2",
                                         label_visibility="collapsed", placeholder="-")
                    if g1 is not None and g2 is not None:
                        sim[num] = (int(g1), int(g2))

    n_grp = sum(1 for n in sim if n <= 72)
    sim_adv = {}
    if n_grp < 72:
        st.info(f"Grupos preenchidos: **{n_grp}/72**. O chaveamento abaixo já mostra a "
                "**classificação de momento** (cada vaga vira o time real conforme o grupo decide). "
                "Complete os 72 para **simular** os jogos do mata-mata.")
    else:
        st.subheader("Mata-mata (simule os confrontos)")
        sd_partial = scoring.derive_full_adv(sim, {})
        for fase_key in ("R32", "R16", "QF", "SF", "3P", "F"):
            nums = sorted(n for n, (f_, *_), in KO_INFO.items() if f_ == fase_key)
            with st.expander(FASE_PT[fase_key], expanded=(fase_key == "R32")):
                for num in nums:
                    sd_partial = scoring.derive_full_adv(sim, sim_adv)
                    a, b = sd_partial["teams"][num]
                    if not (a and b):
                        st.markdown(f"J{num}: — *(defina os jogos anteriores)*")
                        continue
                    r = REAL.get(num)
                    for suf, dv in (("1", r[0] if r else None), ("2", r[1] if r else None)):
                        st.session_state.setdefault(f"sim_{num}_{suf}", dv)
                    c1, c2, c3 = st.columns([3, 1, 1])
                    c1.markdown(f"<div style='padding-top:0.6rem'>J{num} · {tn(a)} x {tn(b)}</div>",
                                unsafe_allow_html=True)
                    g1 = c2.number_input("g1", min_value=0, max_value=99, step=1, value=None,
                                         key=f"sim_{num}_1",
                                         label_visibility="collapsed", placeholder="-")
                    g2 = c3.number_input("g2", min_value=0, max_value=99, step=1, value=None,
                                         key=f"sim_{num}_2",
                                         label_visibility="collapsed", placeholder="-")
                    if g1 is not None and g2 is not None:
                        sim[num] = (int(g1), int(g2))
                        if g1 == g2:
                            adv = st.radio(f"Pênaltis J{num} — quem passa?", [tn(a), tn(b)],
                                           key=f"sim_{num}_adv", horizontal=True)
                            sim_adv[num] = a if adv == tn(a) else b

    st.subheader("🗺️ Chaveamento")
    st.caption("Times pela **classificação de momento** dos grupos — cada vaga vira o real conforme "
               "o grupo decide; o vencedor de cada chave avança. Rola na horizontal/vertical."
               if n_grp < 72 else
               "Derivado da sua simulação — o vencedor de cada chave avança; o campeão sai no centro.")
    _sd_bracket = scoring.derive_partial(sim, sim_adv)
    if _sd_bracket:
        _bk = _bracket_struct(_sd_bracket, sim)
        st.html(_bracket_html(_bk))
        with st.expander("🖼️ Imagem do chaveamento (p/ compartilhar)"):
            _bk_png = _bracket_png_bytes(_bk)
            st.image(_bk_png, width="stretch")
            st.download_button("⬇️ Baixar chaveamento (PNG)", data=_bk_png,
                               file_name="chaveamento_simulado.png", mime="image/png", key="bk_png")
            st.caption("No celular: segure na imagem (ou baixe) → Compartilhar → WhatsApp.")
    else:
        st.info("Preencha ao menos alguns jogos de grupo para ver o chaveamento.")

    st.subheader("🏅 Ranking simulado")
    rows = scoring.ranking(PALPS, sim, sim_adv, PEN)
    medal = {1: "🥇", 2: "🥈", 3: "🥉"}
    df = pd.DataFrame([{
        "Pos": f"{medal.get(r['pos'], r['pos'])}",
        "Palpiteiro": r["nome"] + (" ⚠️" if r["anulados"] else ""),
        "Total": r["total"], "A": r["A"], "B": r["B"], "C": r["C"],
    } for r in rows])
    st.dataframe(df, width="stretch", hide_index=True)
    sd = scoring.derive_full_adv(sim, sim_adv)
    if sd and sd["champion"]:
        st.success(f"Na sua simulação: 🥇 {tn(sd['champion'])} · 🥈 {tn(sd['vice'])} · "
                   f"🥉 {tn(sd['third'])} · 4º {tn(sd['fourth'])}")


# ============================================================ 📜 REGRAS & AUDITORIA
else:
    st.title("📜 Regras & auditoria")
    st.markdown("### Penalidade aplicada (decisão da organização, 11/jun/2026)")
    for nome, info in PEN.items():
        st.warning(f"**{nome}** — jogo(s) {', '.join('J'+str(j) for j in info['jogos_anulados_secao_A'])} "
                   f"anulado(s) na Seção A. {info.get('motivo', '')}")
    st.markdown("**Regra geral declarada:** palpite entregue após o início do 1º jogo → "
                "todo jogo **já iniciado** no momento da entrega é **anulado** para o retardatário.")

    st.markdown("### Integridade dos palpites")
    st.caption(f"Consolidação: {meta.get('consolidacao', '')} · Fonte: {meta.get('gerado_de', '')}")
    st.code(meta.get("sha256_arquivos_originais", ""), language="text")

    st.markdown("### Regulamento")
    import os
    rg = os.path.join(os.path.dirname(os.path.abspath(__file__)), "regras.md")
    if os.path.exists(rg):
        st.markdown(open(rg, encoding="utf-8").read())
    else:
        st.info("regras.md não encontrado no deploy — veja o regulamento no grupo.")
