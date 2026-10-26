# aplats — couleurs franches et traits noirs, à la Keith Haring

Trois scripts qui posent des aplats de couleur, de gros contours noirs et des
traits de vibration sur **n'importe quelle photo**. Aucune IA, aucun modèle :
la photo n'est jamais retouchée, elle est seulement analysée pour savoir où
peindre, puis on superpose.

## Palette

| Rôle | Couleur |
| --- | --- |
| fond | `#F8F8F8` blanc cassé (liserés entre les anneaux, fond de la planche) |
| contour | `#1D1B1A` noir chaud (tous les traits) |
| aplats | jaune `#F4C946` · vert `#6AB357` · rose `#DB6DA2` · orange `#E26E3B` · bleu `#53B5E3` |

## Les scripts

| Fichier | Traitement |
| --- | --- |
| `figures.py` | chaque sujet saillant reçoit une silhouette de couleur élargie, décalée comme un repérage raté de sérigraphie, cernée de noir ; le principal vibre |
| `ondes.py` | le sujet principal est cerné de noir et émet des anneaux de couleur qui épousent sa forme, séparés par un liseré blanc, puis des traits rayonnants |
| `plages.py` | la photo est réduite à ses grandes masses ; chacune devient une plage peinte (deux voisines n'ont jamais la même couleur), frontières au gros trait ; le sujet reste la photo |
| `pop.py` | les outils communs : palette, détection du sujet, morphologie, composition, CLI |
| `build_page.py` | génère `index.html` |

```sh
pip install Pillow numpy
python3 figures.py photo.jpg                     # -> output/figures/photo.jpg
python3 ondes.py dossier/ --variants 3           # trois tirages par image
python3 plages.py photo.jpg --seed 2005          # rejoue un tirage précis
```

Options communes : `-o` (dossier de sortie), `--seed`, `--variants`,
`--max-size`, `--quality`. Chaque passage complète `output/<script>/seeds.json`.
Options propres : `figures.py --subjects 3 --no-rays` ·
`ondes.py --rings 3 --mode auto|multiply|normal` ·
`plages.py --levels 6 --blank 0.2 --dark 0.22 --no-protect`.

## Comment on trouve où peindre, sans IA

**Le sujet** (`pop.subjects`) vient d'une carte de saillance faite de trois
indices : l'écart à la couleur dominante de l'image (presque toujours le fond),
le contraste local (luminance moins luminance très floutée) et la saturation,
avec un léger biais vers le centre. Cette carte est seuillée à plusieurs
hauteurs — plus le seuil monte, plus le sujet se décolle du décor voisin — et
toutes les zones obtenues sont notées par `pop.shape_score` : contraste avec
un anneau autour d'elles, forme ramassée qui remplit son cadre, pénalité pour
les bandes qui traversent l'image (ciel, plage, ligne d'arbres) et pour les
zones trop grandes. Les sujets secondaires doivent valoir au moins le tiers du
principal, sinon rien n'est peint.

**La forme au pinceau** (`pop.bold_shape`) : une fermeture morphologique
(dilater puis éroder) comble les creux, les trous sont bouchés, le bord est
arrondi puis rendu tremblé par un bruit basse fréquence. Une foule ou un décor
chargé redevient une seule forme franche, comme chez Haring. Toute la
morphologie est faite au flou gaussien re-seuillé, d'où les bords ronds.

**Les plages** (`plages.py`) : flou fort, quantification median cut de Pillow
à quelques teintes, filtre de mode pour nettoyer, puis coloration gloutonne du
graphe des voisinages.

**Les traits de vibration** (`pop.rays`) : points espacés sur le bord du
masque, normale sortante prise sur le gradient du masque flouté, trait court à
bouts ronds, dessiné en sur-échantillonnage pour l'antialiasing.

**La fusion** (`pop.blend_for`) : sur une zone claire, l'aplat est en
*multiply* — la couleur éclate et la photo reste visible au travers. Sur une
zone sombre le multiply ne donnerait rien : l'aplat devient couvrant.

## Limites

La saillance n'est qu'une heuristique. Sur [`test/`](test/), 26 photos
Unsplash de tous genres, `figures.py` vise juste sur une vingtaine ; il se
trompe encore quand le sujet est petit et fondu dans un décor coloré
(kickflip, aire de jeux, fresque, surfeur au loin), où un pan de décor se
détache mieux que la personne. Sur les photos très sombres, `plages.py` peint peu.
`--seed` permet de tirer jusqu'à obtenir le bon rendu, et les options de
chaque script de pousser le traitement.

Les douze vignettes reprennent les photos de [`../mask/`](../mask/), sous
[licence Unsplash](https://unsplash.com/license).
