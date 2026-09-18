#!/usr/bin/env python3
"""
mask.py — duotone noir + une couleur, avec un aplat de forme en multiply.

Le traitement se fait en deux temps :

1. duotone  : la photo est ramenée en luminance puis re-mappée sur une rampe
              qui va du noir (ombres) vers une seule couleur (hautes lumières).
2. overlay  : une forme aléatoire (triangle, cercle ou rectangle) est posée
              par-dessus en fusion multiply — l'aplat assombrit et teinte
              la zone qu'il recouvre sans jamais l'éclaircir.

Usage
-----
    python3 mask.py photo.jpg                      # une image, réglages aléatoires
    python3 mask.py sources/ -o output/            # tout un dossier
    python3 mask.py photo.jpg --color "#FF4D8D" --shape circle --seed 7

Dépendance : Pillow.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageOps

# --------------------------------------------------------------------------
# Palette
# --------------------------------------------------------------------------

# Encres franches, esprit sérigraphie / risographie : chacune tient seule
# face au noir, ce qui est la contrainte d'un duotone à une couleur.
PALETTE: dict[str, str] = {
    "rose":      "#FF4D8D",
    "menthe":    "#00A878",
    "outremer":  "#2B50FF",
    "mandarine": "#FF6B35",
    "violet":    "#7B2FF7",
    "safran":    "#FFC300",
    "cyan":      "#00B3D6",
    "vermillon": "#E4002B",
    "olive":     "#8FB339",
    "lagon":     "#00D1B2",
}

SHAPES = ("triangle", "circle", "rectangle")

# Antialiasing : on dessine les formes à cette échelle puis on réduit.
SUPERSAMPLE = 4


# --------------------------------------------------------------------------
# Utilitaires couleur
# --------------------------------------------------------------------------

def hex_to_rgb(value: str) -> tuple[int, int, int]:
    """'#FF4D8D' ou 'FF4D8D' -> (255, 77, 141)."""
    v = value.strip().lstrip("#")
    if len(v) == 3:
        v = "".join(c * 2 for c in v)
    if len(v) != 6:
        raise ValueError(f"couleur hexadécimale invalide : {value!r}")
    return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def resolve_color(value: str) -> tuple[int, int, int]:
    """Accepte un nom de la palette ou un code hexadécimal."""
    if value in PALETTE:
        return hex_to_rgb(PALETTE[value])
    return hex_to_rgb(value)


def mix(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))  # type: ignore[return-value]


# --------------------------------------------------------------------------
# Étape 1 — duotone
# --------------------------------------------------------------------------

def duotone(
    img: Image.Image,
    color: tuple[int, int, int],
    shadow: tuple[int, int, int] | None = None,
    highlight: tuple[int, int, int] | None = None,
    contrast: float = 1.15,
    midpoint: float = 0.55,
) -> Image.Image:
    """Ramène l'image sur une rampe à deux encres : noir et `color`.

    La rampe passe par trois points plutôt que deux. Un simple noir -> couleur
    plafonne les hautes lumières à la densité de l'encre : tout l'image devient
    sourde, et un aplat en multiply posé dessus n'a plus rien à assombrir. En
    faisant passer la rampe par la couleur à mi-parcours puis vers un blanc
    teinté, on garde des blancs qui respirent et la couleur reste lisible dans
    les demi-tons — c'est la mécanique d'une bichromie imprimée.

    `shadow` reste quasi noir mais conserve la teinte de l'encre ;
    `midpoint` place la couleur pure sur l'échelle des gris.
    """
    if shadow is None:
        shadow = mix(color, (0, 0, 0), 0.90)
    if highlight is None:
        highlight = mix(color, (255, 255, 255), 0.88)

    gray = ImageOps.grayscale(img.convert("RGB"))

    if contrast != 1.0:
        gray = gray.point(lambda v: max(0, min(255, round((v - 128) * contrast + 128))))

    knee = max(1, min(254, round(midpoint * 255)))

    # Une LUT par canal : Image.point sur une image L renvoyant du RGB.
    lut: list[int] = []
    for channel in range(3):
        for v in range(256):
            if v <= knee:
                t = v / knee
                lut.append(round(shadow[channel] + (color[channel] - shadow[channel]) * t))
            else:
                t = (v - knee) / (255 - knee)
                lut.append(round(color[channel] + (highlight[channel] - color[channel]) * t))

    return gray.convert("RGB").point(lut)


# --------------------------------------------------------------------------
# Étape 2 — forme aléatoire en multiply
# --------------------------------------------------------------------------

def _triangle_points(rng: random.Random, w: int, h: int) -> list[tuple[float, float]]:
    """Triangle isocèle, taille et orientation tirées au sort."""
    cx = rng.uniform(0.15, 0.85) * w
    cy = rng.uniform(0.15, 0.85) * h
    radius = rng.uniform(0.22, 0.48) * min(w, h)
    rotation = rng.uniform(0, 2 * math.pi)
    return [
        (cx + radius * math.cos(rotation + i * 2 * math.pi / 3),
         cy + radius * math.sin(rotation + i * 2 * math.pi / 3))
        for i in range(3)
    ]


def _rectangle_points(rng: random.Random, w: int, h: int) -> list[tuple[float, float]]:
    """Rectangle quelconque, légèrement incliné."""
    cx = rng.uniform(0.2, 0.8) * w
    cy = rng.uniform(0.2, 0.8) * h
    half_w = rng.uniform(0.16, 0.42) * w
    half_h = rng.uniform(0.16, 0.42) * h
    angle = math.radians(rng.uniform(-28, 28))
    cos_a, sin_a = math.cos(angle), math.sin(angle)
    corners = [(-half_w, -half_h), (half_w, -half_h), (half_w, half_h), (-half_w, half_h)]
    return [(cx + x * cos_a - y * sin_a, cy + x * sin_a + y * cos_a) for x, y in corners]


def shape_mask(
    size: tuple[int, int],
    shape: str,
    rng: random.Random,
    opacity: float,
) -> Image.Image:
    """Masque niveaux de gris : `opacity * 255` dans la forme, 0 ailleurs."""
    w, h = size
    big = (w * SUPERSAMPLE, h * SUPERSAMPLE)
    layer = Image.new("L", big, 0)
    draw = ImageDraw.Draw(layer)
    level = round(max(0.0, min(1.0, opacity)) * 255)

    if shape == "circle":
        cx = rng.uniform(0.2, 0.8) * w
        cy = rng.uniform(0.2, 0.8) * h
        r = rng.uniform(0.18, 0.40) * min(w, h)
        box = [(cx - r) * SUPERSAMPLE, (cy - r) * SUPERSAMPLE,
               (cx + r) * SUPERSAMPLE, (cy + r) * SUPERSAMPLE]
        draw.ellipse(box, fill=level)
    elif shape == "triangle":
        pts = _triangle_points(rng, w, h)
        draw.polygon([(x * SUPERSAMPLE, y * SUPERSAMPLE) for x, y in pts], fill=level)
    elif shape == "rectangle":
        pts = _rectangle_points(rng, w, h)
        draw.polygon([(x * SUPERSAMPLE, y * SUPERSAMPLE) for x, y in pts], fill=level)
    else:
        raise ValueError(f"forme inconnue : {shape!r} (attendu : {', '.join(SHAPES)})")

    return layer.resize((w, h), Image.LANCZOS)


def multiply_shape(
    base: Image.Image,
    shape: str,
    color: tuple[int, int, int],
    rng: random.Random,
    opacity: float = 0.85,
) -> Image.Image:
    """Pose un aplat de `color` en fusion multiply, limité à la forme."""
    mask = shape_mask(base.size, shape, rng, opacity)
    flat = Image.new("RGB", base.size, color)
    multiplied = ImageChops.multiply(base, flat)
    return Image.composite(multiplied, base, mask)


# --------------------------------------------------------------------------
# Rendu complet
# --------------------------------------------------------------------------

@dataclass
class Recipe:
    """Les réglages tirés au sort pour une image — reproductibles via `seed`."""
    seed: int
    duotone_color: str
    duotone_name: str
    shape: str
    shape_color: str
    shape_name: str
    opacity: float
    contrast: float


def render(
    img: Image.Image,
    seed: int | None = None,
    color: str | None = None,
    shape: str | None = None,
    opacity: float | None = None,
    contrast: float | None = None,
    max_size: int = 1400,
) -> tuple[Image.Image, Recipe]:
    """Applique duotone + forme et renvoie l'image avec sa recette."""
    if seed is None:
        seed = random.randrange(1, 10 ** 6)
    rng = random.Random(seed)

    img = img.convert("RGB")
    if max_size and max(img.size) > max_size:
        img = ImageOps.contain(img, (max_size, max_size), Image.LANCZOS)

    names = list(PALETTE)

    if color is None:
        duo_name = rng.choice(names)
        duo_rgb = hex_to_rgb(PALETTE[duo_name])
    else:
        duo_rgb = resolve_color(color)
        duo_name = color if color in PALETTE else rgb_to_hex(duo_rgb)

    if shape is None:
        shape = rng.choice(SHAPES)

    # L'aplat reprend l'encre du duotone une fois sur deux ; sinon il en prend
    # une autre, ce qui fait apparaître une troisième valeur là où ils se croisent.
    if rng.random() < 0.5:
        shape_rgb, shape_name = duo_rgb, duo_name
    else:
        shape_name = rng.choice([n for n in names if n != duo_name])
        shape_rgb = hex_to_rgb(PALETTE[shape_name])

    if opacity is None:
        opacity = round(rng.uniform(0.55, 0.9), 2)
    if contrast is None:
        contrast = round(rng.uniform(1.05, 1.35), 2)

    out = duotone(img, duo_rgb, contrast=contrast)
    out = multiply_shape(out, shape, shape_rgb, rng, opacity)

    recipe = Recipe(
        seed=seed,
        duotone_color=rgb_to_hex(duo_rgb),
        duotone_name=duo_name,
        shape=shape,
        shape_color=rgb_to_hex(shape_rgb),
        shape_name=shape_name,
        opacity=opacity,
        contrast=contrast,
    )
    return out, recipe


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


