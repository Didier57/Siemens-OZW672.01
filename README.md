# Siemens OZW672.01

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/Didier57/Siemens-OZW672.01)](https://github.com/Didier57/Siemens-OZW672.01/releases)
[![License](https://img.shields.io/github/license/Didier57/Siemens-OZW672.01)](LICENSE)
[![Validate](https://github.com/Didier57/Siemens-OZW672.01/actions/workflows/validate.yml/badge.svg)](https://github.com/Didier57/Siemens-OZW672.01/actions/workflows/validate.yml)
[![Hassfest](https://github.com/Didier57/Siemens-OZW672.01/actions/workflows/hassfest.yml/badge.svg)](https://github.com/Didier57/Siemens-OZW672.01/actions/workflows/hassfest.yml)

Custom Home Assistant integration for Siemens heating controllers exposed through the **OZW672** (and compatible OZW67x) web server.

The integration talks directly to the OZW672 JSON API over your local network: no cloud, no YAML, no `rest_command` boilerplate.

## Why datapoints are identified by topic

The OZW672 does **not** ship a fixed datapoint numbering. It builds its menu tree from the controllers actually wired to it, and the identifiers of that tree are generated for each plant:

- two different installations almost never share the same ids;
- on the same installation the ids can change after the OZW672 server parameters are refreshed or the device list is rebuilt.

The integration therefore identifies every datapoint by its **topic path** in the menu tree, for example:

```
Diagnostic consommateurs/Pompe à chaleur/Modulation compresseur
Configuration/Circuit de chauffage 1/Consigne confort
Etat/Etat du circuit de chauffage 1
```

The numeric id is only a cached pointer kept in the config entry. On every setup — that is at each Home Assistant start, restart, reload and options change — the integration walks the OZW672 menu tree again, compares the topics with the stored ones and updates the ids before the first poll. Renamed/renumbered ids are logged, and a topic that disappeared from the plant is reported in the log so it can be removed.

The same pass reads the **description** of every configured datapoint on the device and adapts the entity to what the controller announces now: a datapoint that became writable turns into a `number` (or a `select`), the range, the step, the unit and the enumeration values follow the description. A field you edited by hand in *Edit a datapoint* is never overwritten, and a value the device stops reporting is kept as it is. The changes are logged at info level.

Two siblings sharing the same title (the OZW672 has a few, for example `Texte de défaut`) are suffixed `#2`, `#3` … in menu order, which makes the generated paths unique and reproducible. The numbering is computed on the whole sibling list, so a targeted walk finds exactly the same paths as a full one.

The topic is stored as a **list of segments** rather than a joined string, because a title of the controller may itself contain a slash (`Heating/Cooling circuit 1`, `Jour/heure`, `URL / IP address`, …). Splitting a joined path back into segments would produce wrong topics for those branches, so the joined text is only used for display.

## Features

- **UI configuration** — set up everything from the Home Assistant interface (host, credentials, HTTPS).
- **Plant device selection** — the OZW672 lists the controllers it is wired to; pick the one the entry is for.
- **Choose your own datapoints** — the plant is browsed **topic after topic**: tick what you want on each screen, move to the next topic, come back when needed, and finish whenever you like. Works during setup and later from the options.
- **Topic based identity** — ids are re-resolved against the topics at every reload, so they survive a regeneration of the OZW672 identifiers.
- **Entities adapted on every reload** — the description of each configured datapoint is read again on the device, so the entity kind, the range, the step, the unit and the enumeration values follow the controller.
- **Read datapoints as sensors** — temperatures, pressures, modulation, energy, operating hours, states and messages.
- **Write datapoints as numbers** — writable numeric datapoints become `number` entities (unit, device class, range and step are detected from the device and can be adjusted).
- **Enumerations** — turn an enumeration datapoint into a `select` entity pre-filled with the labels of the controller.
- **Entity kind detected from the device** — the description of each datapoint (`type`, `unit`, `Min`/`Max`/`Resolution`, enumeration values) decides whether it becomes a read-only sensor, a number with the range and step of the controller, or a select.
- **Add a datapoint by its id** — paste a numeric identifier of the menutree and the integration reads its description on the device.
- **Generic service** — `siemens_ozw672.write_datapoint` writes to any datapoint.
- **Automatic re-login** — the session id is refreshed whenever the OZW672 invalidates it.
- **Re-authentication** — Home Assistant asks for new credentials if they change.

## Requirements

- A Siemens OZW672 (or compatible OZW67x) reachable on your local network, with the web server API enabled.
- A user account on the device. Create a **dedicated read/write user** if possible.
- Home Assistant 2024.6 or newer.

## Installation

### HACS (recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Didier57&repository=Siemens-OZW672.01&category=integration)

1. Open HACS → **Integrations**.
2. Click the three dots (top right) → **Custom repositories**.
3. Add `https://github.com/Didier57/Siemens-OZW672.01` with the category **Integration**.
4. Search for **Siemens OZW672** in HACS and install it.
5. Restart Home Assistant.

### Manual

Copy the `custom_components/siemens_ozw672` folder into your Home Assistant `config/custom_components/` directory and restart Home Assistant.

## Configuration

1. Go to **Settings → Devices & services → Add integration**.
2. Search for **Siemens OZW672**.
3. Fill in:

| Field | Description |
| --- | --- |
| Host | IP address or hostname of the OZW672. A pasted `http://…` URL also works. |
| Port | Optional. Leave empty for the default port (80, or 443 with HTTPS). |
| Username / Password | Credentials of the OZW672 web account. |
| Use HTTPS | Enable if the web server runs on HTTPS. |
| Verify the SSL certificate | Leave disabled for the usual self-signed OZW672 certificate. |

The credentials are validated immediately by performing a real login against the device.

4. **Select the plant device.** The OZW672 reports the controllers it is wired to (for example `1 RVS21.831F/127` for the heat pump controller on bus address 1, plus the gateway itself). The integration then reads the whole menu tree of that device.
5. **Pick the datapoints, topic after topic.** The plant is browsed one topic at a time (for example `Configuration/Circuit de chauffage 1`): each screen lists the datapoints of that topic, tick the ones you want and continue. Tick again what you already have — the datapoints you picked earlier stay ticked when you come back — and use **Previous topic** to review. You can finish at any moment; everything already ticked is kept.

The name, the entity type, the unit and the guessed device class are filled in automatically. The number entity is created for writable numeric datapoints; everything else becomes a sensor. Read-only numeric datapoints with a unit get a matching device class and a `measurement`/`total_increasing` state class.

6. Optional: **Add a datapoint by its id**. Paste the numeric identifier of any datapoint of the menutree — the integration reads its description from the device and adds it.

### How the entity type is decided

The integration asks the OZW672 for the **description** of each datapoint (`datapoint_desc.json`): it reports the type, the unit, the allowed range, the resolution and, for an enumeration or a radio button, the complete list of the values the controller accepts with the labels it uses. From that:

- a **writable numeric** datapoint becomes a `number`, with the range and the step announced by the controller (for example 44 – 65 °C, step 1, for a DHW setpoint);
- a **writable enumeration or radio button** becomes a `select` pre-filled with the controller labels;
- everything else — read-only measurements, states, fault messages, operating hours, time-of-day counters — becomes a **sensor**.

Nothing is imposed: the entity type, the unit, the classes, the range and the step stay editable in *Configure → Edit a datapoint*.

## Entities

Entity names follow the datapoint name; when two selected datapoints of the same plant share a name, the parent topic is prepended to keep the names readable. Entities are grouped under a single device named after the selected controller, with the gateway serial number and firmware version as device information.

| Kind | Created for | Notes |
| --- | --- | --- |
| `sensor` | every selected datapoint that is not writable | numeric values with a unit are converted to numbers, enumerations/radio buttons become text sensors |
| `number` | writable numeric datapoints (`WriteAccess` true) | range and step come from the device description, and are editable |
| `select` | writable enumerations and radio buttons | options come from the device description |
| `binary_sensor` | always | *Connectivity*, on when the last poll returned at least one value; disabled by default |

Datapoints that are configured but not wired on your plant (`----`, `---`) are reported as unknown instead of being shown as a value.

## Options

Go to **Settings → Devices & services → Siemens OZW672 → Configure**:

- **Polling settings** — change the scan interval (10 – 3600 s).
- **Add datapoints** — the topics of the plant are browsed one after the other. Tick the datapoints to add on each screen: they are kept as you go, **Previous topic** lets you review, and **Save** stores everything picked so far. Re-running it later lets you add or remove datapoints of the topics you visit; the datapoints you already configured keep their settings.
- **Add a datapoint by its id** — paste the numeric identifier of any datapoint of the menutree. Its description is read on the device and decides the kind of entity created; if the identifier belongs to the menu tree, its topic is stored too so it is re-resolved on the next reloads.
- **Remove datapoints** — tick the datapoints to drop from the entry.
- **Edit a datapoint** — adjust the name, the entity type (sensor/number/select), the value type (`Numeric`/`Enumeration`), the enumeration options, the unit, the device class, the state class and the min/max/step of a number.
- **Save the selection to a file** — the selection is shown as JSON, with the identifier and the name of every datapoint; copy it and keep it in a file of your choice.
- **Restore a selection from a file** — paste a file saved earlier to replace the selection in one go; every datapoint is described again by the controller.

Every options change reloads the entry, which re-resolves the ids from the topics.

### Saving and restoring your selection

Selecting the datapoints again after a clean installation of Home Assistant is tedious, so the selection can be exported:

1. **Configure → Save the selection to a file**: the selection is displayed as an indented JSON document holding the identifier and the name of each datapoint. Copy the whole text and save it as, for example, `siemens_ozw672_datapoints.json`.
2. On a fresh install, add the integration again (host and credentials), then **Configure → Restore a selection from a file** and paste the content. The selection is replaced by the one of the file and takes effect on the spot.

Connection details are deliberately **not** part of the file — no password is ever written in plain text. Only the identifiers and the names are stored: every datapoint is described again by the OZW672 when the file is restored, so its type, unit, range and enumeration values follow what the controller announces right now, and a datapoint becomes a sensor or an entity that can be changed accordingly. The identifiers are also resolved again from the topics when the entry reloads, so a file saved on one OZW672 can be restored on another one wired the same way. If an identifier or a topic no longer exists on the new plant, it is reported in the log and the other datapoints keep working.

## Services

### `siemens_ozw672.write_datapoint`

| Field | Required | Description |
| --- | --- | --- |
| `datapoint_id` | yes | Datapoint id in the OZW672 menutree. |
| `value` | yes | Value to write. |
| `value_type` | no | `Numeric` (default) or `Enumeration`. |
| `entry_id` | no | Target config entry, only needed with several OZW672 devices. |

```yaml
action: siemens_ozw672.write_datapoint
data:
  datapoint_id: 14408
  value: 52
```

## Migration from `rest` / `rest_command`

The entities replace the old YAML approach: instead of `input_number` + `automation` + `rest_command`, set a value directly on the number entity.

```yaml
action: number.set_value
target:
  entity_id: number.siemens_ozw672_consigne_nominale_de_temperature_ecs
data:
  value: 52
```

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `invalid_auth` | Check the username/password; note that the OZW672 locks accounts after repeated failures. |
| `cannot_connect` | Verify the IP address, that the web server is enabled, and the port (80/443). |
| One entity stays `unknown` | The datapoint is configured but not wired on the plant (`----`), or it was removed from the menu tree. Check the log, then remove or edit it in the options. |
| Every entity stays `unknown` | Check the log: the topic could not be resolved any more. Re-select the datapoints in **Configure → Add datapoints**. |
| Setting up takes a few seconds | The integration reads the menu tree of the plant, one request per topic node (about 120 for the reference installation). This happens only during setup and at reload. |
| Values never change | Increase the scan interval or check the OZW672 web UI load; the device has limited concurrent sessions. |

Enable debug logging to inspect the API traffic:

```yaml
logger:
  logs:
    custom_components.siemens_ozw672: debug
```

## Credits

Inspired by [vencakratky/API-OZW672--HomeAssistant](https://github.com/vencakratky/API-OZW672--HomeAssistant), which documents the OZW672 web API and the original YAML/`rest_command` approach.

## Disclaimer

Not affiliated with or endorsed by Siemens. Heating equipment control is your responsibility — use at your own risk.

## License

[MIT](LICENSE)

---

## Version française

Intégration Home Assistant pour les régulations de chauffage Siemens exposées par le serveur web **OZW672** (et OZW67x compatibles).

### Pourquoi les points de données sont identifiés par leur topic

L'OZW672 ne possède pas de numérotation fixe : il construit son arborescence à partir des appareils réellement raccordés, et **les identifiants sont générés pour chaque installation**. Ils peuvent même changer sur une même installation lorsque la liste des appareils du serveur est réactualisée. L'intégration identifie donc chaque point de données par son **chemin de topic** (par exemple `Diagnostic consommateurs/Pompe à chaleur/Modulation compresseur`) et ne conserve l'identifiant numérique que comme pointeur. À chaque démarrage, rechargement ou modification des options, l'intégration relit l'arborescence, compare les topics et met les identifiants à jour. Les identifiants modifiés sont tracés dans le journal, et un topic disparu y est signalé. Le chemin est mémorisé sous forme de **liste de segments**, car un libellé du régulateur peut lui-même contenir une barre oblique (`Heating/Cooling circuit 1`, `Jour/heure`, …) : la version texte n'est utilisée que pour l'affichage.

- **Installation** : HACS → Intégrations → dépôts personnalisés → `https://github.com/Didier57/Siemens-OZW672.01` (catégorie *Integration*), puis redémarrer Home Assistant.
- **Configuration** : Paramètres → Appareils et services → Ajouter une intégration → *Siemens OZW672*. Renseignez l'adresse IP, l'utilisateur et le mot de passe, puis choisissez **l'appareil de l'installation** parmi ceux que l'OZW672 annonce (par exemple `1 RVS21.831F/127`).
- **Choix des points de données** : l'installation est parcourue **topic par topic**. Chaque écran liste les points de données d'un topic : cochez ceux qui vous intéressent, passez au topic suivant avec **Topic suivant**, revenez avec **Topic précédent**, et terminez quand vous voulez — tout ce qui est coché est conservé. Les points inscriptibles deviennent des entités `number`, les énumérations peuvent devenir des `select` en renseignant leur liste d'options, tout le reste devient des capteurs.
- **Type d'entité déduit de la description de l'appareil** : pour chaque point de données, l'intégration lit sa description sur l'OZW672 (`datapoint_desc.json`), qui fournit le type, l'unité, la plage de valeurs autorisée, la résolution et, pour une énumération ou un bouton radio, la liste complète des valeurs avec les libellés du régulateur. Un point de données numérique inscriptible devient un `number` avec la plage et le pas annoncés par l'appareil, une énumération inscriptible devient un `select` pré-rempli, et tout le reste (mesures, états, messages, compteurs d'heures) reste un capteur en lecture seule. Tout reste modifiable dans *Modifier un point de données*.
- **Ajout manuel par identifiant** : *Ajouter un datapoint par son id* permet de saisir directement l'identifiant numérique d'un point de données de l'arborescence ; sa description est lue sur l'appareil et détermine le type d'entité créé.
- **Options** : *Réglages de scrutation* (intervalle de 10 à 3600 s), *Ajouter des points de données*, *Ajouter un datapoint par son id*, *Supprimer des points de données*, *Modifier un point de données* (nom, type, unité, classes, min/max/pas, options d'énumération), *Enregistrer la sélection dans un fichier* et *Restaurer une sélection depuis un fichier*.
- **Sauvegarde de la sélection** : *Enregistrer la sélection dans un fichier* affiche toute votre sélection au format JSON (l'identifiant et le nom de chaque point de données) : copiez le texte et conservez-le dans un fichier. Après une réinstallation complète, recréez l'intégration (adresse et identifiants) puis *Restaurer une sélection depuis un fichier* en collant le contenu : vos points de données sont repris tels quels, sans avoir à les resélectionner. Les informations de connexion ne figurent **pas** dans le fichier (aucun mot de passe n'est écrit en clair). Seuls les identifiants et les noms y sont enregistrés : chaque point de données est redécrit par l'OZW672 à la restauration, son type, son unité, sa plage et ses valeurs d'énumération suivent donc ce que le régulateur annonce à ce moment-là, et il devient un capteur ou une entité modifiable en conséquence. Les identifiants sont également recalculés depuis les topics au rechargement, si bien qu'une sauvegarde faite sur un OZW672 peut être restaurée sur un autre câblé de la même façon ; un identifiant ou un topic disparu est signalé dans le journal sans casser le reste.
Crédits à [vencakratky](https://github.com/vencakratky/API-OZW672--HomeAssistant) pour la documentation de l'API.
