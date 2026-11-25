# Empreinte : notes techniques

Pour les curieux et pour ceux qui veulent modifier le programme. Pour l'utiliser, le [README](../README.md) suffit.

## L'algorithme, étape par étape

1. **Découpage** (`engine.segment`) : une hausse au-dessus du seuil principal (350 W par défaut) ouvre une utilisation. Un second seuil (10 W par défaut) détecte les petites hausses par rapport au niveau médian précédent, avec une confirmation d'au moins 30 secondes mais sans exiger une puissance constante. Le bruit est estimé sur les différences entre mesures récentes et peut relever le seuil effectif. Le fond de départ reste fixe pendant la confirmation ; la fin dépend du retour vers ce fond, pas d'une fraction du pic. Cela couvre notamment les cycles variables de 60–150 W sans pic de démarrage. Une phase stable jusqu'à 180 W après une chauffe peut prolonger la même utilisation ; les pauses jusqu'à 150 s sont conservées. La courbe agrégée ne permet pas toujours de distinguer deux appareils qui se chevauchent.
2. **Résumé** (`engine.features`) : puissance du palier de départ, durée, part du temps allumé, nombre de marche/arrêt, forme (stable, paliers, cycles), heure et signature normalisée de la courbe complète.
3. **Séparation** (`engine.split_session`) : quand plusieurs appareils tournent ensemble, chaque montée est associée à la descente de même taille. On ne sépare que si c'est net.
4. **Recollage** (`engine.should_stitch`) : un appareil qui reprend dans les 6 minutes avec la même puissance (thermostat) reste une seule utilisation.
5. **Regroupement** (`engine.dbscan`, `engine.assign`) : les utilisations qui se ressemblent forment un groupe, en respectant les corrections de l'utilisateur. La comparaison prend en compte les résumés et la forme complète de la courbe ; les utilisations confirmées apportent des exemples, sans attribuer automatiquement un nom incertain. Les rangements automatiques restent « probables » et ne servent pas à l'apprentissage.
6. **Suivi** (`engine.track`) : un appareil désigné (ou reconnu net) est suivi de son démarrage à son arrêt au milieu des autres, avec ses propres sauts, sa tolérance apprise et les pauses longues des programmes.
7. **Coupures** : plus de 10 minutes sans valeur = coupure ; rien n'est compté pendant le trou et le retour du courant n'est pas pris pour un appareil.

Tout est en Python pur : aucune bibliothèque à installer, aucun service externe.

## Ce que l'intégration publie

Pour chaque appareil validé : `binary_sensor.empreinte_<nom>` (en marche), `sensor.empreinte_<nom>_puissance` (W) et `sensor.empreinte_<nom>_energie` (kWh, pour le tableau de bord Énergie). Pour chaque catégorie ajoutée dans Énergie : `sensor.empreinte_categorie_<nom>_puissance` et `_energie`.

Bilan par jour (pour des barres empilées dans un tableau de bord) : `sensor.empreinte_bilan_reste_energie` (« Non identifié » : la
maison moins chaque ligne du tableau Énergie), `sensor.empreinte_bilan_reste_cout`, et `sensor.empreinte_bilan_cout_<ligne>`
pour chaque ligne, au prix du kWh du tableau Énergie. Une ligne ajoutée au tableau Énergie est prise en compte seule.

## Les réglages

