"""Monta o vídeo final com ffmpeg: Ken Burns por cena + voz + legendas + música opcional."""
import hashlib
import subprocess
from pathlib import Path

from . import captions, tts, visuals
from .script import Script

FPS = 30
PAD = 0.25  # respiro ao fim de cada cena


def _run(cmd: list[str]) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"ffmpeg falhou:\n{' '.join(cmd)}\n{r.stderr[-1500:]}")


def _scene_clip(frame: Path, audio: Path, dur: float, idx: int, out: Path) -> None:
    frames = int(dur * FPS) + 1
    # alterna zoom-in / zoom-out para dar movimento
    zoom = "min(zoom+0.0007,1.18)" if idx % 2 == 0 else "if(eq(on,0),1.18,max(zoom-0.0007,1.0))"
    vf = (f"scale=1620:2880,zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
          f":d={frames}:s=1080x1920:fps={FPS},format=yuv420p")
    _run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(frame), "-i", str(audio),
          "-vf", vf, "-af", f"apad=pad_dur={PAD},aresample=44100", "-ac", "2",
          "-t", f"{dur:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
          "-c:a", "aac", "-b:a", "160k", str(out)])


def _pick_music(music_dir: Path, seed: str) -> Path | None:
    files = sorted(p for p in music_dir.glob("*") if p.suffix.lower() in {".mp3", ".wav", ".m4a", ".ogg"})
    if not files:
        return None
    return files[int(hashlib.md5(seed.encode()).hexdigest(), 16) % len(files)]


def build(script: Script, out_dir: Path, provider: str = "edge", voice: str = tts.DEFAULT_VOICE,
          rate: str = "+8%", assets: Path = Path("assets")) -> dict:
    work = out_dir / "work"
    work.mkdir(parents=True, exist_ok=True)
    clips, timeline, t0 = [], [], 0.0
    for i, sc in enumerate(script.scenes):
        audio = work / f"s{i:02d}.{'mp3' if provider == 'edge' else 'wav'}"
        words = tts.synthesize(sc.narration, audio, provider, voice, rate)
        dur = tts.audio_duration(audio) + PAD
        words = words or captions.estimate_words(sc.narration, dur - PAD)
        img = assets / "images" / sc.image if sc.image else None
        frame = visuals.render_frame(sc.text, script.niche, work / f"s{i:02d}.png", img)
        clip = work / f"s{i:02d}.mp4"
        _scene_clip(frame, audio, dur, i, clip)
        clips.append(clip)
        timeline.append((t0, dur, words))
        t0 += dur

    ass = work / "captions.ass"
    ass.write_text(captions.build_ass(timeline), encoding="utf-8")
    concat = work / "list.txt"
    concat.write_text("".join(f"file '{c.resolve()}'\n" for c in clips), encoding="utf-8")
    joined = work / "joined.mp4"
    _run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(concat),
          "-c", "copy", str(joined)])

    final = out_dir / f"{script.slug}.mp4"
    music = _pick_music(assets / "music", script.slug)
    vf = f"ass={ass.name}"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(joined.resolve())]
    if music:
        cmd += ["-stream_loop", "-1", "-i", str(music.resolve()), "-filter_complex",
                f"[0:v]{vf}[v];[1:a]volume=0.08[m];[0:a][m]amix=inputs=2:duration=first:normalize=0[a]",
                "-map", "[v]", "-map", "[a]"]
    else:
        cmd += ["-vf", vf]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "160k",
            "-movflags", "+faststart", "-shortest", str(final.resolve())]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=work)
    if r.returncode:
        raise RuntimeError(f"ffmpeg falhou:\n{r.stderr[-1500:]}")
    meta = out_dir / f"{script.slug}.txt"
    meta.write_text(
        f"{script.title}\n\n{script.description}\n\n{' '.join('#' + t for t in script.tags)}\n"
        + (f"\n{script.disclaimer}\n" if script.disclaimer else ""), encoding="utf-8")
    return {"video": final, "duration": t0, "meta": meta, "music": music}
