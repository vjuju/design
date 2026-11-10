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
| [`sphere/`](sphere/) | site de Reskif : la sphère de Bruno Simon tombe dans une flaque, un arbre en sort et mène à quatre profils (feu, air avec The Spirit d'Edan Kwan, eau, buste en éclats) — [en ligne](https://vjuju.github.io/design/sphere/) |
| [`spiro/`](spiro/) | effet spirographe : sphères en fil de fer déformées puis projetées à plat, tracées au trait fin, export SVG pour traceur |
| [`spiro/boucles/`](spiro/boucles/) | un ruban en huit tordu dans l'espace, tracé par un millier de fils fins : voiles de face, trait dense de profil |
| [`gigot/accueil/`](gigot/accueil/) | maquette de l'accueil de gigot.app avec le design system : cartes, aperçu au survol, fiche, clair / sombre |

## Reskif (`sphere/`)

Une page autonome : HTML, CSS et JS dans `sphere/index.html`, three.js 0.132.2 et
les polices chargés par CDN, rien à installer. Elle doit être servie en HTTP
(le buste, `models/LeePerrySmith.json`, est chargé par `fetch`).

Crédits et licences, gardés dans le dossier :
- sphère : [Organic Sphere](https://github.com/brunosimon/organic-sphere) de Bruno Simon
  (dépôt sans licence : accord de l'auteur à demander avant un usage public) ;
- particules de l'air : [The Spirit](https://github.com/edankwan/The-Spirit) d'Edan Kwan,
  MIT (`sphere/LICENSE-The-Spirit.md`) ;
- buste : scan Lee Perry-Smith d'Infinite-Realities, CC BY 3.0
  (`sphere/models/LeePerrySmith-LICENSE.txt`) ;
- arbre : d'après les croissances procédurales de Marius Ballot, code original ;
- logo : `sphere/reskif_logo.svg`, repris de reskif.org.

## Publication

`.github/workflows/pages.yml` publie le repo sur GitHub Pages à chaque push sur
la branche par défaut. Le site est le repo lui-même : `photo/mask/index.html`
est servi à `/design/photo/mask/`.
