#!/usr/bin/env python3
"""
molecule.py — des molécules qui fusionnent comme des gouttes (effet « gooey »),
rendues en SVG vectoriel pur : une couleur ou un dégradé par molécule.

Comment une image est fabriquée
-------------------------------
1. Croissance. Chaque molécule pousse comme un petit arbre : un premier atome
   (un disque), puis des voisins posés à distance de liaison, dans une
   direction qui tourne doucement, avec parfois une branche. Les atomes ne se
   chevauchent pas : c'est la liaison qui les relie.
2. Champ de distance. Chaque atome est un disque, chaque liaison une capsule
   plus fine (le « col »). On les réunit par un minimum lissé (smooth-min) :
   là où deux formes se rapprochent, la matière coule de l'une à l'autre,
   exactement comme deux gouttes qui se touchent.
3. Contour vectoriel. Le champ est échantillonné sur une grille fine, la
   courbe de niveau zéro est extraite par marching squares, rééchantillonnée
   à pas régulier puis lissée en courbes de Bézier (Catmull-Rom). Le résultat
   est un vrai tracé SVG, net à toutes les tailles, éditable dans Illustrator
   ou Figma.
4. Couleur. Chaque molécule reçoit un dégradé linéaire (deux ou trois
   couleurs) orienté au hasard ; les satellites isolés prennent une couleur
   franche. Certains atomes sont creusés en anneau.

Utilisation
-----------
    python3 molecule.py                          # une affiche au hasard
    python3 molecule.py --seed 7 --palette lagon
    python3 molecule.py --serie 12 -o output/    # douze affiches + manifeste
    python3 molecule.py --format carre --molecules 4 --titre "TECHNOLOGY" \\
                        --sous-titre "CONNECT"

Seule dépendance : numpy.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

# --------------------------------------------------------------------------
# Palettes : chaque entrée de `degrades` est le dégradé d'une molécule.
# --------------------------------------------------------------------------

PALETTES: dict[str, dict] = {
    "aurore": {
        "fond": "#ffffff",
        "encre": "#2b2b33",
        "degrades": [
            ["#d36ee0", "#7c8cf0", "#4aa8f5"],
            ["#b46ee6", "#5b8def"],
            ["#e07ad0", "#9b7df0"],
            ["#8a7cf2", "#3fb4f2"],
        ],
        "satellites": ["#b26fe3", "#56a6f4", "#d36ee0"],
    },
    "lagon": {
        "fond": "#ffffff",
        "encre": "#2b2b33",
        "degrades": [
            ["#12c9de", "#7fcf98", "#d8b33c"],
            ["#00c7e6", "#33d1c4"],
            ["#9ccf7c", "#d9b23a"],
            ["#ff4f8b", "#ff7fa8"],
        ],
        "satellites": ["#00c7e6", "#ff4f8b", "#d8b33c", "#5fcfa9"],
    },
    "sous-bois": {
        "fond": "#f6f3ec",
        "encre": "#2f3a2c",
        "degrades": [
            ["#2f7d5b", "#7fb069", "#d9c35c"],
            ["#5c9e6e", "#b6d36b"],
            ["#c4793a", "#e3b04b"],
            ["#3d8c95", "#8cc7a1"],
        ],
        "satellites": ["#e3b04b", "#2f7d5b", "#c4793a"],
    },
    "corail": {
        "fond": "#fff8f3",
        "encre": "#3a2a2a",
        "degrades": [
            ["#ff5e7a", "#ff9a6b", "#ffd166"],
            ["#ff7a9c", "#c86ad8"],
            ["#ff9a6b", "#ffcd5e"],
            ["#29b6c8", "#6fd3b8"],
        ],
        "satellites": ["#ff5e7a", "#ffd166", "#29b6c8"],
    },
    "nuit": {
        "fond": "#120d2b",
        "encre": "#ece8ff",
        "degrades": [
            ["#ff4fa3", "#8b5cf6", "#22d3ee"],
            ["#22d3ee", "#34d399"],
            ["#f59e0b", "#ef4444"],
            ["#a78bfa", "#60a5fa"],
        ],
        "satellites": ["#22d3ee", "#ff4fa3", "#f59e0b"],
    },
}

FORMATS = {  # largeur, hauteur (unités SVG)
    "affiche": (800, 1131),  # proportion A4
    "carre": (1000, 1000),
    "paysage": (1600, 900),
    "story": (900, 1600),
}

# Zones où naissent les molécules, en fraction du cadre (x0, x1, y0, y1).
ZONES = {
    "droite": (0.55, 1.05, -0.02, 1.02),  # laisse la gauche libre pour un texte
    "gauche": (-0.05, 0.52, -0.02, 1.02),
    "bas": (-0.05, 1.05, 0.45, 1.05),
    "partout": (-0.03, 1.03, -0.03, 1.03),
}


# --------------------------------------------------------------------------
# 1. Croissance
# --------------------------------------------------------------------------

@dataclass
class Atome:
    x: float
    y: float
    r: float
    anneau: float = 0.0  # rayon du trou (0 : atome plein)


@dataclass
class Molecule:
    atomes: list[Atome] = field(default_factory=list)
    liaisons: list[tuple[int, int, float]] = field(default_factory=list)  # i, j, rayon du col
    couleurs: list[str] = field(default_factory=list)
    angle: float = 0.0  # orientation du dégradé, en degrés


def faire_pousser(rng: random.Random, x: float, y: float, n: int, echelle: float,
                  obstacles: list[Atome], zone: tuple[float, float, float, float],
                  anneaux: float) -> Molecule:
    """Fait pousser une molécule de `n` atomes à partir de (x, y), sans sortir de `zone`
    (x0, x1, y0, y1 en unités SVG)."""
    zx0, zx1, zy0, zy1 = zone

    def rayon() -> float:
        # Mélange de gros atomes et de petits : c'est ce contraste qui fait vivre la forme.
        if rng.random() < 0.5:
            return rng.uniform(40, 66) * echelle
        return rng.uniform(17, 32) * echelle

    m = Molecule()
    m.atomes.append(Atome(x, y, rayon()))
    caps = [rng.uniform(0, 2 * math.pi)]  # direction de croissance de chaque atome
    degre = [0]

    def libre(a: Atome) -> bool:
        for b in m.atomes:
            if math.hypot(a.x - b.x, a.y - b.y) < (a.r + b.r) * 1.08:
                return False
        for b in obstacles:  # les autres molécules : on les frôle sans les envahir
            if math.hypot(a.x - b.x, a.y - b.y) < (a.r + b.r) * 0.75:
                return False
        return zx0 < a.x < zx1 and zy0 < a.y < zy1

    essais = 0
    while len(m.atomes) < n and essais < n * 40:
        essais += 1
        # Le plus souvent on prolonge le dernier atome (chaîne), parfois on branche.
        if rng.random() < 0.55:
            p = len(m.atomes) - 1
        else:
            p = rng.randrange(len(m.atomes))
        if degre[p] >= 3:
            continue
        parent = m.atomes[p]
        cap = caps[p] + rng.gauss(0, 1.1)
        r = rayon()
        d = (parent.r + r) * rng.uniform(1.2, 1.7)
        a = Atome(parent.x + d * math.cos(cap), parent.y + d * math.sin(cap), r)
        if not libre(a):
            continue
        if r > 38 * echelle and rng.random() < anneaux:
            a.anneau = r * rng.uniform(0.38, 0.52)
        m.atomes.append(a)
        caps.append(cap)
        degre.append(1)
        degre[p] += 1
        col = min(parent.r, r) * rng.uniform(0.38, 0.55)
        m.liaisons.append((p, len(m.atomes) - 1, col))
    return m


# --------------------------------------------------------------------------
# 2. Champ de distance
# --------------------------------------------------------------------------

def smin(a: np.ndarray, b: np.ndarray, k: float) -> np.ndarray:
    """Minimum lissé polynomial : la jonction « gooey » entre deux formes."""
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b * (1 - h) + a * h - k * h * (1 - h)


def champ(m: Molecule, X: np.ndarray, Y: np.ndarray, k: float) -> np.ndarray:
    d = np.full(X.shape, 1e9)
    for (i, j, col) in m.liaisons:
        a, b = m.atomes[i], m.atomes[j]
        bx, by = b.x - a.x, b.y - a.y
        t = np.clip(((X - a.x) * bx + (Y - a.y) * by) / (bx * bx + by * by), 0, 1)
        dc = np.hypot(X - a.x - t * bx, Y - a.y - t * by) - col
        d = smin(d, dc, k)
    for a in m.atomes:
        d = smin(d, np.hypot(X - a.x, Y - a.y) - a.r, k)
    for a in m.atomes:  # les anneaux : on creuse après la fusion
        if a.anneau:
            d = np.maximum(d, a.anneau - np.hypot(X - a.x, Y - a.y))
    return d


# --------------------------------------------------------------------------
# 3. Contour vectoriel
# --------------------------------------------------------------------------

def contours(v: np.ndarray, x0: float, y0: float, pas: float) -> list[np.ndarray]:
    """Courbes de niveau 0 de `v` (marching squares), en boucles fermées."""
    v = v.copy()
    v[0, :] = v[-1, :] = v[:, 0] = v[:, -1] = 1.0  # bord « dehors » : toutes les boucles se ferment
    ny, nx = v.shape
    dedans = v < 0
    cas = (dedans[:-1, :-1] * 8 + dedans[:-1, 1:] * 4 + dedans[1:, 1:] * 2 + dedans[1:, :-1] * 1)

    # Identifiant d'arête : 2*(j*nx+i) pour l'horizontale partant de (i, j), +1 pour la verticale.
    def H(j, i): return 2 * (j * nx + i)
    def V(j, i): return 2 * (j * nx + i) + 1

    voisins: dict[int, list[int]] = {}

    def lien(e1: int, e2: int) -> None:
        voisins.setdefault(e1, []).append(e2)
        voisins.setdefault(e2, []).append(e1)

    js, is_ = np.nonzero((cas != 0) & (cas != 15))
    for j, i in zip(js.tolist(), is_.tolist()):
        c = int(cas[j, i])
        haut, droite, bas, gauche = H(j, i), V(j, i + 1), H(j + 1, i), V(j, i)
        if c in (1, 14): lien(gauche, bas)
        elif c in (2, 13): lien(bas, droite)
        elif c in (3, 12): lien(gauche, droite)
        elif c in (4, 11): lien(haut, droite)
        elif c in (6, 9): lien(haut, bas)
        elif c in (7, 8): lien(gauche, haut)
        else:  # cols-de-selle 5 et 10 : on tranche avec la valeur au centre
            centre = (v[j, i] + v[j, i + 1] + v[j + 1, i] + v[j + 1, i + 1]) / 4 < 0
            if (c == 5) == centre:
                lien(gauche, haut); lien(bas, droite)
            else:
                lien(gauche, bas); lien(haut, droite)

    def point(e: int) -> tuple[float, float]:
        n, vert = divmod(e, 2)
        j, i = divmod(n, nx)
        if vert:
            a, b = v[j, i], v[j + 1, i]
            t = a / (a - b)
            return x0 + i * pas, y0 + (j + t) * pas
        a, b = v[j, i], v[j, i + 1]
        t = a / (a - b)
        return x0 + (i + t) * pas, y0 + j * pas

    boucles = []
    vus: set[int] = set()
    for depart in voisins:
        if depart in vus:
            continue
        chemin = [depart]
        vus.add(depart)
        prec, cour = None, depart
        while True:
            suiv = [e for e in voisins[cour] if e != prec]
            if not suiv:
                break
            prec, cour = cour, suiv[0]
            if cour == depart or cour in vus:
                break
            vus.add(cour)
            chemin.append(cour)
        if len(chemin) >= 4:
            boucles.append(np.array([point(e) for e in chemin]))
    return boucles


def reechantillonner(p: np.ndarray, ecart: float) -> np.ndarray:
    """Points régulièrement espacés le long d'une boucle fermée."""
    q = np.vstack([p, p[:1]])
    seg = np.hypot(*np.diff(q, axis=0).T)
    s = np.concatenate([[0], np.cumsum(seg)])
    n = max(8, int(round(s[-1] / ecart)))
    t = np.linspace(0, s[-1], n, endpoint=False)
    return np.column_stack([np.interp(t, s, q[:, 0]), np.interp(t, s, q[:, 1])])


