"""Gera o site (HTML) do estudo de eletroposto em BH.

Uso: python3 build.py
Saídas:
  ../index.html          documento completo e autocontido (fotos embutidas)
  ../site/artifact.html  mesmo conteúdo, sem <html>/<head>, para publicação como Artifact
"""
import base64, html, json, math, os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FOTOS = os.path.join(ROOT, "fotos")

# ---------------------------------------------------------------- dados de mercado
BH_SALES, BR_SALES_1S = 9896, 215023          # 1º semestre 2026 (ABVE)
BH_CHG, BR_CHG = 399, 25429                   # eletropostos jun/2026 (ABVE)
bh_sales_share = BH_SALES / BR_SALES_1S * 100
bh_chg_share = BH_CHG / BR_CHG * 100

# ---------------------------------------------------------------- modelo financeiro
P, E, DED, FIX = 2.19, 0.85, 0.29, 1350
AC_KWH, AC_P, CAP = 400, 1.49, 13000
CAPEX_ITEMS = [
    ("Carregador DC 60 kW, 2 saídas CCS2", 95000),
    ("Carregador AC 22 kW (amenidade)", 9000),
    ("Infraestrutura elétrica (cabos, quadro, proteção, adequação de entrada)", 28000),
    ("Obra civil (base, protetores, piso, pintura da vaga)", 9000),
    ("Projeto elétrico, ART, aprovação Cemig", 6000),
    ("Sinalização, totem e lançamento", 4000),
    ("Abertura da empresa e contrato com o local", 5000),
    ("Reserva de caixa (3 meses de custo fixo)", 4000),
]
CAPEX = sum(v for _, v in CAPEX_ITEMS)
SCEN = {"Conservador": (3000, 0.10), "Base": (6000, 0.20), "Otimista": (9000, 0.25)}
MRATE = 1.15 ** (1 / 12) - 1


def run(S, g, price=P, energy=E, capex=CAPEX, months=60, ded=DED, fix=FIX):
    cum, npv, pb = -capex, -capex, None
    cums, res_list, vols = [cum], [], []
    for m in range(1, months + 1):
        v = S * min(1, 0.35 + 0.65 * (m - 1) / 11) if m <= 12 else S * (1 + g) ** ((m - 12) / 12)
        v = min(v, CAP)
        res = v * (price * (1 - ded) - energy) + AC_KWH * (AC_P * (1 - ded) - energy) - fix
        cum += res
        npv += res / (1 + MRATE) ** m
        if pb is None and cum >= 0:
            pb = m
        cums.append(cum); res_list.append(res); vols.append(v)
    return dict(cum=cums, res=res_list, vol=vols, pb=pb, npv=npv)


R = {k: run(*v) for k, v in SCEN.items()}
lever = run(6000, 0.20, capex=125000)
OWN_DED, OWN_FIX = DED - 0.10 + 0.01, FIX + 500     # plataforma própria: troca 10% por Pix ~1% e soma R$ 500 fixos
own = run(6000, 0.20, ded=OWN_DED, fix=OWN_FIX)
def steady(ded, fix, kwh=6000):
    return kwh * (P * (1 - ded) - E) + AC_KWH * (AC_P * (1 - ded) - E) - fix
base_res, own_res = steady(DED, FIX), steady(OWN_DED, OWN_FIX)
third_fee = 0.10 * (6000 * P + AC_KWH * AC_P)
margin = P * (1 - DED) - E
ac_res = AC_KWH * (AC_P * (1 - DED) - E)
be_day = (FIX - ac_res) / (margin * 25 * 30)
per_session = margin * 25 * 30


def brl(v, d=0):
    s = f"{abs(v):,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return ("−" if v < 0 else "") + "R$ " + s


def fmt(v, d=0):
    return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ---------------------------------------------------------------- fotos
CREDITS = {
    "delrey": ("Alexandre Nogelino", "CC BY-SA 3.0", "Shopping_Del_Rey_o_melhor_de_BH_-_panoramio.jpg"),
    "boulevard": ("Paulo JC Nogueira", "CC BY-SA 3.0", "Shopping_Boulevar_-_BH_-_Área_Central_-_panoramio.jpg"),
    "minas": ("Marinna", "CC BY-SA 4.0", "Minas_Shopping_Terminal.jpg"),
    "estacao": ("Andrevruas", "CC BY-SA 3.0", "Vilarinho4.jpg"),
    "ponteio": ("Andrevruas", "CC BY 3.0", "Ponteio.JPG"),
    "viladaserra": ("Andrevruas", "CC BY 3.0", "Viladaserra.JPG"),
    "mercado": ("Paulo SP", "CC BY-SA 4.0", "Mercado_Central,_Belo_Horizonte,_Minas_Gerais_-_2023-11-05_-_DSC01893_(cropped).jpg"),
    "verdemar": ("Andrevruas", "CC BY 3.0", "Verdemar.JPG"),
    "supernosso": ("Andrevruas", "CC BY-SA 4.0", "Supernosso.jpg"),
    "cidade": ("Ajmcbarreto", "CC BY-SA 4.0", "Cineart_Shopping_Cidade_04.jpg"),
    "big": ("Fronteira", "CC BY-SA 4.0", "Ponto_de_ônibus_em_frente_ao_Big_Shopping,_Eldorado,_Contagem,_janeiro_de_2023.jpg"),
    "c_ac": ("Matti Blume", "CC BY-SA 4.0", "Easee_Wallbox,_Walluf_(20250725-LRM_20250725_173937).jpg"),
    "c_dc": ("G. Edward Johnson", "CC BY 4.0", "DC_fast_charging_at_Ikea_College_Park_MD_2026-01-20_13-23-57.jpg"),
    "c_hpc": ("RC-hpbt", "CC BY 4.0", "Recharge_fast_charging_station_Rygge_Norway_2022.jpg"),
}


