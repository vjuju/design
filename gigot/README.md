# gigot — design system

Identité visuelle de [gigot.app](https://gigot.app), l'agenda culturel pour gigoter :
pop art, couleurs flash cernées de noir épais, dans l'esprit de Keith Haring.

**Planche en ligne : https://vjuju.github.io/design/gigot/**

## Contenu

| Chemin | Contenu |
| --- | --- |
| `tokens.css`, `tokens.json` | palette, police, règles et variantes du logo |
| `logo/gigot-logo-<fond>.svg` | logo complet « gigot » + tagline « L'APP POUR GIGOTER », 600×600, texte vectorisé |
| `picto/gigot-picto-<fond>.svg` | pictogramme seul (le O, son flanc, ses deux arcs), 160×160 |
| `bouton/gigot-button.js` + `.css` | bouton-case à cocher animé, sans framework |
| `bouton/react/GigotButton.tsx` + `.module.css` | le même bouton en composant React / Next.js |
| `scripts/gen-logo.py`, `gen-picto.py` | génèrent les SVG |
| `aplats/figures.py` + `pop.py` | aplats gigot sur photo, en Python |
| `aplats/aplats.js` | le même traitement dans le navigateur, formes animées |
| `aplats/index.html`, `aplats/exemples/` | la planche des aplats, en direct et en Python |
| `accueil/index.html`, `accueil/photos/` | maquette de la page d'accueil de l'app (voir plus bas) |
| `index.html` | la planche |

`<fond>` ∈ rose, jaune, cyan, vert, orange, violet, noir, blanc.

## Palette

| Nom | Hex | Texte dessus |
| --- | --- | --- |
| noir | `#111111` | blanc |
| blanc | `#FFFFFF` | noir |
| rose | `#FF3EA5` | noir |
| jaune | `#FFD60A` | noir |
| violet | `#7B2FF7` | blanc |
| cyan | `#2EC4F1` | noir |
| vert | `#39D353` | noir |
| orange | `#FF6A13` | noir |

Police : [Titan One](https://fonts.google.com/specimen/Titan+One) (Rodrigo Fuenzalida, SIL OFL).

## Règles du logo

- Le fond prend une des 8 couleurs ; lettres, face du O et flanc du O en prennent trois autres, toutes différentes.
- Ombre portée, arcs et tagline : blancs sur fond noir ou violet, noirs sur tous les autres fonds.
- Contours des lettres et du O, rond central : toujours `#111111`.

Toutes les couleurs d'un SVG sont dans le bloc `<style>` en tête :

```css
.fond    { fill: … }   /* fond */
.lettres { fill: … }   /* gig + t */
.o       { fill: … }   /* face du O */
.contour { fill: … }   /* flanc du O */
.encre   { color: … }  /* ombre, arcs, tagline : noir ou blanc */
```

## Accessibilité (WCAG 2.2 AA)

Seules ces paires passent 4,5:1 pour du texte : noir avec rose, orange, cyan, vert, jaune ou blanc ; blanc avec violet.
Les couleurs flash entre elles ne servent qu'à la décoration, toujours séparées par un contour noir.
À ne jamais juxtaposer sans contour : cyan/vert (1,03), rose/orange (1,13), jaune/vert et orange/vert (confusion rouge-vert).

## Bouton

Sans framework :

```html
<link rel="stylesheet" href="bouton/gigot-button.css">
<script src="bouton/gigot-button.js"></script>
<script>
  const b = GigotButton.create({ fond: 'rose', face: 'cyan', flanc: 'violet', label: 'Suivre' });
  b.addEventListener('change', e => console.log(e.detail.checked));
  document.body.append(b);
</script>
```

React / Next.js (copier `bouton/react/` dans le projet) :

```tsx
import GigotButton from '@/components/gigot/GigotButton';

<GigotButton fond="rose" face="cyan" flanc="violet" taille={132}
  checked={suivi} onCheckedChange={setSuivi} label="Suivre cet événement" />
```

Survol : la face du O suit le curseur, les arcs pivotent à 90° de l'axe centre → curseur et gardent leur position en sortie.
Clic : la face rejoint le flanc, un seul rond recentré rebondit, les arcs deviennent des paupières depuis leur angle courant, des traits rayonnent dans le O ; la pupille suit ensuite le curseur.
Re-clic : retour. `aria-pressed` reflète l'état ; `prefers-reduced-motion` coupe les mouvements.

## Aplats sur photo

Les couleurs flash posées sur n'importe quelle photo, cernées de noir `#111111`, avec les traits de
vibration de Keith Haring. Aucune IA : la photo est analysée (couleur dominante, contraste local,
saturation) pour trouver ses sujets, chacun reçoit une silhouette lisse, décalée comme un repérage
de sérigraphie raté. Sur fond clair l'aplat est en multiply, sur fond sombre en screen : la photo
reste visible dessous. Planche : [`aplats/`](aplats/).

Python (Pillow + numpy) :

```sh
python3 aplats/figures.py photo.jpg                # -> output/figures/photo.jpg
python3 aplats/figures.py dossier/ --variants 3 -o sortie/
python3 aplats/figures.py photo.jpg --seed 6005    # rejoue un tirage
```

Options : `--subjects 3`, `--corners 3`, `--no-rays`, `--detail 0.03`, `--dark screen|halo`,
`--palette vive|pop` (`vive` = les six couleurs flash de gigot).

Navigateur, sans dépendance (les photos doivent venir du même site que la page) :

```html
<img src="photo.jpg" data-aplats>
<script src="aplats/aplats.js"></script>
<script>Aplats.attach(img, { seed: 7, fill: 'screen', palette: 'vive' })</script>
```

Survol : les formes s'écartent du curseur. Clic sur une forme : elle part vers une autre zone
saillante et en prend la silhouette. `fill` choisit la pose de la couleur (`screen` par défaut,
`figures`, `multiply`, `halo`, `transparence`, `trame`).

Ces fichiers sont la version gigot de [`photo/aplats/`](../photo/aplats/), où la piste a été
explorée : mêmes scripts, contours en noir gigot et palette gigot par défaut.

## Accueil de l'app

[`accueil/`](accueil/) : la page d'arrivée de gigot.app refaite avec le design system, sur les vraies sorties
de Rouen du 27 octobre 2026 (75 sorties, aujourd'hui et demain, relevées sur gigot.app avec leurs photos).

- Barre du haut : le logo, puis des pictos ronds (rechercher, ajouter, mes sorties, ma commu, clair / sombre, compte).
- Filtres : Quand, Catégorie, En journée, En soirée, Gratuit, Ma commu, Nouveaux.
- Liste : un jour, des créneaux horaires repliables à gauche, des cartes réduites à la photo et au titre.
- Survol : la carte grandit sans décaler la grille et montre horaire, prix, lieu, catégories, « Garder » et le
  chevron *Plus d'infos*. Le chevron ouvre la fiche au centre avec l'API View Transitions.
- Aplats : deux couleurs par catégorie, regroupées en familles.

| Famille | Catégorie | Aplats |
| --- | --- | --- |
| Sur scène | Musique | rose, violet |
| | Théâtre & spectacles | rose, jaune |
| | Cinéma | violet, rose |
| À voir, à apprendre | Expositions | cyan, violet |
| | Conférences & savoirs | cyan, jaune |
| En famille, à table | Famille & ateliers | jaune, cyan |
| | Fêtes & gastronomie | orange, jaune |
| Au grand air | Sport | vert, violet |
| | Balades & patrimoine | vert, orange |

- Fin de liste : « Je suis prêt à gigoter plus loin », « Dis-moi dès qu'il y a du neuf », « Il manque un événement ! ».
- Clair / sombre : suit l'appareil ; le bouton soleil / lune impose l'autre mode et s'en souvient.

La page charge `../bouton/` et `../aplats/aplats.js` : elle se sert sur le site, pas en `file://`
(les aplats lisent les pixels des photos).

## Régénérer les SVG

```sh
pip install fonttools
curl -LO https://raw.githubusercontent.com/google/fonts/main/ofl/titanone/TitanOne-Regular.ttf
TITAN_ONE_TTF=TitanOne-Regular.ttf python3 scripts/gen-logo.py logo
python3 scripts/gen-picto.py picto
```

Les combinaisons de couleurs sont dans la liste `VERSIONS` de chaque script.
