# mask — bichromie noir + une couleur, avec aplat en multiply

Test de direction artistique : ramener une photographie à deux encres, puis poser
par-dessus une forme géométrique tirée au sort en fusion **multiply**. L'aplat
n'éclaircit jamais — il assombrit et teinte la zone qu'il recouvre, comme une
seconde passe d'encre sur du papier.

## Contenu

| Fichier | Rôle |
| --- | --- |
| `mask.py` | le script de traitement (duotone + aplat), utilisable en CLI |
| `fetch_sources.py` | télécharge les photos listées dans `sources.json` |
| `build_page.py` | génère `index.html` à partir des manifestes |
| `sources.json` | les douze photos Unsplash, avec crédits |
| `sources/` | les originaux |
| `output/` | les rendus + `recipes.json` (la recette de chaque image) |
| `index.html` | la planche des douze résultats |

## Rejouer la série

```sh
pip install Pillow
python3 fetch_sources.py
python3 mask.py sources/ -o output/ --seed 2017 --manifest output/recipes.json --max-size 900
python3 build_page.py
```

Ouvrir ensuite `index.html`. Sans `--seed`, chaque passage tire une nouvelle série.

## Le script

```sh
python3 mask.py photo.jpg                          # réglages entièrement aléatoires
python3 mask.py sources/ -o output/                # tout un dossier
python3 mask.py photo.jpg --color rose --shape circle --opacity 0.7
python3 mask.py photo.jpg --color "#2B50FF" --seed 42
```

Options : `--color` (nom de la palette ou `#RRGGBB`), `--shape`
(`triangle` · `circle` · `rectangle`), `--opacity`, `--contrast`, `--seed`,
`--max-size`, `--quality`, `--manifest`.

### Comment la bichromie est calculée

La rampe passe par **trois** points, pas deux : noir teinté → couleur pure (à
55 % de l'échelle des gris) → blanc teinté. Un simple noir → couleur plafonne
les hautes lumières à la densité de l'encre : l'image devient sourde, et l'aplat
posé dessus n'a plus rien à assombrir. Le passage par un blanc cassé garde des
zones claires où le multiply peut mordre — c'est la mécanique d'une bichromie
imprimée.

### La palette

Dix encres franches, esprit sérigraphie : rose, menthe, outremer, mandarine,
violet, safran, cyan, vermillon, olive, lagon. Chacune tient seule face au noir,
ce qui est la contrainte d'un duotone à une seule couleur.

Une fois sur deux l'aplat reprend l'encre de la bichromie — la forme ne se lit
alors que par sa densité. L'autre fois il en prend une différente, et une
troisième valeur apparaît à l'endroit du recouvrement.

## Note sur les sources

Chaque entrée de `sources.json` porte deux adresses : `url` (CDN Unsplash, pleine
résolution) et `mirror` (miroir S3, 400 px de large). `fetch_sources.py` tente la
première puis retombe sur la seconde — utile derrière un proxy filtrant, ce qui
était le cas ici : les images de cette planche viennent du miroir et sont donc en
basse définition. Sur un réseau ouvert, le même script récupère les pleines
résolutions sans changement.

Photos sous [licence Unsplash](https://unsplash.com/license), créditées sous
chaque rendu de la planche.
