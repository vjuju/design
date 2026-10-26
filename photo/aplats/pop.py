#!/usr/bin/env python3
"""
pop.py — la boîte à outils commune aux trois scripts d'aplats.

Aucune IA, aucun modèle : tout repose sur de l'analyse d'image classique
(luminance, contraste local, distance à la couleur du fond, quantification
des couleurs) et sur de la morphologie faite au flou gaussien. La photo n'est
jamais retouchée : on calcule des masques, puis on pose par-dessus des aplats
de couleur, des contours noirs et des traits.

Dépendances : Pillow et numpy.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

# --------------------------------------------------------------------------
# Palette
# --------------------------------------------------------------------------

FOND = "#F8F8F8"      # blanc cassé
CONTOUR = "#1D1B1A"   # noir chaud

COULEURS: dict[str, str] = {
    "jaune":  "#F4C946",
    "vert":   "#6AB357",
    "rose":   "#DB6DA2",
    "orange": "#E26E3B",
    "bleu":   "#53B5E3",
}

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".bmp"}


def rgb(hex_value: str) -> np.ndarray:
    v = hex_value.lstrip("#")
    return np.array([int(v[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float32) / 255.0


# --------------------------------------------------------------------------
# Chargement et mesures
# --------------------------------------------------------------------------

def load(path: Path, max_size: int) -> np.ndarray:
    """Photo en float32 RGB 0..1, réduite à `max_size` sur le grand côté."""
    im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    im.thumbnail((max_size, max_size), Image.LANCZOS)
    return np.asarray(im, dtype=np.float32) / 255.0


def save(a: np.ndarray, path: Path, quality: int = 90) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.clip(a * 255 + 0.5, 0, 255).astype(np.uint8)).save(
        path, quality=quality, optimize=True)


def luminance(a: np.ndarray) -> np.ndarray:
    return a[..., 0] * 0.299 + a[..., 1] * 0.587 + a[..., 2] * 0.114


def normalize(x: np.ndarray, lo: float = 2, hi: float = 98) -> np.ndarray:
    """Étirement par percentiles : c'est la « montée de contraste »."""
    a, b = np.percentile(x, [lo, hi])
    if b - a < 1e-6:
        return np.zeros_like(x)
    return np.clip((x - a) / (b - a), 0, 1)


def diag(shape) -> float:
    return math.hypot(shape[0], shape[1])


# --------------------------------------------------------------------------
# Morphologie au flou gaussien
#
# Dilater, éroder, lisser : on floute le masque puis on le re-seuille. C'est
# moins exact qu'une vraie morphologie mais les bords sortent ronds, comme
# tracés au pinceau — c'est précisément ce qu'on veut.
# --------------------------------------------------------------------------

def blur(x: np.ndarray, radius: float) -> np.ndarray:
    if radius <= 0:
        return x.astype(np.float32)
    im = Image.fromarray(np.clip(x * 255 + 0.5, 0, 255).astype(np.uint8))
    return np.asarray(im.filter(ImageFilter.GaussianBlur(radius)), dtype=np.float32) / 255.0


def dilate(m: np.ndarray, d: float) -> np.ndarray:
    """Grossit le masque d'environ `d` pixels (le bord flouté passe 8 % à 1,4 σ)."""
    if d <= 0.5:
        return m.astype(bool)
    return blur(m.astype(np.float32), d / 1.4) > 0.08


def erode(m: np.ndarray, d: float) -> np.ndarray:
    if d <= 0.5:
        return m.astype(bool)
    return blur(m.astype(np.float32), d / 1.4) > 0.92


def wobble(shape, rng: random.Random, cells: int = 7, amp: float = 0.12) -> np.ndarray:
    """Bruit basse fréquence centré sur 0 : il fait trembler les seuils."""
    g = np.array([[rng.random() for _ in range(cells)] for _ in range(cells)], dtype=np.float32)
    im = Image.fromarray((g * 255).astype(np.uint8)).resize((shape[1], shape[0]), Image.BICUBIC)
    return (np.asarray(im, dtype=np.float32) / 255.0 - 0.5) * 2 * amp


