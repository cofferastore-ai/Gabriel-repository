"""Formato do roteiro (JSON) e validação.

Tipos de cena (`kind`), todos com `narration` e `text` (título curto na tela):
  (vazio)   foto se houver `image`/`image_query`, senão texto com fundo animado
  counter   número que sobe: data = {value, prefix, suffix, decimals, label}
  bars      barras que crescem: data = {items: [{label, value}], prefix, suffix}
  growth    gráfico de juros compostos: data = {monthly, rate, months, prefix}
  timeline  linha do tempo proporcional: data = {events: [{year, label}], scale: proportional|even, gaps}
  list      itens que entram um a um: data = {items: [texto, ...]}
  map       mapa animado com zoom, rotas e marcadores: veja vvm/mapscene.py
"""
import json
from dataclasses import dataclass, field
from pathlib import Path

THEMES = {
    "historia": ((28, 18, 10), (92, 58, 24), (255, 215, 0)),
    "financas": ((6, 24, 20), (14, 92, 70), (120, 255, 190)),
    "default": ((12, 14, 28), (40, 52, 110), (255, 215, 0)),
}
ANIMATED = {"counter", "bars", "growth", "timeline", "map", "list"}


@dataclass
class Scene:
    narration: str
    text: str = ""
    image: str = ""        # arquivo em assets/images (tem prioridade)
    image_query: str = ""  # busca na Wikimedia Commons (domínio público / CC BY)
    kind: str = ""
    data: dict = field(default_factory=dict)


@dataclass
class Script:
    title: str
    niche: str
    scenes: list[Scene]
    description: str = ""
    tags: list[str] = field(default_factory=list)
    disclaimer: str = ""
    slug: str = ""

    @property
    def narration(self) -> str:
        return " ".join(s.narration for s in self.scenes)


def load(path: Path) -> Script:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    scenes = [Scene(**s) for s in data["scenes"]]
    if not scenes or any(not s.narration.strip() for s in scenes):
        raise ValueError("roteiro precisa de cenas com narração")
    for s in scenes:
        if s.kind and s.kind not in ANIMATED:
            raise ValueError(f"kind desconhecido: {s.kind}")
        if s.kind and not s.data:
            raise ValueError(f"cena '{s.kind}' precisa de `data`")
    return Script(
        title=data["title"], niche=data.get("niche", "default"), scenes=scenes,
        description=data.get("description", ""), tags=data.get("tags", []),
        disclaimer=data.get("disclaimer", ""), slug=data.get("slug") or Path(path).stem,
    )
