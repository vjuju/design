#!/usr/bin/env python3
"""Génère index.html à partir de output/*/seeds.json et de ../mask/sources.json.

Comme pour photo/mask, la page est autonome : tout est écrit en dur dans le
HTML, rien n'est chargé au moment de l'affichage.
"""

import html
import json
from pathlib import Path

import pop

HERE = Path(__file__).parent

SCRIPTS = [
    ("figures", "Figures",
     "Chaque sujet saillant reçoit une silhouette de couleur élargie, décalée comme un "
     "repérage raté, cernée de noir. Le sujet principal vibre."),
    ("ondes", "Ondes",
     "Le sujet principal est cerné de noir et émet des anneaux de couleur qui épousent "
     "sa forme, séparés par un liseré blanc, puis des traits rayonnants."),
    ("plages", "Plages",
     "La photo est réduite à ses grandes masses de couleur ; chacune devient une plage "
     "peinte, deux voisines n'ont jamais la même teinte, les frontières sont tracées au "
     "gros trait. Le sujet reste la photo."),
]

PAGE = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Aplats pop</title>
<meta name="description" content="Trois scripts sans IA qui posent sur n'importe quelle photo des aplats de couleur, des contours noirs et des traits de vibration à la Keith Haring.">
<style>
  :root {{
    --paper: {fond};
    --ink: {contour};
    --muted: #6b6762;
    --rule: #e2dfdb;
    --card: #ffffff;
    --shadow: 0 1px 2px rgba(29, 27, 26, .06), 0 10px 28px rgba(29, 27, 26, .07);
  }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{
      --paper: #141312;
      --ink: {fond};
      --muted: #a29d97;
      --rule: #2d2a28;
      --card: #1d1b1a;
      --shadow: 0 1px 2px rgba(0, 0, 0, .5), 0 10px 28px rgba(0, 0, 0, .45);
    }}
  }}

  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    padding: 0 16px 96px;
    background: var(--paper);
    color: var(--ink);
    font: 16px/1.55 ui-sans-serif, system-ui, -apple-system, "Segoe UI", Inter, Helvetica, Arial, sans-serif;
    -webkit-font-smoothing: antialiased;
  }}
  .wrap {{ max-width: 1180px; margin: 0 auto; }}
  a {{ color: inherit; text-underline-offset: 2px; }}
  code {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 13px; }}

  header {{ padding: 64px 0 36px; display: grid; gap: 28px; grid-template-columns: 1.1fr 1fr; align-items: end; }}
  .back {{ grid-column: 1 / -1; font-size: 14px; color: var(--muted); }}
  h1 {{
    margin: 0; font-size: clamp(54px, 11vw, 132px); line-height: .84;
    letter-spacing: -.05em; font-weight: 900; text-transform: uppercase;
  }}
  h1 span {{ display: inline-block; padding: 0 .08em; border: .07em solid var(--ink); border-radius: .18em; }}
  .lede {{ margin: 0; color: var(--muted); max-width: 52ch; }}
  .palette {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 18px; }}
  .chip {{
    display: flex; align-items: center; gap: 7px; font-size: 12.5px;
    padding: 4px 10px 4px 4px; border: 2px solid var(--ink); border-radius: 99px;
  }}
  .chip i {{ width: 18px; height: 18px; border-radius: 50%; border: 2px solid var(--ink); }}

  .source {{ display: grid; grid-template-columns: minmax(0, 2fr) minmax(0, 1fr); gap: 24px; align-items: center;
             padding: 28px 0 8px; border-top: 3px solid var(--ink); }}
  .source img {{ width: 100%; display: block; border-radius: 3px; box-shadow: var(--shadow); }}
  .source p {{ margin: 0; color: var(--muted); font-size: 15px; }}

  section {{ margin-top: 64px; padding-top: 24px; border-top: 3px solid var(--ink); }}
  .head {{ display: flex; flex-wrap: wrap; gap: 10px 22px; align-items: baseline; }}
  h2 {{ margin: 0; font-size: clamp(34px, 5vw, 54px); letter-spacing: -.035em; line-height: 1; font-weight: 900; }}
  h2 em {{ font-style: normal; display: inline-block; width: .55em; height: .55em; border-radius: 50%;
           border: .09em solid var(--ink); margin-right: .2em; vertical-align: .02em; }}
  .head p {{ margin: 0; color: var(--muted); max-width: 62ch; flex: 1 1 320px; }}
  .cmd {{ margin: 14px 0 0; padding: 10px 14px; background: var(--card); border-radius: 3px;
          box-shadow: var(--shadow); overflow-x: auto; white-space: nowrap; }}

  .trio {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; margin-top: 22px; }}
  .grid {{ display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 10px; margin-top: 14px; }}
  figure {{ margin: 0; background: var(--card); border-radius: 3px; overflow: hidden; box-shadow: var(--shadow); }}
  figure img {{ width: 100%; display: block; height: auto; }}
  .grid img {{ aspect-ratio: 2 / 3; object-fit: cover; }}
  figcaption {{ padding: 7px 10px 9px; font-size: 12px; color: var(--muted); line-height: 1.4; }}
  .seed {{ white-space: nowrap; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 11px; }}

  footer {{ margin-top: 72px; padding-top: 24px; border-top: 1px solid var(--rule); color: var(--muted); font-size: 14px; }}

  @media (max-width: 900px) {{
    header {{ grid-template-columns: 1fr; padding-top: 40px; }}
    .grid {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
  }}
  @media (max-width: 620px) {{
    .source {{ grid-template-columns: 1fr; }}
    .trio {{ grid-template-columns: 1fr; }}
    .grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
  }}
</style>
</head>
<body>
<div class="wrap">

<header>
  <a class="back" href="../../">← bac à sable</a>
  <h1>Aplats<br><span>pop</span></h1>
  <div>
    <p class="lede">Trois scripts qui posent sur n'importe quelle photo des aplats de couleur,
    de gros contours noirs et des traits de vibration, à la manière de Keith Haring.
    Aucune IA : la photo n'est jamais retouchée, elle est seulement analysée
    (contraste, couleur dominante, quantification) pour savoir où peindre.
    <a href="web/">La version vivante, dans le navigateur →</a></p>
    <div class="palette">{chips}</div>
  </div>
</header>

<div class="source">
  <img src="sources/00-galerie.jpg" alt="Un couple de dos devant une spirale noire et blanche, dans une galerie blanche" width="798" height="400">
  <p><strong>La photo de départ.</strong> Chaque script la reçoit telle quelle, sans
  réglage propre : trois tirages par script ci-dessous. Puis les mêmes scripts,
  toujours sans réglage, sur les douze photos de la piste <a href="../mask/">mask</a>.</p>
</div>

{sections}

<footer>
  <p>Scripts : <code>pop.py</code> (outils communs), <code>figures.py</code>, <code>ondes.py</code>,
  <code>plages.py</code> — Pillow et numpy, rien d'autre. Sources sur
  <a href="https://github.com/vjuju/design/tree/main/photo/aplats">github.com/vjuju/design</a>.
  Photos des douze vignettes sous <a href="https://unsplash.com/license">licence Unsplash</a>.</p>
</footer>

</div>
</body>
</html>
"""

SECTION = """<section>
  <div class="head">
    <h2><em style="background:{color}"></em>{title}</h2>
    <p>{text}</p>
  </div>
  <div class="cmd"><code>python3 {name}.py photo.jpg --variants 3</code></div>
  <div class="trio">{trio}</div>
  <div class="grid">{grid}</div>
</section>"""


def fig(src: str, alt: str, caption: str, size) -> str:
    return (f'<figure><img src="{src}" alt="{html.escape(alt)}" width="{size[0]}" height="{size[1]}" '
            f'loading="lazy"><figcaption>{caption}</figcaption></figure>')


def main() -> None:
    from PIL import Image

    credits = {s["file"]: s for s in json.loads((HERE / "../mask/sources.json").read_text())}
    chips = "".join(f'<span class="chip"><i style="background:{v}"></i>{k} <code>{v}</code></span>'
                    for k, v in [("fond", pop.FOND), ("contour", pop.CONTOUR), *pop.COULEURS.items()])
    colors = list(pop.COULEURS.values())

    sections = []
    for n, (name, title, text) in enumerate(SCRIPTS):
        seeds = json.loads((HERE / "output" / name / "seeds.json").read_text())
        trio, grid = [], []
        for f, seed in seeds.items():
            src = f"output/{name}/{f}"
            size = Image.open(HERE / src).size
            seed_tag = f'<span class="seed">--seed {seed}</span>'
            if f.startswith("00-galerie"):
                trio.append(fig(src, f"La galerie, traitement {title.lower()}", f"tirage {f[-5]} · {seed_tag}", size))
            else:
                c = credits[f]
                cap = f'<a href="{c["page"]}">{html.escape(c["author"])}</a><br>{seed_tag}'
                grid.append(fig(src, f'{c["alt"]}, traitement {title.lower()}', cap, size))
        sections.append(SECTION.format(name=name, title=title, text=html.escape(text),
                                       color=colors[n * 2 % len(colors)],
                                       trio="".join(trio), grid="".join(grid)))

    page = PAGE.format(fond=pop.FOND, contour=pop.CONTOUR, chips=chips, sections="\n\n".join(sections))
    (HERE / "index.html").write_text(page)
    print("index.html")


if __name__ == "__main__":
    main()
