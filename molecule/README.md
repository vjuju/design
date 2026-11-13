# molecule — molécules qui fusionnent comme des gouttes

Des atomes reliés par des liaisons, fondus les uns dans les autres (effet
« gooey »), une couleur ou un dégradé par molécule. Tout est **vectoriel** :
chaque image est un SVG de tracés de Bézier et de dégradés linéaires, net à toutes
les tailles et éditable dans Figma ou Illustrator.

## Contenu

| Fichier | Rôle |
| --- | --- |
| `molecule.py` | le générateur, utilisable en CLI (seule dépendance : numpy) |
| `build_page.py` | tire la série de référence dans `output/` et écrit `index.html` |
| `output/` | les SVG + `recettes.json` (la recette de chaque image) |
| `index.html` | la planche |

## Utilisation

```sh
pip install numpy
python3 molecule.py                                  # une affiche au hasard
python3 molecule.py --seed 7 --palette lagon
python3 molecule.py --titre "TECHNOLOGY" --sous-titre "CONNECT"
python3 molecule.py --format carre --zone partout --molecules 5 --serie 12 -o essais/
python3 build_page.py                                # refait la série et la planche
```

Options : `--palette` (`aurore` · `lagon` · `sous-bois` · `corail` · `nuit`),
`--format` (`affiche` · `carre` · `paysage` · `story`), `--zone` (`droite` ·
`gauche` · `bas` · `partout` : où poussent les molécules ; `droite` laisse la
place à un titre), `--molecules`, `--atomes MIN MAX`, `--satellites`,
`--anneaux` (part des gros atomes creusés), `--fusion` (viscosité des
jonctions), `--echelle`, `--titre`, `--sous-titre`, `--seed`, `--serie`, `-o`.
Même graine, mêmes réglages : même image.

## Comment c'est fait

1. **Croissance.** Une molécule pousse comme un petit arbre : un atome, puis des
   voisins à distance de liaison, dans une direction qui tourne doucement, avec
   des branches. Gros et petits atomes alternent ; ils ne se chevauchent pas.
2. **Champ de distance.** Chaque atome est un disque, chaque liaison une capsule
   plus fine (le col). Ils sont réunis par un *minimum lissé* : là où deux formes
   se rapprochent, la matière coule de l'une à l'autre comme deux gouttes.
   Les anneaux sont creusés après la fusion.
3. **Contour.** La courbe de niveau zéro est extraite par *marching squares* sur
   une grille de 2 unités, rééchantillonnée à pas régulier puis lissée en
   Bézier cubiques (Catmull-Rom).
4. **Couleur.** Un dégradé linéaire de deux ou trois teintes par molécule, à
   orientation libre ; les satellites isolés sont en aplat.

Pour ajouter une palette, compléter `PALETTES` dans `molecule.py` : un fond, une
encre pour le texte, une liste de dégradés (un par molécule) et les teintes des
satellites.
