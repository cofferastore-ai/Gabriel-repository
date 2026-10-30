"""Cenas animadas desenhadas quadro a quadro com Pillow (contador, barras, gráfico, texto)."""
import math
import random
from typing import Iterator

from PIL import Image, ImageDraw, ImageFilter

from . import visuals
from .script import THEMES, Scene

W, H = visuals.SIZE
FPS = 30
CHART_TOP, CHART_BOTTOM = 860, 1260  # acima da legenda (que fica em ~y 1400)


def ease(t: float) -> float:
    t = min(max(t, 0.0), 1.0)
    return 1 - (1 - t) ** 3


def fmt(v: float, prefix: str = "", suffix: str = "", decimals: int = 0) -> str:
    s = f"{v:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{prefix}{s}{suffix}"


def growth_series(monthly: float, rate: float, months: int) -> tuple[list[float], list[float]]:
    total, invested, bal = [0.0], [0.0], 0.0
    for m in range(1, months + 1):
        bal = bal * (1 + rate) + monthly
        total.append(bal)
        invested.append(monthly * m)
    return total, invested


def _bokeh_bg(niche: str, t: float, circles) -> Image.Image:
    """Gradiente com círculos suaves à deriva, desenhado pequeno e ampliado (fica naturalmente desfocado)."""
    top, bottom, accent = THEMES.get(niche, THEMES["default"])
    sw, sh = W // 4, H // 4
    base = visuals.gradient(top, bottom, (sw, sh)).convert("RGBA")
    layer = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for x, y, r, ph, sp, a in circles:
        cx = (x + 0.06 * math.sin(sp * t + ph)) * sw
        cy = (y + 0.05 * math.cos(sp * 0.8 * t + ph)) * sh
        d.ellipse([cx - r * sw, cy - r * sw, cx + r * sw, cy + r * sw], fill=accent + (a,))
    soft = Image.alpha_composite(base, layer).convert("RGB").filter(ImageFilter.GaussianBlur(1.6))
    return soft.resize((W, H), Image.BICUBIC)


def _circles(seed: str, n: int = 7):
    rnd = random.Random(seed)
    return [(rnd.random(), rnd.random(), rnd.uniform(0.08, 0.22), rnd.uniform(0, 6.28),
             rnd.uniform(0.4, 1.1), rnd.randint(22, 48)) for _ in range(n)]


def _center(d: ImageDraw.ImageDraw, text: str, f, y: int, fill) -> None:
    d.text(((W - f.getlength(text)) / 2, y), text, font=f, fill=fill)


def _counter(img, d, p, accent, t):
    v = d["value"] * p
    txt = fmt(v, d.get("prefix", ""), d.get("suffix", ""), d.get("decimals", 0))
    final = fmt(d["value"], d.get("prefix", ""), d.get("suffix", ""), d.get("decimals", 0))
    f = visuals.font(230)
    while f.getlength(final) > W - 2 * visuals.MARGIN and f.size > 80:
        f = visuals.font(f.size - 10)
    dr = ImageDraw.Draw(img)
    y = 900
    dr.text(((W - f.getlength(txt)) / 2 + 5, y + 7), txt, font=f, fill=(0, 0, 0))
    _center(dr, txt, f, y, (255, 255, 255))
    bar_w = int((W - 2 * visuals.MARGIN) * p)
    dr.rectangle([visuals.MARGIN, y + f.size + 40, visuals.MARGIN + bar_w, y + f.size + 52], fill=accent)
    if d.get("label"):
        _center(dr, d["label"].upper(), visuals.font(54), y + f.size + 90, accent)


def _bars(img, d, p, accent, t):
    items, n = d["items"], len(d["items"])
    maxv = max(i["value"] for i in items)
    dr = ImageDraw.Draw(img)
    slot = (CHART_BOTTOM - CHART_TOP + 40) / n
    lf, vf = visuals.font(46), visuals.font(46)
    track = tuple(int(c * 0.16) for c in accent)
    left, right = visuals.MARGIN, W - visuals.MARGIN
    for i, it in enumerate(items):
        q = ease((p - 0.18 * i) / (1 - 0.18 * (n - 1)))
        y = CHART_TOP + i * slot
        col = accent if i == n - 1 else (235, 235, 235)
        dr.text((left, y), it["label"], font=lf, fill=col)
        val = fmt(it["value"] * q, d.get("prefix", ""), d.get("suffix", ""), d.get("decimals", 0))
        dr.text((right - vf.getlength(val), y), val, font=vf, fill=col)
        dr.rounded_rectangle([left, y + 62, right, y + 62 + 56], 14, fill=track)
        length = max(int((right - left) * it["value"] / maxv * q), 0)
        if length > 28:
            dr.rounded_rectangle([left, y + 62, left + length, y + 62 + 56], 14, fill=col)


