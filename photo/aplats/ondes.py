#!/usr/bin/env python3
"""
ondes.py — le sujet principal émet des ondes de couleur.

Le sujet le plus saillant est cerné de noir, puis entouré d'anneaux qui
suivent sa forme (dilatations successives du masque), chacun d'une couleur
de la palette et séparé du suivant par un liseré de blanc cassé : les
« vibrations » des figures de Keith Haring. Au-delà du dernier anneau,
quelques traits rayonnants.

    python3 ondes.py photo.jpg
    python3 ondes.py photo.jpg --rings 4 --seed 12
"""

from __future__ import annotations

import pop


def add_args(ap) -> None:
    ap.add_argument("--rings", type=int, default=3, help="nombre d'anneaux")
    ap.add_argument("--mode", choices=("auto", "multiply", "normal"), default="auto",
                    help="multiply : la photo transparaît ; normal : aplats couvrants ; "
                         "auto : selon la clarté du fond")


def render(photo, rng, args):
    h, w = photo.shape[:2]
    d = pop.diag(photo.shape)
    canvas = photo.copy()
    subs = pop.subjects(photo, 1)
    if not subs:
        return canvas

    noise = pop.wobble((h, w), rng, cells=6, amp=0.12)
    core = pop.bold_shape(subs[0], d, noise)
    band = 0.03 * d
    gap = 0.008 * d
    stroke = 0.008 * d
    colors = pop.pick_colors(rng, args.rings)

    # Du plus large au plus serré : chaque anneau recouvre le précédent.
    edges = []
    for i in reversed(range(args.rings)):
        outer = pop.smooth(pop.dilate(core, gap + (i + 1) * band), 0.006 * d)
        inner = pop.dilate(core, gap + i * band + gap)
        ring = outer & ~inner
        mode, alpha = pop.blend_for(photo, ring) if args.mode == "auto" else (args.mode, 0.95)
        pop.paint(canvas, ring, colors[i], mode, alpha)
        pop.paint(canvas, pop.outline(inner, gap * 0.9) & outer, pop.FOND, "normal", 0.9)
        edges.append(outer)

    for e in edges:
        pop.paint(canvas, pop.outline(e, stroke * 0.7), pop.CONTOUR, "normal")
    pop.paint(canvas, pop.outline(core, stroke), pop.CONTOUR, "normal")

    ray = pop.rays((h, w), edges[0], rng, gap=0.015 * d, length=0.03 * d,
                   width=stroke * 0.9, spacing=0.05 * d)
    pop.paint(canvas, ray, pop.CONTOUR, "normal")
    return canvas


if __name__ == "__main__":
    pop.run_cli("ondes", __doc__.strip().splitlines()[0], render, add_args)
