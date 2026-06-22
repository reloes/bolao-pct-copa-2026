# -*- coding: utf-8 -*-
"""
Imagem PNG da GRADE de palpites de um dia (para compartilhar no WhatsApp).

Grade palpiteiros × jogos do dia. A COR de cada célula segue as colunas 1-X-2 da
aposta (estilo Loteca): vence o time da ESQUERDA (1, azul) · empate (X, vermelho) ·
vence o time da DIREITA (2, verde). A INTENSIDADE do tom = total de gols no jogo
(mais gols, tom mais forte). Desenhada com Pillow (sem navegador).

FONTE: embarcamos a DejaVu Sans no próprio repo (fonts/) e a carregamos por caminho
RELATIVO, em PRIMEIRO lugar — porque no Streamlit Cloud as fontes do sistema podem
NÃO estar no caminho esperado e o Pillow cai num default sem os glifos 'Ã'/'—'
(produção mostrava "BOL□O", "BET□O"). Com a fonte no repo, produção = local.
DejaVu é livremente redistribuível (licença Bitstream Vera/Arev) — ver fonts/README.txt.

WhatsApp não aceita imagem por URL (wa.me só leva texto) → o caminho é baixar/segurar
na imagem e usar Compartilhar → WhatsApp. Por isso o app entrega via download_button.
"""
import io
import os
from PIL import Image, ImageDraw, ImageFont

# --- cores base das 3 colunas da aposta (1-X-2); ajustáveis ---
AZUL = (30, 110, 200)       # coluna 1: vence o time da ESQUERDA (listado primeiro)
VERMELHO = (220, 90, 95)    # coluna do meio (X): empate
VERDE = (40, 165, 90)       # coluna 2: vence o time da DIREITA
BRANCO = (255, 255, 255)
PRETO = (26, 26, 26)
CINZA = (120, 120, 120)
NAVY = (26, 43, 99)         # cabeçalho (navy D1A)
CINZA_CAB = (236, 239, 244)  # fundo da linha de cabeçalho (TLAs)
ZEBRA = (247, 248, 250)     # leve faixa alternada na coluna de nomes

SCALE = 2   # render em 2x → nítido mesmo esticado pelo st.image(width="stretch")

_HERE = os.path.dirname(os.path.abspath(__file__))
_FONTES = [
    os.path.join(_HERE, "fonts", "DejaVuSans.ttf"),               # embarcada (garante glifos no Cloud)
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",            # Streamlit Cloud (Debian)
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",       # macOS
    "/System/Library/Fonts/Supplemental/Arial.ttf",
]
_FONTES_BOLD = [
    os.path.join(_HERE, "fonts", "DejaVuSans-Bold.ttf"),
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
]


def _font(paths, size):
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    try:                                # último recurso (não deve ocorrer: a fonte do repo é a 1ª)
        return ImageFont.load_default(size)
    except TypeError:
        return ImageFont.load_default()


def _lerp(c1, c2, a):
    """Interpola RGB de c1 a c2 com fator a∈[0,1]."""
    return tuple(round(c1[i] + (c2[i] - c1[i]) * a) for i in range(3))


def cor_palpite(g1, g2):
    """Cor da célula para o palpite (g1, g2). Devolve (rgb, coluna).

    coluna ∈ {'1','X','2'}: vence esquerda / empate / vence direita.
    Matiz = coluna 1-X-2; intensidade = total de gols (mais gols → tom mais forte).
    """
    if g1 > g2:
        base, col = AZUL, "1"
    elif g1 < g2:
        base, col = VERDE, "2"
    else:
        base, col = VERMELHO, "X"
    total = g1 + g2
    alpha = 0.15 + 0.85 * min(total, 6) / 6.0   # t=0 → leve tinta; t≥6 → cor cheia
    return _lerp(BRANCO, base, alpha), col