def img(key):
    with open(os.path.join(FOTOS, key + ".jpg"), "rb") as f:
        return "data:image/jpeg;base64," + base64.b64encode(f.read()).decode()


def credit(key):
    a, lic, _ = CREDITS[key]
    return f"{html.escape(a)}, {lic}, via Wikimedia Commons"


# ---------------------------------------------------------------- locais
W = [0.25, 0.20, 0.20, 0.10, 0.15, 0.10]  # demanda, app, concorrência, permanência, local, elétrica
PLACES = [
    dict(k="delrey", name="Shopping Del Rey", addr="Av. Presidente Carlos Luz, 3001 · Caiçara (Noroeste)",
         ll=(-19.874, -43.970), s=[4, 5, 4, 4, 4, 4], hoje="4 vagas AC gratuitas (2023)",
         why="Fica entre o Anel Rodoviário, a Av. Pedro II e a região da Pampulha e do Mineirão, onde circula e mora muita gente que dirige por aplicativo. Não encontramos recarga rápida paga no entorno. Já tem cultura de recarga (vagas AC), o que facilita a conversa.",
         fit="DC 60 kW perto de uma portaria de alto giro; manter as vagas AC."),
    dict(k="estacao", name="Shopping Estação BH", addr="Av. Cristiano Machado, 11.833 · Venda Nova",
         ll=(-19.815, -43.952), s=[3, 5, 5, 4, 4, 4], hoje="2 vagas de recarga (2023)",
         why="Integrado à Estação Vilarinho (metrô e MOVE). As regiões Norte e Venda Nova concentram motoristas de aplicativo, que recarregam perto de casa antes do turno. É o vetor norte da cidade, sem DC pago identificado.",
         fit="DC 60 kW com preço de fidelidade para motoristas cadastrados.", cap="Foto de arquivo, da época da construção"),
    dict(k="verdemar", name="Verdemar (rede)", addr="Ex.: loja Belvedere, 17ª e maior da rede · Centro-Sul e bairros de alta renda",
         ll=(-19.973, -43.940), s=[5, 2, 4, 5, 4, 4], hoje="Nenhuma recarga identificada",
         why="A compra de supermercado leva de 30 a 50 minutos, o tempo exato de uma recarga DC. O público tem a maior concentração de carros elétricos da cidade. Com 17 lojas, um bom contrato vira caminho de expansão.",
         fit="DC 40–60 kW na vaga mais próxima da entrada; contrato-quadro para a rede."),
    dict(k="supernosso", name="Supernosso (rede)", addr="Várias lojas em BH · a unidade de Lourdes já recebeu ponto da Cemig SIM",
         ll=(-19.933, -43.945), s=[5, 3, 3, 5, 4, 4], hoje="Ponto público Cemig SIM em Lourdes (situação atual a confirmar)",
         why="Mesma lógica do Verdemar, com lojas em bairros de renda alta e média. Já recebeu eletroposto, então a diretoria conhece o tema. Escolher uma loja diferente da de Lourdes.",
         fit="DC 40–60 kW em loja com estacionamento próprio."),
    dict(k="ponteio", name="Ponteio Lar Shopping", addr="BR-356 · Santa Lúcia, saída para Nova Lima",
         ll=(-19.963, -43.952), s=[5, 3, 4, 4, 3, 4], hoje="Nenhuma recarga identificada",
         why="Na BR-356, corredor de alta renda entre BH e Nova Lima. Shopping de decoração e serviços, com permanência longa. Boa visibilidade para quem vai e volta do Vila da Serra.",
         fit="DC 60 kW de frente para a via + AC para clientes que ficam mais tempo."),
    dict(k="boulevard", name="Boulevard Shopping", addr="Av. dos Andradas, 3000 · Santa Efigênia (Leste)",
         ll=(-19.920, -43.919), s=[4, 5, 2, 4, 4, 4], hoje="Um guia de 2026 cita DC de alta potência (a confirmar)",
         why="Ao lado do Centro e da área hospitalar, com muito fluxo de aplicativo. Se a recarga DC citada existir, o local perde atratividade: confirmar no PlugShare antes de visitar.",
         fit="Só seguir se não houver DC ativo."),
    dict(k="minas", name="Minas Shopping", addr="Av. Cristiano Machado, 4000 · União (Nordeste)",
         ll=(-19.877, -43.926), s=[4, 4, 2, 4, 4, 4], hoje="2 vagas AC gratuitas, “constantemente ocupadas”",
         why="A demanda está provada: as vagas grátis vivem cheias. Mas a Watton abriu recarga rápida no Centerminas, a poucas quadras, em setembro de 2026.",
         fit="Plano B do eixo Cristiano Machado."),
    dict(k="viladaserra", name="Vila da Serra (Nova Lima)", addr="Bairro comercial e residencial · local exato a definir",
         ll=(-19.982, -43.945), s=[5, 3, 3, 3, 3, 3], hoje="Sem levantamento detalhado",
         why="Uma das maiores concentrações de renda e de prédios novos da região metropolitana. Muitos moradores recarregam em casa, por isso o volume público é incerto. Bom candidato para a fase 2.",
         fit="Estacionamento de centro comercial ou supermercado."),
    dict(k="cidade", name="Shopping Cidade", addr="Hipercentro de BH",
         ll=(-19.919, -43.937), s=[3, 5, 3, 3, 3, 3], hoje="Situação não confirmada",
         why="Altíssimo fluxo de pessoas e de aplicativos no Hipercentro. A garagem em edifício costuma limitar a potência e as regras de segurança são mais rígidas.",
         fit="Verificar capacidade elétrica da garagem.", cap="Foto interna (cinema do shopping)"),
    dict(k="mercado", name="Mercado Central", addr="Av. Augusto de Lima, 744 · Centro",
         ll=(-19.923, -43.944), s=[3, 4, 3, 3, 4, 3], hoje="Ponto público da Cemig SIM (desde 2019)",
         why="Fluxo enorme de visitantes e estacionamento próprio. Já tem recarga da Cemig SIM, o que reduz a lacuna.",
         fit="Complemento a um ponto já existente."),
    dict(k="big", name="Big Shopping", addr="Eldorado · Contagem",
         ll=(-19.944, -44.036), s=[3, 3, 2, 4, 4, 4], hoje="Situação não confirmada",
         why="Contagem é a segunda cidade da região metropolitana, mas o ItaúPower Shopping, na mesma cidade, já tem DC de 240 kW.",
         fit="Fase 2 ou 3, se a demanda do oeste crescer.", cap="Ponto de ônibus em frente ao shopping"),
]
for p in PLACES:
    p["score"] = round(sum(a * b for a, b in zip(p["s"], W)), 2)
