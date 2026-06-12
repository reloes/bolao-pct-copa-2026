# -*- coding: utf-8 -*-
"""
Gera a IMAGEM PNG do ranking oficial (para compartilhar no WhatsApp).
Desenhada com Pillow (sem dependência de navegador); fontes do sistema com
fallback (DejaVu no Streamlit Cloud/Debian; Helvetica/Arial no macOS local).
"""
import io
from PIL import Image, ImageDraw, ImageFont

VERDE = (14, 124, 58)
VERDE_ESCURO = (10, 95, 45)
BRANCO = (255, 255, 255)
PRETO = (26, 26, 26)
CINZA = (110, 110, 110)
ZEBRA = (242, 247, 242)
OURO = (212, 175, 55)
PRATA = (158, 158, 158)
BRONZE = (176, 112, 60)
AMARELO_AVISO = (255, 248, 220)

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


def ranking_png(linhas, n_jogados, quando):
    """linhas: [(pos, nome, total, anulado_bool), ...] já ordenadas.
    quando: string 'dd/mmm HH:MM'. Devolve bytes PNG (1000px de largura)."""
    W = 1000
    header_h, row_h, foot_h = 170, 78, 96
    H = header_h + 26 + row_h * len(linhas) + foot_h
    img = Image.new("RGB", (W, H), BRANCO)
    d = ImageDraw.Draw(img)

    f_tit = _font(_FONTES_BOLD, 52)
    f_sub = _font(_FONTES, 28)
    f_nome = _font(_FONTES_BOLD, 34)
    f_nota = _font(_FONTES, 22)
    f_total = _font(_FONTES_BOLD, 38)
    f_pos = _font(_FONTES_BOLD, 30)
    f_foot = _font(_FONTES, 24)

    # cabeçalho
    d.rectangle([0, 0, W, header_h], fill=VERDE)
    d.rectangle([0, header_h - 8, W, header_h], fill=VERDE_ESCURO)
    d.text((40, 32), "BOLÃO PCT — COPA 2026", font=f_tit, fill=BRANCO)
    d.text((40, 104), f"Ranking oficial · {n_jogados}/104 jogos · atualizado {quando}",
           font=f_sub, fill=(220, 240, 225))

    # linhas
    y = header_h + 26
    medal = {1: OURO, 2: PRATA, 3: BRONZE}
    for pos, nome, total, anulado in linhas:
        if (y - header_h - 26) // row_h % 2 == 1:
            d.rectangle([0, y, W, y + row_h], fill=ZEBRA)
        cx, cy = 76, y + row_h // 2
        if pos in medal:
            d.ellipse([cx - 26, cy - 26, cx + 26, cy + 26], fill=medal[pos])
            tw = d.textlength(str(pos), font=f_pos)
            d.text((cx - tw / 2, cy - 19), str(pos), font=f_pos, fill=BRANCO)
        else:
            tw = d.textlength(f"{pos}º", font=f_pos)
            d.text((cx - tw / 2, cy - 19), f"{pos}º", font=f_pos, fill=CINZA)
        d.text((150, cy - 22), nome, font=f_nome, fill=PRETO)
        if anulado:
            nw = d.textlength(nome, font=f_nome)
            d.text((150 + nw + 16, cy - 12), "(J1 anulado)", font=f_nota, fill=(180, 90, 0))
        t = f"{total:g}"
        tw = d.textlength(t, font=f_total)
        d.text((W - 60 - tw, cy - 24), t, font=f_total, fill=VERDE)
        y += row_h

    # rodapé
    d.rectangle([0, H - foot_h, W, H], fill=(245, 245, 245))
    d.text((40, H - foot_h + 22), "bolao-pct-copa-2026.streamlit.app", font=f_foot, fill=CINZA)
    d.text((W - 60 - d.textlength("pontos", font=f_foot), H - foot_h + 22),
           "pontos", font=f_foot, fill=CINZA)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