def _text_color(bg):
    """Preto em fundo claro, branco em fundo escuro (luminância perceptual)."""
    lum = 0.299 * bg[0] + 0.587 * bg[1] + 0.114 * bg[2]
    return BRANCO if lum < 145 else PRETO


def _centro(d, box, text, font, fill):
    """Desenha text centralizado (h e v) na caixa box=(x0,y0,x1,y1)."""
    x0, y0, x1, y1 = box
    l, t, r, b = d.textbbox((0, 0), text, font=font)
    d.text((x0 + (x1 - x0 - (r - l)) / 2 - l, y0 + (y1 - y0 - (b - t)) / 2 - t),
           text, font=font, fill=fill)


def palpites_grid_png(dia, jogos):
    """Grade colorida dos palpites de um dia → bytes PNG.

    dia: 'dd/mmm' (ex.: '16/jun').
    jogos: [(num, tla1, tla2, [(nome, g1, g2), ...]), ...] — a lista de palpiteiros
           vem na MESMA ordem em todos os jogos (ordem fixa de PALPS).
    """
    if not jogos:
        raise ValueError("nenhum jogo no dia")
    nomes = [n for n, _, _ in jogos[0][3]]
    n_col, n_lin = len(jogos), len(nomes)
    S = SCALE

    COL_NOME = 200 * S       # largura da coluna de nomes
    CEL = 152 * S            # largura de cada coluna de jogo
    TIT_H = 72 * S           # faixa do título
    CAB_H = 58 * S           # linha de cabeçalho (TLAs)
    LIN_H = 64 * S           # altura de cada linha de palpiteiro
    LEG_H = 92 * S           # rodapé com a legenda
    GAP = 4 * S              # respiro entre células (gera o "grid" branco)
    RAIO = 9 * S             # cantos arredondados das células
    PAD = 18 * S             # padding lateral

    W = COL_NOME + n_col * CEL
    H = TIT_H + CAB_H + n_lin * LIN_H + LEG_H

    img = Image.new("RGB", (W, H), BRANCO)
    d = ImageDraw.Draw(img)

    f_tit = _font(_FONTES_BOLD, 34 * S)
    f_cab = _font(_FONTES_BOLD, 25 * S)
    f_nome = _font(_FONTES_BOLD, 25 * S)
    f_cel = _font(_FONTES_BOLD, 27 * S)
    f_leg = _font(_FONTES, 20 * S)

    # --- título (faixa navy) ---
    d.rectangle([0, 0, W, TIT_H], fill=NAVY)
    _centro(d, (0, 0, W, TIT_H), f"BOLÃO PCT — palpites de {dia}", f_tit, BRANCO)

    # --- linha de cabeçalho: canto vazio + TLA1xTLA2 por jogo ---
    y0 = TIT_H
    d.rectangle([0, y0, W, y0 + CAB_H], fill=CINZA_CAB)
    for c, (num, tla1, tla2, _linhas) in enumerate(jogos):
        x = COL_NOME + c * CEL
        _centro(d, (x, y0, x + CEL, y0 + CAB_H), f"{tla1}x{tla2}", f_cab, NAVY)

    # --- linhas de palpiteiros ---
    yb = TIT_H + CAB_H
    for li, nome in enumerate(nomes):
        y = yb + li * LIN_H
        if li % 2 == 1:                                   # zebra suave na coluna de nomes
            d.rectangle([0, y, COL_NOME, y + LIN_H], fill=ZEBRA)
        lb, tb, rb, bb = d.textbbox((0, 0), nome, font=f_nome)
        d.text((PAD, y + (LIN_H - (bb - tb)) / 2 - tb), nome, font=f_nome, fill=PRETO)
        for c, (num, _t1, _t2, linhas) in enumerate(jogos):
            _, g1, g2 = linhas[li]
            bg, _col = cor_palpite(g1, g2)
            x = COL_NOME + c * CEL
            d.rounded_rectangle([x + GAP, y + GAP, x + CEL - GAP, y + LIN_H - GAP],
                                radius=RAIO, fill=bg)
            _centro(d, (x, y, x + CEL, y + LIN_H), f"{g1}x{g2}", f_cel, _text_color(bg))

    # --- legenda (rodapé) ---
    yl = H - LEG_H
    d.line([0, yl, W, yl], fill=CINZA_CAB, width=2 * S)
    sw = 22 * S                                           # tamanho do quadrado-amostra
    cy = yl + 18 * S
    itens = [(AZUL, "1 vence o time da esquerda"),
             (VERMELHO, "X empate"),
             (VERDE, "2 vence o time da direita")]
    x = PAD
    for cor, txt in itens:
        d.rounded_rectangle([x, cy, x + sw, cy + sw], radius=5 * S, fill=cor)
        lb, tb, rb, bb = d.textbbox((0, 0), txt, font=f_leg)
        d.text((x + sw + 8 * S, cy + (sw - (bb - tb)) / 2 - tb), txt, font=f_leg, fill=PRETO)
        x += sw + 8 * S + (rb - lb) + 28 * S
    d.text((PAD, cy + sw + 12 * S),
           "Tom mais forte = mais gols no jogo  ·  bolao-pct-copa-2026.streamlit.app",
           font=f_leg, fill=CINZA)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ===================== Chaveamento do mata-mata (bracket) =====================
