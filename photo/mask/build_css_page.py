#!/usr/bin/env python3
"""Génère css/index.html : la même bichromie, mais calculée par le navigateur.

Aucun pixel n'est cuit à l'avance ici. La page charge les photos d'origine et
refait le traitement en CSS :

* la bichromie par un filtre SVG inline (`filter: url(#...)`) ;
* l'aplat par un `clip-path` en `mix-blend-mode: multiply`.

Les valeurs des filtres et la géométrie des formes viennent de `mask.py` et de
`output/recipes.json` : les deux rendus décrivent la même chose, ce qui permet
de les superposer et de regarder l'écart.

Pas une ligne de JavaScript — le sélecteur de vue est un groupe de boutons
radio et quelques sélecteurs `:checked ~`.
"""

import html
import json
from pathlib import Path

from PIL import Image

import mask

HERE = Path(__file__).parent
OUT = HERE / "css"

# Luma ITU-R 601, les coefficients qu'utilise ImageOps.grayscale de Pillow.
# `saturate 0` en SVG utiliserait le Rec. 709 (0.2126 / 0.7152 / 0.0722) et
# décalerait tous les demi-tons par rapport au rendu Python.
LUMA = (0.299, 0.587, 0.114)

# 0.55 × 20 = 11 : avec 21 points, le coude de la rampe tombe exactement sur un
# nœud de la table, et l'interpolation du navigateur redonne la courbe au bit
# près. Le contraste est sorti de la table et passé en transfert linéaire, qui
# est exact lui aussi — sans quoi ses deux ruptures de pente obligeraient à une
# table bien plus dense pour une fidélité moindre.
TABLE_POINTS = 21

SHAPE_LABELS = {"triangle": "triangle", "circle": "cercle", "rectangle": "rectangle"}

SHAPE_GLYPHS = {
    "triangle": '<svg viewBox="0 0 16 16" aria-hidden="true"><polygon points="8,2 15,14 1,14"/></svg>',
    "circle": '<svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="6.5"/></svg>',
    "rectangle": '<svg viewBox="0 0 16 16" aria-hidden="true"><rect x="1.5" y="3" width="13" height="10"/></svg>',
}


def num(value: float, digits: int = 4) -> str:
    """Nombre court : pas de zéros inutiles, pas de notation scientifique."""
    text = f"{value:.{digits}f}".rstrip("0").rstrip(".")
    return text or "0"


def svg_filter(index: int, recipe: dict) -> str:
    """Le filtre SVG qui reproduit `mask.duotone` pour une recette donnée."""
    color = mask.hex_to_rgb(recipe["duotone_color"])
    contrast = recipe["contrast"]
    ramp = mask.transfer_curve(color, contrast=1.0, samples=TABLE_POINTS)

    # feFunc type="linear" : C' = slope × C + intercept, borné à [0, 1] par le
    # filtre — exactement le contraste autour du gris moyen appliqué en Python.
    slope = num(contrast)
    intercept = num((1 - contrast) / 2)

    row = " ".join(num(c) for c in LUMA)
    matrix = f"{row} 0 0  {row} 0 0  {row} 0 0  0 0 0 1 0"

    tables = "\n".join(
        f'      <feFunc{ch} type="table" tableValues="{" ".join(num(v) for v in ramp[i])}"/>'
        for i, ch in enumerate("RGB")
    )
    linears = "\n".join(
        f'      <feFunc{ch} type="linear" slope="{slope}" intercept="{intercept}"/>'
        for ch in "RGB"
    )

    return f'''    <filter id="duo-{index:02d}" x="0" y="0" width="100%" height="100%"
            color-interpolation-filters="sRGB">
      <feColorMatrix type="matrix" values="{matrix}"/>
      <feComponentTransfer>
{linears}
      </feComponentTransfer>
      <feComponentTransfer>
{tables}
      </feComponentTransfer>
    </filter>'''


def clip_path(geometry: dict) -> str:
    """La géométrie de `mask.shape_geometry`, traduite en clip-path CSS.

    Les coordonnées sont déjà normalisées par axe, et un pourcentage de
    clip-path se résout sur la dimension correspondante de la boîte : la
    traduction est directe, sans dépendre de la taille d'affichage.
    """
    if geometry["shape"] == "circle":
        return (f'ellipse({num(geometry["rx"] * 100, 3)}% {num(geometry["ry"] * 100, 3)}% '
                f'at {num(geometry["cx"] * 100, 3)}% {num(geometry["cy"] * 100, 3)}%)')
    points = ", ".join(f'{num(x * 100, 3)}% {num(y * 100, 3)}%' for x, y in geometry["points"])
    return f"polygon({points})"


CARD = '''      <figure style="--ratio: {w} / {h}; --duo: url(#duo-{index:02d}); --flat: {shape_color}; --clip: {clip}; --op: {opacity}">
        <div class="frame">
          <img class="live" src="../sources/{source}" alt="{alt} — bichromie {duotone_name} avec un {shape_label} en multiply" loading="lazy" decoding="async">
          <span class="flat"></span>
          <img class="baked" src="../output/{output}" alt="" aria-hidden="true" loading="lazy" decoding="async">
        </div>
        <figcaption>
          <div class="recipe">
            <span class="chip" title="encre de la bichromie"><span class="swatch" style="background:{duotone_color}"></span>{duotone_name}</span>
            <span class="chip" title="aplat en multiply">{glyph}<span class="swatch" style="background:{shape_color}"></span>{opacity_pct}&nbsp;%</span>
          </div>
          <p class="credit">{alt}<br>photo <a href="{page}">{author}</a> · <span class="seed">seed {seed}</span></p>
        </figcaption>
      </figure>'''


def main() -> int:
    sources = {p["file"]: p for p in json.loads((HERE / "sources.json").read_text(encoding="utf-8"))}
    recipes = json.loads((HERE / "output" / "recipes.json").read_text(encoding="utf-8"))

    filters, cards = [], []
    for index, recipe in enumerate(recipes, start=1):
        photo = sources[recipe["source"]]
        with Image.open(HERE / "sources" / recipe["source"]) as im:
            width, height = im.size

        filters.append(svg_filter(index, recipe))
        cards.append(CARD.format(
            index=index,
            w=width,
            h=height,
            source=recipe["source"],
            output=recipe["output"],
            alt=html.escape(photo["alt"]),
            page=html.escape(photo["page"]),
            author=html.escape(photo["author"]),
            duotone_color=recipe["duotone_color"],
            duotone_name=html.escape(recipe["duotone_name"]),
            shape_color=recipe["shape_color"],
            shape_label=SHAPE_LABELS[recipe["shape"]],
            glyph=SHAPE_GLYPHS[recipe["shape"]],
            clip=clip_path(recipe["geometry"]),
            opacity=num(recipe["opacity"]),
            opacity_pct=round(recipe["opacity"] * 100),
            seed=recipe["seed"],
        ))

    template = (HERE / "css_template.html").read_text(encoding="utf-8")
    page = template.replace("<!--FILTERS-->", "\n".join(filters)) \
                   .replace("<!--CARDS-->", "\n".join(cards)) \
                   .replace("<!--COUNT-->", str(len(recipes))) \
                   .replace("<!--POINTS-->", str(TABLE_POINTS))

    OUT.mkdir(exist_ok=True)
    (OUT / "index.html").write_text(page, encoding="utf-8")
    print(f"{OUT / 'index.html'} — {len(recipes)} rendus, {len(filters)} filtres SVG")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
