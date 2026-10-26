"""Pictogramme gigot : le O, son flanc et ses deux arcs, dans un carré."""
import os, sys
T = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 160 160" width="512" height="512">
  <title>gigot — pictogramme</title>
  <style>
    .fond    {{ fill: {fond}; }}
    .o       {{ fill: {o}; }}
    .contour {{ fill: {contour}; }}
    .encre   {{ color: {encre}; }} /* arcs : noir ou blanc */
  </style>
  <rect class="fond" width="160" height="160"/>
  <g transform="translate(15 15)">
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
P = {"noir":"#111111","blanc":"#FFFFFF","rose":"#FF3EA5","jaune":"#FFD60A",
     "violet":"#7B2FF7","cyan":"#2EC4F1","vert":"#39D353","orange":"#FF6A13"}
V = [("rose","cyan","violet"),("jaune","cyan","violet"),("cyan","jaune","rose"),
     ("vert","rose","violet"),("orange","jaune","violet"),("violet","rose","cyan"),
     ("noir","jaune","rose"),("blanc","jaune","violet")]
out = sys.argv[1]
os.makedirs(out, exist_ok=True)
for fond,o,c in V:
    assert len({fond,o,c})==3
    enc = "blanc" if fond in ("noir","violet") else "noir"
    open(os.path.join(out,f"gigot-picto-{fond}.svg"),"w").write(
        T.format(fond=P[fond],o=P[o],contour=P[c],encre=P[enc]))
