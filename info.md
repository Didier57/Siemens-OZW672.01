# Siemens OZW672.01

Local Home Assistant integration for Siemens heating controllers exposed through the
**OZW672** web server.

## Highlights

- 100% UI configuration, no YAML.
- Sensors: boiler, return, room, outside and DHW temperatures, burner modulation,
  boiler/burner state and fault message.
- Writable setpoints: comfort, reduced and heating curve slope.
- Operating mode selector: Automatic / Reduced / Comfort.
- Declare any extra datapoint of the OZW672 menutree from the options flow.
- Generic `siemens_ozw672.write_datapoint` service.
- Automatic session renewal and re-authentication support.

## Quick start

1. Install through HACS (category *Integration*) and restart Home Assistant.
2. **Settings → Devices & services → Add integration → Siemens OZW672**.
3. Enter the IP address and the credentials of the OZW672 web account.

See the [README](https://github.com/Didier57/Siemens-OZW672.01#readme) for the full
documentation, the datapoint table and troubleshooting tips.

---

# Siemens OZW672.01 (Français)

Intégration locale Home Assistant pour les régulations de chauffage Siemens pilotées
par le serveur web **OZW672**.

- Configuration entièrement via l'interface, sans YAML.
- Capteurs de températures (chaudière, retour, ambiante, extérieure, ECS), modulation
  du brûleur, états et message de défaut.
- Consignes modifiables : confort, réduit et pente de courbe de chauffe.
- Sélecteur de mode : Automatique / Réduit / Confort.
- Ajout de n'importe quel point de données de l'arborescence via le flux d'options.
- Service générique `siemens_ozw672.write_datapoint`.
