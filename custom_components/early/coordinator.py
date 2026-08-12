"""DataUpdateCoordinator for the EARLY integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import EarlyApiClientAuthenticationError, EarlyApiClientError

if TYPE_CHECKING:
    from .data import EarlyConfigEntry


class EarlyDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Poll the EARLY API for the current tracking and activities."""

    config_entry: EarlyConfigEntry

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch the current tracking state and the list of activities."""
        client = self.config_entry.runtime_data.client
        try:
            activities_payload = await client.async_get_activities()
            current_tracking = await client.async_get_current_tracking()
        except EarlyApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except EarlyApiClientError as exception:
            raise UpdateFailed(exception) from exception

        active = activities_payload.get("activities", [])
        # Build an id -> name map across every activity list so a running
        # tracking can be named even if its activity is inactive or archived.
        activity_names: dict[str, str] = {}
        for key in ("activities", "inactiveActivities", "archivedActivities"):
            for activity in activities_payload.get(key, []):
                if (activity_id := activity.get("id")) is not None:
                    activity_names[str(activity_id)] = activity.get("name")

        return {
            "activities": active,
            "activity_names": activity_names,
            "current_tracking": _normalize_tracking(current_tracking, activity_names),
        }


def _normalize_tracking(
    tracking: dict[str, Any] | None,
    activity_names: dict[str, str],
) -> dict[str, Any] | None:
    """Reduce a raw tracking object to a stable, shape-independent structure."""
    if not tracking:
        return None
    activity = tracking.get("activity") or {}
    raw_id = tracking.get("activityId") or activity.get("id")
    activity_id = str(raw_id) if raw_id is not None else None
    name = activity.get("name") or (
        activity_names.get(activity_id) if activity_id else None
    )
    return {
        "activity_id": activity_id,
        "activity_name": name,
        "started_at": tracking.get("startedAt"),
        "note": (tracking.get("note") or {}).get("text"),
    }
