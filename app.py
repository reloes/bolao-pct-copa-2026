# -*- coding: utf-8 -*-
"""
🏆 Bolão PCT — Copa 2026 · site oficial da apuração (Streamlit).

Reusa os motores Python validados do projeto (bolao_engine/score_engine via scoring.py).
Palpites: congelados em palpites.json (imutáveis — auditoria por SHA-256 na página Regras).
Gabarito: Google Sheet do organizador (CSV publicado em st.secrets["GABARITO_CSV_URL"])
ou gabarito_local.json. Rode local: streamlit run app.py --server.port 8503
"""
import urllib.parse
import streamlit as st
import pandas as pd
import fixture_copa_2026 as fx
import score_engine as se
import scoring
import data as D

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
FASE_PT = {"R32": "32-avos", "R16": "Oitavas", "QF": "Quartas", "SF": "Semifinal",
           "3P": "3º lugar", "F": "FINAL"}
GROUP_INFO = {num: (d, t1, t2) for num, d, _, t1, t2, _ in fx.GROUP_MATCHES}
KO_INFO = {num: (fase, d, s1, s2) for num, fase, d, _, s1, s2 in fx.KO_MATCHES}


def tn(team):
    """Nome de exibição com bandeira (ou — para indefinido)."""
    return f"{FLAG.get(team, '')} {PT[team]}".strip() if team else "—"


@st.cache_data(ttl=60)
def carregar():
    meta, palps = D.load_palpites()
    try:
        url = st.secrets["GABARITO_CSV_URL"]
    except Exception:
        url = None
    real, radv, fonte = D.load_gabarito(url)
    return meta, palps, real, radv, fonte


