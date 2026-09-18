#!/usr/bin/env python3
"""Génère index.html à partir de sources.json et output/recipes.json.

La page est volontairement autonome : pas de fetch au chargement (une page
ouverte en file:// ne peut pas lire un JSON voisin), pas de dépendance
externe. Tout ce qui vient des deux manifestes est écrit en dur dans le HTML.
"""

import html
import json
from pathlib import Path

HERE = Path(__file__).parent

SHAPE_LABELS = {"triangle": "triangle", "circle": "cercle", "rectangle": "rectangle"}

SHAPE_GLYPHS = {
    "triangle": '<svg viewBox="0 0 16 16" aria-hidden="true"><polygon points="8,2 15,14 1,14"/></svg>',
    "circle": '<svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="6.5"/></svg>',
    "rectangle": '<svg viewBox="0 0 16 16" aria-hidden="true"><rect x="1.5" y="3" width="13" height="10"/></svg>',
}

PAGE = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Mask — bichromie &amp; aplats</title>
<meta name="description" content="Douze photos passées en bichromie noir + une couleur, recouvertes d'une forme aléatoire en fusion multiply.">
<style>
  :root {{
    --paper: #f2efe7;
    --ink: #14130f;
    --muted: #6d6a60;
    --rule: #d8d3c6;
    --card: #ffffff;
    --accent: #e4002b;
    --shadow: 0 1px 2px rgba(20, 19, 15, .06), 0 12px 32px rgba(20, 19, 15, .07);
  }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{
      --paper: #100f0d;
      --ink: #f2efe7;
      --muted: #9a958a;
      --rule: #2c2a25;
      --card: #1a1815;
      --shadow: 0 1px 2px rgba(0, 0, 0, .5), 0 12px 32px rgba(0, 0, 0, .45);
      --accent: #ff4d6d;
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

  header {{ padding: 72px 0 40px; border-bottom: 1px solid var(--rule); }}

  h1 {{
    margin: 0;
    font-size: clamp(44px, 11vw, 132px);
    line-height: .88;
    letter-spacing: -.045em;
    font-weight: 800;
    text-transform: uppercase;
  }}
  h1 em {{ font-style: normal; color: var(--accent); }}

  .lede {{
    margin: 28px 0 0;
    max-width: 58ch;
    font-size: clamp(16px, 2.2vw, 19px);
    color: var(--muted);
  }}

  .meta {{
    margin-top: 28px;
    display: flex;
    flex-wrap: wrap;
    gap: 10px 28px;
    font-size: 13px;
    letter-spacing: .06em;
    text-transform: uppercase;
    color: var(--muted);
  }}

  .toolbar {{
    position: sticky;
    top: 0;
    z-index: 5;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 12px;
    padding: 14px 0;
    margin-bottom: 8px;
    background: color-mix(in srgb, var(--paper) 88%, transparent);
    backdrop-filter: blur(8px);
    border-bottom: 1px solid var(--rule);
  }}
  .toolbar p {{ margin: 0; font-size: 13px; color: var(--muted); }}
  @media (hover: none) {{ .hint {{ display: none; }} }}

  button {{
    font: inherit;
    font-size: 13px;
    letter-spacing: .04em;
    padding: 8px 15px;
    border-radius: 999px;
    border: 1px solid var(--rule);
    background: var(--card);
    color: var(--ink);
    cursor: pointer;
  }}
  button:hover {{ border-color: var(--ink); }}
  button[aria-pressed="true"] {{ background: var(--ink); color: var(--paper); border-color: var(--ink); }}
  button:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 2px; }}

  .grid {{
    margin-top: 32px;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    gap: 28px;
  }}

  figure {{
    margin: 0;
    background: var(--card);
    border-radius: 3px;
    overflow: hidden;
    box-shadow: var(--shadow);
    display: flex;
    flex-direction: column;
  }}

  .frame {{ position: relative; aspect-ratio: 3 / 4; background: var(--ink); }}
  .frame img {{
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }}
  .frame .before {{ opacity: 0; transition: opacity .18s ease; }}
  body.show-before .frame .before,
  .frame:hover .before,
  .frame:focus-within .before {{ opacity: 1; }}

  .frame .tag {{
    position: absolute;
    left: 10px;
    top: 10px;
    padding: 3px 9px;
    border-radius: 999px;
    background: rgba(255, 255, 255, .92);
    color: #14130f;
    font-size: 11px;
    letter-spacing: .08em;
    text-transform: uppercase;
    opacity: 0;
    transition: opacity .18s ease;
  }}
  body.show-before .frame .tag,
  .frame:hover .tag,
  .frame:focus-within .tag {{ opacity: 1; }}

  figcaption {{ padding: 16px 18px 18px; display: flex; flex-direction: column; gap: 12px; flex: 1; }}

  .recipe {{ display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }}

  .chip {{
    display: inline-flex;
    align-items: center;
    gap: 7px;
    padding: 4px 10px 4px 5px;
    border: 1px solid var(--rule);
    border-radius: 999px;
    font-size: 12px;
    letter-spacing: .02em;
  }}
  .swatch {{ width: 14px; height: 14px; border-radius: 50%; box-shadow: inset 0 0 0 1px rgba(0, 0, 0, .18); }}
  .chip svg {{ width: 13px; height: 13px; fill: currentColor; }}

  .credit {{ margin: 0; font-size: 12.5px; color: var(--muted); margin-top: auto; }}
  .credit a {{ color: inherit; text-underline-offset: 2px; }}
  .credit br {{ content: ""; display: block; margin-bottom: 3px; }}
  .seed {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 11.5px; color: var(--muted); }}

  footer {{ margin-top: 72px; padding-top: 28px; border-top: 1px solid var(--rule); color: var(--muted); font-size: 14px; }}
  footer code {{
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 13px;
    background: var(--card);
    border: 1px solid var(--rule);
    border-radius: 3px;
    padding: 2px 6px;
  }}
  footer p {{ max-width: 70ch; }}

  @media (max-width: 520px) {{
    header {{ padding-top: 44px; }}
    .grid {{ grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 18px; }}
    figcaption {{ padding: 12px 13px 14px; }}
  }}
