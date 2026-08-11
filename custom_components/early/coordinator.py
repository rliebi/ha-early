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
            activities = await client.async_get_activities()
            current_tracking = await client.async_get_current_tracking()
        except EarlyApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except EarlyApiClientError as exception:
            raise UpdateFailed(exception) from exception
        return {
            "activities": activities,
            "current_tracking": current_tracking,
        }
