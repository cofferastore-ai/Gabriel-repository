"""Busca de imagens na Wikimedia Commons com licença segura para uso em vídeo.

Aceitas: domínio público, CC0 e CC BY (esta exige crédito, que vai para o .txt do vídeo).
Rejeitadas: NC, ND, SA, GFDL, "uso justo" e qualquer licença desconhecida.
"""
import hashlib
import html
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://commons.wikimedia.org/w/api.php"
UA = "ViralVideoMachine/0.1 (projeto educacional; github.com/cofferastore-ai/gabriel-repository)"
MIN_WIDTH = 900


def _license_rank(short: str) -> int | None:
    """0 = sem exigência de crédito; 1 = exige crédito; None = não usar."""
    s = (short or "").lower().replace("-", " ").strip()
    if re.search(r"\b(nc|nd|sa|gfdl|fair use|non free)\b", s):
        return None
    if "public domain" in s or s in {"pd", "cc0"} or s.startswith(("pd ", "cc0")):
        return 0
    if re.fullmatch(r"cc by( \d(\.\d)?)?( \w{2,3})?", s):
        return 1
    return None


def _clean(v: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", v or ""))).strip()


def pick(pages: dict, top: int = 10) -> dict | None:
    """Escolhe o melhor candidato da resposta da API: licença segura, tamanho mínimo, preferindo domínio público."""
    cands = []
    for idx, page in enumerate(sorted(pages.values(), key=lambda p: p.get("index", 0))[:top]):
        info = (page.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata", {})
        rank = _license_rank(meta.get("LicenseShortName", {}).get("value", ""))
        if rank is None or meta.get("NonFree", {}).get("value", "").lower() == "true":
            continue
        if info.get("mime") not in {"image/jpeg", "image/png"} or info.get("width", 0) < MIN_WIDTH:
            continue
        url = info.get("thumburl") or info.get("url")
        if not url:
            continue
        title = page["title"].removeprefix("File:")
        author = _clean(meta.get("Artist", {}).get("value", "")) or "autor desconhecido"
        lic = _clean(meta["LicenseShortName"]["value"])
        cands.append((rank, idx, {
            "url": url, "license": lic, "needs_credit": rank == 1,
            "credit": f"{title} — {author}, {lic}, via Wikimedia Commons",
        }))
    return min(cands, key=lambda c: c[:2])[2] if cands else None


def _search(query: str) -> dict:
    params = {"action": "query", "format": "json", "generator": "search", "gsrnamespace": 6,
              "gsrsearch": f"{query} filetype:bitmap", "gsrlimit": 15, "prop": "imageinfo",
              "iiprop": "url|mime|size|extmetadata", "iiurlwidth": 1600}
    req = urllib.request.Request(f"{API}?{urllib.parse.urlencode(params)}", headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r).get("query", {}).get("pages", {})


def fetch(query: str, cache_dir: Path) -> tuple[Path, str] | None:
    """Devolve (arquivo, crédito) ou None se não achar/der erro (o render segue sem foto)."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(query.lower().encode()).hexdigest()[:16]
    img, meta = cache_dir / f"{key}.jpg", cache_dir / f"{key}.json"
    if img.exists() and meta.exists():
        return img, json.loads(meta.read_text(encoding="utf-8"))["credit"]
    try:
        best = pick(_search(query))
        if not best:
            print(f"  [imagens] sem resultado utilizável para: {query!r}")
            return None
        req = urllib.request.Request(best["url"], headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        print(f"  [imagens] falha ao buscar {query!r}: {e}")
        return None
    img.write_bytes(raw)
    meta.write_text(json.dumps({"query": query, **best}, ensure_ascii=False, indent=1), encoding="utf-8")
    return img, best["credit"]