</style>
</head>
<body>
<div class="wrap">

<header>
  <h1>Noir<br>&amp; <em>une</em><br>couleur</h1>
  <p class="lede">Douze photos passées à la même moulinette : bichromie sur une seule encre,
  puis un aplat — triangle, cercle ou rectangle — posé au hasard en fusion multiply.
  Aucun cadrage n'a été retouché à la main : tout vient du tirage d'une graine.</p>
  <div class="meta">
    <span>{count} rendus</span>
    <span>{inks} encres</span>
    <span>graine 2017</span>
    <span>photos&nbsp;: Unsplash</span>
  </div>
</header>

<div class="toolbar">
  <button id="toggle" type="button" aria-pressed="false">Afficher les originaux</button>
  <p class="hint">ou survolez une image</p>
</div>

<div class="grid">
{cards}
</div>

<footer>
  <p><strong>Rejouer&nbsp;:</strong> <code>python3 fetch_sources.py</code> puis
  <code>python3 mask.py sources/ -o output/ --seed 2017 --manifest output/recipes.json</code>.
  Sans <code>--seed</code>, chaque passage retire une nouvelle série&nbsp;; la graine indiquée
  sous chaque image suffit à retrouver un rendu précis.</p>
  <p>Photos sous licence Unsplash, créditées sous chaque rendu. Les originaux sont dans
  <code>sources/</code>, les rendus dans <code>output/</code>.</p>
</footer>

</div>
<script>
  const button = document.getElementById('toggle');
  button.addEventListener('click', () => {{
    const on = document.body.classList.toggle('show-before');
    button.setAttribute('aria-pressed', String(on));
    button.textContent = on ? 'Afficher les rendus' : 'Afficher les originaux';
  }});
</script>
</body>
</html>
"""

CARD = """  <figure>
    <div class="frame">
      <img class="after" src="output/{output}" alt="{alt} — bichromie {duotone_name} avec un {shape_label} en multiply" loading="lazy">
      <img class="before" src="sources/{source}" alt="{alt} — photo d'origine" loading="lazy">
      <span class="tag">original</span>
    </div>
    <figcaption>
      <div class="recipe">
        <span class="chip" title="encre de la bichromie"><span class="swatch" style="background:{duotone_color}"></span>{duotone_name}</span>
        <span class="chip" title="aplat en multiply">{glyph}<span class="swatch" style="background:{shape_color}"></span>{opacity_pct}&nbsp;%</span>
      </div>
      <p class="credit">{alt}<br>photo <a href="{page}">{author}</a> · <span class="seed">seed {seed}</span></p>
    </figcaption>
  </figure>"""


def main() -> int:
    sources = {p["file"]: p for p in json.loads((HERE / "sources.json").read_text(encoding="utf-8"))}
    recipes = json.loads((HERE / "output" / "recipes.json").read_text(encoding="utf-8"))

    cards = []
    for recipe in recipes:
        photo = sources[recipe["source"]]
        cards.append(CARD.format(
            output=recipe["output"],
            source=recipe["source"],
            alt=html.escape(photo["alt"]),
            page=html.escape(photo["page"]),
            author=html.escape(photo["author"]),
            author_url=html.escape(photo["author_url"]),
            duotone_color=recipe["duotone_color"],
            duotone_name=html.escape(recipe["duotone_name"]),
            shape_color=recipe["shape_color"],
            shape_label=SHAPE_LABELS[recipe["shape"]],
            glyph=SHAPE_GLYPHS[recipe["shape"]],
            opacity_pct=round(recipe["opacity"] * 100),
            seed=recipe["seed"],
        ))

    page = PAGE.format(
        count=len(recipes),
        inks=len({r["duotone_name"] for r in recipes} | {r["shape_name"] for r in recipes}),
        cards="\n".join(cards),
    )
    target = HERE / "index.html"
    target.write_text(page, encoding="utf-8")
    print(f"{target} — {len(recipes)} rendus")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
