"""Cena de mapa animado: câmera com zoom, países destacados, marcadores e rotas.

data = {
  "from": {"lon": -20, "lat": 30, "span": 120},   # visão inicial (span = largura visível em graus de longitude)
  "to":   {"lon": -45, "lat": -10, "span": 60},   # visão final (a câmera interpola entre as duas)
  "highlight": ["Brazil", "Portugal"],            # nomes em inglês (world-atlas)
  "points": [{"name": "Lisboa", "lon": -9.1, "lat": 38.7, "at": 0.1, "side": "right", "dot": true}],
  "routes": [{"from": [-9.1, 38.7], "to": [-43.2, -22.9], "at": 0.3, "label": "1807", "curve": 0.2}]
}
`at` = momento (0..1) da animação em que o elemento aparece. Limite prático de zoom: 3x entre `from` e `to`.
"""
import math
from typing import Iterator

from PIL import Image, ImageDraw

from . import geo, visuals
from .animate import FPS, W, H, ease
from .script import THEMES, Scene

MAX_W, MAX_H = 3600, 6400
SUPERSAMPLE = 1.4


def _view(v: dict) -> tuple[float, float, float, float]:
    """(centro x, centro y, largura, altura) em unidades Mercator normalizadas."""
    cx, cy = geo.mercator(v["lon"], v["lat"])
    w = v["span"] / 360
    return cx, cy, w, w * H / W


def _palette(niche: str):
    top, bottom, accent = THEMES.get(niche, THEMES["default"])
    ocean = tuple(int(c * 0.9) for c in top)
    land = tuple(min(255, int(c * 1.15 + 14)) for c in bottom)
    border = tuple(int(c * 0.45 + o * 0.55) for c, o in zip(accent, land))
    high = tuple(int(a * 0.42 + l * 0.58) for a, l in zip(accent, land))
    return ocean, land, border, high, accent


def build_base(data: dict, niche: str) -> tuple[Image.Image, tuple[float, float], float]:
    """Mapa-base em alta resolução cobrindo a união das duas visões. Devolve (imagem, origem, px por unidade)."""
    a, b = _view(data["from"]), _view(data["to"])
    x0 = min(a[0] - a[2] / 2, b[0] - b[2] / 2)
    x1 = max(a[0] + a[2] / 2, b[0] + b[2] / 2)
    y0 = min(a[1] - a[3] / 2, b[1] - b[3] / 2)
    y1 = max(a[1] + a[3] / 2, b[1] + b[3] / 2)
    ppu = min(SUPERSAMPLE * W / min(a[2], b[2]), MAX_W / (x1 - x0), MAX_H / (y1 - y0))
    size = (int((x1 - x0) * ppu) + 1, int((y1 - y0) * ppu) + 1)
    ocean, land, border, high, _ = _palette(niche)
    img = visuals.gradient(tuple(int(c * 0.8) for c in ocean), ocean, size)
    d = ImageDraw.Draw(img)

    def px(p):
        return ((p[0] - x0) * ppu, (p[1] - y0) * ppu)

    # grade de lat/lon discreta
    grid = tuple(int(o * 0.75 + l * 0.25) for o, l in zip(ocean, land))
    for lon in range(-180, 181, 15):
        gx = px(geo.mercator(lon, 0))[0]
        d.line([(gx, 0), (gx, size[1])], fill=grid, width=2)
    for lat in range(-75, 76, 15):
        gy = px(geo.mercator(0, lat))[1]
        d.line([(0, gy), (size[0], gy)], fill=grid, width=2)

    highlight = set(data.get("highlight", []))
    lw = max(1, round(ppu / 1800))
    for name, polys in geo.countries().items():
        fill = high if name in highlight else land
        for poly in polys:
            xs = [p[0] for p in poly[0]]
            ys = [p[1] for p in poly[0]]
            if max(ys) < y0 or min(ys) > y1:
                continue
            for off in (-1.0, 0.0, 1.0):  # cópias deslocadas: visões que cruzam a linha de data
                if max(xs) + off < x0 or min(xs) + off > x1:
                    continue
                d.polygon([px((p[0] + off, p[1])) for p in poly[0]], fill=fill)
                for hole in poly[1:]:
                    d.polygon([px((p[0] + off, p[1])) for p in hole], fill=ocean)
                d.line([px((p[0] + off, p[1])) for p in poly[0]], fill=border,
                       width=lw + (1 if name in highlight else 0))
    return img, (x0, y0), ppu


def _shade_mask() -> Image.Image:
    col = Image.new("L", (1, H))
    col.putdata([int(255 * (0.80 * max(0, (560 - y) / 560) + 0.78 * max(0, (y - 1180) / 740))) for y in range(H)])
    return col.resize((W, H))


