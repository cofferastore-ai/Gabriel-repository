"""Síntese de voz. Provedores: edge (gratuito, pt-BR neural) e espeak (offline, só para testes)."""
import asyncio
import subprocess
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


def _espeak(text: str, out: Path) -> list[Word]:
    subprocess.run(["espeak-ng", "-v", "pt-br", "-s", "165", "-w", str(out), text], check=True)
    return []


def synthesize(text: str, out: Path, provider: str = "edge", voice: str = DEFAULT_VOICE,
               rate: str = "+8%") -> list[Word]:
    """Gera o áudio em `out` e devolve tempos por palavra (lista vazia se o provedor não informa)."""
    out.parent.mkdir(parents=True, exist_ok=True)
    if provider == "edge":
        return asyncio.run(_edge(text, out, voice, rate))
    if provider == "espeak":
        return _espeak(text, out)
    raise ValueError(f"provedor de voz desconhecido: {provider}")