| Clé (options de l'intégration) | Rôle |
|---|---|
| `power_entity` | La puissance de toute la maison (W ou VA). Seul réglage obligatoire, choisi à l'installation. |
| `detection_w` | Seuil principal des utilisations à forte variation (350 W par défaut). |
| `plateau_w` | Hausse minimale des petits appareils par rapport au niveau précédent (10 W par défaut, plage 1–100 W). Confirmation sur au moins 30 secondes sans contrainte de puissance constante ; seuil effectif adapté au bruit. Les phases basses après une chauffe suivent une règle distincte. Disponible dans le panneau et les options de l'intégration. Le changement de seuil relance l'analyse de l'historique conservé. Le nom interne est conservé pour la compatibilité des réglages. |
| `measured` | Prises qui mesurent déjà un appareil : leur puissance est soustraite avant l'analyse. |
| `climate_entity` | La clim / pompe à chaleur : quand elle tourne, les sauts de moins de 450 W ne sont pas des appareils. |
| `climate_energy` | Son compteur de kWh : une ligne lissée dans le bilan, qui ne prend jamais plus que ce que la maison a laissé. |
| `fridge_kwh_year` | Le frigo, estimé à partir de son étiquette (0 = pas estimé). |
| `extra_lines` | Compteurs d'énergie estimés (Powercalc…) retirés du « non identifié », jamais ajoutés au tableau Énergie. |

## Contenu du dépôt

| Dossier | Rôle |
|---|---|
| `custom_components/empreinte/` | L'intégration Home Assistant (algorithme, stockage SQLite, capteurs, API WebSocket, panneau) |
| `custom_components/empreinte/frontend/` | L'interface affichée dans le menu « Empreinte » de HA |
| `tests/` | Maison simulée, suivi d'appareils, coordinateur, bilan, conseils, désinstallation |
| `dev/mock.html` | L'interface sans Home Assistant (`?demo` : maison imaginaire de `dev/make_demo.py`) |
| `dev/harness.html` | L'interface en local, branchée sur un Home Assistant avec un jeton saisi à la main |

## Vérifier l'algorithme

```
python tests/test_scenarios.py
python tests/test_tracking.py     # suivi d'un appareil au milieu des autres (référence : 377/390)
python tests/test_coordinator.py
node tests/test_habits.mjs
python tests/test_bilan.py       # reste de la maison et coût par ligne (graphiques par jour)
python tests/test_clim.py        # clim en marche et faux démarrages en direct
python tests/test_desinstallation.py  # supprimer l'intégration efface tout ce qu'elle a ajouté, et rien d'autre
python tests/test_partagee.py   # prise partagée : programmes découpés, lave-linge ou sèche-linge, réponses apprises
python tests/test_fil_principal.py  # rien ne lit la base de données sur le fil principal de Home Assistant
python tests/test_conseils.py    # économies possibles, programmes du lave-vaisselle comptés une fois
```

À relancer après chaque modification : aucun score ne doit baisser.

Toutes les maisons des tests sont simulées : aucune courbe réelle n'est publiée. Pour vérifier une modification
sur votre propre maison, rejouez votre historique dans `dev/harness.html` (branché sur votre Home Assistant).

## Bilan : ce qui empêche les heures négatives

- Le frigo, les veilles **et la clim** ne prennent jamais plus que ce que la maison a laissé chaque minute ; le
  reste attend et se rattrape ensuite (la clim : au plus 0,5 kWh de retard). Le compteur de la clim n'avance que par
  paliers de 0,1 kWh relevés avec 30 à 45 min de retard : sans cela, le non identifié passait sous zéro certaines heures.
- Une utilisation comptée après coup est remise à ses vraies minutes **selon sa propre courbe** (un sèche-linge
  chauffe surtout au début), et non plus à parts égales.
- En direct, le chauffage n'est annoncé que s'il ne clignote pas (pas de saut de même taille dans les 10 min d'avant,
  pas d'extinction suivie d'un rallumage) et si son saut ne ressemble pas davantage à un autre appareil nommé (plaques).

## Limites connues

- Le Linky donne une valeur toutes les 7 à 38 s : un appareil allumé moins de 30 s est invisible.
- Les petits appareils doivent créer une hausse discernable par rapport au niveau précédent, mais leur puissance peut ensuite varier. Une variation plus faible que le seuil effectif, ou trop courte/bruitée, reste dans le fond. Une puissance agrégée ne permet pas de confirmer l'identité d'un appareil.
- Les petits appareils peuvent être détectés et regroupés, mais les capteurs de marche dédiés ne sont pas garantis pour eux. Le suivi en direct des petits sauts connus utilise aussi une confirmation de 30 secondes, avec des contrôles supplémentaires pour éviter les fausses identifications.
- Une modification d'un seuil resegmente l'historique encore conservé ; des événements/réponses peuvent donc changer ou ne plus avoir d'équivalent. Une estimation séparée du frigo peut compter une seconde fois un événement identifié comme frigo : désactivez-la si vous utilisez ce groupe.
- Le capteur de puissance du Linky est souvent en VA (puissance apparente) : les kWh affichés par Empreinte sont un peu au-dessus des vrais.
- Des plaques à induction qui changent souvent de puissance, en même temps que le four, restent le cas le plus difficile.