def smooth(m: np.ndarray, r: float, noise: np.ndarray | None = None) -> np.ndarray:
    """Arrondit un masque ; avec `noise`, son bord ondule comme à main levée."""
    f = blur(m.astype(np.float32), r)
    return f > (0.5 + (noise if noise is not None else 0))


def outline(m: np.ndarray, width: float) -> np.ndarray:
    """Le trait de contour d'un masque, centré sur son bord."""
    return dilate(m, width / 2) & ~erode(m, width / 2)


def fill_holes(m: np.ndarray, bottom_is_open: bool = True) -> np.ndarray:
    """Bouche les trous : tout ce qui n'est pas relié au bord du cadre.

    Avec `bottom_is_open=False`, le bas du cadre compte comme un mur : un
    sujet coupé par le bas (un buste, un chat assis) ne reste pas creux.
    """
    lab = label(~m)
    sides = [lab[0], lab[:, 0], lab[:, -1]] + ([lab[-1]] if bottom_is_open else [])
    edge = np.unique(np.concatenate(sides))
    return m | ((lab >= 0) & ~np.isin(lab, edge))


def bold_shape(m: np.ndarray, d: float, noise: np.ndarray | None = None) -> np.ndarray:
    """La silhouette « au pinceau » d'un sujet : on comble les creux
    (fermeture : dilater puis éroder d'autant), on bouche les trous et on
    arrondit. Une foule ou un décor chargé redevient une seule forme franche.
    """
    r = 0.035 * d
    closed = erode(dilate(m, r), r * 0.8)
    return fill_holes(smooth(closed | m, 0.008 * d, noise), bottom_is_open=False)


def shift(m: np.ndarray, dx: int, dy: int) -> np.ndarray:
    out = np.zeros_like(m)
    h, w = m.shape
    xs, xd = (slice(0, w - dx), slice(dx, w)) if dx >= 0 else (slice(-dx, w), slice(0, w + dx))
    ys, yd = (slice(0, h - dy), slice(dy, h)) if dy >= 0 else (slice(-dy, h), slice(0, h + dy))
    out[yd, xd] = m[ys, xs]
    return out


# --------------------------------------------------------------------------
# Composantes connexes (sans scipy)
#
# Propagation du plus petit indice entre voisins, accélérée par saut de
# pointeur : chaque étiquette est aussi l'adresse d'un pixel, on remplace
# donc l'étiquette d'un pixel par celle du pixel qu'elle désigne.
# --------------------------------------------------------------------------

def label(mask: np.ndarray) -> np.ndarray:
    h, w = mask.shape
    big = h * w + 1
    lab = np.where(mask, np.arange(h * w, dtype=np.int64).reshape(h, w), big)
    while True:
        m = lab.copy()
        m[1:] = np.minimum(m[1:], lab[:-1])
        m[:-1] = np.minimum(m[:-1], lab[1:])
        m[:, 1:] = np.minimum(m[:, 1:], lab[:, :-1])
        m[:, :-1] = np.minimum(m[:, :-1], lab[:, 1:])
        m = np.where(mask, m, big)
        inside = m < big
        for _ in range(32):
            jumped = m.ravel()[m[inside]]
            if np.array_equal(jumped, m[inside]):
                break
            m[inside] = jumped
        if np.array_equal(m, lab):
            break
        lab = m
    lab = np.where(mask, lab, -1)
    _, inv = np.unique(lab, return_inverse=True)
    inv = inv.reshape(h, w)
    return np.where(mask, inv - (1 if (~mask).any() else 0), -1)


def components(mask: np.ndarray, min_area: int) -> list[np.ndarray]:
    lab = label(mask)
    n = lab.max() + 1
    if n <= 0:
        return []
    counts = np.bincount(lab[lab >= 0], minlength=n)
    keep = [i for i in np.argsort(-counts) if counts[i] >= min_area]
    return [lab == i for i in keep]