def _bezier(p0, p1, curve: float, n: int = 70):
    mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    c = (mx - dy * curve, my + dx * curve)
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * c[0] + t * t * p1[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * c[1] + t * t * p1[1]) for t in (i / n for i in range(n + 1))]


def _label(d: ImageDraw.ImageDraw, xy, text: str, size: int, fill, side: str = "right") -> None:
    f = visuals.font(size)
    x, y = xy
    tw = f.getlength(text)
    x = x + 26 if side == "right" else x - 26 - tw if side == "left" else x - tw / 2
    x = max(40, min(x, W - 40 - tw))
    d.text((x, y - size * 0.6), text, font=f, fill=fill, stroke_width=5, stroke_fill=(0, 0, 0))


def frames(scene: Scene, niche: str, dur: float, seed: str = "") -> Iterator[Image.Image]:
    data = scene.data
    base, (bx0, by0), ppu = build_base(data, niche)
    accent = _palette(niche)[4]
    a, b = _view(data["from"]), _view(data["to"])
    shade, black = _shade_mask(), Image.new("RGB", (W, H), (0, 0, 0))
    ov = visuals.overlay(scene.text, niche, max_lines=2, y0=190, size=96)
    points, routes = data.get("points", []), data.get("routes", [])
    n = int(dur * FPS) + 1
    anim = max(dur * 0.85, 1.0)
    for i in range(n):
        t = i / FPS
        x = min(t / max(dur - 0.2, 0.5), 1.0)
        pc = x * x * (3 - 2 * x)  # câmera: entra e sai suave
        w = math.exp(math.log(a[2]) * (1 - pc) + math.log(b[2]) * pc)
        h = w * H / W
        cx, cy = a[0] + (b[0] - a[0]) * pc, a[1] + (b[1] - a[1]) * pc
        l, tp = (cx - w / 2 - bx0) * ppu, (cy - h / 2 - by0) * ppu
        l, tp = max(0.0, l), max(0.0, tp)  # arredondamento pode dar -1e-13 na borda do mapa-base
        box = (l, tp, min(l + w * ppu, base.width), min(tp + h * ppu, base.height))
        img = base.resize((W, H), Image.BILINEAR, box=box)
        img.paste(black, mask=shade)

        def scr(lon, lat):
            mx, my = geo.mercator(lon, lat)
            return ((mx - (cx - w / 2)) / w * W, (my - (cy - h / 2)) / h * H)

        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        prog = min(t / anim, 1.0)
        for r in routes:
            q = ease((prog - r.get("at", 0.2)) / 0.4)
            if q <= 0:
                continue
            path = _bezier(scr(*r["from"]), scr(*r["to"]), r.get("curve", 0.2))
            k = max(int(q * (len(path) - 1)), 1)
            ld.line(path[:k + 1], fill=accent + (70,), width=26, joint="curve")
            ld.line(path[:k + 1], fill=accent + (255,), width=9, joint="curve")
            tx, ty = path[k]
            ld.ellipse([tx - 17, ty - 17, tx + 17, ty + 17], fill=(255, 255, 255, 255), outline=accent + (255,), width=6)
            if r.get("label") and q > 0.85:
                mx, my = path[len(path) // 2]
                _label(ld, (mx, my - 36), r["label"], 52, (255, 255, 255, 255), "center")
        for p in points:
            q = ease((prog - p.get("at", 0.0)) / 0.12)
            if q <= 0:
                continue
            px_, py_ = scr(p["lon"], p["lat"])
            if p.get("dot", True):
                pulse = (t * 0.9 + p["lon"]) % 1.0
                rr = 16 + 46 * pulse
                ld.ellipse([px_ - rr, py_ - rr, px_ + rr, py_ + rr], outline=accent + (int(200 * (1 - pulse) * q),), width=5)
                rd = 15 * q
                ld.ellipse([px_ - rd, py_ - rd, px_ + rd, py_ + rd], fill=(255, 255, 255, 255), outline=accent + (255,), width=5)
            if p.get("name"):
                _label(ld, (px_, py_), p["name"], 50, (255, 255, 255, int(255 * q)), p.get("side", "right"))
        img = Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")
        if t < 0.35:
            e = ease(t / 0.35)
            tl = ov.copy()
            tl.putalpha(ov.getchannel("A").point(lambda v, e=e: int(v * e)))
            img.paste(tl, (0, int((1 - e) * 40)), tl)
        else:
            img.paste(ov, (0, 0), ov)
        yield img
