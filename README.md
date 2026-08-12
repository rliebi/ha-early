<img src="brands/icon.svg" alt="EARLY icon" width="96" align="right" />

# EARLY (Timeular) — Home Assistant integration

[![hacs][hacs-badge]][hacs] [![Validate][validate-badge]][validate-workflow]

A [HACS][hacs] custom integration that connects Home Assistant to the
[EARLY][early] time-tracking API (formerly **Timeular**,
`api.timeular.com/api/v2`). It exposes the current tracking state as entities
and adds **start / stop tracking** services you can call from automations,
scripts, dashboards or voice assistants.

Built on top of the [`integration_blueprint`][blueprint] by @ludeeus.

## Features

- 🔐 UI config flow — sign in with your EARLY **API Key** and **API Secret**.
- ▶️ `early.start_tracking` — start tracking an activity (by id or name).
- ⏹️ `early.stop_tracking` — stop the running tracking (or a specific activity).
- 🔽 `select` **Activity** — a dropdown populated live from your EARLY
  activities. Picking one starts tracking it (stopping any running tracking
  first); picking **Not tracking** stops the current tracking.
- 📟 Entities that reflect the live tracking state:
  - `binary_sensor` **Tracking active** — on while a tracking runs, with the
    running activity, start time and note as attributes.
  - `sensor` **Current activity** — the name of the activity being tracked.
  - `sensor` **Tracking started at** — a timestamp of when tracking started.
- 🔄 **Automatic token refresh** — the bearer token (a JWT) is renewed in the
  background before it expires, so the integration keeps working without
  re-authentication.

## Installation

### HACS (recommended)

1. In HACS, open the three-dot menu → **Custom repositories**.
2. Add `https://github.com/rliebi/ha-early` with category **Integration**.
3. Search for **EARLY (Timeular)** in HACS and install it.
4. Restart Home Assistant.

### Manual

Copy `custom_components/early` into your Home Assistant `config/custom_components`
directory and restart Home Assistant.

## Configuration

1. Generate an **API Key** and **API Secret** in your EARLY account
   (Settings → Account → API — or via the developer API-access endpoint).
2. In Home Assistant go to **Settings → Devices & Services → Add Integration**
   and search for **EARLY (Timeular)**.
3. Paste the API Key and API Secret.

The API Key is used as the unique id, so the same account cannot be added twice.

## Services

### `early.start_tracking`

Start tracking time for an activity.

| Field             | Required | Description                                                        |
| ----------------- | -------- | ------------------------------------------------------------------ |
| `activity_id`     | one of\* | The EARLY activity id.                                             |
| `activity_name`   | one of\* | The activity name (case-insensitive).                             |
| `started_at`      | no       | When tracking should start. Defaults to now.                       |
| `note`            | no       | An optional note attached to the tracking.                         |
| `config_entry_id` | no       | Which account to use (only needed with multiple EARLY accounts).   |

\* Provide either `activity_id` **or** `activity_name`.

```yaml
action: early.start_tracking
data:
  activity_name: "Deep Work"
  note: "Quarterly report"
```

### `early.stop_tracking`

Stop the currently running tracking. If you omit `activity_id`/`activity_name`,
whatever is currently running is stopped.

| Field             | Required | Description                                                      |
| ----------------- | -------- | ---------------------------------------------------------------- |
| `activity_id`     | no       | Stop this activity (defaults to the running one).                |
| `activity_name`   | no       | Stop the activity with this name.                                |
| `stopped_at`      | no       | When tracking should stop. Defaults to now.                      |
| `config_entry_id` | no       | Which account to use (only needed with multiple EARLY accounts). |

```yaml
action: early.stop_tracking
```

Both services return the API response (`supports_response: optional`), so you
can capture the created/updated time entry in a script variable.

## Example automation

Start "Focus" tracking when a helper toggle turns on, and stop it when off:

```yaml
automation:
  - alias: "EARLY: start focus"
    triggers:
      - trigger: state
        entity_id: input_boolean.focus_mode
        to: "on"
    actions:
      - action: early.start_tracking
        data:
          activity_name: "Focus"
  - alias: "EARLY: stop focus"
    triggers:
      - trigger: state
        entity_id: input_boolean.focus_mode
        to: "off"
    actions:
      - action: early.stop_tracking
```

## Development

```bash
scripts/setup     # install dev + lint requirements
scripts/develop   # run a local Home Assistant with this integration loaded
scripts/lint      # ruff format + check --fix
```

## Notes

- The EARLY rebrand kept the public API on the `api.timeular.com/api/v2` host.
- The integration polls the current tracking every 60 seconds; the entities also
  refresh immediately after a start/stop service call.
- This is an unofficial, community project and is not affiliated with EARLY.

## License

[MIT](LICENSE)

[hacs]: https://hacs.xyz
[hacs-badge]: https://img.shields.io/badge/HACS-Custom-41BDF5.svg
[early]: https://early.app
[blueprint]: https://github.com/ludeeus/integration_blueprint
[validate-badge]: https://github.com/rliebi/ha-early/actions/workflows/validate.yml/badge.svg
[validate-workflow]: https://github.com/rliebi/ha-early/actions/workflows/validate.yml
