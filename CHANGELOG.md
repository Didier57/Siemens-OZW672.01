# Changelog

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.2] - 2026-09-17

### Added

- New options step **Enable / disable built-in datapoints**. The built-in
  catalog matches the reference installation only; on a different plant the
  datapoints that do not exist have to be disabled and replaced by custom ones.
- A datapoint of the built-in catalog that is disabled can be re-declared as a
  custom datapoint.

### Fixed

- Device side errors were swallowed. A failed read answers with
  `{"Data": {}, "Result": {"Success": "false", "Error": {...}}}`, which was
  turned into a `None` value, so every entity silently showed `unknown`. The
  device message (for example `read failed (Nr 6)`) is now raised and logged.
- A datapoint that cannot be read is logged once at warning level instead of
  only at debug level, and a completely unreadable catalog is reported as an
  error without preventing the config entry from loading, so the options flow
  stays reachable.

## [1.0.1] - 2026-09-17

### Fixed

- Connection to the device always failed with "Failed to connect" when a port
  was entered. Home Assistant number selectors always return a float, so the
  port `80` became `80.0` and produced the invalid URL `http://host:80.0`.
  The port is now coerced to an integer.
- The real cause of a connection, authentication or API failure is now written
  to the Home Assistant log instead of being silently mapped to a form error.

## [1.0.0] - 2026-09-17

### Added

- Initial release of the Siemens OZW672 custom integration.
- Async API client for the OZW672 web API (`login`, `read_datapoint`, `write_datapoint`, `logout`).
- `DataUpdateCoordinator` based polling with automatic session renewal.
- UI configuration flow (host, port, credentials, HTTPS, SSL verification).
- Re-authentication flow when credentials become invalid.
- Options flow: scan interval, add and remove custom datapoints.
- Sensor entities: boiler state, burner state, boiler/return/room/outside/DHW
  temperatures, burner modulation and fault message.
- Number entities: comfort setpoint, reduced setpoint, heating curve slope.
- Select entity: operating mode (Automatic / Reduced / Comfort).
- Connectivity binary sensor.
- `siemens_ozw672.write_datapoint` service for arbitrary datapoint writes.
- HACS and hassfest validation workflows.
- English and French translations.

[1.0.2]: https://github.com/Didier57/Siemens-OZW672.01/releases/tag/v1.0.2
[1.0.1]: https://github.com/Didier57/Siemens-OZW672.01/releases/tag/v1.0.1
[1.0.0]: https://github.com/Didier57/Siemens-OZW672.01/releases/tag/v1.0.0
