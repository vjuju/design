"""Génère les SVG du logo gigot.app (texte vectorisé en Titan One)."""
import sys, os
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen

FONT = TTFont(os.environ.get("TITAN_ONE_TTF", os.path.join(os.path.dirname(__file__), "TitanOne-Regular.ttf")))
UPM = FONT["head"].unitsPerEm
CMAP = FONT.getBestCmap()
GS = FONT.getGlyphSet()
HHEA = FONT["hhea"]

def text_path(txt, size, x, baseline, spacing=0.0):
    """Chemin SVG d'un texte, origine gauche à x, ligne de base à baseline."""
    s = size / UPM
    pen = SVGPathPen(GS, ntos=lambda v: ("%.1f" % v).rstrip("0").rstrip("."))
    cx = x
    for ch in txt:
        g = CMAP[ord(ch)]
        tp = TransformPen(pen, (s, 0, 0, -s, cx, baseline))
        GS[g].draw(tp)
        cx += GS[g].width * s + spacing
    return pen.getCommands(), cx - x - spacing

def width(txt, size, spacing=0.0):
    s = size / UPM
    return sum(GS[CMAP[ord(c)]].width * s for c in txt) + spacing * (len(txt) - 1)

def r(v): return round(v, 1)

# ---- mise en page (identique à la maquette 600×600) ----
W = H = 600
SIZE, GAP_O, O_BOX = 160, 4, 136
TAG_SIZE, TAG_SP, ROW_GAP = 36, 3, 28
asc, desc = HHEA.ascent, -HHEA.descent
line = SIZE  # line-height: 1
base_in_line = (line - (asc + desc) * SIZE / UPM) / 2 + asc * SIZE / UPM
tag_line = TAG_SIZE * 1.1
tag_base_in_line = (tag_line - (asc + desc) * TAG_SIZE / UPM) / 2 + asc * TAG_SIZE / UPM

block_h = line + ROW_GAP + tag_line
top = (H - block_h) / 2
row_w = width("gig", SIZE) + GAP_O + O_BOX + GAP_O + width("t", SIZE)
x0 = (W - row_w) / 2
base = top + base_in_line

gig_d, gig_w = text_path("gig", SIZE, x0, base)
ox = x0 + gig_w + GAP_O
t_d, _ = text_path("t", SIZE, ox + O_BOX + GAP_O, base)
oy = top + (line - O_BOX) / 2 - 12          # O remonté (margin-top -24)
tag = "L'APP POUR GIGOTER"
tw = width(tag, TAG_SIZE, TAG_SP)
tag_d, _ = text_path(tag, TAG_SIZE, (W - tw) / 2, top + line + ROW_GAP + tag_base_in_line, TAG_SP)
# l'O (version picto) : contenu de -2 à 134 → origine décalée de 2 ;
# centre de la face gardé à la même hauteur qu'avant (top + 66)
OX, OY = r(ox + 2), r(top + 66 - 58)

TEMPLATE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 600" width="600" height="600">
  <title>gigot — l'app pour gigoter</title>
  <style>
    .fond    {{ fill: {fond}; }}
    .lettres {{ fill: {lettres}; }}
    .o       {{ fill: {o}; }}
    .contour {{ fill: {contour}; }}
    .encre   {{ color: {encre}; }} /* ombre, arcs et tagline : noir ou blanc */
  </style>
  <defs>
    <path id="gig" d="{gig}"/>
    <path id="t" d="{t}"/>
  </defs>

  <rect class="fond" width="600" height="600"/>

  <!-- ombre portée des lettres -->
  <g class="encre" fill="currentColor" stroke="currentColor" stroke-width="6" stroke-linejoin="round" transform="translate(10 10)">
    <use href="#gig"/><use href="#t"/>
  </g>
  <!-- lettres gig + t -->
  <g class="lettres" stroke="#111111" stroke-width="6" stroke-linejoin="round">
    <use href="#gig"/><use href="#t"/>
  </g>

  <!-- le O : arcs de mouvement, contour (flanc) décalé, face, rond central -->
  <g transform="translate({OX} {OY})">
    <g class="encre" fill="none" stroke="currentColor" stroke-width="7" stroke-linecap="round">
      <path d="M1.6 37.5A60 60 0 0 1 37.5 1.6"/>
      <path d="M128.4 92.5A60 60 0 0 1 92.5 128.4"/>
    </g>
    <circle class="contour" cx="72" cy="72" r="46" stroke="#111111" stroke-width="7"/>
    <circle class="o" cx="58" cy="58" r="46" stroke="#111111" stroke-width="7"/>
    <circle cx="58" cy="58" r="13" fill="#111111"/>
  </g>

  <!-- tagline -->
  <path class="encre" fill="currentColor" d="{tag}"/>
