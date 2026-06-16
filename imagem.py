# -*- coding: utf-8 -*-
"""
Imagem PNG da GRADE de palpites de um dia (para compartilhar no WhatsApp).

Grade palpiteiros × jogos do dia. A COR de cada célula segue as colunas 1-X-2 da
aposta (estilo Loteca): vence o time da ESQUERDA (1, azul) · empate (X, vermelho) ·
vence o time da DIREITA (2, verde). A INTENSIDADE do tom = total de gols no jogo
(mais gols, tom mais forte). Desenhada com Pillow (sem navegador); fontes do sistema
com fallback (DejaVu no Streamlit Cloud/Debian; Arial no macOS local).

WhatsApp não aceita imagem por URL (wa.me só leva texto) → o caminho é baixar/segurar
na imagem e usar Compartilhar → WhatsApp. Por isso o app entrega via download_button.
"""
import io
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

_FONTES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",            # Streamlit Cloud (Debian)
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",       # macOS
    "/System/Library/Fonts/Supplemental/Arial.ttf",
]
_FONTES_BOLD = [
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
    """Desenha text centralizado na caixa box=(x0,y0,x1,y1)."""
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

    COL_NOME = 200       # largura da coluna de nomes
    CEL = 152            # largura de cada coluna de jogo
    TIT_H = 72           # faixa do título
    CAB_H = 58           # linha de cabeçalho (TLAs)
    LIN_H = 64           # altura de cada linha de palpiteiro
    LEG_H = 86           # rodapé com a legenda
    GAP = 4              # respiro entre células (gera o "grid" branco)
    RAIO = 9             # cantos arredondados das células

    W = COL_NOME + n_col * CEL
    H = TIT_H + CAB_H + n_lin * LIN_H + LEG_H

    img = Image.new("RGB", (W, H), BRANCO)
    d = ImageDraw.Draw(img)

    f_tit = _font(_FONTES_BOLD, 34)
    f_cab = _font(_FONTES_BOLD, 25)
    f_nome = _font(_FONTES_BOLD, 25)
    f_cel = _font(_FONTES_BOLD, 27)
    f_leg = _font(_FONTES, 20)
    f_leg_b = _font(_FONTES_BOLD, 20)

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
        d.text((18, y + (LIN_H - 25) / 2), nome, font=f_nome, fill=PRETO)
        for c, (num, _t1, _t2, linhas) in enumerate(jogos):
            _, g1, g2 = linhas[li]
            bg, _col = cor_palpite(g1, g2)
            x = COL_NOME + c * CEL
            d.rounded_rectangle([x + GAP, y + GAP, x + CEL - GAP, y + LIN_H - GAP],
                                radius=RAIO, fill=bg)
            _centro(d, (x, y, x + CEL, y + LIN_H), f"{g1}x{g2}", f_cel, _text_color(bg))

    # --- legenda (rodapé) ---
    yl = H - LEG_H
    d.rectangle([0, yl, W, H], fill=BRANCO)
    d.line([0, yl, W, yl], fill=CINZA_CAB, width=2)
    sw = 22                                               # tamanho do quadrado-amostra
    cy = yl + 18
    itens = [(AZUL, "1 vence o time da esquerda"),
             (VERMELHO, "X empate"),
             (VERDE, "2 vence o time da direita")]
    x = 18
    for cor, txt in itens:
        d.rounded_rectangle([x, cy, x + sw, cy + sw], radius=5, fill=cor)
        d.text((x + sw + 8, cy + 1), txt, font=f_leg, fill=PRETO)
        x += sw + 8 + d.textlength(txt, font=f_leg) + 28
    d.text((18, cy + sw + 12),
           "Tom mais forte = mais gols no jogo  ·  bolao-pct-copa-2026.streamlit.app",
           font=f_leg, fill=CINZA)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
