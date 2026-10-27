# design

Bac à sable : un repo pour tester des idées de design. Chaque dossier est une
piste, avec le script qui fabrique et la planche qui montre le résultat.

**En ligne : https://vjuju.github.io/design/**

## Pistes

| Dossier | Piste |
| --- | --- |
| [`photo/mask/`](photo/mask/) | bichromie noir + une couleur, avec un aplat de forme aléatoire en fusion multiply |
| [`photo/mask/css/`](photo/mask/css/) | le même traitement rejoué par le navigateur : filtre SVG + `clip-path`, sans JavaScript |
| [`photo/aplats/`](photo/aplats/) | aplats francs, contours noirs et traits de vibration à la Keith Haring, posés sans IA sur n'importe quelle photo |
| [`photo/aplats/web/`](photo/aplats/web/) | les aplats de `figures.py` calculés par le navigateur, et animés : ils évitent le curseur, un clic les déplace |
| [`gigot/`](gigot/) | design system de gigot.app : palette, logo, pictogramme, bouton animé et aplats sur photo, façon Keith Haring |
| [`gigot/accueil/`](gigot/accueil/) | maquette de l'accueil de gigot.app avec le design system : cartes, aperçu au survol, fiche, clair / sombre |

## Publication

`.github/workflows/pages.yml` publie le repo sur GitHub Pages à chaque push sur
la branche par défaut. Le site est le repo lui-même : `photo/mask/index.html`
est servi à `/design/photo/mask/`.
