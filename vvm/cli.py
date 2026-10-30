import argparse
import os
import sys
from pathlib import Path

from . import render, research, script, tts


def _load_env() -> None:
    env = Path(".env")
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def main(argv=None) -> int:
    _load_env()
    ap = argparse.ArgumentParser(prog="vvm")
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("research", help="mapeia vídeos/canais que mais performam (YouTube Data API)")
    r.add_argument("--niche", choices=sorted(research.NICHES), action="append",
                   help="repita para vários; padrão: todos")
    r.add_argument("--days", type=int, default=30)
    r.add_argument("--max-seconds", type=int, default=70)
    r.add_argument("--out", default="data/research")

    v = sub.add_parser("render", help="gera o vídeo a partir de um roteiro JSON")
    v.add_argument("script", type=Path)
    v.add_argument("--out", default="output")
    v.add_argument("--provider", choices=["edge", "espeak"], default="edge")
    v.add_argument("--voice", default=tts.DEFAULT_VOICE)
    v.add_argument("--rate", default="+8%")
    v.add_argument("--assets", type=Path, default=Path("assets"))
    v.add_argument("--no-fetch", action="store_true", help="não buscar imagens na Commons")

    i = sub.add_parser("images", help="pré-busca (e mostra) as imagens e créditos de um roteiro")
    i.add_argument("script", type=Path)
    i.add_argument("--assets", type=Path, default=Path("assets"))

    a = ap.parse_args(argv)
    if a.cmd == "research":
        key = os.environ.get("YOUTUBE_API_KEY")
        if not key:
            sys.exit("Defina YOUTUBE_API_KEY (veja .env.example).")
        paths = research.run(key, a.niche or sorted(research.NICHES), a.days, a.max_seconds, Path(a.out))
        print("Relatório:", paths["report"])
    elif a.cmd == "images":
        sc = script.load(a.script)
        for n, s in enumerate(sc.scenes, 1):
            if s.image or s.image_query:
                path, credit = render.resolve_image(s, a.assets)
                print(f"cena {n}: {'OK ' + str(path) if path else 'SEM IMAGEM'}  {credit}")
    else:
        sc = script.load(a.script)
        res = render.build(sc, Path(a.out) / sc.slug, a.provider, a.voice, a.rate, a.assets, not a.no_fetch)
        print(f"Vídeo: {res['video']}  ({res['duration']:.1f}s)\nLegenda/descrição: {res['meta']}")
        if not res["in_target"]:
            lo, hi = render.TARGET
            print(f"AVISO: duração fora da meta de {lo}–{hi}s; ajuste a narração.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