PLACES.sort(key=lambda p: -p["score"])
for i, p in enumerate(PLACES, 1):
    p["rank"] = i

COMP = [  # nome, (lat, lon), deslocamento do rótulo (dx, dy, âncora)
    ("Rodoviária", (-19.915, -43.941), (8, -6, "start")), ("Centerminas", (-19.872, -43.933), (-8, -6, "end")),
    ("ItaúPower", (-19.952, -44.027), (8, 12, "start")), ("ViaShopping Barreiro", (-19.977, -44.014), (8, 12, "start")),
    ("Shell Barro Preto", (-19.927, -43.954), (-8, 4, "end")), ("BH Shopping", (-19.976, -43.945), (-8, 12, "end")),
    ("DiamondMall", (-19.932, -43.948), (-8, 14, "end")), ("Pátio Savassi", (-19.942, -43.933), (8, 12, "start")),
    ("Assaí Belvedere", (-19.969, -43.938), (8, 4, "start")),
]

# ---------------------------------------------------------------- gráficos SVG


def chart_sales():
    bars = [("2025", 223912, False), ("2026 jan–ago", 328477, False), ("2026 projeção", 508000, True)]
    w, h, x0, y0, top = 520, 250, 56, 210, 20
    mx = 550000
    ky = (y0 - top) / mx
    out = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="Vendas de eletrificados leves no Brasil: 2025, 223.912; 2026 até agosto, 328.477; 2026 projeção, 508 mil">']
    out.append('<defs><pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="6" height="6" style="fill:var(--copper-soft)"/><line x1="0" y1="0" x2="0" y2="6" style="stroke:var(--s2);stroke-width:2"/></pattern></defs>')
    for t in range(0, 600001, 100000):
        if t > mx: break
        y = y0 - t * ky
        out.append(f'<line class="grid" x1="{x0}" x2="{w-10}" y1="{y:.1f}" y2="{y:.1f}"/><text class="lbl-s" x="{x0-8}" y="{y+4:.1f}" text-anchor="end">{fmt(t/1000)} mil</text>')
    bw, gap = 96, 150
    for i, (lab, v, proj) in enumerate(bars):
        x = x0 + 40 + i * gap
        y = y0 - v * ky
        hgt = v * ky
        fill = 'url(#hatch)' if proj else 'var(--s2)'
        r = 4
        path = f'M{x},{y0} L{x},{y+r} Q{x},{y} {x+r},{y} L{x+bw-r},{y} Q{x+bw},{y} {x+bw},{y+r} L{x+bw},{y0} Z'
        out.append(f'<path d="{path}" style="fill:{fill}" data-tip="{lab}: {fmt(v)} veículos"/>')
        out.append(f'<text class="val" x="{x+bw/2}" y="{y-8:.1f}" text-anchor="middle">{fmt(v)}</text>')
        out.append(f'<text class="lbl" x="{x+bw/2}" y="{y0+18}" text-anchor="middle">{lab}</text>')
    out.append(f'<line class="zero" x1="{x0}" x2="{w-10}" y1="{y0}" y2="{y0}"/>')
    out.append('</svg>')
    return "".join(out)