AZUL_CLARO = _lerp(BRANCO, AZUL, 0.20)
OURO = (212, 175, 55)
OURO_BG = (250, 238, 218)
OURO_TX = (99, 56, 6)


def _bx(d, x, y, w, h, m, fb, fs):
    """Uma chave (2 times). m = (a_tla, a_sc, a_win, b_tla, b_sc, b_win)."""
    a_tla, a_sc, a_win, b_tla, b_sc, b_win = m
    rh = h / 2
    for k, (tla, sc, win) in enumerate(((a_tla, a_sc, a_win), (b_tla, b_sc, b_win))):
        ry = y + k * rh
        if win:
            d.rectangle([x, ry, x + w, ry + rh], fill=AZUL_CLARO)
        cor = NAVY if win else (PRETO if tla else CINZA)
        d.text((x + 9, ry + rh / 2 - getattr(fb, "size", 20) / 2), tla or "—", font=fb, fill=cor)
        if sc is not None:
            s = str(sc)
            d.text((x + w - 9 - d.textlength(s, font=fs), ry + rh / 2 - getattr(fs, "size", 18) / 2),
                   s, font=fs, fill=cor)
    d.rectangle([x, y, x + w, y + h], outline=CINZA, width=1)
    d.line([x, y + rh, x + w, y + rh], fill=CINZA_CAB, width=1)