def _growth(img, d, p, accent, t):
    total, invested = growth_series(d["monthly"], d["rate"], d["months"])
    m_max = d["months"]
    k = max(int(p * m_max), 1)
    ymax = total[-1]
    x0, x1, y0, y1 = visuals.MARGIN, W - visuals.MARGIN, CHART_TOP + 60, CHART_BOTTOM

    def pt(series, m):
        return (x0 + (x1 - x0) * m / m_max, y1 - (y1 - y0) * series[m] / ymax)

    region = (0, CHART_TOP, W, CHART_BOTTOM + 10)
    layer = Image.new("RGBA", (W, region[3] - region[1]), (0, 0, 0, 0))
    poly = [(x0, y1)] + [pt(total, m) for m in range(k + 1)] + [(pt(total, k)[0], y1)]
    ImageDraw.Draw(layer).polygon([(x, y - CHART_TOP) for x, y in poly], fill=accent + (70,))
    img.paste(layer, (0, CHART_TOP), layer)
    dr = ImageDraw.Draw(img)
    dr.line([(x0, y1), (x1, y1)], fill=(255, 255, 255), width=3)
    dr.line([pt(invested, m) for m in range(k + 1)], fill=(255, 255, 255), width=7, joint="curve")
    dr.line([pt(total, m) for m in range(k + 1)], fill=accent, width=10, joint="curve")
    ex, ey = pt(total, k)
    dr.ellipse([ex - 14, ey - 14, ex + 14, ey + 14], fill=accent)
    lf = visuals.font(44)
    pre = d.get("prefix", "")
    dr.text((x0, CHART_TOP - 30), f"■ Total com juros  {fmt(total[k], pre)}", font=lf, fill=accent)
    dr.text((x0, CHART_TOP + 20), f"■ Você investiu  {fmt(invested[k], pre)}", font=lf, fill=(255, 255, 255))
    sf = visuals.font(36)
    dr.text((x0, y1 + 14), "0", font=sf, fill=(220, 220, 220))
    end = f"{m_max // 12} anos"
    dr.text((x1 - sf.getlength(end), y1 + 14), end, font=sf, fill=(220, 220, 220))


MIN_GAP = 124  # distância mínima entre eventos da linha do tempo (px)


def _year(y: int) -> str:
    return f"{abs(int(y))} a.C." if y < 0 else f"{int(y)}"


def year_gap(a: int, b: int) -> int:
    """Anos entre dois anos do calendário (não existe ano zero: de 69 a.C. a 1969 são 2037 anos)."""
    return abs(b - a) - (1 if (a < 0) != (b < 0) else 0)


def timeline_positions(years: list[int], top: float, bottom: float, even: bool = False) -> list[float]:
    """Posição vertical de cada evento: proporcional ao tempo real (ou uniforme), com espaçamento mínimo."""
    n = len(years)
    lo, hi = min(years), max(years)
    if even or hi == lo or n == 1:
        pos = [top + (bottom - top) * i / max(n - 1, 1) for i in range(n)]
    else:
        pos = [top + (bottom - top) * (y - lo) / (hi - lo) for y in years]
    for i in range(1, n):
        pos[i] = max(pos[i], pos[i - 1] + MIN_GAP)
    if pos[-1] > bottom:  # estourou a área: comprime mantendo a ordem
        pos = [top + (p - top) * (bottom - top) / (pos[-1] - top) for p in pos]
    return pos


