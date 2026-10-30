# Viral Video Machine

Pipeline de Shorts/TikTok em português: pesquisa o que viraliza, gera o vídeo (voz, cenas, legendas) e deixa
pronto para publicar. Nichos iniciais: **história** e **finanças**.

## Custo: quase zero
| Etapa | Ferramenta | Custo |
|---|---|---|
| Roteiro | escrito pelo Claude Code (JSON em `scripts/`) | sem API |
| Voz | `edge-tts` (vozes pt-BR neurais) | grátis |
| Fotos | Wikimedia Commons (só domínio público, CC0 e CC BY; créditos vão no `.txt`) ou arquivos seus em `assets/images` | grátis |
| Animações | contador, barras, gráfico de juros e fundo animado (Pillow) + Ken Burns nas fotos (ffmpeg) | grátis |
| Legendas | palavra a palavra, destaque na palavra ativa | grátis |
| Pesquisa | YouTube Data API v3 | cota gratuita (10 mil/dia) |

## Uso
```bash
pip install -r requirements.txt        # requer ffmpeg instalado
cp .env.example .env                   # coloque a YOUTUBE_API_KEY

python -m vvm research --niche historia --niche financas   # -> data/research/relatorio-AAAAMMDD.md
python -m vvm render scripts/examples/guerra-mais-curta.json  # -> output/<slug>/<slug>.mp4 + .txt
python -m vvm estimate <roteiro>                              # duração só pela narração (rápido); meta ~90 s
python -m vvm images <roteiro>                                # pré-busca fotos e mostra os créditos
python -m vvm render <roteiro> --provider espeak              # voz offline, só para testes
python -m unittest discover -s tests
```

## Fluxo
1. `research` gera ranking de vídeos/canais (views/dia, *outlier* = views ÷ inscritos) e padrões de título.
2. Com o relatório, escrevemos o formato em `formats/` e novos roteiros em `scripts/` (copie um exemplo).
3. `render` produz o MP4 vertical 1080×1920 e um `.txt` com título, descrição, hashtags e aviso legal.
4. Você revisa e publica. Música opcional: coloque `.mp3` livres de direitos em `assets/music/`.

## Tipos de cena (campo `kind` no roteiro)
| kind | Resultado | `data` |
|---|---|---|
| *(vazio)* com `image_query` ou `image` | foto com movimento de câmera + título | — |
| *(vazio)* sem foto | título sobre fundo animado | — |
| `counter` | número que sobe até o valor | `value, prefix, suffix, decimals, label` |
| `bars` | barras que crescem | `items[{label,value}], prefix, suffix` |
| `growth` | gráfico de juros compostos se desenhando | `monthly, rate, months, prefix` |

Dica: alterne foto e animação a cada 4–8 s. Cena sem foto encontrada cai automaticamente para o fundo animado.

## Regras do jogo (monetização)
- Copiamos **formato** (estrutura, ritmo), nunca conteúdo, clipes ou vozes de terceiros.
- YouTube demonetiza conteúdo repetitivo/produzido em massa: varie roteiro, ritmo e visual, e mantenha revisão humana.
- Finanças: só conteúdo educativo, sem promessa de ganho nem recomendação de ativo.
- Fatos de história devem ser conferidos antes de publicar.
