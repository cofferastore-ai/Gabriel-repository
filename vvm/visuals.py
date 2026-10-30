"""Quadros verticais 1080x1920 gerados localmente (sem custo de API)."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

from .script import THEMES

SIZE = (1080, 1920)
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]


def _font(size: int) -> ImageFont.FreeTypeFont:
    for p in FONT_CANDIDATES:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def _wrap(text: str, font: ImageFont.FreeTypeFont, max_px: int) -> list[str]:
    """Quebra por largura real em pixels (evita estourar a tela)."""
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if cur and font.getlength(trial) > max_px:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    return lines + ([cur] if cur else [])


def _gradient(top, bottom) -> Image.Image:
    w, h = SIZE
    img = Image.new("RGB", SIZE)
    px = ImageDraw.Draw(img)
    for y in range(h):
        t = y / (h - 1)
        px.line([(0, y), (w, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(top, bottom)))
    return img


def _cover(path: Path) -> Image.Image:
    img = Image.open(path).convert("RGB")
    w, h = SIZE
    scale = max(w / img.width, h / img.height)
    img = img.resize((int(img.width * scale) + 1, int(img.height * scale) + 1), Image.LANCZOS)
    left, top = (img.width - w) // 2, (img.height - h) // 2
    img = img.crop((left, top, left + w, top + h))
    return Image.blend(img, Image.new("RGB", SIZE, (0, 0, 0)), 0.45)


def render_frame(text: str, niche: str, out: Path, image: Path | None = None) -> Path:
    top, bottom, accent = THEMES.get(niche, THEMES["default"])
    img = _cover(image) if image and image.exists() else _gradient(top, bottom)
    draw = ImageDraw.Draw(img)
    # faixa de destaque + texto-chave no terço superior (a legenda fica embaixo)
    draw.rectangle([90, 380, 190, 392], fill=accent)
    if text:
        font = _font(118)
        max_px = SIZE[0] - 2 * 90
        lines = _wrap(text.upper(), font, max_px)
        while (len(lines) > 4 or any(font.getlength(l) > max_px for l in lines)) and font.size > 60:
            font = _font(font.size - 8)  # palavra única muito longa: reduz a fonte
            lines = _wrap(text.upper(), font, max_px)
        lines = lines[:4]
        y = 430
        shadow = Image.new("RGBA", SIZE, (0, 0, 0, 0))
        sd = ImageDraw.Draw(shadow)
        for ln in lines:
            sd.text((94, y + 6), ln, font=font, fill=(0, 0, 0, 200))
            y += 140
        img = Image.alpha_composite(img.convert("RGBA"), shadow.filter(ImageFilter.GaussianBlur(6))).convert("RGB")
        draw = ImageDraw.Draw(img)
        y = 430
        for ln in lines:
            draw.text((90, y), ln, font=font, fill=(255, 255, 255))
            y += 140
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, quality=92)
    return out