def _timeline(img, d, p, accent, t):
    ev = d["events"]
    n = len(ev)
    years = [e["year"] for e in ev]
    pos = timeline_positions(years, CHART_TOP - 50, CHART_BOTTOM - 80, d.get("scale") == "even")
    xl = 380
    dr = ImageDraw.Draw(img)
    yf, gf = visuals.font(66), visuals.font(48)
    room = W - 50 - (xl + 52)  # largura disponível para o rótulo, à direita da linha
    lf = visuals.font(46)
    longest = max(ev, key=lambda e: len(e["label"]))["label"]
    while lf.getlength(longest) > room and lf.size > 30:
        lf = visuals.font(lf.size - 2)
    starts = [i / n * 0.85 for i in range(n)]
    for i in range(1, n):  # segmento da linha crescendo até o próximo evento
        m = ease((p - starts[i] + 0.12) / 0.2)
        if m > 0:
            y2 = pos[i - 1] + (pos[i] - pos[i - 1]) * m
            dr.line([(xl, pos[i - 1]), (xl, y2)], fill=accent, width=8)
    for i, e in enumerate(ev):
        q = ease((p - starts[i]) / 0.15)
        if q <= 0:
            continue
        y = pos[i]
        r = 20 * q
        dr.ellipse([xl - r, y - r, xl + r, y + r], fill=(255, 255, 255), outline=accent, width=7)
        off = (1 - q) * 40
        dr.text((xl + 52 + off, y - 44), _year(e["year"]), font=yf, fill=accent, stroke_width=3, stroke_fill=(0, 0, 0))
        dr.text((xl + 52 + off, y + 28), e["label"], font=lf, fill=(255, 255, 255), stroke_width=3, stroke_fill=(0, 0, 0))
        if d.get("gaps", True) and i > 0:
            g = ease((p - starts[i] - 0.08) / 0.2)
            if g > 0:
                val = year_gap(years[i - 1], years[i]) * g
                txt = fmt(val, suffix=" anos")
                mid = (pos[i - 1] + pos[i]) / 2
                dr.line([(xl - 34, pos[i - 1] + 26), (xl - 34, pos[i] - 26)], fill=accent, width=4)
                dr.text((xl - 54 - gf.getlength(txt), mid - 23), txt, font=gf, fill=accent, stroke_width=3, stroke_fill=(0, 0, 0))


def _list(img, d, p, accent, t):
    """Itens que entram um a um, cada um com marcador de 'check' (até 5 itens)."""
    items = d["items"][:5]
    n = len(items)
    f = visuals.font(54)
    layer = Image.new("RGBA", (W, CHART_BOTTOM - CHART_TOP + 80), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    step = min(112, (CHART_BOTTOM - CHART_TOP + 40) // max(n, 1))
    for i, text in enumerate(items):
        q = ease((p - i / n * 0.8) / 0.18)
        if q <= 0:
            continue
        y = 10 + i * step
        x = visuals.MARGIN + (1 - q) * 120
        ld.rounded_rectangle([x, y, W - visuals.MARGIN, y + step - 18], 22, fill=(0, 0, 0, int(120 * q)))
        cx, cy, r = x + 46, y + (step - 18) / 2, 24 * q
        ld.ellipse([cx - r, cy - r, cx + r, cy + r], fill=accent + (255,))
        ld.line([(cx - 11, cy + 1), (cx - 3, cy + 10), (cx + 12, cy - 9)], fill=(10, 10, 10, int(255 * q)), width=6, joint="curve")
        ld.text((x + 92, cy - 34), text, font=f, fill=(255, 255, 255, int(255 * q)), stroke_width=2, stroke_fill=(0, 0, 0, int(255 * q)))
    img.paste(layer, (0, CHART_TOP - 30), layer)


KINDS = {"counter": _counter, "bars": _bars, "growth": _growth, "timeline": _timeline, "list": _list}


def frames(scene: Scene, niche: str, dur: float, seed: str = "") -> Iterator[Image.Image]:
    """Gera os quadros (RGB 1080x1920) de uma cena animada. A animação termina em ~70% da cena."""
    accent = THEMES.get(niche, THEMES["default"])[2]
    circles = _circles(seed or scene.text or niche)
    chart = scene.kind in KINDS
    if chart:
        ov = visuals.overlay(scene.text, niche, max_lines=2, y0=430, size=96)
    else:
        ov = visuals.overlay(scene.text, niche, max_lines=4, y0=760, size=130)
    a_ov = ov.getchannel("A")
    n = int(dur * FPS) + 1
    for i in range(n):
        t = i / FPS
        img = _bokeh_bg(niche, t, circles)
        if chart:
            KINDS[scene.kind](img, scene.data, ease(t / max(dur * 0.7, 0.6)), accent, t)
        if t < 0.35:  # título entra subindo e aparecendo; depois é colado direto
            e = ease(t / 0.35)
            layer = ov.copy()
            layer.putalpha(a_ov.point(lambda a, e=e: int(a * e)))
            img.paste(layer, (0, int((1 - e) * 40)), layer)
        else:
            img.paste(ov, (0, 0), ov)
        yield img
