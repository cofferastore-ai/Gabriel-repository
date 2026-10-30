"""Áudio sintetizado localmente (sem downloads): trilha ambiente por nicho e efeito de transição."""
import subprocess
from pathlib import Path

# acordes (Hz): história = lá menor aberto e grave; finanças = dó maior com 9ª, mais leve
CHORDS = {
    "historia": [110.0, 164.81, 220.0, 261.63, 329.63],
    "financas": [130.81, 196.0, 261.63, 329.63, 392.0, 587.33],
    "default": [110.0, 164.81, 220.0, 277.18],
}


def _ffmpeg(args: list[str]) -> None:
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"ffmpeg falhou ao gerar áudio:\n{r.stderr[-800:]}")


def ambient(niche: str, duration: float, out: Path) -> Path:
    """Pad de acordes com leve desafinação (efeito coral), respiração lenta e eco: fundo discreto e contínuo."""
    freqs = CHORDS.get(niche, CHORDS["default"])
    voices = []
    for i, f in enumerate(freqs):
        amp = 0.30 / (1 + 0.35 * i)
        voices.append(f"{amp:.3f}*sin(2*PI*{f}*t)+{amp * 0.7:.3f}*sin(2*PI*{f + 0.35 + 0.1 * i:.2f}*t)")
    expr = f"({'+'.join(voices)})*(0.72+0.28*sin(2*PI*0.09*t))"
    out.parent.mkdir(parents=True, exist_ok=True)
    _ffmpeg(["-f", "lavfi", "-i", f"aevalsrc='{expr}':s=44100:d={duration:.2f}",
             "-af", "lowpass=f=1400,aecho=0.8:0.75:70|140:0.45|0.3,afade=t=in:d=2,"
                    f"afade=t=out:st={max(duration - 3, 0):.2f}:d=3,volume=1.4",
             "-ac", "2", str(out)])
    return out


def whoosh(out: Path) -> Path:
    """Passagem de ar curta para marcar o corte entre cenas."""
    out.parent.mkdir(parents=True, exist_ok=True)
    _ffmpeg(["-f", "lavfi", "-i", "anoisesrc=d=0.8:c=pink:a=0.9:r=44100",
             "-af", "highpass=f=250,lowpass=f=5500,afade=t=in:d=0.3,afade=t=out:st=0.28:d=0.5,"
                    "tremolo=f=9:d=0.35,volume=3.2", "-ac", "2", str(out)])
    return out
