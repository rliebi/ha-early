"""Services for the EARLY integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.util import dt as dt_util

from .api import (
    EarlyApiClientAuthenticationError,
    EarlyApiClientConflictError,
    EarlyApiClientError,
)
from .const import (
    ATTR_ACTIVITY_ID,
    ATTR_ACTIVITY_NAME,
    ATTR_CONFIG_ENTRY_ID,
    ATTR_NOTE,
    ATTR_STARTED_AT,
    ATTR_STOPPED_AT,
    DOMAIN,
    SERVICE_CANCEL_TRACKING,
    SERVICE_START_TRACKING,
    SERVICE_STOP_TRACKING,
)

if TYPE_CHECKING:
    from .data import EarlyConfigEntry

START_TRACKING_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Exclusive(ATTR_ACTIVITY_ID, "activity"): cv.string,
        vol.Exclusive(ATTR_ACTIVITY_NAME, "activity"): cv.string,
        vol.Optional(ATTR_STARTED_AT): cv.datetime,
        vol.Optional(ATTR_NOTE): cv.string,
    }
)

STOP_TRACKING_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Optional(ATTR_STOPPED_AT): cv.datetime,
    }
)

CANCEL_TRACKING_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
    }
)


def _get_entry(hass: HomeAssistant, call: ServiceCall) -> EarlyConfigEntry:
    """Resolve which EARLY config entry a service call targets."""
    entries: list[EarlyConfigEntry] = list(
        hass.config_entries.async_loaded_entries(DOMAIN)
    )
    entry_id = call.data.get(ATTR_CONFIG_ENTRY_ID)
    if entry_id is not None:
        for entry in entries:
            if entry.entry_id == entry_id:
                return entry
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="entry_not_found",
            translation_placeholders={"config_entry_id": entry_id},
        )
    if not entries:
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="no_entries"
        )
    if len(entries) > 1:
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="multiple_entries"
        )
    return entries[0]


def _resolve_activity_id(entry: EarlyConfigEntry, call: ServiceCall) -> str:
    """Resolve the activity id from an explicit id or a (case-insensitive) name."""
    if (activity_id := call.data.get(ATTR_ACTIVITY_ID)) is not None:
        return activity_id

    name = call.data.get(ATTR_ACTIVITY_NAME)
    if name is None:
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="activity_required"
        )

    activities = (entry.runtime_data.coordinator.data or {}).get("activities", [])
    for activity in activities:
        if str(activity.get("name", "")).casefold() == name.casefold():
            return str(activity["id"])

    raise ServiceValidationError(
        translation_domain=DOMAIN,
        translation_key="activity_not_found",
        translation_placeholders={"activity_name": name},
    )


def async_setup_services(hass: HomeAssistant) -> None:
    """Register the EARLY services (idempotent)."""
    if hass.services.has_service(DOMAIN, SERVICE_START_TRACKING):
        return

    async def async_start_tracking(call: ServiceCall) -> ServiceResponse:
        """Start tracking an activity."""
        entry = _get_entry(hass, call)
        activity_id = _resolve_activity_id(entry, call)
        started_at = call.data.get(ATTR_STARTED_AT)
        if started_at is not None:
            started_at = dt_util.as_utc(started_at)
        try:
            result = await entry.runtime_data.client.async_start_tracking(
                activity_id=activity_id,
                started_at=started_at,
                note=call.data.get(ATTR_NOTE),
            )
        except EarlyApiClientAuthenticationError as exception:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="auth_error"
            ) from exception
        except EarlyApiClientConflictError as exception:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="already_tracking"
            ) from exception
        except EarlyApiClientError as exception:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="api_error",
                translation_placeholders={"error": str(exception)},
            ) from exception
        await entry.runtime_data.coordinator.async_request_refresh()
        return _as_response(result)

    async def async_stop_tracking(call: ServiceCall) -> ServiceResponse:
        """Stop the currently running tracking."""
        entry = _get_entry(hass, call)
        client = entry.runtime_data.client
        if not await _guard(client.async_get_current_tracking):
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="nothing_tracking"
            )
        stopped_at = call.data.get(ATTR_STOPPED_AT)
        if stopped_at is not None:
            stopped_at = dt_util.as_utc(stopped_at)
        result = await _guard(lambda: client.async_stop_tracking(stopped_at=stopped_at))
        await entry.runtime_data.coordinator.async_request_refresh()
        return _as_response(result)

    async def async_cancel_tracking(call: ServiceCall) -> ServiceResponse:
        """Cancel the current tracking without creating a time entry."""
        entry = _get_entry(hass, call)
        client = entry.runtime_data.client
        if not await _guard(client.async_get_current_tracking):
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="nothing_tracking"
            )
        result = await _guard(client.async_cancel_tracking)
        await entry.runtime_data.coordinator.async_request_refresh()
        return _as_response(result)

    hass.services.async_register(
        DOMAIN,
        SERVICE_START_TRACKING,
        async_start_tracking,
        schema=START_TRACKING_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_STOP_TRACKING,
        async_stop_tracking,
        schema=STOP_TRACKING_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CANCEL_TRACKING,
        async_cancel_tracking,
        schema=CANCEL_TRACKING_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )


def async_unload_services(hass: HomeAssistant) -> None:
    """Remove the EARLY services."""
    hass.services.async_remove(DOMAIN, SERVICE_START_TRACKING)
    hass.services.async_remove(DOMAIN, SERVICE_STOP_TRACKING)
    hass.services.async_remove(DOMAIN, SERVICE_CANCEL_TRACKING)


async def _guard(factory: Any) -> Any:
    """Await an API coroutine, mapping client errors to HomeAssistantError."""
    try:
        return await factory()
    except EarlyApiClientAuthenticationError as exception:
        raise HomeAssistantError(
            translation_domain=DOMAIN, translation_key="auth_error"
        ) from exception
    except EarlyApiClientError as exception:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="api_error",
            translation_placeholders={"error": str(exception)},
        ) from exception


def _as_response(result: Any) -> ServiceResponse:
    """Normalize an API result into a service response dict."""
    if isinstance(result, dict):
        return result
    return {"result": result}
