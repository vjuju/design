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

# Six couleurs plus vives : celles de figures.py (et de web/aplats.js).
VIVE: dict[str, str] = {
    "rose":   "#FF3EA5",
    "jaune":  "#FFD60A",
    "violet": "#7B2FF7",
    "cyan":   "#2EC4F1",
    "vert":   "#39D353",
    "orange": "#FF6A13",
}

PALETTES = {"vive": VIVE, "pop": COULEURS}

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


def fill_holes(m: np.ndarray) -> np.ndarray:
    """Bouche les trous : tout ce qui n'est pas relié au bord du cadre."""
    lab = label(~m)
    edge = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    return m | ((lab >= 0) & ~np.isin(lab, edge))


def bold_shape(m: np.ndarray, d: float, noise: np.ndarray | None = None) -> np.ndarray:
    """La silhouette « au pinceau » d'un sujet : on comble les creux
    (fermeture : dilater puis éroder d'autant), on bouche les trous et on
    arrondit. Une foule ou un décor chargé redevient une seule forme franche.
    """
    r = 0.035 * d
    closed = erode(dilate(m, r), r * 0.8)
    return fill_holes(smooth(closed | m, 0.008 * d, noise))


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


def subjects(a: np.ndarray, max_count: int = 3) -> list[np.ndarray]:
    """Les zones saillantes, de la plus importante à la moins importante."""
    s = saliency(a)
    m = s > max(otsu(s), 0.4)
    d = diag(a.shape)
    m = smooth(m, 0.006 * d)
    parts = components(m, int(0.002 * m.size))

    def score(p: np.ndarray) -> float:
        ys, xs = np.nonzero(p)
        h, w = p.shape
        touches = sum([ys.min() == 0, xs.min() == 0, ys.max() == h - 1, xs.max() == w - 1])
        return float(s[p].sum()) * (0.5 ** touches)

    parts.sort(key=score, reverse=True)
    return parts[:max_count]


# --------------------------------------------------------------------------
# Composition
# --------------------------------------------------------------------------

def soft(m: np.ndarray) -> np.ndarray:
    """Masque booléen -> alpha antialiasé."""
    return blur(m.astype(np.float32), 0.7)


def paint(canvas: np.ndarray, mask: np.ndarray, color: str,
          mode: str = "multiply", opacity: float = 1.0, box: tuple | None = None) -> None:
    """Pose un aplat. multiply : la photo transparaît ; normal : il la couvre.

    Avec `box` (x0, y0, x1, y1), `mask` ne couvre que ce rectangle et seul lui
    est recalculé : le reste de l'image n'est pas touché.
    """
    if box is not None:
        x0, y0, x1, y1 = box
        canvas = canvas[y0:y1, x0:x1]          # vue : on écrit dans l'original
    alpha = (mask if mask.dtype != bool else soft(mask)) * opacity
    c = rgb(color)
    # Un trait ou une couronne ne couvre qu'une petite partie de son
    # rectangle : on ne recalcule alors que les pixels touchés.
    sel = alpha > 0
    if sel.mean() < 0.4:
        px, a = canvas[sel], alpha[sel][:, None]
        canvas[sel] = px * (1 - a * (1 - c)) if mode == "multiply" else px + (c - px) * a
    elif mode == "multiply":
        canvas *= 1 - alpha[..., None] * (1 - c)
    else:
        canvas += (c - canvas) * alpha[..., None]


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


# --------------------------------------------------------------------------
# Formes vectorielles
#
# Plutôt que de peindre des masques pixel par pixel (bords hachés, et lent en
# pleine résolution), on analyse une petite copie de la photo, on suit le
# contour du sujet, on n'en garde que quelques points de passage, puis on
# trace en pleine résolution une courbe lisse passant par ces points, avec un
# trait de largeur constante.
# --------------------------------------------------------------------------

ANALYSIS_SIZE = 256

_DIRS = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]
_DIR_INDEX = {d: i for i, d in enumerate(_DIRS)}


def shrink(a: np.ndarray, size: int = ANALYSIS_SIZE) -> tuple[np.ndarray, float]:
    """Copie réduite pour l'analyse, et le facteur pour revenir à la taille réelle."""
    h, w = a.shape[:2]
    k = max(h, w) / size
    if k <= 1:
        return a, 1.0
    im = Image.fromarray(np.clip(a * 255 + 0.5, 0, 255).astype(np.uint8))
    im = im.resize((round(w / k), round(h / k)), Image.BILINEAR)
    small = np.asarray(im, dtype=np.float32) / 255.0
    return small, w / small.shape[1]