def chart_gap():
    rows = [("Vendas de eletrificados", bh_sales_share, "var(--s2)"), ("Eletropostos instalados", bh_chg_share, "var(--s1)")]
    w, h, x0, top = 520, 170, 170, 26
    mx = 5.0
    kx = (w - x0 - 40) / mx
    out = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="BH tem {bh_sales_share:.1f}% das vendas nacionais e {bh_chg_share:.1f}% dos eletropostos">']
    for t in range(0, 6):
        x = x0 + t * kx
        out.append(f'<line class="grid" x1="{x:.1f}" x2="{x:.1f}" y1="{top-8}" y2="{h-30}"/><text class="lbl-s" x="{x:.1f}" y="{h-12}" text-anchor="middle">{t}%</text>')
    for i, (lab, v, c) in enumerate(rows):
        y = top + i * 56
        bw = v * kx
        out.append(f'<text class="lbl" x="{x0-10}" y="{y+22}" text-anchor="end">{lab}</text>')
        out.append(f'<path d="M{x0},{y+6} L{x0+bw-4:.1f},{y+6} Q{x0+bw:.1f},{y+6} {x0+bw:.1f},{y+10} L{x0+bw:.1f},{y+28} Q{x0+bw:.1f},{y+32} {x0+bw-4:.1f},{y+32} L{x0},{y+32} Z" style="fill:{c}" data-tip="{lab}: {v:.1f}% do Brasil"/>')
        out.append(f'<text class="val" x="{x0+bw+8:.1f}" y="{y+24}">{fmt(v,1)}%</text>')
    out.append(f'<line class="zero" x1="{x0}" x2="{x0}" y1="{top-8}" y2="{h-30}"/>')
    out.append('</svg>')
    return "".join(out)


def chart_scores():
    n = len(PLACES)
    rh, w, x0, top = 30, 960, 230, 10
    h = top + n * rh + 30
    kx = (w - x0 - 40) / 5
    out = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="Nota ponderada de cada local candidato">']
    for t in range(0, 6):
        x = x0 + t * kx
        out.append(f'<line class="grid" x1="{x:.1f}" x2="{x:.1f}" y1="{top}" y2="{top+n*rh}"/><text class="lbl-s" x="{x:.1f}" y="{top+n*rh+18}" text-anchor="middle">{t}</text>')
    for i, p in enumerate(PLACES):
        y = top + i * rh
        bw = p["score"] * kx
        c = "var(--s2)" if i < 5 else "var(--muted)"
        out.append(f'<text class="lbl" x="{x0-10}" y="{y+19}" text-anchor="end">{p["rank"]}. {html.escape(p["name"])}</text>')
        out.append(f'<path d="M{x0},{y+7} L{x0+bw-4:.1f},{y+7} Q{x0+bw:.1f},{y+7} {x0+bw:.1f},{y+11} L{x0+bw:.1f},{y+21} Q{x0+bw:.1f},{y+25} {x0+bw-4:.1f},{y+25} L{x0},{y+25} Z" style="fill:{c}" data-tip="{html.escape(p["name"])}: {fmt(p["score"],2)} de 5"/>')
        out.append(f'<text class="val" x="{x0+bw+8:.1f}" y="{y+20}">{fmt(p["score"],2)}</text>')
    out.append(f'<line class="zero" x1="{x0}" x2="{x0}" y1="{top}" y2="{top+n*rh}"/>')
    out.append('</svg>')
    return "".join(out)


def chart_cash():
    w, h, x0, top, bottom = 960, 340, 70, 16, 300
    allv = [v for r in R.values() for v in r["cum"]]
    mn, mxv = -200000, 250000
    ky = (bottom - top) / (mxv - mn)
    dx = (w - x0 - 20) / 60
    Y = lambda v: bottom - (v - mn) * ky
    out = [f'<svg id="cashchart" viewBox="0 0 {w} {h}" role="img" aria-label="Caixa acumulado em 60 meses por cenário" '
           f'data-series=\'{json.dumps({k: [round(v) for v in r["cum"]] for k, r in R.items()})}\' '
           f'data-cfg=\'{json.dumps({"x0": x0, "dx": dx, "y0": bottom, "min": mn, "ky": ky})}\'>']
    for t in range(-200000, 250001, 50000):
        y = Y(t)
        cls = "zero" if t == 0 else "grid"
        lab = "0" if t == 0 else f"{'−' if t<0 else ''}{abs(t)//1000} mil"
        out.append(f'<line class="{cls}" x1="{x0}" x2="{w-20}" y1="{y:.1f}" y2="{y:.1f}"/><text class="lbl-s" x="{x0-8}" y="{y+4:.1f}" text-anchor="end">{lab}</text>')
    for m in range(0, 61, 12):
        x = x0 + m * dx
        out.append(f'<text class="lbl-s" x="{x:.1f}" y="{bottom+18}" text-anchor="middle">{"mês " + str(m) if m else "0"}</text>')
    colors = {"Conservador": "var(--s1)", "Base": "var(--s2)", "Otimista": "var(--s3)"}
    for k, r in R.items():
        pts = " ".join(f"{x0+i*dx:.1f},{Y(v):.1f}" for i, v in enumerate(r["cum"]))
        out.append(f'<polyline points="{pts}" style="fill:none;stroke:{colors[k]};stroke-width:2;stroke-linejoin:round"/>')
        endv = r["cum"][-1]
        out.append(f'<text class="val" x="{w-22}" y="{Y(endv)-8:.1f}" text-anchor="end">{k}</text>')
        if r["pb"]:
            px = x0 + r["pb"] * dx
            out.append(f'<circle cx="{px:.1f}" cy="{Y(0):.1f}" r="5" style="fill:{colors[k]};stroke:var(--surface);stroke-width:2"/>')
            out.append(f'<text class="lbl-s" x="{px:.1f}" y="{Y(0)+20:.1f}" text-anchor="middle">{r["pb"]} m</text>')
    out.append(f'<line class="xh" x1="0" x2="0" y1="{top}" y2="{bottom}" style="stroke:var(--muted);stroke-width:1;display:none"/>')
    for k in R:
        out.append(f'<circle class="xh-dot" r="5" cx="0" cy="0" style="fill:{colors[k]};stroke:var(--surface);stroke-width:2;display:none"/>')
    out.append(f'<rect class="hit" x="{x0}" y="{top}" width="{w-x0-20}" height="{bottom-top}" style="fill:transparent"/>')
    out.append('</svg>')
    return "".join(out)


