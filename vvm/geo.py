"""Geometria dos países (TopoJSON -> polígonos em projeção Mercator normalizada)."""
import json
import math
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "assets" / "data" / "countries-50m.json"
MAX_LAT = 85.0
SKIP = {"Antarctica"}


def mercator(lon: float, lat: float) -> tuple[float, float]:
    """(lon, lat) em graus -> (x, y) em 0..1 (x: oeste->leste, y: norte->sul)."""
    lat = max(-MAX_LAT, min(MAX_LAT, lat))
    return ((lon + 180) / 360,
            0.5 - math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)) / (2 * math.pi))


def _decode_arcs(topo: dict) -> list[list[tuple[float, float]]]:
    sx, sy = topo["transform"]["scale"]
    tx, ty = topo["transform"]["translate"]
    arcs = []
    for arc in topo["arcs"]:
        x = y = 0
        pts = []
        for dx, dy in arc:
            x += dx
            y += dy
            pts.append((x * sx + tx, y * sy + ty))
        arcs.append(pts)
    return arcs


def _ring(indices: list[int], arcs) -> list[tuple[float, float]]:
    pts: list[tuple[float, float]] = []
    for i in indices:
        seg = arcs[i] if i >= 0 else arcs[~i][::-1]
        pts.extend(seg if not pts else seg[1:])
    return pts


def _unwrap(ring: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Desfaz saltos na linha de data (x de ~0 para ~1): o anel fica contínuo, podendo passar de [0, 1]."""
    out, shift, prev = [], 0.0, None
    for x, y in ring:
        if prev is not None:
            if x - prev > 0.5:
                shift -= 1.0
            elif x - prev < -0.5:
                shift += 1.0
        prev = x
        out.append((x + shift, y))
    return out


@lru_cache(maxsize=1)
def countries() -> dict[str, list[list[list[tuple[float, float]]]]]:
    """nome -> lista de polígonos; cada polígono = lista de anéis; anel = pontos Mercator (x, y)."""
    topo = json.loads(DATA.read_text(encoding="utf-8"))
    arcs = _decode_arcs(topo)
    out: dict[str, list] = {}
    for g in topo["objects"]["countries"]["geometries"]:
        name = (g.get("properties") or {}).get("name", "")
        if name in SKIP or g["type"] not in ("Polygon", "MultiPolygon"):
            continue
        polys = g["arcs"] if g["type"] == "MultiPolygon" else [g["arcs"]]
        out.setdefault(name, []).extend(
            [_unwrap([mercator(lon, lat) for lon, lat in _ring(r, arcs)]) for r in poly] for poly in polys)
    return out
