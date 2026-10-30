"""Síntese de voz. Provedores: edge (gratuito, pt-BR neural) e espeak (offline, só para testes)."""
import asyncio
import os
import re
import subprocess
import tarfile
import urllib.request
import wave
from pathlib import Path
from typing import NamedTuple

DEFAULT_VOICE = "pt-BR-AntonioNeural"  # alternativas: pt-BR-FranciscaNeural, pt-BR-ThalitaMultilingualNeural


class Word(NamedTuple):
    text: str
    start: float
    end: float


def audio_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout
    return float(out.strip())


async def _edge(text: str, out: Path, voice: str, rate: str) -> list[Word]:
    import edge_tts

    com = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    words: list[Word] = []
    with open(out, "wb") as f:
        async for chunk in com.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                start = chunk["offset"] / 1e7
                words.append(Word(chunk["text"], start, start + chunk["duration"] / 1e7))
    return words


PIPER_MODEL = "vits-piper-pt_BR-faber-medium"
PIPER_URL = f"https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/{PIPER_MODEL}.tar.bz2"
_piper = None


def _voices_dir() -> Path:
    return Path(os.environ.get("VVM_VOICES_DIR", Path.home() / ".cache" / "vvm" / "voices"))


def _piper_model_dir() -> Path:
    """Modelo neural pt-BR offline (Piper). Baixa do GitHub na primeira vez (~67 MB)."""
    d = _voices_dir() / PIPER_MODEL
    if not (d / "tokens.txt").exists():
        d.parent.mkdir(parents=True, exist_ok=True)
        archive = d.parent / f"{PIPER_MODEL}.tar.bz2"
        print(f"  [voz] baixando modelo {PIPER_MODEL} (uma vez só)...")
        urllib.request.urlretrieve(PIPER_URL, archive)
        with tarfile.open(archive) as tar:
            tar.extractall(d.parent, filter="data")
        archive.unlink()
    return d


def _piper_engine():
    global _piper
    if _piper is None:
        import sherpa_onnx  # pip install sherpa-onnx==1.12.40 (versões 2.x não leem este modelo)

        d = _piper_model_dir()
        vits = sherpa_onnx.OfflineTtsVitsModelConfig(
            model=str(d / "pt_BR-faber-medium.onnx"), tokens=str(d / "tokens.txt"),
            data_dir=str(d / "espeak-ng-data"))
        cfg = sherpa_onnx.OfflineTtsConfig(model=sherpa_onnx.OfflineTtsModelConfig(vits=vits, num_threads=4))
        _piper = sherpa_onnx.OfflineTts(cfg)
    return _piper


def _piper_speak(text: str, out: Path, rate: str) -> list[Word]:
    m = re.fullmatch(r"([+-]\d+)%", rate)
    speed = 1 + int(m.group(1)) / 100 if m else 1.0
    audio = _piper_engine().generate(text, sid=0, speed=speed)
    if not len(audio.samples):
        raise RuntimeError(f"voz não gerou áudio para: {text[:60]!r}")
    pcm = b"".join(int(max(-1.0, min(1.0, x)) * 32767).to_bytes(2, "little", signed=True) for x in audio.samples)
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(audio.sample_rate)
        w.writeframes(pcm)
    return []


def _espeak(text: str, out: Path) -> list[Word]:
    subprocess.run(["espeak-ng", "-v", "pt-br", "-s", "165", "-w", str(out), text], check=True)
    return []


def synthesize(text: str, out: Path, provider: str = "piper", voice: str = DEFAULT_VOICE,
               rate: str = "+8%") -> list[Word]:
    """Gera o áudio em `out` e devolve tempos por palavra (lista vazia se o provedor não informa)."""
    out.parent.mkdir(parents=True, exist_ok=True)
    if provider == "edge":
        return asyncio.run(_edge(text, out, voice, rate))
    if provider == "piper":
        return _piper_speak(text, out, rate)
    if provider == "espeak":
        return _espeak(text, out)
    raise ValueError(f"provedor de voz desconhecido: {provider}")
