"""Formato do roteiro (JSON) e validação."""
import json
from dataclasses import dataclass, field
from pathlib import Path

THEMES = {
    "historia": ((28, 18, 10), (92, 58, 24), (255, 215, 0)),
    "financas": ((6, 24, 20), (14, 92, 70), (120, 255, 190)),
    "default": ((12, 14, 28), (40, 52, 110), (255, 215, 0)),
}


@dataclass
class Scene:
    narration: str
    text: str = ""    # palavra/frase de destaque na tela
    image: str = ""   # imagem opcional (relativa a assets/images)


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
    return Script(
        title=data["title"], niche=data.get("niche", "default"), scenes=scenes,
        description=data.get("description", ""), tags=data.get("tags", []),
        disclaimer=data.get("disclaimer", ""), slug=data.get("slug") or Path(path).stem,
    )
