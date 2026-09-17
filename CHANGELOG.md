# Changelog

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.0] - 2026-09-17

### Added

- **Save the selection to a file**: a new option shows the whole selection of
  datapoints as an indented JSON document that can be copied and kept on disk,
  for example to survive a clean installation of Home Assistant.
- **Restore a selection from a file**: the matching option replaces the
  selection of the entry with the content of a file saved earlier, in one go.
  The connection details are deliberately kept out of the file, so no password
  is ever written in plain text, and the identifiers are written down again
  from the topics when the entry reloads, so a selection saved on one
  installation can be restored on another one wired the same way.
- The file is validated before it is applied: a document that is not JSON, not
  a Siemens OZW672 backup, empty or written by a newer version is refused with
  a message explaining which of those it is.

## [1.2.3] - 2026-09-17

### Fixed

- **Reloading the integration now updates the kind of every entity.** A
  datapoint stores what the OZW672 announced when it was added, so a field the
  user edited can be told apart from a field the device changed. The comparison
  assumed that snapshot always existed, but datapoints created before it was
  introduced have none: every stored field then looked like a user edit and was
  skipped, so the entity kind, the unit and the range read when the datapoint
  was first added were frozen for good. A reload could therefore never turn a
  sensor into a number or a select, and the range of a number never followed
  the controller. A field absent from the snapshot is now adopted from the
  device, a field the snapshot knows and the user changed is still preserved,
  and the entry is only written back when something actually changed.

## [1.2.2] - 2026-09-17

### Fixed

- **Datapoints under a topic whose title contains a slash were reported as
  removed** (`Datapoint 'Configuration/Heating/Cooling circuit 1/…' was not
  found in the OZW672 menu tree anymore`) although they were perfectly valid.
  The controller allows a title to contain a slash - the reference plant has
  seven of them, for example the `Heating/Cooling circuit 1` menu - so the
  stored path, which was the chain of titles joined with `/`, could not be
  split back into its segments: the resolution looked for a four level path
  where the device has three, found nothing, and kept the (correct) saved
  identifier while logging a false alarm. Datapoints are now identified by the
  **list of segments** (`segments`), which is stored next to the joined path;
  the joined path is kept for display only and is never split again. Paths
  stored by an older version keep working through the previous lookup.
- **The entity names of duplicate titles were computed from the joined path**,
  so two datapoints whose titles contained a slash could be disambiguated with
  the wrong parent. The comparison now uses the segments.

### Changed

- The sibling suffix numbering (`#2`, `#3` ...) that makes repeated titles
  unique is computed on the whole sibling list at once instead of incrementally
  while walking, so a filtered walk (used to re-resolve the configured
  datapoints) generates exactly the same titles as a complete walk.

## [1.2.1] - 2026-09-17

### Fixed

- **The integration could not load any more** (`cannot import name
  'describe_datapoint' from ...coordinator`). The function was renamed when the
  datapoint metadata was shared between the setup flow and the coordinator, but
  only its call sites were updated: the definition kept the private name, so
  importing the config flow failed and the config entry could not be set up.
- A datapoint whose identifier moved in the menu tree raised
  `FrozenInstanceError` on the next reload: `Datapoint` is a frozen dataclass, so
  the new identifier is now applied by rebuilding the datapoint instead of
  assigning to its field.

### Added

- A **Checks** workflow runs on every push: `compileall`, `ruff check`,
  `ruff format --check` and a check that every import between the modules of the
  integration resolves. Hassfest and the HACS validation do not load the Python
  modules, which is why the import error could be released.

## [1.2.0] - 2026-09-17

### Added

- **The datapoints of the entry are re-checked against the device on every
  reload.** Restarting or reloading the integration now reads
  `api/menutree/datapoint_desc.json` for each configured datapoint and adapts
  the entity to what the device currently announces, exactly as it is done when
  a datapoint is added:
  - a datapoint that becomes writable is exposed as a `number` (or a `select`
    when it carries an enumeration) without being removed and added again;
  - the range and the step of a `number` follow the description of the
    controller;
  - the enumeration values and the labels are refreshed, and a datapoint that
    previously reported no option list is upgraded to a `select` as soon as the
    controller reports one;
  - the unit and the device class follow the description.
- A configuration edited by hand is **never overwritten**. The integration keeps
  a snapshot of what the device announced when the datapoint was configured, so
  a field whose value differs from that snapshot was edited by the user and is
  left alone; a value the device stops reporting (an option list, a range) is
  kept as well, because replacing it with nothing would make the entity
  unusable. Changes brought by the device are logged at info level.

### Changed

- The datapoint metadata is now derived from the device description in one
  place, shared by the setup flow and the coordinator, so a datapoint is
  exposed the same way whether it was just added or read back on a reload.

## [1.1.0] - 2026-09-17

### Added

- **Add a datapoint by its id** (setup flow and options). Paste the numeric
  identifier of any datapoint of the OZW672 menutree and the integration adds
  it; when the identifier belongs to the menu tree of the plant, its topic is
  stored as well, so it is re-resolved automatically on the next reloads.
- **The device description decides the kind of entity that is created.** The
  metadata of a datapoint is now read from `api/menutree/datapoint_desc.json`,
  which reports the type, the unit, the allowed range, the resolution (number
  of decimals) and, for an enumeration or a radio button, the complete list of
  the values the controller accepts with its own labels. As a result a writable
  numeric datapoint becomes a `number` with the range and the step announced by
  the controller (instead of 0 – 100 / 0.5), and a writable enumeration or
  radio button becomes a `select` pre-filled with the controller labels.
  Read-only datapoints - states, fault messages, operating hours - stay
  sensors, and everything remains editable in *Edit a datapoint*.
- Datapoints that are read-only for the plant but carry an enumeration are
  stored with the option list of the device, so they can be switched to a
  `select` in the options without typing the list by hand.

### Changed

- The enumeration options of a newly added datapoint are filled with the
  controller labels, and the datapoint name is the one reported by the device
  description when it is available.

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

[1.3.0]: https://github.com/Didier57/Siemens-OZW672.01/releases/tag/v1.3.0
[1.2.3]: https://github.com/Didier57/Siemens-OZW672.01/releases/tag/v1.2.3
[1.2.2]: https://github.com/Didier57/Siemens-OZW672.01/releases/tag/v1.2.2
[1.2.1]: https://github.com/Didier57/Siemens-OZW672.01/releases/tag/v1.2.1
[1.2.0]: https://github.com/Didier57/Siemens-OZW672.01/releases/tag/v1.2.0
[1.1.0]: https://github.com/Didier57/Siemens-OZW672.01/releases/tag/v1.1.0
[1.0.0]: https://github.com/Didier57/Siemens-OZW672.01/releases/tag/v1.0.0
