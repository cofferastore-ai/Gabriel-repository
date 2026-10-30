"""Monta o vídeo final com ffmpeg: cenas (foto/animação) + voz + legendas + música opcional."""
import hashlib
import subprocess
from pathlib import Path

from . import animate, captions, images, tts, visuals
from .script import ANIMATED, Scene, Script

FPS = 30
PAD = 0.25  # respiro ao fim de cada cena
TARGET = (75, 105)  # janela de duração desejada, em segundos


def _run(cmd: list[str], cwd: Path | None = None) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    if r.returncode:
        raise RuntimeError(f"ffmpeg falhou:\n{' '.join(cmd)}\n{r.stderr[-1500:]}")


def _kenburns(idx: int, frames: int) -> str:
    """Quatro movimentos de câmera em rodízio: zoom in, zoom out, pan →, pan ←."""
    pan = f"(iw-iw/zoom)*on/{frames}"
    return [
        "z='min(zoom+0.0007,1.18)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
        "z='if(eq(on,0),1.18,max(zoom-0.0007,1.0))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
        f"z=1.15:x='{pan}':y='ih/2-(ih/zoom/2)'",
        f"z=1.15:x='(iw-iw/zoom)-{pan}':y='ih/2-(ih/zoom/2)'",
    ][idx % 4]


def _still_clip(bg: Path, ov: Path, audio: Path, dur: float, idx: int, out: Path) -> None:
    """Fundo com movimento de câmera; o título (overlay) fica parado e entra com fade."""
    frames = int(dur * FPS) + 1
    fc = (f"[0:v]zoompan={_kenburns(idx, frames)}:d={frames}:s=1080x1920:fps={FPS}[bg];"
          f"[2:v]format=rgba,fade=in:st=0:d=0.35:alpha=1[ov];[bg][ov]overlay=0:0,format=yuv420p[v]")
    _run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(bg), "-i", str(audio),
          "-loop", "1", "-i", str(ov), "-filter_complex", fc, "-map", "[v]", "-map", "1:a",
          "-af", f"apad=pad_dur={PAD},aresample=44100", "-ac", "2", "-t", f"{dur:.3f}",
          "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", "-b:a", "160k", str(out)])


def _anim_clip(scene: Scene, niche: str, audio: Path, dur: float, seed: str, out: Path) -> None:
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "1080x1920",
           "-r", str(FPS), "-i", "-", "-i", str(audio), "-af", f"apad=pad_dur={PAD},aresample=44100",
           "-ac", "2", "-t", f"{dur:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", str(out)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        for frame in animate.frames(scene, niche, dur, seed):
            p.stdin.write(frame.tobytes())
        p.stdin.close()
    except BrokenPipeError:
        pass
    err = p.stderr.read().decode(errors="replace")
    if p.wait():
        raise RuntimeError(f"ffmpeg falhou na cena animada:\n{err[-1500:]}")


def _pick_music(music_dir: Path, seed: str) -> Path | None:
    files = sorted(p for p in music_dir.glob("*") if p.suffix.lower() in {".mp3", ".wav", ".m4a", ".ogg"})
    if not files:
        return None
    return files[int(hashlib.md5(seed.encode()).hexdigest(), 16) % len(files)]


def resolve_image(sc: Scene, assets: Path, fetch: bool = True) -> tuple[Path | None, str]:
    """Foto da cena: arquivo local (prioridade) ou busca na Commons. Devolve (caminho, crédito)."""
    if sc.image:
        p = assets / "images" / sc.image
        return (p, "") if p.exists() else (None, "")
    if sc.image_query and fetch:
        got = images.fetch(sc.image_query, assets / "images" / "cache")
        if got:
            return got
    return None, ""


def build(script: Script, out_dir: Path, provider: str = "edge", voice: str = tts.DEFAULT_VOICE,
          rate: str = "+8%", assets: Path = Path("assets"), fetch_images: bool = True) -> dict:
    work = out_dir / "work"
    work.mkdir(parents=True, exist_ok=True)
    clips, timeline, credits, t0 = [], [], [], 0.0
    for i, sc in enumerate(script.scenes):
        print(f"  cena {i + 1}/{len(script.scenes)} ({sc.kind or ('foto' if sc.image or sc.image_query else 'texto')})")
        audio = work / f"s{i:02d}.{'mp3' if provider == 'edge' else 'wav'}"
        words = tts.synthesize(sc.narration, audio, provider, voice, rate)
        dur = tts.audio_duration(audio) + PAD
        words = words or captions.estimate_words(sc.narration, dur - PAD)
        clip = work / f"s{i:02d}.mp4"
        photo, credit = (None, "") if sc.kind in ANIMATED else resolve_image(sc, assets, fetch_images)
        if photo:
            bg = work / f"s{i:02d}_bg.jpg"
            visuals.background(script.niche, photo, scale=1.5).save(bg, quality=93)
            ov = work / f"s{i:02d}_ov.png"
            visuals.overlay(sc.text, script.niche).save(ov)
            _still_clip(bg, ov, audio, dur, i, clip)
            if credit:
                credits.append(credit)
        else:
            _anim_clip(sc, script.niche, audio, dur, f"{script.slug}{i}", clip)
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
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(joined.resolve())]
    if music:
        cmd += ["-stream_loop", "-1", "-i", str(music.resolve()), "-filter_complex",
                f"[0:v]ass={ass.name}[v];[1:a]volume=0.08[m];[0:a][m]amix=inputs=2:duration=first:normalize=0[a]",
                "-map", "[v]", "-map", "[a]"]
    else:
        cmd += ["-vf", f"ass={ass.name}"]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "160k",
            "-movflags", "+faststart", "-shortest", str(final.resolve())]
    _run(cmd, cwd=work)

    meta = out_dir / f"{script.slug}.txt"
    body = f"{script.title}\n\n{script.description}\n\n{' '.join('#' + t for t in script.tags)}\n"
    if script.disclaimer:
        body += f"\n{script.disclaimer}\n"
    if credits:
        body += "\nImagens:\n" + "\n".join(f"- {c}" for c in dict.fromkeys(credits)) + "\n"
    meta.write_text(body, encoding="utf-8")
    return {"video": final, "duration": t0, "meta": meta, "music": music,
            "in_target": TARGET[0] <= t0 <= TARGET[1]}