def bracket_png(left, right, final, champ, terceiro=None):
    """Árvore TWO-SIDED (converge na final central) → bytes PNG. left/right: 4 colunas de FORA p/
    DENTRO [R32(8), R16(4), QF(2), SF(1)]; cada chave (a_tla,a_sc,a_win,b_tla,b_sc,b_win).
    final: chave da final; champ: sigla do campeão; terceiro: chave do 3º ou None."""
    S = SCALE
    BW, BH, GAPX, SLOT = 110 * S, 46 * S, 34 * S, 58 * S
    PADX, TITLE, HEADH = 22 * S, 58 * S, 26 * S
    n0 = len(left[0])
    step = BW + GAPX
    xfin = PADX + 4 * step
    W = PADX * 2 + 9 * BW + 8 * GAPX
    top = TITLE + HEADH + 10 * S
    treeH = n0 * SLOT
    H = top + treeH + (132 * S if terceiro else 64 * S)
    img = Image.new("RGB", (W, H), BRANCO)
    d = ImageDraw.Draw(img)
    f_t, f_hd = _font(_FONTES_BOLD, 28 * S), _font(_FONTES_BOLD, 16 * S)
    f_b, f_s = _font(_FONTES_BOLD, 18 * S), _font(_FONTES, 16 * S)
    lw = max(1, S)
    d.rectangle([0, 0, W, TITLE], fill=NAVY)
    _centro(d, (0, 0, W, TITLE), "Chaveamento — sua simulação", f_t, BRANCO)
    heads = ["16-avos", "Oitavas", "Quartas", "Semi", "Final", "Semi", "Quartas", "Oitavas", "16-avos"]
    for i, h in enumerate(heads):
        hx = PADX + i * step
        _centro(d, (hx, TITLE + 2 * S, hx + BW, TITLE + HEADH), h, f_hd, NAVY)

    def ys_of(cols):
        ys = [[top + i * SLOT + SLOT / 2 for i in range(len(cols[0]))]]
        for r in range(1, len(cols)):
            p = ys[-1]
            ys.append([(p[2 * j] + p[2 * j + 1]) / 2 for j in range(len(cols[r]))])
        return ys

    ysl, ysr = ys_of(left), ys_of(right)
    for r, col in enumerate(left):                        # lado esquerdo cresce p/ a direita
        cx = PADX + r * step
        for j, m in enumerate(col):
            cy = ysl[r][j]
            _bx(d, cx, cy - BH / 2, BW, BH, m, f_b, f_s)
            if r < len(left) - 1 and j % 2 == 0:
                midx, ny = cx + BW + GAPX / 2, ysl[r + 1][j // 2]
                d.line([cx + BW, cy, midx, cy], fill=CINZA_CAB, width=lw)
                d.line([cx + BW, ysl[r][j + 1], midx, ysl[r][j + 1]], fill=CINZA_CAB, width=lw)
                d.line([midx, cy, midx, ysl[r][j + 1]], fill=CINZA_CAB, width=lw)
                d.line([midx, ny, cx + step, ny], fill=CINZA_CAB, width=lw)
    for r, col in enumerate(right):                       # lado direito cresce p/ a esquerda
        cx = xfin + (4 - r) * step
        for j, m in enumerate(col):
            cy = ysr[r][j]
            _bx(d, cx, cy - BH / 2, BW, BH, m, f_b, f_s)
            if r < len(right) - 1 and j % 2 == 0:
                midx, ny = cx - GAPX / 2, ysr[r + 1][j // 2]
                d.line([cx, cy, midx, cy], fill=CINZA_CAB, width=lw)
                d.line([cx, ysr[r][j + 1], midx, ysr[r][j + 1]], fill=CINZA_CAB, width=lw)
                d.line([midx, cy, midx, ysr[r][j + 1]], fill=CINZA_CAB, width=lw)
                d.line([midx, ny, cx - step + BW, ny], fill=CINZA_CAB, width=lw)
    fcy = top + treeH / 2                                 # final no centro
    d.line([PADX + 3 * step + BW, fcy, xfin, fcy], fill=CINZA_CAB, width=lw)
    d.line([xfin + BW, fcy, xfin + step, fcy], fill=CINZA_CAB, width=lw)
    _bx(d, xfin, fcy - BH / 2, BW, BH, final, f_b, f_s)
    chy = fcy + BH / 2 + 20 * S                           # campeão (chip dourado, abaixo da final)
    _centro(d, (xfin, chy - 19 * S, xfin + BW, chy), "campeão", f_hd, OURO_TX)
    d.rounded_rectangle([xfin, chy, xfin + BW, chy + 38 * S], radius=8 * S,
                        fill=OURO_BG, outline=OURO, width=2 * S)
    _centro(d, (xfin, chy, xfin + BW, chy + 38 * S), champ or "—", _font(_FONTES_BOLD, 22 * S), OURO_TX)
    if terceiro:                                          # disputa de 3º (abaixo do campeão)
        ty = chy + 38 * S + 32 * S
        _centro(d, (xfin, ty - 22 * S, xfin + BW, ty), "disputa de 3º", f_hd, CINZA)
        _bx(d, xfin, ty, BW, BH, terceiro, f_b, f_s)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