</svg>
"""

PALETTE = {
    "noir": "#111111", "blanc": "#FFFFFF", "rose": "#FF3EA5", "jaune": "#FFD60A",
    "violet": "#7B2FF7", "cyan": "#2EC4F1", "vert": "#39D353", "orange": "#FF6A13",
}
# encre blanche seulement sur les fonds sombres (contraste ≥ 4,5 : noir, violet)
ENCRE_BLANCHE = {"noir", "violet"}

# ---- version animée : le mot seul, fond transparent, sans tagline ----
# Lettres, face et flanc parcourent les six couleurs flash dans l'ordre des teintes,
# en fondu continu, sans pause. Elles partent à deux crans d'écart et avancent
# ensemble : jamais deux parties de la même couleur.
CYCLE = ["rose", "orange", "jaune", "vert", "cyan", "violet"]
DEPART = {"lettres": "jaune", "o": "cyan", "contour": "rose"}
PAS = 4.0   # secondes de fondu d'une couleur à la suivante

def bounds(txt, size, x, baseline):
    s = size / UPM
    bp = BoundsPen(GS)
    cx = x
    for ch in txt:
        g = CMAP[ord(ch)]
        GS[g].draw(TransformPen(bp, (s, 0, 0, -s, cx, baseline)))
        cx += GS[g].width * s
    return bp.bounds   # (xmin, ymin, xmax, ymax) en coordonnées SVG

def make_anime():
    n, duree = len(CYCLE), len(CYCLE) * PAS
    pct = lambda i: ("%.2f" % (100 * i / n)).rstrip("0").rstrip(".")
    etapes = "\n      ".join(f"{pct(i)}% {{ fill: {PALETTE[c]}; }}" for i, c in enumerate(CYCLE))
    etapes += f"\n      100% {{ fill: {PALETTE[CYCLE[0]]}; }}"
    regles = "".join(
        f"\n      .{cls} {{ animation: gigot-couleurs {duree:g}s linear {-CYCLE.index(c) * PAS:g}s infinite; }}"
        for cls, c in DEPART.items())
    # cadrage : lettres (contour 3 + ombre décalée de 10), O (arcs jusqu'à -2 / 132)
    g0, t0 = bounds("gig", SIZE, x0, base), bounds("t", SIZE, ox + O_BOX + GAP_O, base)
    m = 6
    x1, y1 = min(g0[0], OX - 2) - 3 - m, min(g0[1], t0[1], OY - 2) - 3 - m
    x2, y2 = max(t0[2], OX + 132) + 13 + m, max(g0[3], t0[3], OY + 132) + 13 + m
    vb = " ".join(("%.1f" % v).rstrip("0").rstrip(".") for v in (x1, y1, x2 - x1, y2 - y1))
    w, h = round(x2 - x1), round(y2 - y1)
    P = PALETTE
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}" width="{w}" height="{h}">
  <title>gigot</title>
  <style>
    .lettres {{ fill: {P[DEPART["lettres"]]}; }}
    .o       {{ fill: {P[DEPART["o"]]}; }}
    .contour {{ fill: {P[DEPART["contour"]]}; }}
    .encre   {{ color: {P["noir"]}; }} /* ombre et arcs */
    /* couleurs en cycle, fondu continu ; mouvement réduit : couleurs fixes ci-dessus */
    @keyframes gigot-couleurs {{
      {etapes}
    }}
    @media (prefers-reduced-motion: no-preference) {{{regles}
    }}
  </style>
  <defs>
    <path id="gig" d="{gig_d}"/>
    <path id="t" d="{t_d}"/>
  </defs>

  <!-- ombre portée des lettres -->
  <g class="encre" fill="currentColor" stroke="currentColor" stroke-width="6" stroke-linejoin="round" transform="translate(10 10)">
    <use href="#gig"/><use href="#t"/>
  </g>
  <!-- lettres gig + t -->
  <g class="lettres" stroke="#111111" stroke-width="6" stroke-linejoin="round">
    <use href="#gig"/><use href="#t"/>
  </g>

  <!-- le O : arcs de mouvement, contour (flanc) décalé, face, rond central -->
  <g transform="translate({OX} {OY})">
    <g class="encre" fill="none" stroke="currentColor" stroke-width="7" stroke-linecap="round">
      <path d="M1.6 37.5A60 60 0 0 1 37.5 1.6"/>
      <path d="M128.4 92.5A60 60 0 0 1 92.5 128.4"/>
    </g>
    <circle class="contour" cx="72" cy="72" r="46" stroke="#111111" stroke-width="7"/>
    <circle class="o" cx="58" cy="58" r="46" stroke="#111111" stroke-width="7"/>
    <circle cx="58" cy="58" r="13" fill="#111111"/>
  </g>
</svg>
"""

def make(fond, lettres, o, contour):
    assert len({fond, lettres, o, contour}) == 4, "quatre couleurs distinctes requises"
    encre = "blanc" if fond in ENCRE_BLANCHE else "noir"
    P = PALETTE
    return TEMPLATE.format(fond=P[fond], lettres=P[lettres], o=P[o], contour=P[contour],
                           encre=P[encre], gig=gig_d, t=t_d, tag=tag_d, OX=OX, OY=OY)

VERSIONS = [
    ("rose",   "jaune",  "cyan",   "violet"),
    ("jaune",  "rose",   "cyan",   "violet"),
    ("cyan",   "blanc",  "jaune",  "rose"),
    ("vert",   "blanc",  "rose",   "violet"),
    ("orange", "blanc",  "jaune",  "violet"),
    ("violet", "jaune",  "rose",   "cyan"),
    ("noir",   "jaune",  "rose",   "violet"),
    ("blanc",  "rose",   "jaune",  "violet"),
]

if __name__ == "__main__":
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    for v in VERSIONS:
        name = f"gigot-logo-{v[0]}.svg"
        with open(os.path.join(out, name), "w") as f:
            f.write(make(*v))
        print(name)
    with open(os.path.join(out, "gigot-logo-anime.svg"), "w") as f:
        f.write(make_anime())
    print("gigot-logo-anime.svg")
