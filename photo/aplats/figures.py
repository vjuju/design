#!/usr/bin/env python3
"""
figures.py — chaque sujet reçoit son aplat, cerné de noir, et le principal
vibre.

1. On cherche les zones saillantes (voir `pop.subjects`).
2. Autour de chacune on pose une silhouette élargie, aux bords tremblés, dans
   une couleur de la palette, légèrement décalée comme un repérage raté de
   sérigraphie. Sur un fond clair, fusion multiply : la couleur éclate et le
   sujet reste lisible au travers. Sur un fond sombre, où le multiply ne
   donnerait rien, l'aplat devient couvrant et s'arrête au bord du sujet.
3. La silhouette est cernée d'un gros trait noir chaud.
4. Autour du sujet principal, les traits rayonnants de Keith Haring.

    python3 figures.py photo.jpg
    python3 figures.py sources/ --variants 3 --seed 7
"""

from __future__ import annotations

import pop


def add_args(ap) -> None:
    ap.add_argument("--subjects", type=int, default=3, help="nombre de sujets colorés")
    ap.add_argument("--no-rays", action="store_true", help="sans traits de vibration")


def render(photo, rng, args):
    h, w = photo.shape[:2]
    d = pop.diag(photo.shape)
    canvas = photo.copy()
    subs = pop.subjects(photo, args.subjects)
    colors = pop.pick_colors(rng, len(subs))
    stroke = 0.009 * d

    blobs = []
    for i, (m, color) in enumerate(zip(subs, colors)):
        pad = d * (0.025 if i == 0 else 0.015)
        noise = pop.wobble(m.shape, rng, cells=9, amp=0.18)
        blob = pop.smooth(pop.dilate(pop.bold_shape(m, d), pad), 0.012 * d, noise)
        off = 0.012 * d
        blob = pop.shift(blob, int(rng.uniform(-off, off)), int(rng.uniform(-off, off)))
        mode, alpha = pop.blend_for(photo, blob & ~m)
        if mode == "normal":                 # fond sombre : halo couvrant,
            blob = blob & ~pop.smooth(m, 0.004 * d)   # le sujet reste visible
        pop.paint(canvas, blob, color, mode, alpha)
        blobs.append(blob)

    for blob in blobs:
        pop.paint(canvas, pop.outline(blob, stroke), pop.CONTOUR, "normal")

    if subs and not args.no_rays:
        ray = pop.rays((h, w), blobs[0], rng, gap=0.018 * d, length=0.035 * d,
                       width=stroke * 0.85, spacing=0.045 * d)
        pop.paint(canvas, ray, pop.CONTOUR, "normal")
    return canvas


if __name__ == "__main__":
    pop.run_cli("figures", __doc__.strip().splitlines()[0], render, add_args)