def map_svg():
    lat0, lat1, lon0, lon1 = -19.795, -20.000, -44.065, -43.895
    w = 560
    sx = w / ((lon1 - lon0) * math.cos(math.radians(19.9)))
    h = round((lat0 - lat1) * sx)
    X = lambda lon: (lon - lon0) * math.cos(math.radians(19.9)) * sx
    Yp = lambda lat: (lat0 - lat) * sx
    out = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="Mapa esquemático de BH com locais candidatos e concorrentes">']
    out.append(f'<rect x="0" y="0" width="{w}" height="{h}" style="fill:var(--paper)"/>')
    # Lagoa da Pampulha (elipse aproximada)
    out.append(f'<ellipse class="map-water" cx="{X(-43.978):.1f}" cy="{Yp(-19.851):.1f}" rx="{X(-43.958)-X(-43.978):.1f}" ry="{Yp(-19.862)-Yp(-19.851):.1f}"/>')
    out.append(f'<text class="map-ref" x="{X(-43.978):.1f}" y="{Yp(-19.851)+3:.1f}" text-anchor="middle">Lagoa da Pampulha</text>')
    # Av. do Contorno (anel aproximado)
    out.append(f'<ellipse class="map-road2" cx="{X(-43.938):.1f}" cy="{Yp(-19.926):.1f}" rx="{X(-43.920)-X(-43.938):.1f}" ry="{Yp(-19.945)-Yp(-19.926):.1f}"/>')
    out.append(f'<text class="map-ref" x="{X(-43.938):.1f}" y="{Yp(-19.904):.1f}" text-anchor="middle">Av. do Contorno</text>')
    # Anel Rodoviário (traçado aproximado)
    anel = [(-19.985, -44.010), (-19.960, -44.000), (-19.935, -43.995), (-19.905, -43.985), (-19.880, -43.975), (-19.866, -43.955), (-19.868, -43.925), (-19.880, -43.905)]
    out.append('<polyline class="map-road" points="' + " ".join(f"{X(lo):.1f},{Yp(la):.1f}" for la, lo in anel) + '"/>')
    out.append(f'<text class="map-ref" x="{X(-44.004)+6:.1f}" y="{Yp(-19.948):.1f}">Anel Rodoviário</text>')
    # Cristiano Machado
    cm = [(-19.905, -43.930), (-19.880, -43.927), (-19.850, -43.935), (-19.815, -43.952)]
    out.append('<polyline class="map-road2" points="' + " ".join(f"{X(lo):.1f},{Yp(la):.1f}" for la, lo in cm) + '"/>')
    out.append(f'<text class="map-ref" x="{X(-43.932)+6:.1f}" y="{Yp(-19.848):.1f}">Av. Cristiano Machado</text>')
    # BR-356
    br = [(-19.945, -43.935), (-19.963, -43.950), (-19.978, -43.946), (-19.990, -43.942)]
    out.append('<polyline class="map-road2" points="' + " ".join(f"{X(lo):.1f},{Yp(la):.1f}" for la, lo in br) + '"/>')
    out.append(f'<text class="map-ref" x="{X(-43.938)+4:.1f}" y="{Yp(-19.992):.1f}">BR-356 → Nova Lima</text>')
    out.append(f'<text class="map-ref" x="{X(-44.040):.1f}" y="{Yp(-19.925):.1f}">Contagem</text>')
    out.append(f'<text class="map-ref" x="{X(-44.035):.1f}" y="{Yp(-19.990):.1f}">Barreiro</text>')
    for name, (la, lo), (ldx, ldy, anc) in COMP:
        x, y = X(lo), Yp(la)
        out.append(f'<g class="map-comp" data-tip="Concorrente: {html.escape(name)}"><rect x="{x-5:.1f}" y="{y-5:.1f}" width="10" height="10"/></g>')
        out.append(f'<text class="map-label" x="{x+ldx:.1f}" y="{y+ldy:.1f}" text-anchor="{anc}">{html.escape(name)}</text>')
    for p in sorted(PLACES, key=lambda p: -p["rank"]):
        la, lo = p["ll"]
        x, y = X(lo), Yp(la)
        out.append(f'<g class="map-cand" data-tip="{p["rank"]}. {html.escape(p["name"])} · nota {fmt(p["score"],2)}"><circle cx="{x:.1f}" cy="{y:.1f}" r="10"/><text x="{x:.1f}" y="{y+4:.1f}" text-anchor="middle">{p["rank"]}</text></g>')
    out.append('</svg>')
    return "".join(out)


def map_list():
    rows = []
    for p in PLACES:
        rows.append(f'<div class="k"><span class="dot"></span><span><strong>{p["rank"]}.</strong> {html.escape(p["name"])} <span class="muted">· {fmt(p["score"],2)}</span></span></div>')
    return "".join(rows)