# --------------------------------------------------------------------------
# Détection du sujet
# --------------------------------------------------------------------------

def otsu(x: np.ndarray) -> float:
    hist, edges = np.histogram(x, bins=256, range=(0, 1))
    p = hist.astype(np.float64) / max(hist.sum(), 1)
    omega = np.cumsum(p)
    mu = np.cumsum(p * np.arange(256))
    mu_t = mu[-1]
    with np.errstate(divide="ignore", invalid="ignore"):
        sigma = (mu_t * omega - mu) ** 2 / (omega * (1 - omega))
    return float(edges[int(np.nanargmax(sigma))])


def dominant(a: np.ndarray, bins: int = 8) -> np.ndarray:
    """La couleur la plus répandue : sur la plupart des photos, c'est le fond."""
    q = np.clip((a * bins).astype(np.int32), 0, bins - 1)
    key = (q[..., 0] * bins + q[..., 1]) * bins + q[..., 2]
    top = np.bincount(key.ravel(), minlength=bins ** 3).argmax()
    return a[key == top].mean(axis=0)


def saliency(a: np.ndarray) -> np.ndarray:
    """Carte de « ce qui se détache », entre 0 et 1.

    Trois indices, tous calculables à la main :
      * l'écart à la couleur du fond (la couleur dominante, voir `dominant`) ;
      * le contraste local (luminance moins luminance très floutée) ;
      * la saturation.
    Un léger biais vers le centre traduit l'habitude du cadrage.
    """
    h, w = a.shape[:2]
    d_bg = np.linalg.norm(a - dominant(a), axis=2)

    lum = luminance(a)
    local = np.abs(lum - blur(lum, 0.06 * diag(a.shape)))
    sat = a.max(axis=2) - a.min(axis=2)

    s = 0.45 * normalize(d_bg) + 0.35 * normalize(local) + 0.20 * normalize(sat)
    yy, xx = np.mgrid[0:h, 0:w]
    centre = np.exp(-(((xx / w - 0.5) ** 2) + ((yy / h - 0.5) ** 2)) / (2 * 0.33 ** 2))
    s = s * (0.55 + 0.45 * centre)
    return normalize(blur(s, 0.006 * diag(a.shape)), 1, 99.5)


def shape_score(p: np.ndarray, s: np.ndarray, d: float) -> float:
    """Ce qui fait un sujet : une forme ramassée qui tranche sur son entourage.

    Un ciel, une ligne d'arbres, une plage se détachent souvent autant que la
    personne, mais ils s'étirent d'un bord à l'autre et remplissent mal leur
    rectangle. On part du contraste de saillance entre la zone et un anneau
    autour d'elle (un vrai sujet est cerné d'une chute nette), multiplié par
    la racine de la surface (une grande zone compte plus, mais pas
    proportionnellement), puis :
      * remplissage : surface / rectangle englobant — une silhouette pleine
        tient son cadre, une frange déchiquetée non ;
      * étendue : au-delà de 75 % de la largeur ou de la hauteur du cadre, la
        zone ressemble à un fond et perd vite des points ;
      * taille : au-delà d'un quart de l'image, idem ;
      * bords : chaque bord touché divise par deux, sauf le bas, que les
        personnes cadrées en buste ou en pied touchent naturellement ; deux
        bords opposés (une bande qui traverse l'image) divisent par dix.
    """
    ys, xs = np.nonzero(p)
    h, w = p.shape
    area = len(xs)
    bw, bh = xs.max() - xs.min() + 1, ys.max() - ys.min() + 1
    fill = area / (bw * bh)
    span = max(bw / w, bh / h)
    size = area / (h * w)
    left, right = xs.min() == 0, xs.max() == w - 1
    top, bottom = ys.min() == 0, ys.max() == h - 1

    ring = dilate(p, 0.025 * d) & ~p
    contrast = float(s[p].mean()) - (float(s[ring].mean()) if ring.any() else 0.0)
    value = max(contrast, 0.0) * math.sqrt(area)
    value *= 0.4 + fill
    value *= max(0.1, 1 - 2.5 * max(0.0, span - 0.75))
    value *= max(0.1, 1 - 2.5 * max(0.0, size - 0.25))
    value *= 0.5 ** sum([left, right, top])
    value *= 0.85 if bottom else 1.0      # une silhouette coupée par le bas reste un sujet
    if (left and right) or (top and bottom):
        value *= 0.1
    return value


