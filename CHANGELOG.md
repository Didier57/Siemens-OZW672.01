# Changelog

Toutes les évolutions notables de ce projet sont documentées dans ce fichier.
Le format s'inspire de [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/)
et le versionnage suit [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2026-09-18

### Corrigé

- **L'écriture d'un `select` échouait avec `datatype not supported`** pour les
  points de données de type bouton radio (par exemple `Circuit de chauffage 1`,
  id 14511). Le régulateur refuse toute écriture dont le type n'est pas celui
  qu'il a annoncé : un bouton radio doit être écrit avec `Type=RadioButton` et
  non `Type=Enumeration`. Le type annoncé par l'appareil est désormais mémorisé
  puis utilisé pour écrire (`Numeric`, `Enumeration`, `RadioButton`,
  `TimeOfDay`), et le service `siemens_ozw672.write_datapoint` accepte les
  quatre types.
- Le type d'un point de données configuré par une version antérieure était
  considéré comme modifié par l'utilisateur et n'était donc jamais corrigé :
  il est maintenant réaligné sur le type annoncé par le régulateur à chaque
  rechargement, même si l'instantané de l'appareil contient encore l'ancienne
  valeur.

## [1.0.0] - 2026-09-17

Première version : l'intégration couvre tout le cycle de vie d'un point de données,
de la sélection à l'écriture d'une consigne sur le régulateur.

### Ajouté

- **Points de données identifiés par leur topic.** L'OZW672 ne possède pas de
  numérotation fixe : il génère les identifiants pour l'installation à laquelle il
  est raccordé, et ceux-ci peuvent changer lors d'une réactualisation des paramètres
  du serveur. Chaque point de données est donc mémorisé avec son chemin de topic
  (par exemple `Diagnostic consommateurs/Pompe à chaleur/Modulation compresseur`) et
  l'identifiant numérique ne sert que de pointeur en cache. Les identifiants sont
  recalculés depuis les topics à chaque mise en route — démarrage de Home Assistant,
  redémarrage, rechargement et modification des options — et un identifiant modifié
  est tracé dans le journal. Le chemin est conservé sous forme de **liste de
  segments**, car un libellé du régulateur peut lui-même contenir une barre oblique
  (`Heating/Cooling circuit 1`, `Jour/heure`, …) : la version texte n'est utilisée
  que pour l'affichage.
- **Sélection guidée des points de données par topic**, à l'installation comme
  depuis les options : l'installation est parcourue topic après topic, avec
  *Topic suivant*, *Topic précédent* (vos cases cochées sont restaurées) et
  *Terminer*. Les points de données déjà configurés reviennent pré-cochés.
- **Choix de l'appareil de l'installation** : l'OZW672 annonce les régulateurs qui
  lui sont raccordés, vous choisissez celui de l'entrée.
- **Ajout d'un point de données par son identifiant** : collez l'identifiant
  numérique d'un point de l'arborescence, l'intégration lit sa description sur
  l'appareil et l'ajoute. Si l'identifiant appartient à l'arborescence, son topic
  est également mémorisé pour être recalculé aux rechargements suivants.
- **Type d'entité déduit de la description de l'appareil.** Les métadonnées d'un
  point de données sont lues dans `api/menutree/datapoint_desc.json`, qui fournit le
  type, l'unité, la plage autorisée, la résolution et, pour une énumération ou un
  bouton radio, la liste complète des valeurs acceptées avec les libellés du
  régulateur. Un point de données numérique inscriptible devient donc un `number`
  avec la plage et le pas annoncés par l'appareil, une énumération ou un bouton
  radio inscriptible devient un `select` pré-rempli. Les points en lecture seule —
  états, messages de défaut, heures de fonctionnement — restent des capteurs, et
  tout reste modifiable dans *Modifier un point de données*.
- **Entités adaptées à chaque rechargement** : la description de chaque point de
  données configuré est relue sur l'appareil au démarrage, au redémarrage, au
  rechargement et à chaque changement d'options, sans avoir à supprimer puis
  rajouter l'entité. Un réglage modifié à la main n'est jamais écrasé, et une valeur
  que l'appareil cesse de fournir est conservée.
- **Entités** : capteurs pour les points en lecture seule (températures, pression,
  modulation, énergie, heures de fonctionnement, états, messages), entités `number`
  pour les points numériques inscriptibles, entités `select` pour les énumérations
  avec liste d'options, et un capteur binaire *Connectivité*.
- **Options** : réglages de scrutation (10 – 3600 s, 60 s par défaut), ajout de
  points de données, ajout par identifiant, suppression, modification d'un point de
  données (nom, type d'entité, type de valeur, options d'énumération, unité, classe
  d'appareil, classe d'état, min/max/pas).
- **Sauvegarde et restauration de la sélection** dans un fichier JSON : le fichier
  ne contient que l'identifiant et le nom de chaque point de données — aucune
  information de connexion, donc aucun mot de passe en clair. À la restauration,
  chaque identifiant est redécrit par l'OZW672, si bien que le type, l'unité, la
  plage et les valeurs d'énumération suivent ce que le régulateur annonce à ce
  moment-là. Les identifiants sont également recalculés depuis les topics au
  rechargement : une sauvegarde faite sur un OZW672 est donc acceptée sur un autre
  câblé de la même façon. Un fichier invalide est refusé avec un message précisant
  le motif.
- Service `siemens_ozw672.write_datapoint` pour écrire dans n'importe quel point de
  données.
- Renouvellement automatique de la session, prise en charge de la ré-authentification
  et traductions anglaise et française.
- Workflows de validation HACS et hassfest, plus un workflow qui purge les anciennes
  exécutions GitHub Actions.

### Remarques

- Les points de données non câblés sur l'installation (`----`, `---`) sont signalés
  comme inconnus au lieu d'être affichés comme une valeur.
- Deux frères portant le même libellé (le régulateur en compte quelques-uns, par
  exemple `Texte de défaut`) sont suffixés `#2`, `#3` … afin que les chemins de
  topic générés soient uniques et reproductibles.

[1.0.1]: https://github.com/Didier57/Siemens-OZW672.01/releases/tag/v1.0.1
[1.0.0]: https://github.com/Didier57/Siemens-OZW672.01/releases/tag/v1.0.0
