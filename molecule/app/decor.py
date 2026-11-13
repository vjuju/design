#!/usr/bin/env python3
"""Génère les SVG de l'app (logo, avatar de Glia, bandeau du fil) avec molecule.py.

    python3 decor.py

Fonds transparents : les formes se posent sur la couleur de la page, claire ou
sombre.
"""

import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))

from molecule import Atome, Molecule, composer, trace  # noqa: E402


def degrade(id_, couleurs, x1, y1, x2, y2):
    arrets = "".join(f'<stop offset="{i / (len(couleurs) - 1):.2f}" stop-color="{c}"/>'
                     for i, c in enumerate(couleurs))
    return (f'<linearGradient id="{id_}" gradientUnits="userSpaceOnUse" x1="{x1}" y1="{y1}" '
            f'x2="{x2}" y2="{y2}">{arrets}</linearGradient>')


def petite(atomes, liens, couleurs, taille, nom):
    """Une molécule dessinée à la main : atomes (x, y, r) et liaisons (i, j, col)."""
    m = Molecule([Atome(*a) for a in atomes], liens)
    d = trace(m, k=taille * .05, pas=taille / 200, ecart=taille / 80, evasement=1.0)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {taille} {taille}">'
           f'<defs>{degrade("g", couleurs, 0, taille, taille, 0)}</defs>'
           f'<path fill="url(#g)" d="{d}"/></svg>\n')
    (HERE / nom).write_text(svg, encoding="utf-8")


# Logo : trois atomes en équerre, la signature des molécules.
petite([(30, 68, 20), (66, 70, 12), (70, 32, 17)], [(0, 1, 6), (1, 2, 5)],
       ["#d36ee0", "#7c8cf0", "#4aa8f5"], 100, "logo.svg")
# Glia : deux atomes, l'un sort de l'autre.
petite([(38, 60, 26), (74, 30, 13)], [(0, 1, 7)], ["#12c9de", "#7fcf98"], 100, "glia.svg")

# Bandeau d'en-tête : une composition large et basse, fond retiré.
import molecule  # noqa: E402
molecule.FORMATS["bandeau"] = (1000, 220)
svg, _ = composer(seed=12, palette="aurore", format_="bandeau", plans=5, atomes=(2, 4),
                  satellites=5, zone="partout", echelle=3.4)
svg = re.sub(r'<rect width="\d+" height="\d+" fill="#[0-9a-f]+"/>', "", svg)
svg = re.sub(r' width="\d+" height="\d+">', ">", svg, count=1)
(HERE / "bandeau.svg").write_text(svg, encoding="utf-8")
print("logo.svg, glia.svg, bandeau.svg")
