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
| `web/aplats.js` | `figures.py` rejoué par le navigateur, formes animées (voir plus bas) |

```sh
pip install Pillow numpy
python3 figures.py photo.jpg                     # -> output/figures/photo.jpg
python3 ondes.py dossier/ --variants 3           # trois tirages par image
python3 plages.py photo.jpg --seed 2005          # rejoue un tirage précis
```

Options communes : `-o` (dossier de sortie), `--seed`, `--variants`,
`--max-size`, `--quality`. Chaque passage complète `output/<script>/seeds.json`.
Options propres : `figures.py --subjects 3 --no-rays --corners 3 --detail 0.03` ·
`ondes.py --rings 3 --mode auto|multiply|normal` ·
`plages.py --levels 6 --blank 0.2 --dark 0.22 --no-protect`.

## Comment on trouve où peindre, sans IA

**Le sujet** (`pop.subjects`) vient d'une carte de saillance faite de trois
indices : l'écart à la couleur dominante de l'image (presque toujours le fond),
le contraste local (luminance moins luminance très floutée) et la saturation,
avec un léger biais vers le centre. Seuil d'Otsu, composantes connexes, et on
classe les zones par saillance cumulée en pénalisant celles qui touchent le
bord du cadre.

**Les formes vectorielles** (`figures.py`) : toute l'analyse se fait sur une
copie de 256 px de la photo (`pop.shrink`), ce qui la rend environ quatre fois
plus rapide. Le contour du sujet y est suivi pixel par pixel
(`pop.trace_contour`), réduit à quelques points de passage par
Douglas-Peucker (`pop.key_points`, réglable avec `--detail`), puis relié en
pleine résolution par une courbe de Catmull-Rom centripète (`pop.spline`) :
pas de bord haché, un trait noir de largeur constante. Les vibrations
(`pop.vibrations`) mêlent deux gestes : aux angles les plus saillants de la
forme (là où la courbe tourne le plus vite), un petit arc parallèle à la courbe,
doublé à l'extérieur d'un second deux fois plus court, souligne l'angle ;
ailleurs, quelques traits droits perpendiculaires. Le rendu ne touche que le
rectangle de chaque forme (`pop.box_of`), et dans ce rectangle seulement les
pixels qu'un trait recouvre : environ 0,3 s par photo de 900 px, 0,6 s à
1800 px.

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

## Dans le navigateur : `web/`

`web/aplats.js` refait la chaîne de `figures.py` en JavaScript, sans
dépendance : même analyse sur 256 px (saillance, Otsu, composantes, forme au
pinceau, morphologie au flou gaussien, suivi de Moore, Douglas-Peucker,
Catmull-Rom centripète), même palette, mêmes proportions de traits, même
choix multiply / halo couvrant, mêmes vibrations. Le rendu est à peu de chose
près celui du script : le hasard n'est pas le même (une graine Python ne
redonne pas le même tirage) et le mode de fusion est décidé sur la copie
réduite.

Puis les formes s'animent. Chaque courbe est rééchantillonnée en 160 points
montés sur ressorts (retour au repos, cohésion entre voisins, amortissement) :

* **au survol**, le curseur repousse les points proches — la forme se creuse
  autour de lui — et fait glisser toute la forme pour l'éviter ;
* **au clic sur une forme**, elle part vers une autre zone saillante de la
  photo restée libre (l'analyse en garde huit, trois seulement sont peintes)
  et prend sa silhouette : les deux courbes sont alignées point à point puis
  interpolées, avec une pseudo-force d'inertie qui la fait traîner et
  rebondir à l'arrivée. Le halo devient multiply en chemin si le nouveau fond
  est clair, et inversement ;
* **au clic à côté**, la forme la plus proche vient sur la zone cliquée, ou
  glisse simplement jusqu'au clic s'il n'y a pas de zone libre là ;
* au clavier, Entrée envoie le sujet principal ailleurs. Avec
  `prefers-reduced-motion`, plus de survol et les déplacements sont
  instantanés.

```html
<img src="photo.jpg" data-aplats>            <!-- tout img[data-aplats] -->
<script src="aplats.js"></script>
<script>Aplats.attach(img, { seed: 7, subjects: 3, corners: 3, detail: 0.03 })</script>
```

Les images doivent être servies par la même origine que la page (le
navigateur refuse sinon d'en lire les pixels) : `python3 -m http.server` à la
racine du repo, puis `http://localhost:8000/photo/aplats/web/`. La page
propose aussi d'essayer sur sa propre photo, qui ne quitte pas le navigateur.

## Limites

La saillance n'est qu'une heuristique : sur un fond sombre et chargé, la zone
la plus « détachée » peut être un pan de décor clair plutôt que la personne
(voir l'accordéoniste). Sur les photos très sombres, `plages.py` peint peu.
`--seed` permet de tirer jusqu'à obtenir le bon rendu, et les options de
chaque script de pousser le traitement.

Les douze vignettes reprennent les photos de [`../mask/`](../mask/), sous
[licence Unsplash](https://unsplash.com/license).