def places_html():
    out = []
    for p in PLACES:
        top = " top" if p["rank"] <= 3 else ""
        cap = p.get("cap")
        capt = f"{html.escape(cap)}. " if cap else ""
        out.append(f'''<article class="place{top}">
  <div class="ph"><img src="{img(p["k"])}" alt="{html.escape(p["name"])}"><span class="rank">{p["rank"]}</span></div>
  <div class="b">
    <h3>{html.escape(p["name"])}</h3>
    <span class="addr">{html.escape(p["addr"])}</span>
    <div class="score"><span>Nota {fmt(p["score"],2)}</span><span class="bar"><i style="width:{p["score"]/5*100:.0f}%"></i></span></div>
    <p><strong>Hoje:</strong> {html.escape(p["hoje"])}</p>
    <p>{html.escape(p["why"])}</p>
    <p><strong>Proposta:</strong> {html.escape(p["fit"])}</p>
    <span class="credit">{capt}Foto: {credit(p["k"])}</span>
  </div>
</article>''')
    return "\n".join(out)


def scen_rows():
    out = []
    reading = {"Conservador": '<span class="pill bad">Não investir assim</span>',
               "Base": '<span class="pill warn">Marginal; exige alavancas</span>',
               "Otimista": '<span class="pill good">Bom negócio</span>'}
    for k, (S, g) in SCEN.items():
        r = R[k]
        out.append(f'<tr{" class=\"hl\"" if k=="Base" else ""}><td>{k}</td><td class="r">{S/25/30:.0f}</td><td class="r">{brl(r["res"][11])}</td><td class="r">{brl(r["res"][59])}</td>'
                   f'<td class="r">{str(r["pb"])+" meses" if r["pb"] else "acima de 60 meses"}</td><td class="r">{brl(r["npv"])}</td><td>{reading[k]}</td></tr>')
    return "".join(out)


def sens_rows():
    out = []
    for price in (1.89, 2.19, 2.49):
        cells = []
        for e in (0.75, 0.85, 1.13):
            v = 6000 * (price * (1 - DED) - e) + AC_KWH * (AC_P * (1 - DED) - e) - FIX
            cls = "good" if v >= 3000 else ("warn" if v >= 1500 else "bad")
            cells.append(f'<td class="r"><span class="pill {cls}">{brl(v)}</span></td>')
        out.append(f'<tr><td>Preço R$ {fmt(price,2)}</td>{"".join(cells)}</tr>')
    return "".join(out)


def capex_rows():
    rows = [f'<tr><td>{html.escape(n)}</td><td class="r num">{fmt(v)}</td></tr>' for n, v in CAPEX_ITEMS]
    rows.append(f'<tr class="hl"><td><strong>Total</strong></td><td class="r num"><strong>{fmt(CAPEX)}</strong></td></tr>')
    return "".join(rows)


