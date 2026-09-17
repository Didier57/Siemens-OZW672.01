# Siemens OZW672.01

Local Home Assistant integration for Siemens heating controllers exposed through the
**OZW672** web server.

## Highlights

- 100% UI configuration, no YAML.
- Device selection: pick the controller the OZW672 is wired to.
- Sensors: outside, room, flow, heat pump and DHW temperatures, hydraulic pressure,
  compressor modulation, thermal energy, operating hours, states and fault message.
- Writable setpoints: DHW normal/reduced and cooling comfort setpoint.
- Declare any extra datapoint of the OZW672 menutree from the options flow.
- Generic `siemens_ozw672.write_datapoint` service.
- Automatic session renewal and re-authentication support.

## Quick start

1. Install through HACS (category *Integration*) and restart Home Assistant.
2. **Settings → Devices & services → Add integration → Siemens OZW672**.
3. Enter the IP address and the credentials of the OZW672 web account, then select
   the plant device.

See the [README](https://github.com/Didier57/Siemens-OZW672.01#readme) for the full
documentation, the datapoint table and troubleshooting tips.

---

# Siemens OZW672.01 (Français)

Intégration locale Home Assistant pour les régulations de chauffage Siemens pilotées
par le serveur web **OZW672**.

- Configuration entièrement via l'interface, sans YAML.
- Choix de l'appareil de l'installation parmi ceux annoncés par l'OZW672.
- Capteurs de températures (extérieure, ambiante, départ, PAC, ECS), pression
  hydraulique, modulation compresseur, énergie, heures de fonctionnement, états et
  message de défaut.
- Consignes modifiables : ECS nominale/réduite, confort rafraîchissement.
- Ajout de n'importe quel point de données de l'arborescence via le flux d'options.
- Service générique `siemens_ozw672.write_datapoint`.
