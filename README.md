# design

Bac à sable : un repo pour tester des idées de design. Chaque dossier est une
piste, avec le script qui fabrique et la planche qui montre le résultat.

**En ligne : https://vjuju.github.io/design/**

## Pistes

| Dossier | Piste |
| --- | --- |
| [`photo/mask/`](photo/mask/) | bichromie noir + une couleur, avec un aplat de forme aléatoire en fusion multiply |
| [`photo/mask/css/`](photo/mask/css/) | le même traitement rejoué par le navigateur : filtre SVG + `clip-path`, sans JavaScript |

## Publication

`.github/workflows/pages.yml` publie le repo sur GitHub Pages à chaque push sur
la branche par défaut. Le site est le repo lui-même : `photo/mask/index.html`
est servi à `/design/photo/mask/`.