SOURCES = [
    ("ABVE: eletrificados podem chegar a 30% das vendas em 2027 (Autodata, out. 2026)", "https://www.autodata.com.br/noticias/2026/10/20/abve-preve-que-eletrificados-alcancem-30-das-vendas-de-veiculos-leves-em-2027/138063/"),
    ("Brasil passa de 1 milhão de eletrificados (Forbes, out. 2026)", "https://forbes.com.br/forbes-life/forbes-motors/2026/10/brasil-passa-de-1-milhao-de-carros-eletrificados-quase-40-vieram-so-em-2026/"),
    ("Brasil perto de 1 milhão de VEs (Webmotors)", "https://www.webmotors.com.br/wm1/noticias/brasil-1-milhao-carros-eletrificados"),
    ("Minas é o 3º estado em vendas de eletrificados (Diário do Comércio)", "https://diariodocomercio.com.br/?p=635775"),
    ("Venda de elétricos e híbridos em MG, jan. 2026 (Diário do Comércio)", "https://diariodocomercio.com.br/economia/venda-veiculos-eletricos-hibridos-minas-gerais/"),
    ("Vendas de elétricos disparam em MG (Vrum, out. 2026)", "https://www.vrum.com.br/mercado/2026/10/7517205-vendas-de-carros-eletricos-disparam-310-em-minas-gerais-com-dominio-da-byd.html"),
    ("Watton instala eletroposto no Centerminas; dados ABVE de eletropostos (Diário do Comércio, set. 2026)", "https://diariodocomercio.com.br/negocios/watton-energia-instala-eletroposto-centerminas/"),
    ("CMU investirá R$ 70 milhões em eletropostos em MG (Diário do Comércio)", "https://diariodocomercio.com.br/negocios/cmu-investira-r-70-milhoes-eletropostos-rapidos-minas-gerais/"),
    ("Rodoviária de BH ganha recarga rápida (Itatiaia, ago. 2026)", "https://www.itatiaia.com.br/auto/rodoviaria-de-bh-ganha-dois-pontos-para-a-recarga-de-carros-eletricos/"),
    ("Anuário VoltBras: carregador de 30 a 60 kW é o mais vantajoso (Canal VE)", "https://canalve.com.br/carregador-30-60-kw-mais-vantajoso-cpo-avalia-voltbras/"),
    ("A guerra dos eletropostos (Vrum, ago. 2026)", "https://www.vrum.com.br/mercado/2026/08/7475954-a-guerra-dos-eletropostos-quem-vai-dominar-a-recarga-no-brasil.html"),
    ("Onde carregar carro elétrico em BH em 2026 (Consulta de Placa; fonte secundária)", "https://consultadeplaca.net/blog/onde-carregar-carro-eletrico-belo-horizonte"),
    ("Shoppings de BH oferecem recarga gratuita (Diário do Comércio, dez. 2023)", "https://diariodocomercio.com.br/negocios/shoppings-oferecem-uso-gratuito-carregador-carro-eletrico/"),
    ("Assaí Belvedere oferece recarga (Mercado & Consumo, 2023)", "https://mercadoeconsumo.com.br/21/08/2023/inovacao/assai-atacadista-de-belo-horizonte-oferece-servico-de-recarregamento-de-carros-eletricos/"),
    ("Cemig SIM: primeiros eletropostos públicos de BH (Jornal Contábil)", "https://jornalcontabil.com.br/noticia/cemig-sim-bh-recebe-os-primeiros-eletropostos-publicos/amp/"),
    ("Cemig abre chamada para eletrovias (Agência Minas)", "https://www.agenciaminas.mg.gov.br/noticia/cemig-abre-chamada-para-implantacao-de-eletrovias-e-amplia-incentivo-a-mobilidade-eletrica-no-estado/"),
    ("Raízen fecha acordo com Minas Gerais (eixos)", "https://eixos.com.br/raizen-fecha-acordo-com-minas-gerais-para-expandir-infraestrutura-de-mobilidade-eletrica/"),
    ("ANEEL aprova reajuste da Cemig de 6,5% (Cenário Energia, mai. 2026)", "https://cenarioenergia.com.br/2026/05/27/aneel-aprova-reajuste-tarifario-da-cemig-com-efeito-medio-de-650/"),
    ("Volvo encerra recarga gratuita (AutoPapo)", "https://autopapo.com.br/curta/volvo-encerra-servico-de-recargas-gratuitas-para-carros-eletricos-no-brasil/"),
    ("Aneel não intervirá em cobranças de recarga (Poder360)", "https://www.poder360.com.br/economia/aneel-nao-vai-intervir-em-cobrancas-para-recarregar-carros-eletricos/"),
    ("A era dos carros elétricos e a REN 1.000 (O Setor Elétrico)", "https://www.osetoreletrico.com.br/?p=161966"),
    ("WEG DC 40 kW, preço (Magnani)", "https://loja.magnani.com.br/carregador-veicular-weg-dc-40kw-ccs2-4-3m-modelo-17850092"),
    ("WEG DC 40 kW, preço (CCR Engenharia)", "https://loja.ccr.eng.br/products/carregador-veiculos-eletricos-40kwcc-com-display-wemob-s-040-w-e-4g-r-h-1cs2-parking-weg-17850092"),
    ("DC 60 kW genérico, preço (Distrisol)", "https://distrisolar.com.br/produto/77/%E2%80%8Bcarregador-veicular---dc-60-kw"),
    ("Catálogo WEMOB (WEG)", "https://static.weg.net/medias/downloadcenter/h1c/h57/WEG-estacoes-de-recarga-de-veiculos-eletricos-WEMOB-50105757-pt.pdf/WEG-estacoes-de-recarga-de-veiculos-eletricos-WEMOB-%2050105757-pt.pdf"),
    ("Intelbras EVE 0600FP, DC 60 kW", "https://backend.intelbras.com/pt-br/estacao-de-recarga-dc-de-60kw-eve-0600fp"),
    ("Nansen fornecerá carregadores para ônibus de BH (O Setor Elétrico)", "https://www.osetoreletrico.com.br/?p=168868"),
    ("BYD chega a 125 carregadores rápidos (Autodata)", "https://www.autodata.com.br/noticias/2026/03/24/byd-alcanca-125-carregadores-rapidos-publicos-no-brasil/101250/"),
    ("Tupinambá: software de gestão", "https://tupinambaenergia.com.br/service-management-software/?lang=en"),
    ("Voltbras capta R$ 12 milhões (Startups)", "https://startups.com.br/energytech/voltbras-capta-r-12-mi-com-solucoes-de-recarga-de-veiculos-eletricos"),
    ("Zletric inaugura eletroposto próprio (Canal VE)", "https://canalve.com.br/zletric-inaugura-eletroposto-porto-alegre/"),
    ("Energia solar e recarga: payback e tarifas (Canal VE)", "https://canalve.com.br/energia-solar-impulsiona-recarga-veiculos-eletricos-brasil/"),
    ("Shop Solar: retorno mais lento que o previsto (Canal VE)", "https://canalve.com.br/shop-solar-amplia-rede-eletropostos-rio-janeiro-projeta-200-pontos-2027/"),
    ("Ficha técnica BYD Dolphin Mini 2026", "https://www.byd.com/material/__CN/byd-site/br/fichas-tecnicas-2026/update-02-07-2026/BYD_DolphinMini_FichaTecnica_2026.pdf"),
    ("Verdemar inaugura maior loja no Belvedere (Diário do Comércio)", "https://diariodocomercio.com.br/negocios/belvedere-recebe-maior-loja-rede-verdemar-belo-horizonte/"),
    ("Bombeiros e regras para recarga em prédios (Canal VE)", "https://canalve.com.br/bombeiros-regras-estacoes-recarga-predios/"),
    ("Now Charge: carregador DC 60 kW e contato em BH", "https://nowcharge.com.br/carregador-d-c-60-kw/"),
    ("FiveStars: projeto e venda de carregadores em BH", "https://www.fivestars.eng.br/projeto-eletroposto-belo-horizonte"),
    ("Nansen terá linha de montagem de carregadores em Betim (Diário do Comércio)", "https://diariodocomercio.com.br/?p=611266"),
    ("Nansen e PVMOB: R$ 1 bilhão em eletropostos (Diário do Comércio)", "https://diariodocomercio.com.br/negocios/eletropostos-investimento-pv-mob-nansen-brasil/"),
    ("Watton planeja 100 eletropostos em Minas até 2027 (Boca)", "https://boca.com.br/negocios/watton-planeja-100-eletropostos-em-minas-ate-2027"),
    ("Fury Charger DC 60 kW", "https://www.furycharger.com.br/carregador-veicular-rapido-dc-60kw-fury-charger"),
    ("GTMax Energy DC duplo 60 kW", "https://www.gtmaxenergy.com.br/carregador-ev-dc-duplo-60kw-estacao-de-carga-rapida-gtmax-energy"),
    ("GreenV Turbo Slim DC 60 kW", "https://loja.greenv.com.br/carregador-turbo-slim-dc-60-kw"),
    ("NeoCharge NDC60", "https://www.neocharge.com.br/loja/carregador-carro-eletrico-dc-ndc60-60kw.html"),
    ("CitrineOS: servidor OCPP de código aberto (LF Energy)", "https://lfenergy.org/projects/citrineos/"),
    ("CitrineOS no GitHub (Apache 2.0)", "https://github.com/citrineos/citrineos-core"),
    ("SteVe: servidor OCPP 1.6 de código aberto (GPL-3)", "https://github.com/steve-community/steve"),
    ("Taxas de Pix para empresas em 2026 (Nuvemshop)", "https://www.nuvemshop.com.br/blog/pix-pessoa-juridica/"),
]


