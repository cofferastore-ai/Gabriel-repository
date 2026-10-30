"""Mapeia vídeos curtos e canais que mais performam em PT-BR via YouTube Data API v3.

Custo de cota: search.list = 100 unidades/chamada; videos.list e channels.list = 1.
Com ~6 buscas por nicho e a cota gratuita (10.000/dia) sobra muito espaço.
"""
import json
import math
import re
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

API = "https://www.googleapis.com/youtube/v3"

NICHES = {
    "historia": ["história curiosidades", "fatos históricos", "história do brasil", "segunda guerra mundial",
                 "império romano", "mistérios da história"],
    "financas": ["educação financeira", "como investir", "juros compostos", "renda passiva",
                 "dicas de dinheiro", "investir do zero"],
}

STOPWORDS = set("""a o as os um uma uns umas de do da dos das em no na nos nas por para com sem sobre que se
e ou mas como mais menos muito pouco foi era são ser ter tem já não sim isso esse essa este esta você voce vc
ao aos à às pelo pela até entre quando onde porque tudo todo toda seu sua seus suas meu minha eu ele ela nós
shorts short viral fyp""".split())


def parse_duration(iso: str) -> int:
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m:
        return 0
    d, h, mi, s = (int(x or 0) for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + s


def _get(path: str, params: dict, key: str) -> dict:
    url = f"{API}/{path}?{urllib.parse.urlencode({**params, 'key': key})}"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:400]
        raise RuntimeError(f"YouTube API {e.code}: {detail}") from None


def _chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def score(video: dict, now: datetime) -> dict:
    published = datetime.fromisoformat(video["published"].replace("Z", "+00:00"))
    age_days = max((now - published).total_seconds() / 86400, 0.5)
    views = video["views"]
    video["age_days"] = round(age_days, 1)
    video["views_per_day"] = round(views / age_days)
    # "outlier": views em relação ao tamanho do canal; > 1 = viralizou além da base de inscritos
    video["outlier"] = round(views / max(video["subs"], 1000), 2)
    return video