def subjects(a: np.ndarray, max_count: int = 3) -> list[np.ndarray]:
    """Les zones saillantes, de la plus « sujet » à la moins (voir `shape_score`).

    Un seuil unique colle souvent le sujet au décor voisin (le randonneur à
    l'horizon, le basketteur au ciel). On seuille donc la carte de saillance à
    plusieurs hauteurs : plus le seuil monte, plus les zones se séparent. On
    garde toutes les composantes de tous les niveaux, on les note, puis on
    choisit les meilleures en écartant celles qui recouvrent une zone déjà
    retenue ou qui valent moins du tiers de la première.
    """
    s = saliency(a)
    d = diag(a.shape)
    levels = sorted({round(float(t), 3) for t in
                     [max(otsu(s), 0.4), *np.quantile(s, [0.72, 0.82, 0.9, 0.95])]})
    candidates = []
    for t in levels:
        m = smooth(s > t, 0.006 * d)
        for p in components(m, int(0.002 * m.size)):
            candidates.append((shape_score(p, s, d), p))
    candidates.sort(key=lambda c: c[0], reverse=True)

    # Les sujets secondaires doivent valoir au moins le tiers du principal :
    # sinon ce sont des restes de décor, mieux vaut ne rien peindre.
    chosen: list[np.ndarray] = []
    best = candidates[0][0] if candidates else 0.0
    for score, p in candidates:
        if score <= 0 or score < best / 3 or len(chosen) == max_count:
            break
        if any((p & q).sum() > 0.3 * min(p.sum(), q.sum()) for q in chosen):
            continue
        chosen.append(p)
    return chosen


# --------------------------------------------------------------------------
# Composition
# --------------------------------------------------------------------------

def soft(m: np.ndarray) -> np.ndarray:
    """Masque booléen -> alpha antialiasé."""
    return blur(m.astype(np.float32), 0.7)


def paint(canvas: np.ndarray, mask: np.ndarray, color: str,
          mode: str = "multiply", opacity: float = 1.0) -> None:
    """Pose un aplat. multiply : la photo transparaît ; normal : il la couvre."""
    alpha = (mask if mask.dtype != bool else soft(mask))[..., None] * opacity
    c = rgb(color)
    top = canvas * c if mode == "multiply" else np.broadcast_to(c, canvas.shape)
    canvas[:] = canvas * (1 - alpha) + top * alpha


def blend_for(canvas: np.ndarray, mask: np.ndarray, threshold: float = 0.5) -> tuple[str, float]:
    """Sur du clair, multiply ; sur du sombre, la couleur y disparaîtrait :
    on passe en aplat couvrant."""
    if luminance(canvas)[mask].mean() > threshold:
        return "multiply", 0.95
    return "normal", 0.88


def outward_normals(m: np.ndarray, spread: float) -> tuple[np.ndarray, np.ndarray]:
    f = blur(m.astype(np.float32), spread)
    gy, gx = np.gradient(f)
    n = np.hypot(gx, gy) + 1e-6
    return -gx / n, -gy / n