def sources_html():
    return "".join(f'<li><a href="{html.escape(u)}" target="_blank" rel="noopener">{html.escape(t)}</a></li>' for t, u in SOURCES)


def credits_html():
    out = []
    for k, (a, lic, f) in CREDITS.items():
        u = "https://commons.wikimedia.org/wiki/File:" + f.replace(" ", "_")
        out.append(f'<li><a href="{html.escape(u)}" target="_blank" rel="noopener">{html.escape(f.replace("_"," "))}</a> · {html.escape(a)} · {lic}</li>')
    return "".join(out)


def build():
    with open(os.path.join(HERE, "template.html"), encoding="utf-8") as f:
        t = f.read()
    rep = {
        "BH_SALES_SHARE": fmt(bh_sales_share, 1), "BH_CHG_SHARE": fmt(bh_chg_share, 1),
        "BH_CHG_GAP": fmt(bh_sales_share / bh_chg_share, 1),
        "CAPEX_K": fmt(CAPEX / 1000), "PB_BASE": str(R["Base"]["pb"]), "PB_OPT": str(R["Otimista"]["pb"]),
        "PB_LEVER": str(lever["pb"]),
        "OWN_PB": str(own["pb"]), "OWN_GAIN": brl(own_res - base_res), "OWN_RES": brl(own_res), "BASE_RES": brl(base_res),
        "THIRD_FEE": "≈ " + brl(round(third_fee, -1)), "THIRD_FEE5": brl(round(third_fee * 5, -2)),
        "CHART_SALES": chart_sales(), "CHART_GAP": chart_gap(), "CHART_SCORES": chart_scores(), "CHART_CASH": chart_cash(),
        "MAP": map_svg(), "MAP_LIST": map_list(), "PLACES": places_html(),
        "CAPEX_ROWS": capex_rows(), "SCEN_ROWS": scen_rows(), "SENS_ROWS": sens_rows(),
        "P": fmt(P, 2), "E": fmt(E, 2), "MARGIN": fmt(margin, 2), "FIX": fmt(FIX),
        "PER_SESSION": fmt(per_session), "BE_DAY": fmt(be_day, 1),
        "SOURCES": sources_html(), "CREDITS": credits_html(),
    }
    for k in ("c_ac", "c_dc", "c_hpc"):
        rep["IMG_" + k] = img(k)
        rep["CR_" + k] = credit(k)
    for k, v in rep.items():
        t = t.replace("{{" + k + "}}", v)
    assert "{{" not in t, t[t.index("{{"):t.index("{{") + 40]
    os.makedirs(os.path.join(ROOT, "site"), exist_ok=True)
    with open(os.path.join(ROOT, "site", "artifact.html"), "w", encoding="utf-8") as f:
        f.write(t)
    head_end = t.index("</style>") + len("</style>")
    full = ('<!doctype html>\n<html lang="pt-BR">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            + t[:head_end] + "\n</head>\n<body>\n" + t[head_end:] + "\n</body>\n</html>\n")
    with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8") as f:
        f.write(full)
    print("own", own["pb"], round(own_res), round(base_res), round(third_fee))
    print("capex", CAPEX, "margin", round(margin, 3), "be/day", round(be_day, 2), "lever pb", lever["pb"])
    for k, r in R.items():
        print(k, "pb", r["pb"], "npv", round(r["npv"]))
    print("ranking", [(p["rank"], p["name"], p["score"]) for p in PLACES])


if __name__ == "__main__":
    build()