meta, PALPS, REAL, RADV, FONTE = carregar()
PEN = meta.get("penalidades", {})
JOGADOS = sorted(REAL)

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
    df = pd.DataFrame([{
        "Pos": f"{medal.get(r['pos'], r['pos'])}",
        "Palpiteiro": r["nome"] + (" ⚠️" if r["anulados"] else ""),
        "Total": r["total"],
        "A · Grupos": r["A"],
        "B · Classificados": r["B"],
        "C · Mata-mata": r["C"],
    } for r in rows])
    st.dataframe(df, width="stretch", hide_index=True)
    if not JOGADOS:
        st.info("Nenhum resultado lançado ainda — todos zerados. O ranking nasce com o 1º jogo.")
    pen_rows = [r for r in rows if r["anulados"]]
    for r in pen_rows:
        info = PEN.get(r["nome"], {})
        st.warning(f"⚠️ **{r['nome']}** — jogo(s) **{', '.join('J'+str(j) for j in r['anulados'])}** "
                   f"anulado(s) na Seção A ({info.get('motivo', '')}) "
                   f"— deixou de marcar **{r['descontado']:g} pt(s)** até agora.")

    # --- exportar pro WhatsApp (pedido do grupo) ---
    medal_txt = {1: "🥇", 2: "🥈", 3: "🥉"}
    zap = ("🏆 BOLÃO PCT — Copa 2026\n"
           f"📊 Ranking após {len(JOGADOS)}/104 jogos:\n"
           + "\n".join(f"{medal_txt.get(r['pos'], str(r['pos']) + 'º')} {r['nome']}"
                       f"{' ⚠️' if r['anulados'] else ''} — {r['total']:g}" for r in rows)
           + "\n🔗 https://bolao-pct-copa-2026.streamlit.app")
    cz1, cz2 = st.columns([1, 2])
    cz1.link_button("📲 Compartilhar no WhatsApp", "https://wa.me/?text=" + urllib.parse.quote(zap))
    with cz2.expander("ver/copiar o texto da mensagem"):
        st.code(zap, language=None)

    st.subheader("Detalhe por palpiteiro")
    sel = st.selectbox("Palpiteiro", [r["nome"] for r in rows])
    r = next(x for x in rows if x["nome"] == sel)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total", f"{r['total']:g}")
    c2.metric("Seção A", f"{r['A']:g}")
    c3.metric("Seção B", f"{r['B']:g}")
    c4.metric("Seção C", f"{r['C']:g}")
    ja = [(f"J{n}", f"{tn(GROUP_INFO[n][1])} {REAL[n][0]} x {REAL[n][1]} {tn(GROUP_INFO[n][2])}",
           ("ANULADO" if n in r["anulados"] else f"{r['perA'][n]:g}"))
          for n in JOGADOS if n <= 72]
    if ja:
        st.caption("Pontos por jogo já realizado (Seção A):")
        st.dataframe(pd.DataFrame(ja, columns=["Jogo", "Resultado", "Pontos"]),
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

    t_grupos, t_mata, t_comp = st.tabs(["Fase de grupos", "Mata-mata", "Comparativo dos grupos"])
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
        st.caption("A classificação prevista por cada palpiteiro, grupo a grupo, lado a lado "
                   "(o 3º é quem disputa a repescagem dos 8 melhores terceiros).")
        all_stand = {q["nome"]: scoring.derive_full_adv(q["scores"], q["advancers"])["standings"]
                     for q in PALPS}
        tabs_g = st.tabs([f"Grupo {L}" for L in "ABCDEFGHIJKL"])
        for L, tg in zip("ABCDEFGHIJKL", tabs_g):
            with tg:
                df_c = pd.DataFrame([{"Palpiteiro": nome,
                                      **{f"{i+1}º": tn(stand[L][i]) for i in range(4)}}
                                     for nome, stand in all_stand.items()])
                st.dataframe(df_c, width="stretch", hide_index=True)
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
            "**Mata-mata (Seção C):** mesma lógica, com valores por fase (6/3/1 nos 32-avos "
            "até 30/16/8 na final) — pontua apenas se o **confronto previsto = confronto "
            "real** na mesma fase, e vale **metade** se a posição de grupo dos times estiver "
            "trocada. Prorrogação conta no placar; pênaltis não.")
    rows = scoring.ranking(PALPS, REAL, RADV, PEN)
    perA = {r["nome"]: r["perA"] for r in rows}
    perCn = {r["nome"]: r["perCn"] for r in rows}
    anul = {r["nome"]: r["anulados"] for r in rows}
    pdvs = {q["nome"]: scoring.derive_full_adv(q["scores"], q["advancers"]) for q in PALPS}
    rd = scoring.derive_full_adv(REAL, RADV)

    st.subheader("Fase de grupos")
    cur_date = None
    for num, d_, t1, t2 in [(n, *GROUP_INFO[n]) for n in sorted(GROUP_INFO)]:
        if d_ != cur_date:
            cur_date = d_
            st.markdown(f"#### 📅 {d_}")
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

    st.subheader("Mata-mata")
    if rd is None:
        st.info("Os confrontos REAIS aparecem quando a fase de grupos terminar — mas o palpite "
                "de cada um já está travado: abra um jogo para ver o confronto que cada um previu.")
    cur_date = None
    for num in sorted(KO_INFO):
        fase_k, d_, s1, s2 = KO_INFO[num]
        if d_ != cur_date:
            cur_date = d_
            st.markdown(f"#### 📅 {d_}")
        r = REAL.get(num)
        placar = f"{r[0]} x {r[1]}" if r else "—"
        if rd:
            a, b = rd["teams"][num]
            confronto = f"{FLAG.get(a, '')} {PT.get(a, '?')}  {placar}  {PT.get(b, '?')} {FLAG.get(b, '')}"
        else:
            confronto = f"{s1} x {s2}"
        pen_real = f" · pênaltis: {tn(RADV.get(num))}" if (r and r[0] == r[1]) else ""
        with st.expander(f"J{num} · {FASE_PT[fase_k]} · {confronto}{pen_real}"):
            linhas = []
            for q in PALPS:
                qa_, qb_ = pdvs[q["nome"]]["teams"][num]
                g1, g2 = q["scores"][num]
                pen_txt = ""
                if g1 == g2:
                    adv = q["advancers"].get(num)
                    pen_txt = f" (pênaltis: {PT.get(adv, '—')})" if adv else ""
                pts = perCn[q["nome"]].get(num, "—") if r else "—"
                pts = f"{pts:g}" if isinstance(pts, (int, float)) else pts
                linhas.append({"Palpiteiro": q["nome"],
                               "Confronto previsto": f"{tn(qa_)} {g1} x {g2} {tn(qb_)}{pen_txt}",
                               "Pontos": pts})
            st.dataframe(pd.DataFrame(linhas), width="stretch", hide_index=True)


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
                    g1 = c2.number_input("g1", min_value=0, max_value=99, step=1,
                                         key=f"sim_{num}_1",
                                         label_visibility="collapsed", placeholder="-")
                    g2 = c3.number_input("g2", min_value=0, max_value=99, step=1,
                                         key=f"sim_{num}_2",
                                         label_visibility="collapsed", placeholder="-")
                    if g1 is not None and g2 is not None:
                        sim[num] = (int(g1), int(g2))

    n_grp = sum(1 for n in sim if n <= 72)
    sim_adv = {}
    if n_grp < 72:
        st.info(f"Grupos preenchidos: **{n_grp}/72**. Complete os 72 para liberar o mata-mata "
                "simulado (igual à planilha: o bracket só deriva com a fase de grupos completa).")
    else:
        st.subheader("Mata-mata (confrontos derivados da sua simulação)")
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
                    g1 = c2.number_input("g1", min_value=0, max_value=99, step=1,
                                         key=f"sim_{num}_1",
                                         label_visibility="collapsed", placeholder="-")
                    g2 = c3.number_input("g2", min_value=0, max_value=99, step=1,
                                         key=f"sim_{num}_2",
                                         label_visibility="collapsed", placeholder="-")
                    if g1 is not None and g2 is not None:
                        sim[num] = (int(g1), int(g2))
                        if g1 == g2:
                            adv = st.radio(f"Pênaltis J{num} — quem passa?", [tn(a), tn(b)],
                                           key=f"sim_{num}_adv", horizontal=True)
                            sim_adv[num] = a if adv == tn(a) else b

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