def rays(shape, m: np.ndarray, rng: random.Random, *, gap: float, length: float,
         width: float, spacing: float, ss: int = 3) -> np.ndarray:
    """Les traits de vibration de Keith Haring autour d'un masque.

    On échantillonne le bord du masque grossi de `gap`, on calcule la normale
    sortante (gradient du masque flouté) et on y trace un trait court à bouts
    ronds. Renvoie un alpha antialiasé (dessin sur-échantillonné x`ss`).
    """
    h, w = shape
    base = dilate(m, gap)
    edge = outline(base, 2)
    nx, ny = outward_normals(base, max(3.0, length * 0.6))
    ys, xs = np.nonzero(edge)
    order = list(range(len(xs)))
    rng.shuffle(order)

    taken: list[tuple[float, float]] = []
    cell = max(spacing, 1.0)
    grid: dict[tuple[int, int], list[tuple[float, float]]] = {}

    im = Image.new("L", (w * ss, h * ss), 0)
    draw = ImageDraw.Draw(im)
    lw = max(1, int(width * ss))
    for i in order:
        x, y = float(xs[i]), float(ys[i])
        gx, gy = int(x // cell), int(y // cell)
        near = [p for dx in (-1, 0, 1) for dy in (-1, 0, 1) for p in grid.get((gx + dx, gy + dy), [])]
        if any((px - x) ** 2 + (py - y) ** 2 < spacing ** 2 for px, py in near):
            continue
        grid.setdefault((gx, gy), []).append((x, y))
        taken.append((x, y))
        L = length * (0.65 + 0.5 * rng.random())
        dx, dy = nx[ys[i], xs[i]], ny[ys[i], xs[i]]
        x1, y1 = x + dx * L, y + dy * L
        p0, p1 = (x * ss, y * ss), (x1 * ss, y1 * ss)
        draw.line([p0, p1], fill=255, width=lw)
        r = lw / 2
        for px, py in (p0, p1):
            draw.ellipse([px - r, py - r, px + r, py + r], fill=255)
    im = im.resize((w, h), Image.LANCZOS)
    return np.asarray(im, dtype=np.float32) / 255.0


def pick_colors(rng: random.Random, n: int) -> list[str]:
    names = list(COULEURS)
    rng.shuffle(names)
    return [COULEURS[names[i % len(names)]] for i in range(n)]


# --------------------------------------------------------------------------
# CLI partagée
# --------------------------------------------------------------------------

def run_cli(name: str, doc: str, render, add_args=None) -> None:
    ap = argparse.ArgumentParser(prog=f"{name}.py", description=doc)
    ap.add_argument("inputs", nargs="+", type=Path, help="images ou dossiers")
    ap.add_argument("-o", "--out", type=Path, default=Path("output") / name,
                    help="dossier de sortie (défaut : output/%(prog)s)")
    ap.add_argument("--seed", type=int, default=None, help="graine (défaut : au hasard)")
    ap.add_argument("--variants", type=int, default=1, help="nombre de tirages par image")
    ap.add_argument("--max-size", type=int, default=900)
    ap.add_argument("--quality", type=int, default=88)
    if add_args:
        add_args(ap)
    args = ap.parse_args()

    files: list[Path] = []
    for p in args.inputs:
        if p.is_dir():
            files += sorted(f for f in p.iterdir() if f.suffix.lower() in IMAGE_EXTS)
        else:
            files.append(p)
    if not files:
        sys.exit("aucune image trouvée")

    base_seed = args.seed if args.seed is not None else random.randrange(1_000_000)
    manifest = args.out / "seeds.json"
    seeds = json.loads(manifest.read_text()) if manifest.exists() else {}
    for k, f in enumerate(files):
        photo = load(f, args.max_size)
        for v in range(args.variants):
            seed = base_seed + 1000 * k + v
            out = render(photo, random.Random(seed), args)
            suffix = f"-{v + 1}" if args.variants > 1 else ""
            dest = args.out / f"{f.stem}{suffix}.jpg"
            save(out, dest, args.quality)
            seeds[dest.name] = seed
            print(f"{dest}  (seed {seed})")
    # La graine de chaque rendu : la rejouer avec --seed redonne la même image.
    manifest.write_text(json.dumps(dict(sorted(seeds.items())), indent=2) + "\n")