def trace_contour(m: np.ndarray) -> np.ndarray:
    """Contour extérieur d'un masque d'un seul tenant (suivi de Moore)."""
    p = np.pad(m, 1)
    ys, xs = np.nonzero(p)
    i = np.lexsort((xs, ys))[0]
    start = cur = (int(xs[i]), int(ys[i]))
    back = 4                                   # on arrive par la gauche
    pts = [start]
    for _ in range(4 * p.size):
        for k in range(1, 9):
            nd = (back + k) % 8
            nx, ny = cur[0] + _DIRS[nd][0], cur[1] + _DIRS[nd][1]
            if p[ny, nx]:
                bd = _DIRS[(back + k - 1) % 8]
                bx, by = cur[0] + bd[0], cur[1] + bd[1]
                back = _DIR_INDEX[(bx - nx, by - ny)]
                cur = (nx, ny)
                break
        else:
            break                              # pixel isolé
        if cur == start:
            break
        pts.append(cur)
    return np.array(pts, dtype=np.float64) - 1


def _rdp(pts: np.ndarray, tol: float) -> np.ndarray:
    keep = np.zeros(len(pts), dtype=bool)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        a, b = pts[i], pts[j]
        ab = b - a
        n = math.hypot(*ab) or 1.0
        seg = pts[i + 1:j]
        dist = np.abs(ab[0] * (seg[:, 1] - a[1]) - ab[1] * (seg[:, 0] - a[0])) / n
        k = int(np.argmax(dist))
        if dist[k] > tol:
            keep[i + 1 + k] = True
            stack += [(i, i + 1 + k), (i + 1 + k, j)]
    return pts[keep]


def key_points(pts: np.ndarray, tol: float, min_points: int = 5) -> np.ndarray:
    """Les quelques points de passage d'un contour fermé (Douglas-Peucker)."""
    far = int(np.argmax(np.hypot(*(pts - pts[0]).T)))
    while True:
        a = _rdp(pts[:far + 1], tol)
        b = _rdp(np.vstack([pts[far:], pts[:1]]), tol)
        keys = np.vstack([a[:-1], b[:-1]])
        if len(keys) >= min_points or tol < 0.5:
            return keys
        tol /= 1.6


def spline(keys: np.ndarray, samples: int = 24) -> np.ndarray:
    """Courbe fermée lisse passant par les points clés (Catmull-Rom centripète :
    pas de boucle ni de pointe même quand les points sont inégalement espacés)."""
    out = []
    n = len(keys)
    for i in range(n):
        p0, p1, p2, p3 = keys[i - 1], keys[i], keys[(i + 1) % n], keys[(i + 2) % n]
        t0 = 0.0
        t1 = t0 + max(math.hypot(*(p1 - p0)), 1e-6) ** 0.5
        t2 = t1 + max(math.hypot(*(p2 - p1)), 1e-6) ** 0.5
        t3 = t2 + max(math.hypot(*(p3 - p2)), 1e-6) ** 0.5
        t = np.linspace(t1, t2, samples, endpoint=False)[:, None]
        a1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
        a2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
        a3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
        b1 = (t2 - t) / (t2 - t0) * a1 + (t - t0) / (t2 - t0) * a2
        b2 = (t3 - t) / (t3 - t1) * a2 + (t - t1) / (t3 - t1) * a3
        out.append((t2 - t) / (t2 - t1) * b1 + (t - t1) / (t2 - t1) * b2)
    return np.vstack(out)


def curve_of(m: np.ndarray, scale: float, tol: float) -> np.ndarray | None:
    """Masque (copie réduite) -> courbe lisse en coordonnées pleine taille.

    Seule la plus grande partie du masque est gardée : une forme, un trait.
    """
    parts = components(m, 4)
    if not parts:
        return None
    pts = trace_contour(parts[0])
    if len(pts) < 8:
        return None
    keys = key_points(pts, tol)
    return (spline(keys) + 0.5) * scale


def box_of(curves: list[np.ndarray], margin: float, shape) -> tuple[int, int, int, int]:
    """Le rectangle (x0, y0, x1, y1) qui contient les courbes plus une marge,
    rogné au cadre de l'image. On ne dessine et ne peint que là-dedans."""
    pts = np.vstack(curves)
    h, w = shape[:2]
    x0 = int(max(0, math.floor(pts[:, 0].min() - margin)))
    y0 = int(max(0, math.floor(pts[:, 1].min() - margin)))
    x1 = int(min(w, math.ceil(pts[:, 0].max() + margin) + 1))
    y1 = int(min(h, math.ceil(pts[:, 1].max() + margin) + 1))
    return x0, y0, max(x0 + 1, x1), max(y0 + 1, y1)


