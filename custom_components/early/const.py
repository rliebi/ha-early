"""Constants for the EARLY (Timeular) integration."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "early"
ATTRIBUTION = "Data provided by the EARLY (Timeular) API"

# Config entry keys
CONF_API_KEY = "api_key"
CONF_API_SECRET = "api_secret"  # noqa: S105 - config key name, not a secret value

# Services
SERVICE_START_TRACKING = "start_tracking"
SERVICE_STOP_TRACKING = "stop_tracking"

ATTR_CONFIG_ENTRY_ID = "config_entry_id"
ATTR_ACTIVITY_ID = "activity_id"
ATTR_ACTIVITY_NAME = "activity_name"
ATTR_NOTE = "note"
ATTR_STARTED_AT = "started_at"
ATTR_STOPPED_AT = "stopped_at"
