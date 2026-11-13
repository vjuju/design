# molecule — molécules qui fusionnent comme des gouttes

Plusieurs plans superposés, chacun portant quelques atomes reliés par des
liaisons évasées, fondus comme des gouttes (effet « gooey »), un dégradé par plan. Tout est **vectoriel** :
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
python3 molecule.py --plans 8 --atomes 2 4 --serie 12 -o essais/
python3 build_page.py                                # refait la série et la planche
```

Options :

| Option | Effet | Défaut |
| --- | --- | --- |
| `--plans N` | nombre de plans superposés, chacun d'une couleur | 6 |
| `--atomes X Y` | atomes par plan, tirés entre X et Y | 3 5 |
| `--coude` | angle moyen entre deux liaisons qui se suivent (± 18° au hasard) | 90 |
| `--evasement` | évasement des liaisons à leur base (0 : col droit) | 1 |
| `--fusion` | douceur des raccords là où plusieurs liaisons se rejoignent | 1 |
| `--satellites` | petites gouttes isolées | 4 |
| `--palette` | `aurore` · `lagon` · `sous-bois` · `corail` · `nuit` | au hasard |
| `--format` | `affiche` · `carre` · `paysage` · `story` | `affiche` |
| `--zone` | `droite` (laisse la place au titre) · `gauche` · `bas` · `partout` | selon le titre |
| `--titre`, `--sous-titre`, `--echelle`, `--seed`, `--serie`, `-o` | | |

Même graine, mêmes réglages : même image.

## Comment c'est fait

1. **Plans.** L'image superpose plusieurs plans, du fond vers l'avant. Chaque
   plan porte une petite molécule de X à Y atomes et sa propre couleur ; les
   plans se chevauchent librement, les satellites se glissent entre eux.
2. **Croissance.** Chaque nouvel atome part à environ 90° de la liaison qui
   arrive, à gauche ou à droite, avec un écart aléatoire : trois atomes liés
   ne sont presque jamais alignés. Une liaison ne traverse jamais un autre atome.
3. **Liaisons évasées.** Un atome est un disque, une liaison un col fin. Chaque
   col est soudé à ses deux atomes par un *minimum lissé* à large rayon : ce
   congé évase sa base, comme une goutte qui s'étire avant de se détacher.
4. **Contour.** La courbe de niveau zéro est extraite par *marching squares* sur
   une grille de 2 unités, rééchantillonnée à pas régulier puis lissée en
   Bézier cubiques (Catmull-Rom).
5. **Couleur.** Un dégradé linéaire de deux ou trois teintes par plan, à
   orientation libre ; les satellites isolés sont en aplat.

Pour ajouter une palette, compléter `PALETTES` dans `molecule.py` : un fond, une
encre pour le texte, une liste de dégradés (un par plan) et les teintes des
satellites.
