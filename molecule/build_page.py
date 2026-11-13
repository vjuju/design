#!/usr/bin/env python3
"""Tire la série de référence dans output/ puis génère index.html, la planche.

Chaque image est un fichier SVG ; la planche les affiche avec un lien de
téléchargement et la commande qui la refait à l'identique.
"""

import html
import json
from pathlib import Path

from molecule import PALETTES, composer

HERE = Path(__file__).parent
OUT = HERE / "output"

# La série : (seed, palette, réglages particuliers)
SERIE = [
    (3, "aurore", dict(titre="ABSTRACT", sous_titre="SPACE")),
    (11, "lagon", dict(titre="TECHNOLOGY", sous_titre="CONNECT")),
    (8, "sous-bois", dict(titre="RELIER", sous_titre="LE VIVANT")),
    (21, "corail", dict(zone="partout", molecules=4)),
    (5, "nuit", dict(zone="partout", molecules=4)),
    (14, "aurore", dict(zone="bas", fusion=1.6)),
    (30, "lagon", dict(format_="carre", zone="partout", molecules=5, atomes=(5, 9))),
    (42, "sous-bois", dict(format_="carre", zone="partout", molecules=4, anneaux=0.5)),
    (9, "nuit", dict(format_="paysage", zone="partout", molecules=6, atomes=(5, 10))),
]

PAGE = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Molécules</title>
<meta name="description" content="Molécules qui fusionnent comme des gouttes, générées en SVG vectoriel, un dégradé par molécule.">
<style>
  :root {{ --paper: #f2f1ee; --ink: #24232a; --muted: #6b6a72; --card: #fff; }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --paper: #17161c; --ink: #ecebf2; --muted: #9a99a6; --card: #222129; }}
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: var(--paper); color: var(--ink);
         font: 16px/1.5 "Helvetica Neue", Helvetica, Arial, sans-serif; }}
  header {{ max-width: 1200px; margin: 0 auto; padding: 48px 16px 24px; }}
  h1 {{ font-weight: 400; letter-spacing: .3em; text-transform: uppercase; font-size: 28px; margin: 0 0 12px; }}
  header p {{ color: var(--muted); max-width: 640px; margin: 0; }}
  main {{ max-width: 1200px; margin: 0 auto; padding: 16px 16px 64px;
          display: grid; gap: 24px; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); }}
  figure {{ margin: 0; background: var(--card); border-radius: 6px; overflow: hidden;
            box-shadow: 0 1px 3px rgb(0 0 0 / .08); }}
  figure.large {{ grid-column: span 2; }}
  @media (max-width: 600px) {{ figure.large {{ grid-column: auto; }} }}
  img {{ display: block; width: 100%; height: auto; }}
  figcaption {{ padding: 10px 12px 12px; font-size: 13px; color: var(--muted); }}
  figcaption a {{ color: var(--ink); }}
  code {{ display: block; margin-top: 6px; font-size: 11px; overflow-wrap: anywhere; }}
</style>
</head>
<body>
<header>
  <h1>Molécules</h1>
  <p>Des atomes reliés par des liaisons, fondus comme des gouttes. Chaque image est un
  SVG vectoriel pur (tracés de Bézier, dégradés linéaires), éditable dans Figma ou
  Illustrator. Même graine, même image.</p>
</header>
<main>
{cartes}
</main>
</body>
</html>
"""


def commande(rec: dict) -> str:
    parts = [f"python3 molecule.py --seed {rec['seed']} --palette {rec['palette']}"]
    if rec["format"] != "affiche":
        parts.append(f"--format {rec['format']}")
    parts.append(f"--zone {rec['zone']}")
    if rec["molecules"] != 3:
        parts.append(f"--molecules {rec['molecules']}")
    if rec["atomes"] != [6, 11]:
        parts.append(f"--atomes {rec['atomes'][0]} {rec['atomes'][1]}")
    if rec["anneaux"] != 0.25:
        parts.append(f"--anneaux {rec['anneaux']}")
    if rec["fusion"] != 1.0:
        parts.append(f"--fusion {rec['fusion']}")
    if rec["titre"]:
        parts.append(f'--titre "{rec["titre"]}"')
    if rec["sous_titre"]:
        parts.append(f'--sous-titre "{rec["sous_titre"]}"')
    return " ".join(parts)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    for f in OUT.glob("*.svg"):
        f.unlink()
    recettes, cartes = [], []
    for seed, palette, reglages in SERIE:
        reglages = {"zone": "droite", **reglages}
        svg, rec = composer(seed, palette, **reglages)
        nom = f"molecule-{palette}-{seed}.svg"
        (OUT / nom).write_text(svg, encoding="utf-8")
        rec["fichier"] = nom
        recettes.append(rec)
        large = ' class="large"' if rec["format"] == "paysage" else ""
        cartes.append(
            f'<figure{large}><img src="output/{nom}" alt="Molécules, palette {palette}" loading="lazy">'
            f'<figcaption><a href="output/{nom}" download>{nom}</a>'
            f'<code>{html.escape(commande(rec))}</code></figcaption></figure>')
    (OUT / "recettes.json").write_text(json.dumps(recettes, indent=2, ensure_ascii=False),
                                       encoding="utf-8")
    (HERE / "index.html").write_text(PAGE.format(cartes="\n".join(cartes)), encoding="utf-8")
    print(f"{len(SERIE)} images, index.html écrit ; palettes : {', '.join(PALETTES)}")


if __name__ == "__main__":
    main()
