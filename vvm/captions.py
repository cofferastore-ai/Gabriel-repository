"""Legendas estilo Shorts/TikTok: poucas palavras por vez, palavra ativa destacada (ASS)."""
from .tts import Word

WORDS_PER_CHUNK = 3
FONT = "DejaVu Sans"


def estimate_words(text: str, duration: float, lead: float = 0.05) -> list[Word]:
    """Distribui o tempo entre as palavras proporcionalmente ao tamanho (quando não há tempos reais)."""
    tokens = text.split()
    if not tokens:
        return []
    weights = [len(t) + 1 for t in tokens]
    total = sum(weights)
    span = max(duration - lead, 0.1)
    t, words = lead, []
    for tok, w in zip(tokens, weights):
        d = span * w / total
        words.append(Word(tok, t, t + d))
        t += d
    return words


def _ts(sec: float) -> str:
    cs = int(round(sec * 100))
    h, rem = divmod(cs, 360000)
    m, rem = divmod(rem, 6000)
    s, c = divmod(rem, 100)
    return f"{h}:{m:02d}:{s:02d}.{c:02d}"


def build_ass(timeline: list[tuple[float, float, list[Word]]], size=(1080, 1920)) -> str:
    """timeline: (início da cena, duração da cena, palavras da cena com tempos relativos à cena)."""
    w, h = size
    header = (
        "[Script Info]\nScriptType: v4.00+\n"
        f"PlayResX: {w}\nPlayResY: {h}\nWrapStyle: 2\n\n"
        "[V4+ Styles]\n"
        "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,"
        "Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,"
        "MarginV,Encoding\n"
        f"Style: Cap,{FONT},84,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,7,2,2,60,60,520,1\n\n"
        "[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n"
    )
    lines = []
    for scene_start, scene_dur, words in timeline:
        for c0 in range(0, len(words), WORDS_PER_CHUNK):
            chunk = words[c0:c0 + WORDS_PER_CHUNK]
            for i, active in enumerate(chunk):
                start = scene_start + active.start
                nxt = chunk[i + 1].start if i + 1 < len(chunk) else active.end
                end = scene_start + max(nxt, active.start + 0.08)
                end = min(end, scene_start + scene_dur)
                parts = []
                for j, wd in enumerate(chunk):
                    txt = wd.text.upper().replace("{", "(").replace("}", ")")
                    parts.append(r"{\c&H00D7FF&}" + txt + r"{\c&HFFFFFF&}" if j == i else txt)
                lines.append(f"Dialogue: 0,{_ts(start)},{_ts(end)},Cap,,0,0,0,,{' '.join(parts)}")
    return header + "\n".join(lines) + "\n"