def bezier(p: np.ndarray) -> str:
    """Boucle fermée → tracé SVG en Bézier cubiques (Catmull-Rom centripète simplifié)."""
    n = len(p)
    f = lambda x: f"{x:.1f}".rstrip("0").rstrip(".")
    morceaux = [f"M{f(p[0, 0])} {f(p[0, 1])}"]
    for k in range(n):
        p0, p1, p2, p3 = p[k - 1], p[k], p[(k + 1) % n], p[(k + 2) % n]
        c1 = p1 + (p2 - p0) / 6
        c2 = p2 - (p3 - p1) / 6
        morceaux.append(f"C{f(c1[0])} {f(c1[1])} {f(c2[0])} {f(c2[1])} {f(p2[0])} {f(p2[1])}")
    return "".join(morceaux) + "Z"


def trace(m: Molecule, k: float, pas: float, ecart: float) -> str:
    marge = k * 2 + 4 * pas
    xs = [a.x - a.r for a in m.atomes] + [a.x + a.r for a in m.atomes]
    ys = [a.y - a.r for a in m.atomes] + [a.y + a.r for a in m.atomes]
    x0, x1 = min(xs) - marge, max(xs) + marge
    y0, y1 = min(ys) - marge, max(ys) + marge
    gx = x0 + pas * np.arange(int((x1 - x0) / pas) + 2)
    gy = y0 + pas * np.arange(int((y1 - y0) / pas) + 2)
    X, Y = np.meshgrid(gx, gy)
    boucles = contours(champ(m, X, Y, k), x0, y0, pas)
    return "".join(bezier(reechantillonner(b, ecart)) for b in boucles)


