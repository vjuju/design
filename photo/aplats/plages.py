#!/usr/bin/env python3
"""
plages.py — la photo découpée en grandes plages, comme une fresque peinte.

1. On floute fortement la photo puis on réduit ses couleurs à quelques
   teintes (quantification median cut de Pillow) : il ne reste que les
   grandes masses — murs, sol, ciel, vêtements.
2. Un filtre de mode nettoie les petites îles, puis chaque masse connexe
   devient une plage.
3. Le sujet principal (voir `pop.subjects`) est réservé : il reste la photo,
   cerné de noir, au milieu de la fresque. Les autres plages reçoivent un
   aplat de la palette, en veillant à ce que deux plages voisines n'aient
   jamais la même couleur (coloration de graphe gloutonne). Les plages très sombres restent la
   photo ; les plages moyennes, où le multiply s'éteindrait, sont couvertes.
4. Les frontières entre plages sont tracées au gros trait noir.

    python3 plages.py photo.jpg
    python3 plages.py photo.jpg --levels 7 --blank 0.3
"""

from __future__ import annotations

import numpy as np
from PIL import Image, ImageFilter

import pop


def add_args(ap) -> None:
    ap.add_argument("--levels", type=int, default=6, help="nombre de teintes de la quantification")
    ap.add_argument("--blank", type=float, default=0.2,
                    help="part des plages laissées sans couleur (0..1)")
    ap.add_argument("--no-protect", action="store_true",
                    help="peindre aussi le sujet principal (par défaut il reste la photo)")
    ap.add_argument("--dark", type=float, default=0.22,
                    help="luminance sous laquelle une plage reste la photo")


def regions(photo, levels: int):
    d = pop.diag(photo.shape)
    soft = pop.blur(photo, 0.012 * d) if photo.ndim == 2 else np.stack(
        [pop.blur(photo[..., c], 0.012 * d) for c in range(3)], axis=2)
    im = Image.fromarray((soft * 255).astype(np.uint8))
    idx = im.quantize(colors=levels, method=Image.Quantize.MEDIANCUT).convert("L")
    size = max(3, int(0.012 * d) | 1)
    for _ in range(2):
        idx = idx.filter(ImageFilter.ModeFilter(size))
    idx = np.asarray(idx)

    lab = np.full(idx.shape, -1, dtype=np.int64)
    n = 0
    for v in np.unique(idx):
        for part in pop.components(idx == v, int(0.004 * idx.size)):
            lab[part] = n
            n += 1
    return lab, n


def adjacency(lab: np.ndarray, n: int) -> list[set[int]]:
    adj = [set() for _ in range(n)]
    for a, b in ((lab[1:], lab[:-1]), (lab[:, 1:], lab[:, :-1])):
        diff = (a != b) & (a >= 0) & (b >= 0)
        for i, j in set(zip(a[diff].tolist(), b[diff].tolist())):
            adj[i].add(j)
            adj[j].add(i)
    return adj


def render(photo, rng, args):
    d = pop.diag(photo.shape)
    canvas = photo.copy()
    lab, n = regions(photo, args.levels)
    adj = adjacency(lab, n)
    lum = pop.luminance(photo)
    subs = [] if args.no_protect else pop.subjects(photo, 1)
    subject = pop.bold_shape(subs[0], d) if subs else np.zeros(lab.shape, bool)

    names = list(pop.COULEURS)
    rng.shuffle(names)
    order = sorted(range(n), key=lambda i: -(lab == i).sum())
    color_of: dict[int, str | None] = {}
    for i in order:
        region = lab == i
        if (lum[region].mean() < args.dark or subject[region].mean() > 0.5
                or rng.random() < args.blank):
            color_of[i] = None
            continue
        used = {color_of.get(j) for j in adj[i]}
        free = [c for c in names if c not in used] or names
        color_of[i] = free[0]
        names = names[1:] + names[:1]          # fait tourner la palette

    noise = pop.wobble(lab.shape, rng, cells=10, amp=0.15)
    for i, c in color_of.items():
        if c:
            m = pop.smooth(lab == i, 0.004 * d, noise) & ~subject
            pop.paint(canvas, m, pop.COULEURS[c], *pop.blend_for(photo, m, 0.4))

    edge = np.zeros(lab.shape, dtype=bool)
    edge[1:] |= lab[1:] != lab[:-1]
    edge[:, 1:] |= lab[:, 1:] != lab[:, :-1]
    edge &= ~pop.erode(subject, 0.004 * d)
    edge |= pop.outline(subject, 2)
    line = pop.smooth(pop.dilate(edge, 0.004 * d), 0.003 * d, noise * 0.5)
    pop.paint(canvas, line, pop.CONTOUR, "normal")
    return canvas


if __name__ == "__main__":
    pop.run_cli("plages", __doc__.strip().splitlines()[0], render, add_args)
