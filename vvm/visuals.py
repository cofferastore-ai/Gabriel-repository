"""Peças visuais 1080x1920 geradas localmente: fundos, fotos escurecidas e títulos."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .script import THEMES

SIZE = (1080, 1920)
MARGIN = 90
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]


def font(size: int) -> ImageFont.FreeTypeFont:
    for p in FONT_CANDIDATES:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def wrap(text: str, f: ImageFont.FreeTypeFont, max_px: int) -> list[str]:
    """Quebra por largura real em pixels (evita estourar a tela)."""
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if cur and f.getlength(trial) > max_px:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    return lines + ([cur] if cur else [])


def fit(text: str, size: int, max_px: int, max_lines: int, min_size: int = 56):
    """Maior fonte (até `size`) em que o texto cabe em `max_lines` linhas."""
    f = font(size)
    lines = wrap(text, f, max_px)
    while (len(lines) > max_lines or any(f.getlength(l) > max_px for l in lines)) and f.size > min_size:
        f = font(f.size - 6)
        lines = wrap(text, f, max_px)
    return f, lines[:max_lines]


def gradient(top, bottom, size=SIZE) -> Image.Image:
    w, h = size
    col = Image.new("RGB", (1, h))
    col.putdata([tuple(int(a + (b - a) * y / (h - 1)) for a, b in zip(top, bottom)) for y in range(h)])
    return col.resize((w, h))


def _cover(path: Path, size) -> Image.Image:
    img = Image.open(path).convert("RGB")
    w, h = size
    scale = max(w / img.width, h / img.height)
    img = img.resize((int(img.width * scale) + 1, int(img.height * scale) + 1), Image.LANCZOS)
    left, top = (img.width - w) // 2, (img.height - h) // 2
    return img.crop((left, top, left + w, top + h))


def _shade(img: Image.Image) -> Image.Image:
    """Escurece topo e base (onde ficam título e legenda) mantendo o centro da foto visível."""
    w, h = img.size
    col = Image.new("L", (1, h))
    col.putdata([int(255 * (0.30 + 0.40 * max(0, (0.45 - y / h) / 0.45) + 0.50 * max(0, (y / h - 0.55) / 0.45)))
                 for y in range(h)])
    return Image.composite(Image.new("RGB", (w, h), (0, 0, 0)), img, col.resize((w, h)))


def background(niche: str, image: Path | None = None, scale: float = 1.0) -> Image.Image:
    size = (int(SIZE[0] * scale), int(SIZE[1] * scale))
    if image and image.exists():
        return _shade(_cover(image, size))
    top, bottom, _ = THEMES.get(niche, THEMES["default"])
    return gradient(top, bottom, size)


def overlay(text: str, niche: str, max_lines: int = 3, y0: int = 430, size: int = 118) -> Image.Image:
    """Título com sombra sobre fundo transparente (aplicado sem sofrer o zoom da câmera)."""
    accent = THEMES.get(niche, THEMES["default"])[2]
    layer = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    ImageDraw.Draw(layer).rectangle([MARGIN, y0 - 50, MARGIN + 100, y0 - 38], fill=accent + (255,))
    if not text:
        return layer
    f, lines = fit(text.upper(), size, SIZE[0] - 2 * MARGIN, max_lines)
    step = int(f.size * 1.18)
    shadow = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    for i, ln in enumerate(lines):
        sd.text((MARGIN + 4, y0 + i * step + 6), ln, font=f, fill=(0, 0, 0, 210))
    layer = Image.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(6)), layer)
    d = ImageDraw.Draw(layer)
    for i, ln in enumerate(lines):
        d.text((MARGIN, y0 + i * step), ln, font=f, fill=(255, 255, 255, 255))
    return layer
