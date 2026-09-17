# Siemens OZW672.01

Intégration locale Home Assistant pour les régulations de chauffage Siemens pilotées
par le serveur web **OZW672**.

## Points forts

- Configuration entièrement via l'interface, sans YAML.
- Choix de l'appareil de l'installation parmi ceux annoncés par l'OZW672.
- **Les points de données sont identifiés par leur topic** : l'OZW672 génère les
  identifiants numériques pour chaque installation ; ils sont vérifiés et mis à jour
  à chaque rechargement.
- Parcours de l'installation **topic par topic** pour choisir librement ses points de
  données (topic suivant / précédent, validation quand vous voulez), à l'installation
  comme depuis les options.
- Capteurs en lecture (températures, pression, modulation, énergie, heures de
  fonctionnement, états, messages), entités `number` pour les consignes numériques
  inscriptibles avec la plage et le pas annoncés par le régulateur, entités `select`
  pour les énumérations inscriptibles, pré-remplies avec les libellés de l'appareil.
- Le type d'entité est déduit de la description que l'OZW672 renvoie pour chaque
  point de données (type, unité, plage, résolution, valeurs d'énumération).
- Ajout possible d'un point de données par son identifiant numérique, à l'installation
  comme depuis les options.
- Service générique `siemens_ozw672.write_datapoint`.
- Renouvellement automatique de la session et prise en charge de la ré-authentification.

## Démarrage rapide

1. Installez via HACS (catégorie *Integration*) et redémarrez Home Assistant.
2. **Paramètres → Appareils et services → Ajouter une intégration → Siemens OZW672**.
3. Renseignez l'adresse IP et les identifiants du compte web de l'OZW672, choisissez
   l'appareil de l'installation, puis sélectionnez vos points de données par topic.

Consultez le [README](https://github.com/Didier57/Siemens-OZW672.01#readme) pour la
documentation complète et le dépannage.