def _canvas_alpha(box, draw_fn, ss: int = 2) -> np.ndarray:
    """Alpha antialiasé de la taille de `box`, dessiné en sur-échantillonnage x`ss`."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    im = Image.new("L", (w * ss, h * ss), 0)
    draw_fn(ImageDraw.Draw(im), ss)
    if ss > 1:
        im = im.resize((w, h), Image.BOX)
    return np.asarray(im, dtype=np.float32) / 255.0


def fill_alpha(box, curve: np.ndarray, ss: int = 1) -> np.ndarray:
    """Intérieur de la courbe. Sans sur-échantillonnage par défaut : le bord
    est recouvert par le trait noir, son crénelage ne se voit pas."""
    local = curve - box[:2]
    return _canvas_alpha(box, lambda d, s: d.polygon([tuple(p) for p in local * s], fill=255), ss)


def stroke_alpha(box, curve: np.ndarray, width: float) -> np.ndarray:
    local = curve - box[:2]

    def draw(d, ss):
        pts = [tuple(p) for p in local * ss]
        d.line(pts + pts[:2], fill=255, width=max(1, round(width * ss)), joint="curve")
    return _canvas_alpha(box, draw)


def resample(curve: np.ndarray, step: float) -> np.ndarray:
    """Points régulièrement espacés de `step` le long d'une courbe fermée."""
    closed = np.vstack([curve, curve[:1]])
    dist = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(closed, axis=0).T))])
    at = np.arange(0, dist[-1], step)
    return np.stack([np.interp(at, dist, closed[:, 0]), np.interp(at, dist, closed[:, 1])], axis=1)


def vibrations(box, curve: np.ndarray, rng: random.Random, *, gap: float, length: float,
               width: float, spacing: float, arc: float, corners: int = 3) -> np.ndarray:
    """Les vibrations de Keith Haring autour d'une courbe fermée.

    * Aux angles les plus marqués de la forme (là où la courbe tourne le plus
      vite, côté bombé), un arc de longueur `arc` parallèle à la courbe,
      décollé d'elle, et un second deux fois plus court juste au-delà :
      ils soulignent l'angle comme un écho.
    * Ailleurs, des traits droits perpendiculaires, plus espacés qu'avant et
      absents autour des arcs.
    Tous les traits ont la même épaisseur et des bouts ronds. L'alpha rendu
    couvre `box` (voir `box_of`).
    """
    curve = curve - box[:2]
    step = max(1.0, width / 2)
    pts = resample(curve, step)
    n = len(pts)
    if n < 12:
        return np.zeros((box[3] - box[1], box[2] - box[0]), dtype=np.float32)
    x, y = pts[:, 0], pts[:, 1]
    area = 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))
    sign = 1.0 if area > 0 else -1.0
    tan = np.roll(pts, -1, axis=0) - np.roll(pts, 1, axis=0)
    tan /= np.hypot(*tan.T)[:, None] + 1e-9
    normal = np.stack([tan[:, 1], -tan[:, 0]], axis=1) * sign   # sortante

    # Virage sur une fenêtre de la longueur d'un arc : positif = angle saillant.
    k = max(2, int(arc / 2 / step))
    t0, t1 = np.roll(tan, k, axis=0), np.roll(tan, -k, axis=0)
    turn = (t0[:, 0] * t1[:, 1] - t0[:, 1] * t1[:, 0]) * sign
    half = max(3, int(arc / 2 / step))             # demi-longueur d'un arc
    picked: list[int] = []
    for i in np.argsort(-turn):
        if len(picked) == corners or turn[i] < 0.15:
            break
        if all(min(abs(i - j), n - abs(i - j)) > 3 * half for j in picked):
            picked.append(int(i))

    covered = np.zeros(n, dtype=bool)
    for i in picked:
        # Une marge vide de part et d'autre de l'arc, avant le premier trait droit.
        margin = int(0.6 * spacing / step)
        covered[np.arange(i - half - margin, i + half + margin + 1) % n] = True

    def draw(d, ss):
        lw = max(1, round(width * ss))
        r = lw / 2

        def caps(*ps):
            for qx, qy in ps:
                d.ellipse([qx - r, qy - r, qx + r, qy + r], fill=255)

        for i in picked:
            # Un arc contre l'angle, un second plus court et plus loin.
            for g, span in ((gap, half), (gap + 2.2 * width, max(2, half // 2))):
                idx = np.arange(i - span, i + span + 1) % n
                line = [tuple(p) for p in (pts[idx] + normal[idx] * g) * ss]
                d.line(line, fill=255, width=lw, joint="curve")
                caps(line[0], line[-1])

        count = max(4, int(n * step / spacing))
        offset = rng.randrange(n)
        for c in range(count):
            i = (offset + int(c * n / count)) % n
            if covered[i]:
                continue
            L = length * (0.7 + 0.5 * rng.random())
            p0 = (pts[i] + normal[i] * gap) * ss
            p1 = (pts[i] + normal[i] * (gap + L)) * ss
            d.line([tuple(p0), tuple(p1)], fill=255, width=lw)
            caps(tuple(p0), tuple(p1))
    return _canvas_alpha(box, draw)


def pick_colors(rng: random.Random, n: int, palette: dict[str, str] = COULEURS) -> list[str]:
    names = list(palette)
    rng.shuffle(names)
    return [palette[names[i % len(names)]] for i in range(n)]


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