def collect_inputs(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for p in paths:
        if p.is_dir():
            files += sorted(f for f in p.iterdir() if f.suffix.lower() in SUFFIXES)
        elif p.is_file():
            files.append(p)
        else:
            print(f"introuvable : {p}", file=sys.stderr)
    return files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Duotone noir + une couleur, avec un aplat de forme en multiply.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Couleurs de la palette : " + ", ".join(PALETTE),
    )
    parser.add_argument("inputs", nargs="+", type=Path, help="fichiers ou dossiers à traiter")
    parser.add_argument("-o", "--output", type=Path, default=Path("output"), help="dossier de sortie")
    parser.add_argument("--color", help="couleur du duotone : nom de la palette ou #RRGGBB")
    parser.add_argument("--shape", choices=SHAPES, help="forme imposée (sinon aléatoire)")
    parser.add_argument("--opacity", type=float, help="opacité de l'aplat, 0 à 1")
    parser.add_argument("--contrast", type=float, help="contraste avant duotone, 1 = neutre")
    parser.add_argument("--seed", type=int, help="graine du tirage, pour rejouer un rendu")
    parser.add_argument("--max-size", type=int, default=1400, help="côté le plus long en sortie")
    parser.add_argument("--quality", type=int, default=90, help="qualité JPEG")
    parser.add_argument("--manifest", type=Path, help="écrit les recettes dans ce fichier JSON")
    args = parser.parse_args(argv)

    files = collect_inputs(args.inputs)
    if not files:
        print("aucune image à traiter", file=sys.stderr)
        return 1

    args.output.mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = []

    for index, path in enumerate(files):
        # Une graine dérivée par image : --seed rejoue la série entière.
        seed = args.seed + index if args.seed is not None else None
        with Image.open(path) as src:
            out, recipe = render(
                src,
                seed=seed,
                color=args.color,
                shape=args.shape,
                opacity=args.opacity,
                contrast=args.contrast,
                max_size=args.max_size,
            )
        target = args.output / f"{path.stem}.jpg"
        out.save(target, "JPEG", quality=args.quality, subsampling=0, optimize=True)
        manifest.append({"source": path.name, "output": target.name, **asdict(recipe)})
        print(f"{path.name} -> {target}  [{recipe.duotone_name} · {recipe.shape} · {recipe.shape_name}]")

    if args.manifest:
        args.manifest.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"recettes écrites dans {args.manifest}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
