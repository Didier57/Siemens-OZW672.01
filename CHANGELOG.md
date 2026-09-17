# Changelog

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-09-17

First release: the integration is stable and covers the whole workflow, from
setup to writing values back to the controller.

### Added

- **Datapoints identified by their topic.** The OZW672 does not ship a fixed
  datapoint numbering: it generates the identifiers for the plant it is wired
  to, and they can change when the server parameters are refreshed. Every
  datapoint is therefore stored with its topic path (for example
  `Diagnostic consommateurs/Pompe à chaleur/Modulation compresseur`) and the
  numeric identifier is only a cached pointer. The identifiers are re-resolved
  against the topics on every setup — Home Assistant start, restart, reload and
  options change — and a changed identifier is logged.
- **Guided datapoint selection by topic**, both during setup and from the
  options: the plant is browsed topic after topic, with *Next topic*,
  *Previous topic* (your ticks are restored) and *Finish*. Already configured
  datapoints are pre-ticked. The entity type, unit, device class and state
  class are guessed from the device answer.
- Plant device selection: the OZW672 lists the controllers it is wired to.
- Entities: sensors for the read-only datapoints (temperatures, pressure,
  modulation, energy, operating hours, states, messages), `number` entities for
  writable numeric datapoints, `select` entities for enumerations with an
  option list, and a *Connectivity* binary sensor.
- Options: polling settings (10 – 3600 s, default 60 s), add datapoints, remove
  datapoints, and edit a datapoint (name, entity type, value type, enumeration
  options, unit, device class, state class, min/max/step).
- `siemens_ozw672.write_datapoint` service to write any datapoint.
- Automatic session renewal, re-authentication support, and English/French
  translations.
- HACS and hassfest validation workflows, plus a workflow that prunes the older
  GitHub Actions runs.

### Notes

- Datapoints that are not wired on the plant (`----`, `---`) are reported as
  unknown instead of being shown as a value.
- Siblings sharing a title (the controller has a few, for example
  `Texte de défaut`) are suffixed `#2`, `#3` … so the generated topic paths are
  unique and reproducible.

[1.0.0]: https://github.com/Didier57/Siemens-OZW672.01/releases/tag/v1.0.0