# --------------------------------------------------------------------------
# 4. Composition
# --------------------------------------------------------------------------

def composer(seed: int | None = None, palette: str = "aurore", format_: str = "affiche",
             molecules: int = 3, atomes: tuple[int, int] = (6, 11), satellites: int = 4,
             zone: str = "droite", anneaux: float = 0.25, fusion: float = 1.0,
             echelle: float = 1.0, titre: str = "", sous_titre: str = "") -> tuple[str, dict]:
    """Renvoie (svg, recette)."""
    if seed is None:
        seed = random.randrange(10 ** 6)
    rng = random.Random(seed)
    pal = PALETTES[palette]
    W, H = FORMATS[format_]
    e = echelle * min(W, H) / 800
    zx0, zx1, zy0, zy1 = ZONES[zone]
    cadre = (zx0 * W - (60 * e if zx0 <= 0 else 0), zx1 * W + 60 * e, zy0 * H - 60 * e, zy1 * H + 60 * e)

    tout: list[Atome] = []
    mols: list[Molecule] = []
    degrades = pal["degrades"][:]
    rng.shuffle(degrades)
    for n in range(molecules):
        for _ in range(30):
            x, y = rng.uniform(zx0, zx1) * W, rng.uniform(zy0, zy1) * H
            if all(math.hypot(x - a.x, y - a.y) > a.r + 70 * e for a in tout):
                break
        m = faire_pousser(rng, x, y, rng.randint(*atomes), e, tout, cadre, anneaux)
        m.couleurs = degrades[n % len(degrades)]
        m.angle = rng.uniform(0, 360)
        tout += m.atomes
        mols.append(m)
    for _ in range(satellites):  # gouttes isolées, ou deux gouttes soudées
        for _ in range(60):
            x, y = rng.uniform(zx0, zx1) * W, rng.uniform(zy0, zy1) * H
            if all(math.hypot(x - a.x, y - a.y) > a.r + 30 * e for a in tout):
                break
        m = faire_pousser(rng, x, y, 1 if rng.random() < 0.7 else 2, e * 0.5, tout, cadre, 0)
        m.couleurs = [rng.choice(pal["satellites"])]
        m.angle = rng.uniform(0, 360)
        tout += m.atomes
        mols.append(m)

    k = 13 * e * fusion
    pas = max(1.0, 2.0 * e)
    defs, corps = [], []
    for idx, m in enumerate(mols):
        d = trace(m, k, pas, ecart=5 * e)
        if not d:
            continue
        if len(m.couleurs) == 1:
            remplissage = m.couleurs[0]
        else:
            xs = [a.x for a in m.atomes]; ys = [a.y for a in m.atomes]
            cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
            demi = max(max(xs) - min(xs), max(ys) - min(ys)) / 2 + 40 * e
            ang = math.radians(m.angle)
            dx, dy = math.cos(ang) * demi, math.sin(ang) * demi
            arrets = "".join(
                f'<stop offset="{i / (len(m.couleurs) - 1):.2f}" stop-color="{c}"/>'
                for i, c in enumerate(m.couleurs))
            defs.append(
                f'<linearGradient id="g{idx}" gradientUnits="userSpaceOnUse" '
                f'x1="{cx - dx:.0f}" y1="{cy - dy:.0f}" x2="{cx + dx:.0f}" y2="{cy + dy:.0f}">'
                f'{arrets}</linearGradient>')
            remplissage = f"url(#g{idx})"
        corps.append(f'<path fill="{remplissage}" fill-rule="evenodd" d="{d}"/>')

    textes = []
    if titre or sous_titre:
        tx, ty = W * 0.1, H * 0.3
        fs = 26 * e
        police = "font-family=\"'Helvetica Neue', Helvetica, Arial, sans-serif\""
        if titre:
            textes.append(f'<text x="{tx:.0f}" y="{ty:.0f}" font-size="{fs:.0f}" '
                          f'letter-spacing="{fs * 0.32:.1f}" fill="{pal["encre"]}" {police}>{titre}</text>')
        if sous_titre:
            textes.append(f'<text x="{tx:.0f}" y="{ty + fs * 1.4:.0f}" font-size="{fs:.0f}" '
                          f'letter-spacing="{fs * 0.32:.1f}" fill="{pal["encre"]}" opacity=".6" '
                          f'{police}>{sous_titre}</text>')

    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">'
           f'<defs>{"".join(defs)}</defs>'
           f'<rect width="{W}" height="{H}" fill="{pal["fond"]}"/>'
           + "".join(corps) + "".join(textes) + "</svg>\n")
    recette = dict(seed=seed, palette=palette, format=format_, molecules=molecules,
                   atomes=list(atomes), satellites=satellites, zone=zone, anneaux=anneaux,
                   fusion=fusion, echelle=echelle, titre=titre, sous_titre=sous_titre)
    return svg, recette


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, help="graine : même graine, même image")
    ap.add_argument("--palette", choices=PALETTES, default=None, help="au hasard si absent")
    ap.add_argument("--format", dest="format_", choices=FORMATS, default="affiche")
    ap.add_argument("--zone", choices=ZONES, default=None,
                    help="où naissent les molécules (droite par défaut avec un titre, sinon partout)")
    ap.add_argument("--molecules", type=int, default=3, help="nombre de molécules colorées")
    ap.add_argument("--atomes", type=int, nargs=2, default=(6, 11), metavar=("MIN", "MAX"))
    ap.add_argument("--satellites", type=int, default=4, help="petites gouttes isolées")
    ap.add_argument("--anneaux", type=float, default=0.25, help="part des atomes creusés (0–1)")
    ap.add_argument("--fusion", type=float, default=1.0, help="viscosité des jonctions (0.3–2)")
    ap.add_argument("--echelle", type=float, default=1.0, help="taille des atomes")
    ap.add_argument("--titre", default="")
    ap.add_argument("--sous-titre", dest="sous_titre", default="")
    ap.add_argument("-o", "--out", default="output", help="dossier de sortie")
    ap.add_argument("--serie", type=int, default=1, help="nombre d'images à tirer")
    a = ap.parse_args()

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    base = a.seed if a.seed is not None else random.randrange(10 ** 6)
    recettes = []
    for n in range(a.serie):
        seed = base + n
        palette = a.palette or random.Random(seed).choice(list(PALETTES))
        zone = a.zone or ("droite" if (a.titre or a.sous_titre) else "partout")
        svg, rec = composer(seed, palette, a.format_, a.molecules, tuple(a.atomes),
                            a.satellites, zone, a.anneaux, a.fusion, a.echelle,
                            a.titre, a.sous_titre)
        nom = f"molecule-{palette}-{seed}.svg"
        (out / nom).write_text(svg, encoding="utf-8")
        rec["fichier"] = nom
        recettes.append(rec)
        print(out / nom)
    if a.serie > 1:
        (out / "recettes.json").write_text(json.dumps(recettes, indent=2, ensure_ascii=False),
                                           encoding="utf-8")


if __name__ == "__main__":
    main()
