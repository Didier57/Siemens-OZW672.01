# Siemens OZW672.01

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/Didier57/Siemens-OZW672.01)](https://github.com/Didier57/Siemens-OZW672.01/releases)
[![License](https://img.shields.io/github/license/Didier57/Siemens-OZW672.01)](LICENSE)
[![Validate](https://github.com/Didier57/Siemens-OZW672.01/actions/workflows/validate.yml/badge.svg)](https://github.com/Didier57/Siemens-OZW672.01/actions/workflows/validate.yml)
[![Hassfest](https://github.com/Didier57/Siemens-OZW672.01/actions/workflows/hassfest.yml/badge.svg)](https://github.com/Didier57/Siemens-OZW672.01/actions/workflows/hassfest.yml)

Intégration personnalisée Home Assistant pour les régulations de chauffage Siemens exposées par le serveur web **OZW672** (et les OZW67x compatibles).

L'intégration dialogue directement avec l'API JSON de l'OZW672 sur votre réseau local : pas de cloud, pas de YAML, pas de `rest_command` à maintenir.

## Pourquoi les points de données sont identifiés par leur topic

L'OZW672 ne possède **pas** de numérotation fixe des points de données. Il construit son arborescence à partir des appareils réellement raccordés, et les identifiants de cette arborescence sont générés pour chaque installation :

- deux installations différentes n'ont presque jamais les mêmes identifiants ;
- sur une même installation, les identifiants peuvent changer après une réactualisation des paramètres du serveur OZW672 ou une reconstruction de la liste des appareils.

L'intégration identifie donc chaque point de données par son **chemin de topic** dans l'arborescence, par exemple :

```
Diagnostic consommateurs/Pompe à chaleur/Modulation compresseur
Configuration/Circuit de chauffage 1/Consigne confort
Etat/Etat du circuit de chauffage 1
```

L'identifiant numérique n'est conservé que comme pointeur en cache dans l'entrée de configuration. À chaque mise en route — c'est-à-dire à chaque démarrage de Home Assistant, redémarrage, rechargement de l'intégration et modification des options — l'intégration reparcourt l'arborescence de l'OZW672, compare les topics avec ceux enregistrés et met les identifiants à jour avant la première scrutation. Un identifiant modifié est tracé dans le journal, et un topic qui a disparu de l'installation y est signalé pour pouvoir être supprimé.

La même passe lit sur l'appareil la **description** de chaque point de données configuré et adapte l'entité à ce que le régulateur annonce à cet instant : un point de données devenu inscriptible se transforme en `number` (ou en `select`), la plage, le pas, l'unité et les valeurs d'énumération suivent la description. Un champ que vous avez modifié à la main dans *Modifier un point de données* n'est jamais écrasé, et une valeur que l'appareil cesse de fournir est conservée telle quelle. Les changements sont tracés dans le journal au niveau info.

Deux frères portant le même libellé (l'OZW672 en compte quelques-uns, par exemple `Texte de défaut`) sont suffixés `#2`, `#3` … dans l'ordre du menu, ce qui rend les chemins générés uniques et reproductibles. La numérotation est calculée sur la liste complète des frères, afin qu'un parcours ciblé retrouve exactement les mêmes chemins qu'un parcours complet.

Le topic est mémorisé sous forme de **liste de segments** plutôt que de texte assemblé, car un libellé du régulateur peut lui-même contenir une barre oblique (`Heating/Cooling circuit 1`, `Jour/heure`, `URL / IP address`, …). Redécouper un chemin assemblé donnerait des topics erronés pour ces branches : la version texte n'est donc utilisée que pour l'affichage.

## Fonctionnalités

- **Configuration par l'interface** — tout se règle depuis Home Assistant (adresse, identifiants, HTTPS).
- **Choix de l'appareil de l'installation** — l'OZW672 annonce les régulateurs qui lui sont raccordés ; vous choisissez celui auquel l'entrée correspond.
- **Choix libre des points de données** — l'installation est parcourue **topic par topic** : cochez ce que vous voulez sur chaque écran, passez au topic suivant, revenez en arrière si besoin et terminez quand vous le souhaitez. Fonctionne à l'installation comme plus tard depuis les options.
- **Identité par topic** — les identifiants sont recalculés depuis les topics à chaque rechargement : ils survivent donc à une régénération des identifiants de l'OZW672.
- **Entités adaptées à chaque rechargement** — la description de chaque point de données configuré est relue sur l'appareil : le type d'entité, la plage, le pas, l'unité et les valeurs d'énumération suivent le régulateur.
- **Lecture des points de données en capteurs** — températures, pressions, modulation, énergie, heures de fonctionnement, états et messages.
- **Écriture des points de données en nombres** — les points de données numériques inscriptibles deviennent des entités `number` (unité, classe, plage et pas détectés sur l'appareil, et modifiables).
- **Énumérations** — un point de données d'énumération peut devenir une entité `select` pré-remplie avec les libellés du régulateur.
- **Écriture avec le type du régulateur** — chaque point de données est écrit avec le type qu'il annonce (`Numeric`, `Enumeration`, `RadioButton`, `TimeOfDay`), car le régulateur refuse tout autre type.
- **Type d'entité déduit de l'appareil** — la description de chaque point de données (`type`, `unit`, `Min`/`Max`/`Resolution`, valeurs d'énumération) décide s'il devient un capteur en lecture seule, un nombre avec la plage et le pas du régulateur, ou un select.
- **Ajout d'un point de données par son identifiant** — collez l'identifiant numérique d'un point de l'arborescence : l'intégration lit sa description sur l'appareil.
- **Service générique** — `siemens_ozw672.write_datapoint` écrit dans n'importe quel point de données.
- **Reconnexion automatique** — l'identifiant de session est renouvelé dès que l'OZW672 l'invalide.
- **Ré-authentification** — Home Assistant redemande les identifiants s'ils changent.

## Prérequis

- Un Siemens OZW672 (ou un OZW67x compatible) accessible sur votre réseau local, avec l'API du serveur web activée.
- Un compte utilisateur sur l'appareil. Créez si possible un **compte dédié en lecture/écriture**.
- Home Assistant 2024.6 ou plus récent.

## Installation

### HACS (recommandé)

[![Ouvrir votre instance Home Assistant et ajouter un dépôt au Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Didier57&repository=Siemens-OZW672.01&category=integration)

1. Ouvrez HACS → **Intégrations**.
2. Cliquez sur les trois points (en haut à droite) → **Dépôts personnalisés**.
3. Ajoutez `https://github.com/Didier57/Siemens-OZW672.01` avec la catégorie **Integration**.
4. Recherchez **Siemens OZW672** dans HACS et installez-le.
5. Redémarrez Home Assistant.

### Manuellement

Copiez le dossier `custom_components/siemens_ozw672` dans le répertoire `config/custom_components/` de Home Assistant, puis redémarrez Home Assistant.

## Configuration

1. Allez dans **Paramètres → Appareils et services → Ajouter une intégration**.
2. Recherchez **Siemens OZW672**.
3. Renseignez :

| Champ | Description |
| --- | --- |
| Hôte | Adresse IP ou nom d'hôte de l'OZW672. Une URL `http://…` collée fonctionne aussi. |
| Port | Facultatif. Laissez vide pour le port par défaut (80, ou 443 en HTTPS). |
| Utilisateur / Mot de passe | Identifiants du compte web de l'OZW672. |
| Utiliser HTTPS | À activer si le serveur web tourne en HTTPS. |
| Vérifier le certificat SSL | À laisser désactivé pour le certificat auto-signé habituel de l'OZW672. |

Les identifiants sont validés immédiatement par une véritable connexion à l'appareil.

4. **Sélectionnez l'appareil de l'installation.** L'OZW672 annonce les régulateurs qui lui sont raccordés (par exemple `1 RVS21.831F/127` pour le régulateur de pompe à chaleur à l'adresse de bus 1, plus la passerelle elle-même). L'intégration lit ensuite toute l'arborescence de cet appareil.
5. **Choisissez les points de données, topic après topic.** L'installation est parcourue un topic à la fois (par exemple `Configuration/Circuit de chauffage 1`) : chaque écran liste les points de données de ce topic, cochez ceux qui vous intéressent et continuez. Recochez ce que vous avez déjà : les points choisis précédemment restent cochés quand vous revenez, et **Topic précédent** permet de revoir. Vous pouvez terminer à tout moment ; tout ce qui est coché est conservé.

Le nom, le type d'entité, l'unité et la classe d'appareil devinée sont remplis automatiquement. L'entité `number` est créée pour les points de données numériques inscriptibles ; tout le reste devient un capteur. Les points numériques en lecture seule qui ont une unité reçoivent une classe d'appareil correspondante et une classe d'état `measurement`/`total_increasing`.

6. Facultatif : **Ajouter un point de données par son identifiant**. Collez l'identifiant numérique de n'importe quel point de l'arborescence — l'intégration lit sa description sur l'appareil et l'ajoute.

### Comment le type d'entité est décidé

L'intégration demande à l'OZW672 la **description** de chaque point de données (`datapoint_desc.json`) : elle fournit le type, l'unité, la plage autorisée, la résolution et, pour une énumération ou un bouton radio, la liste complète des valeurs acceptées par le régulateur avec ses propres libellés. À partir de là :

- un point de données **numérique inscriptible** devient un `number`, avec la plage et le pas annoncés par le régulateur (par exemple 44 – 65 °C, pas 1, pour une consigne ECS) ;
- une **énumération ou un bouton radio inscriptible** devient un `select` pré-rempli avec les libellés du régulateur ;
- tout le reste — mesures en lecture seule, états, messages de défaut, heures de fonctionnement, compteurs horaires — devient un **capteur**.

Rien n'est imposé : le type d'entité, l'unité, les classes, la plage et le pas restent modifiables dans *Configurer → Modifier un point de données*.

Le régulateur refuse une écriture dont le type n'est pas celui qu'il a annoncé (`datatype not supported`). L'intégration écrit donc chaque point de données avec **son propre type** : un bouton radio avec `RadioButton`, une énumération avec `Enumeration`, une valeur numérique avec `Numeric`. Le type annoncé par l'appareil est réappliqué automatiquement à chaque rechargement, y compris pour les points de données créés par une version antérieure de l'intégration.

## Entités

Les noms des entités suivent le nom du point de données ; lorsque deux points de données sélectionnés de la même installation portent le même nom, le topic parent est ajouté devant pour garder des noms lisibles. Les entités sont regroupées sous un seul appareil nommé d'après le régulateur sélectionné, avec le numéro de série et la version de firmware de la passerelle comme informations d'appareil.

| Type | Créé pour | Remarques |
| --- | --- | --- |
| `sensor` | chaque point de données sélectionné non inscriptible | les valeurs numériques avec unité sont converties en nombres, les énumérations et boutons radio deviennent des capteurs texte |
| `number` | les points de données numériques inscriptibles (`WriteAccess` vrai) | la plage et le pas viennent de la description de l'appareil et sont modifiables |
| `select` | les énumérations et boutons radio inscriptibles | les options viennent de la description de l'appareil |
| `binary_sensor` | toujours | *Connectivité*, activée quand la dernière scrutation a renvoyé au moins une valeur ; désactivée par défaut |

Les points de données configurés mais non câblés sur votre installation (`----`, `---`) sont signalés comme inconnus au lieu d'être affichés comme une valeur.

## Options

Allez dans **Paramètres → Appareils et services → Siemens OZW672 → Configurer** :

- **Réglages de scrutation** — modifie l'intervalle de scrutation (10 – 3600 s).
- **Ajouter des points de données** — les topics de l'installation sont parcourus les uns après les autres. Cochez les points de données à ajouter sur chaque écran : ils sont conservés au fur et à mesure, **Topic précédent** permet de revoir, et **Enregistrer** mémorise tout ce qui a été coché. Relancer l'opération plus tard permet d'ajouter ou de retirer des points de données des topics visités ; les points déjà configurés conservent leurs réglages.
- **Ajouter un datapoint par son id** — collez l'identifiant numérique de n'importe quel point de données de l'arborescence. Sa description est lue sur l'appareil et détermine le type d'entité créé ; si l'identifiant appartient à l'arborescence, son topic est également mémorisé pour être recalculé aux rechargements suivants.
- **Supprimer des points de données** — cochez les points de données à retirer de l'entrée.
- **Modifier un point de données** — ajuste le nom, le type d'entité (sensor/number/select), le type de valeur (`Numeric`/`Enumeration`), les options d'énumération, l'unité, la classe d'appareil, la classe d'état et le min/max/pas d'un nombre.
- **Enregistrer la sélection dans un fichier** — la sélection est affichée au format JSON, avec l'identifiant et le nom de chaque point de données ; copiez-la et conservez-la dans un fichier de votre choix.
- **Restaurer une sélection depuis un fichier** — collez un fichier enregistré précédemment pour remplacer la sélection d'un seul coup ; chaque point de données est redécrit par le régulateur.

Chaque modification des options recharge l'entrée, ce qui recalcule les identifiants à partir des topics.

### Sauvegarder et restaurer votre sélection

Resélectionner les points de données après une installation complète de Home Assistant est fastidieux, c'est pourquoi la sélection peut être exportée :

1. **Configurer → Enregistrer la sélection dans un fichier** : la sélection s'affiche sous forme de document JSON indenté contenant l'identifiant et le nom de chaque point de données. Copiez tout le texte et enregistrez-le, par exemple, sous `siemens_ozw672_datapoints.json`.
2. Sur une installation neuve, ajoutez à nouveau l'intégration (adresse et identifiants), puis **Configurer → Restaurer une sélection depuis un fichier** et collez le contenu. La sélection est remplacée par celle du fichier et prend effet immédiatement.

Les informations de connexion ne font volontairement **pas** partie du fichier — aucun mot de passe n'est jamais écrit en clair. Seuls les identifiants et les noms sont enregistrés : chaque point de données est redécrit par l'OZW672 à la restauration, donc son type, son unité, sa plage et ses valeurs d'énumération suivent ce que le régulateur annonce à ce moment-là, et il devient un capteur ou une entité modifiable en conséquence. Les identifiants sont également recalculés depuis les topics au rechargement de l'entrée, si bien qu'un fichier enregistré sur un OZW672 peut être restauré sur un autre câblé de la même façon. Si un identifiant ou un topic n'existe plus sur la nouvelle installation, il est signalé dans le journal et les autres points de données continuent de fonctionner.

## Services

### `siemens_ozw672.write_datapoint`

| Champ | Obligatoire | Description |
| --- | --- | --- |
| `datapoint_id` | oui | Identifiant du point de données dans l'arborescence de l'OZW672. |
| `value` | oui | Valeur à écrire. |
| `value_type` | non | `Numeric` (par défaut), `Enumeration`, `RadioButton` ou `TimeOfDay`. |
| `entry_id` | non | Entrée de configuration cible, utile seulement avec plusieurs appareils OZW672. |

```yaml
action: siemens_ozw672.write_datapoint
data:
  datapoint_id: 14408
  value: 52
```

## Migration depuis `rest` / `rest_command`

Les entités remplacent l'ancienne approche YAML : au lieu d'un `input_number` + `automation` + `rest_command`, écrivez directement la valeur sur l'entité `number`.

```yaml
action: number.set_value
target:
  entity_id: number.siemens_ozw672_consigne_nominale_de_temperature_ecs
data:
  value: 52
```

## Dépannage

| Symptôme | Solution |
| --- | --- |
| `invalid_auth` | Vérifiez l'utilisateur et le mot de passe ; notez que l'OZW672 bloque les comptes après plusieurs échecs. |
| `cannot_connect` | Vérifiez l'adresse IP, que le serveur web est activé, et le port (80/443). |
| `datatype not supported` en écrivant un `select` | Le type mémorisé ne correspond pas à celui annoncé par l'appareil. Ouvrez **Configurer → Modifier un point de données** et choisissez le type du régulateur (`RadioButton` pour un bouton radio, `Enumeration` pour une énumération) ; un rechargement corrige le type automatiquement. |
| Une entité reste `unknown` | Le point de données est configuré mais non câblé sur l'installation (`----`), ou il a été retiré de l'arborescence. Consultez le journal, puis supprimez-le ou modifiez-le dans les options. |
| Toutes les entités restent `unknown` | Consultez le journal : le topic n'a peut-être plus pu être résolu. Resélectionnez les points de données dans **Configurer → Ajouter des points de données**. |
| L'installation prend quelques secondes | L'intégration lit l'arborescence de l'installation, une requête par nœud de topic (environ 120 pour l'installation de référence). Cela n'arrive qu'à l'installation et au rechargement. |
| Les valeurs ne changent jamais | Augmentez l'intervalle de scrutation ou vérifiez la charge du serveur web de l'OZW672 ; l'appareil n'accepte qu'un nombre limité de sessions simultanées. |

Activez la journalisation de débogage pour inspecter le trafic de l'API :

```yaml
logger:
  logs:
    custom_components.siemens_ozw672: debug
```

## Avertissement

Non affilié à Siemens et non approuvé par Siemens. Le pilotage d'une installation de chauffage relève de votre responsabilité — à utiliser à vos propres risques.

## Licence

[MIT](LICENSE)
