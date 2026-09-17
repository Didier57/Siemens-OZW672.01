# Siemens OZW672.01

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/Didier57/Siemens-OZW672.01)](https://github.com/Didier57/Siemens-OZW672.01/releases)
[![License](https://img.shields.io/github/license/Didier57/Siemens-OZW672.01)](LICENSE)
[![Validate](https://github.com/Didier57/Siemens-OZW672.01/actions/workflows/validate.yml/badge.svg)](https://github.com/Didier57/Siemens-OZW672.01/actions/workflows/validate.yml)
[![Hassfest](https://github.com/Didier57/Siemens-OZW672.01/actions/workflows/hassfest.yml/badge.svg)](https://github.com/Didier57/Siemens-OZW672.01/actions/workflows/hassfest.yml)

Custom Home Assistant integration for Siemens heating controllers exposed through the **OZW672** (and compatible OZW67x) web server.

The integration talks directly to the OZW672 JSON API over your local network: no cloud, no YAML, no `rest_command` boilerplate.

## Features

- **UI configuration** — set up everything from the Home Assistant interface (host, credentials, HTTPS).
- **Configurable polling** — the whole datapoint list is fetched with a single scan interval, default 60 s.
- **Read datapoints as sensors** — temperatures, burner modulation, boiler state, fault message…
- **Write setpoints** — comfort/reduced setpoint and heating curve as `number` entities.
- **Switch operating mode** — `Automatic` / `Reduced` / `Comfort` as a `select` entity.
- **Custom datapoints** — declare any extra datapoint of the OZW672 menutree from the options flow.
- **Generic service** — `siemens_ozw672.write_datapoint` writes to any datapoint id.
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

## Entities

### Sensors

| Datapoint id | Entity | Unit |
| --- | --- | --- |
| 3059 | Boiler state | — |
| 3062 | Burner state | — |
| 3068 | Boiler temperature | °C |
| 3074 | Return temperature | °C |
| 3078 | Burner modulation | % |
| 3198 | Fault message | — |
| 3209 | Room temperature | °C |
| 3212 | Outside temperature | °C |
| 3215 | DHW temperature | °C |

### Numbers (writable)

| Datapoint id | Entity | Range |
| --- | --- | --- |
| 2687 | Comfort setpoint | 5 – 35 °C |
| 2688 | Reduced setpoint | 5 – 35 °C |
| 2690 | Heating curve slope | 0.2 – 3.5 |

### Select

| Datapoint id | Entity | Options |
| --- | --- | --- |
| 2686 | Operating mode | Automatic (1), Reduced (2), Comfort (3) |

### Binary sensor

| Entity | Description |
| --- | --- |
| Connectivity | On when the last poll returned at least one value. Disabled by default. |

> Datapoint ids depend on the plant configuration of your OZW672. Ids that do not exist on your device simply stay `unknown`; use the options flow to add your own.

## Custom datapoints

Go to **Settings → Devices & services → Siemens OZW672 → Configure**:

- **Polling settings** — change the scan interval (10 – 3600 s).
- **Add a custom datapoint** — declare an extra datapoint with its id, name, entity type (sensor/number/select), unit, device class and enumeration options.
- **Remove a custom datapoint** — drop previously declared ones.

To find a datapoint id, log in to the OZW672 web interface and browse the tree view, or open:

```
http://<host>/main.app?SessionID=<your-session-id>&Section=webapi
```

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
  datapoint_id: 2687
  value: 21.5
```

## Migration from `rest` / `rest_command`

The entities replace the old YAML approach: instead of `input_number` + `automation` + `rest_command`, set a value directly on the number entity.

```yaml
action: number.set_value
target:
  entity_id: number.siemens_ozw672_comfort_setpoint
data:
  value: 21.5
```

```yaml
action: select.select_option
target:
  entity_id: select.siemens_ozw672_operating_mode
data:
  option: Comfort
```

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `invalid_auth` | Check the username/password; note that the OZW672 locks accounts after repeated failures. |
| `cannot_connect` | Verify the IP address, that the web server is enabled, and the port (80/443). |
| Entities stay `unknown` | The datapoint id likely does not exist on your device — remove it or declare the correct one. |
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

- **Installation** : HACS → Intégrations → dépôts personnalisés → `https://github.com/Didier57/Siemens-OZW672.01` (catégorie *Integration*), puis redémarrer Home Assistant.
- **Configuration** : Paramètres → Appareils et services → Ajouter une intégration → *Siemens OZW672*. Renseignez l'adresse IP, l'utilisateur et le mot de passe du serveur web OZW672.
- **Entités** : capteurs (températures chaudière/retour/ambiante/extérieure/ECS, modulation, états, défaut), nombres modifiables (consignes confort/réduit, courbe de chauffe) et une liste pour le mode de fonctionnement (Automatique / Réduit / Confort).
- **Points de données personnalisés** : via le bouton *Configurer* de l'intégration, vous pouvez déclarer n'importe quel identifiant de l'arborescence de l'OZW672.

Crédits à [vencakratky](https://github.com/vencakratky/API-OZW672--HomeAssistant) pour la documentation de l'API.
