# Siemens OZW672.01

Local Home Assistant integration for Siemens heating controllers exposed through the
**OZW672** web server.

## Highlights

- 100% UI configuration, no YAML.
- Plant device selection: pick the controller the OZW672 is wired to.
- **Datapoints are identified by their topic**, because the OZW672 generates the
  numeric ids for each installation; the ids are checked and updated on every reload.
- Browse the menu tree **classified by topic** and pick the datapoints you want,
  during setup and from the options.
- Read-only datapoints become sensors (temperatures, pressure, modulation, energy,
  operating hours, states, messages), writable numeric datapoints become numbers,
  enumerations can become selects.
- Generic `siemens_ozw672.write_datapoint` service.
- Automatic session renewal and re-authentication support.

## Quick start

1. Install through HACS (category *Integration*) and restart Home Assistant.
2. **Settings → Devices & services → Add integration → Siemens OZW672**.
3. Enter the IP address and the credentials of the OZW672 web account, select the
   plant device, then pick your datapoints by topic.

See the [README](https://github.com/Didier57/Siemens-OZW672.01#readme) for the full
documentation and troubleshooting tips.

---

# Siemens OZW672.01 (Français)

Intégration locale Home Assistant pour les régulations de chauffage Siemens pilotées
par le serveur web **OZW672**.

- Configuration entièrement via l'interface, sans YAML.
- Choix de l'appareil de l'installation parmi ceux annoncés par l'OZW672.
- **Les points de données sont identifiés par leur topic** : l'OZW672 génère les
  identifiants pour chaque installation et les vérifie à chaque rechargement.
- Parcours de l'arborescence **classée par topic** pour choisir librement ses points
  de données, à l'installation comme depuis les options.
- Capteurs en lecture, entités `number` pour les consignes inscriptibles, `select`
  pour les énumérations.
- Service générique `siemens_ozw672.write_datapoint`.
