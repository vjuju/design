#!/usr/bin/env python3
"""
figures.py — chaque sujet reçoit son aplat, cerné de noir, et le principal
vibre.

1. On cherche les zones saillantes (voir `pop.subjects`) sur une copie de
   256 px de la photo.
2. Autour de chacune on pose une silhouette élargie, dans une couleur de la
   palette, légèrement décalée comme un repérage raté de sérigraphie. Sur un
   fond clair, fusion multiply : la couleur éclate et le sujet reste lisible
   au travers. Sur un fond sombre, où le multiply ne
   donnerait rien, l'aplat devient un halo couvrant autour du sujet.
   La silhouette n'est pas un masque de pixels : son contour est réduit à
   quelques points de passage, et une courbe lisse les relie.
3. La silhouette est cernée d'un gros trait noir chaud, de largeur constante.
4. Autour du sujet principal, les vibrations de Keith Haring : un petit
   arc, doublé d'un plus petit à l'extérieur, souligne ses angles les plus
   marqués, et quelques traits
   droits rayonnants ailleurs.

    python3 figures.py photo.jpg
    python3 figures.py sources/ --variants 3 --seed 7
"""

from __future__ import annotations

import pop


def add_args(ap) -> None:
    ap.add_argument("--subjects", type=int, default=3, help="nombre de sujets colorés")
    ap.add_argument("--no-rays", action="store_true", help="sans traits de vibration")
    ap.add_argument("--corners", type=int, default=3,
                    help="nombre d'angles soulignés par des arcs")
    ap.add_argument("--detail", type=float, default=0.03,
                    help="tolérance de simplification du contour, en part de la "
                         "diagonale : plus grand = moins de points de passage")


def render(photo, rng, args):
    h, w = photo.shape[:2]
    d = pop.diag(photo.shape)
    canvas = photo.copy()

    # Toute l'analyse se fait sur une copie de 256 px : c'est elle qui coûte.
    small, k = pop.shrink(photo)
    ds = pop.diag(small.shape)
    subs = pop.subjects(small, args.subjects)
    colors = pop.pick_colors(rng, len(subs))
    stroke = 0.009 * d
    tol = args.detail * ds

    curves = []
    for i, (m, color) in enumerate(zip(subs, colors)):
        shape = pop.bold_shape(m, ds)
        pad = ds * (0.025 if i == 0 else 0.015)
        curve = pop.curve_of(pop.dilate(shape, pad), k, tol)
        if curve is None:
            continue
        off = 0.012 * d
        curve = curve + [rng.uniform(-off, off), rng.uniform(-off, off)]
        fill = pop.fill_alpha((h, w), curve)

        inner = pop.curve_of(shape, k, tol)
        core = pop.fill_alpha((h, w), inner) if inner is not None else fill * 0
        mode, alpha = pop.blend_for(photo, (fill > 0.5) & (core < 0.5))
        if mode == "normal":                 # fond sombre : halo couvrant,
            fill = fill * (1 - core)         # le sujet reste visible
        pop.paint(canvas, fill, color, mode, alpha)
        curves.append(curve)

    for curve in curves:
        pop.paint(canvas, pop.stroke_alpha((h, w), curve, stroke), pop.CONTOUR, "normal")

    if curves and not args.no_rays:
        ray = pop.vibrations((h, w), curves[0], rng, gap=0.018 * d, length=0.035 * d,
                             width=stroke * 0.85, spacing=0.07 * d, arc=0.06 * d,
                             corners=args.corners)
        pop.paint(canvas, ray, pop.CONTOUR, "normal")
    return canvas


if __name__ == "__main__":
    pop.run_cli("figures", __doc__.strip().splitlines()[0], render, add_args)
