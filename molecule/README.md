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
| `web/index.html` | la version vivante, en WebGL2 : naissance, dérive, fusion en dégradé, attraction du curseur |

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

## La version vivante (`web/`)

Une page autonome, sans dépendance ni CDN : `web/index.html`. Le même dessin que
`molecule.py`, recalculé à chaque image par un fragment shader WebGL2.

- **Naissance.** Une molécule naît d'une seule couleur : ses atomes bourgeonnent
  l'un après l'autre, chacun sortant de son parent le long de sa liaison.
- **Dérive et fusion.** Les molécules dérivent et tournent lentement. Quand deux
  se frôlent, leurs champs se fondent (minimum lissé entre molécules) et leurs
  couleurs se mélangent selon la distance à chacune : le dégradé naît de la
  rencontre. Une légère répulsion les empêche de s'empiler.
- **Curseur.** Il attire doucement les atomes proches (ressort amorti) : les
  liaisons s'étirent et la molécule suit un peu.
- **Vie des atomes.** Chaque atome vit 7 à 15 s, puis rentre lentement dans son
  parent (5 s), les feuilles d'abord : un atome qui a encore des enfants attend
  qu'ils soient partis. Pendant 18 à 34 s, la molécule fait bourgeonner de
  nouveaux atomes pour rester entre X et Y ; ensuite elle s'éteint atome par
  atome, jamais d'un coup, et une autre naît ailleurs. Un clic fait naître une
  molécule et met la plus ancienne en déclin.

Réglages dans l'URL, mêmes noms que le script : `?palette=nuit&plans=8&atomes=2-4&coude=90&evasement=1`,
plus `rencontre` (viscosité entre molécules), `attraction` et `vitesse`.
`prefers-reduced-motion` ralentit tout.

Pourquoi pas une librairie : il n'en existe pas qui fasse ce dessin-là. Les
références (tutoriels Codrops et three.js sur les metaballs, metaballs-gpu,
filtres SVG « gooey ») partagent toutes le même principe, un champ de distance
calculé dans un shader ; c'est ce principe qu'on applique ici à nos formes
(cols évasés, coudes à 90°), en WebGL2 nu plutôt qu'avec three.js, qui
n'apporterait qu'un quad plein écran. Le shader se transpose tel quel dans un
`ShaderMaterial` si la page doit un jour vivre dans une scène three.js.
