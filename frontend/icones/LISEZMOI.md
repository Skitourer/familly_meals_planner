# Sources des icônes

L'icône principale est `static/icone.svg` ; `static/favicon.svg` en est une version
simplifiée, lisible à 16–32 px (onglet du navigateur). Les fichiers de ce dossier en sont
dérivés :

| Source                 | PNG exporté (dans `static/`)     | Usage                                                                    |
| ---------------------- | -------------------------------- | ------------------------------------------------------------------------ |
| `static/icone.svg`     | `icone-192.png`, `icone-512.png` | icône standard (manifeste)                                               |
| `maskable.svg`         | `icone-maskable-512.png`         | Android : rognée en cercle ou en goutte, dessin dans la zone sûre (80 %) |
| `monochrome.svg`       | `icone-monochrome-512.png`       | Android 13+ : « icônes à thème », silhouette teintée par le système      |
| `apple-touch-icon.svg` | `apple-touch-icon.png` (180 px)  | iPhone : fond plein, iOS arrondit les coins                              |

Après une modification, réexporter chaque PNG à la taille indiquée, fond transparent
(Inkscape, ou tout navigateur avec une capture d'écran).
