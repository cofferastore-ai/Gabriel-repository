# Pesquisa de formatos — 30/10/2026 (Shorts PT-BR, últimos 30 dias)

Amostra: 47 vídeos de história/curiosidades e 102 de finanças em português (após filtro de idioma),
via YouTube Data API. Limites: 6 buscas por nicho, só views (não receita), correlação ≠ causa.

## História / curiosidades — nicho com teto de viralização alto
- **Duração:** dos 40 melhores, 14 têm ≤30 s, 9 têm 31–59 s e **17 têm 60–90 s** (mediana 55 s). 90 s é viável.
- **Quem estoura sendo pequeno** (outlier = views ÷ inscritos): Minuto em Palitos (4,9 mil inscritos, 1,1 mi de views,
  222x, 63 s), Rei React (158x, 26 s), TudoEm30 (8,5 mil inscritos, 49x e 68x, 20 s), Aldeia dos Cortes (30x, 49 s).
- **Padrões de título:** pergunta direta ao espectador ("Você sobreviveria ao primeiro minuto da bomba de Hiroshima?"),
  fato que contradiz o senso comum ("O seu passaporte tem o nome de um emprego"), e a hashtag **#curiosidades**
  (19 dos 50 títulos do ranking de história).
- **Visual:** vários dos pequenos que viralizam usam **animação/desenho** (#animação, bonecos de palito), não foto parada.

## Finanças — teto bem menor, formato diferente
- Só 1 vídeo passa de 50 mil views/dia em 30 dias; canais grandes de investimento (1 a 1,7 mi de inscritos) ficam
  em 0,02–0,1x de outlier: **educação financeira "seca" quase não viraliza**.
- O que sobe é **história humana + dinheiro**: "mãe ensina educação financeira e filho trabalha para pagar celular",
  "ele ensina a filha antes de…", "este homem faz tijolo em casa e ganha muito dinheiro".
- Duração mediana 47 s; 11 dos 40 melhores têm 60–90 s.

## Decisões para o pipeline
1. Priorizar **história/curiosidades** em Shorts de 60–90 s; finanças como segundo nicho, em formato de **história
   com números** (personagem + decisão + resultado), não aula de investimento.
2. Gancho em **pergunta ao espectador** ou **contradição**; título curto com #curiosidades.
3. Mais **animação** (contadores, barras, linhas do tempo) e menos tela parada; o `vvm` já tem esses tipos de cena.
4. Testar duas durações (~45 s e ~90 s) no mesmo tema e comparar retenção.