def analyze(videos: list[dict]) -> dict:
    """Estatísticas simples do formato dos vídeos que performam (o 'template' a imitar)."""
    if not videos:
        return {}
    words = Counter()
    for v in videos:
        for w in re.findall(r"[\wÀ-ÿ]+", v["title"].lower()):
            if len(w) > 2 and w not in STOPWORDS and not w.isdigit():
                words[w] += 1
    n = len(videos)
    durs = sorted(v["seconds"] for v in videos)
    return {
        "videos": n,
        "duracao_mediana_s": durs[n // 2],
        "titulo_chars_medio": round(sum(len(v["title"]) for v in videos) / n),
        "pct_titulo_com_numero": round(100 * sum(bool(re.search(r"\d", v["title"])) for v in videos) / n),
        "pct_titulo_pergunta": round(100 * sum("?" in v["title"] for v in videos) / n),
        "pct_titulo_reticencias_ou_exclamacao": round(
            100 * sum(("..." in v["title"] or "!" in v["title"]) for v in videos) / n),
        "palavras_mais_comuns": words.most_common(15),
    }


def collect(key: str, niche: str, days: int, max_seconds: int, now: datetime) -> list[dict]:
    after = (now - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    ids: dict[str, str] = {}
    for q in NICHES[niche]:
        res = _get("search", {"part": "snippet", "q": q, "type": "video", "videoDuration": "short",
                              "regionCode": "BR", "relevanceLanguage": "pt", "order": "viewCount",
                              "publishedAfter": after, "maxResults": 50}, key)
        for it in res.get("items", []):
            ids.setdefault(it["id"]["videoId"], q)
    videos = []
    for batch in _chunks(list(ids), 50):
        res = _get("videos", {"part": "snippet,statistics,contentDetails", "id": ",".join(batch)}, key)
        for it in res.get("items", []):
            secs = parse_duration(it["contentDetails"]["duration"])
            if not 5 <= secs <= max_seconds:
                continue
            st = it.get("statistics", {})
            videos.append({
                "id": it["id"], "title": it["snippet"]["title"], "channel_id": it["snippet"]["channelId"],
                "channel": it["snippet"]["channelTitle"], "published": it["snippet"]["publishedAt"],
                "seconds": secs, "views": int(st.get("viewCount", 0)), "likes": int(st.get("likeCount", 0)),
                "comments": int(st.get("commentCount", 0)), "query": ids[it["id"]], "niche": niche,
                "url": f"https://www.youtube.com/shorts/{it['id']}",
            })
    subs = {}
    chan_ids = sorted({v["channel_id"] for v in videos})
    for batch in _chunks(chan_ids, 50):
        res = _get("channels", {"part": "statistics", "id": ",".join(batch)}, key)
        for it in res.get("items", []):
            subs[it["id"]] = int(it["statistics"].get("subscriberCount", 0))
    for v in videos:
        v["subs"] = subs.get(v["channel_id"], 0)
        score(v, now)
    return sorted(videos, key=lambda v: v["views_per_day"], reverse=True)


def rank_channels(videos: list[dict]) -> list[dict]:
    agg = defaultdict(lambda: {"videos": 0, "views_per_day": 0, "subs": 0, "channel": ""})
    for v in videos:
        c = agg[v["channel_id"]]
        c.update(channel=v["channel"], subs=v["subs"])
        c["videos"] += 1
        c["views_per_day"] += v["views_per_day"]
    out = [{"channel_id": k, **c} for k, c in agg.items()]
    return sorted(out, key=lambda c: c["views_per_day"], reverse=True)


def report_md(niche: str, videos: list[dict], days: int) -> str:
    top = videos[:25]
    lines = [f"## {niche.capitalize()} — Shorts PT-BR dos últimos {days} dias ({len(videos)} vídeos analisados)\n",
             "### Top vídeos (views/dia)\n", "| # | Título | Canal | Views/dia | Views | Inscritos | Outlier | Dur. |",
             "|---|---|---|---|---|---|---|---|"]
    for i, v in enumerate(top, 1):
        t = v["title"].replace("|", "/")
        lines.append(f"| {i} | [{t}]({v['url']}) | {v['channel']} | {v['views_per_day']:,} | {v['views']:,} "
                     f"| {v['subs']:,} | {v['outlier']}x | {v['seconds']}s |")
    lines += ["\n### Canais que mais aparecem\n", "| Canal | Vídeos no ranking | Views/dia somadas | Inscritos |",
              "|---|---|---|---|"]
    for c in rank_channels(videos)[:15]:
        lines.append(f"| {c['channel']} | {c['videos']} | {c['views_per_day']:,} | {c['subs']:,} |")
    lines += ["\n### Padrões do formato\n", "```json",
              json.dumps(analyze(videos[:50]), ensure_ascii=False, indent=2), "```\n",
              "> **Outlier** = views ÷ inscritos. Valores altos em canais pequenos indicam que o *formato/tema* "
              "viraliza por mérito próprio, e esses são os melhores modelos a estudar.\n"]
    return "\n".join(lines)


def run(key: str, niches: list[str], days: int, max_seconds: int, out: Path) -> dict:
    now = datetime.now(timezone.utc)
    out.mkdir(parents=True, exist_ok=True)
    stamp = now.strftime("%Y%m%d")
    all_videos, sections = [], [f"# Pesquisa de vídeos virais — {now:%Y-%m-%d}\n"]
    for n in niches:
        vids = collect(key, n, days, max_seconds, now)
        all_videos += vids
        sections.append(report_md(n, vids, days))
    data = out / f"videos-{stamp}.json"
    data.write_text(json.dumps(all_videos, ensure_ascii=False, indent=2), encoding="utf-8")
    report = out / f"relatorio-{stamp}.md"
    report.write_text("\n".join(sections), encoding="utf-8")
    return {"data": data, "report": report}
