"""Select platform for the EARLY integration.

Exposes a per-account dropdown of the live EARLY activities. Picking an activity
starts tracking it (stopping any running tracking first); picking "Not tracking"
stops the current tracking.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.select import SelectEntity
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN
from .entity import EarlyEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import EarlyDataUpdateCoordinator
    from .data import EarlyConfigEntry

# Sentinel option used to represent "no tracking running". It is translated via
# the select entity's state translations; activity names are shown as-is.
OPTION_NOT_TRACKING = "not_tracking"


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: EarlyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the EARLY activity selector."""
    async_add_entities([EarlyActivitySelect(entry.runtime_data.coordinator)])


class EarlyActivitySelect(EarlyEntity, SelectEntity):
    """A dropdown of EARLY activities that also controls tracking."""

    _attr_translation_key = "activity"
    _attr_icon = "mdi:timer-cog-outline"

    def __init__(self, coordinator: EarlyDataUpdateCoordinator) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_activity"

    def _activities(self) -> list[dict]:
        """Return the list of activities from the coordinator data."""
        return (self.coordinator.data or {}).get("activities", [])

    def _current_activity_name(self) -> str | None:
        """Return the name of the currently tracked activity, if any."""
        current = (self.coordinator.data or {}).get("current_tracking")
        if not current:
            return None
        return current.get("activity", {}).get("name")

    @property
    def options(self) -> list[str]:
        """Return the selectable options (the sentinel plus activity names)."""
        names = sorted(
            str(activity["name"])
            for activity in self._activities()
            if activity.get("name")
        )
        current = self._current_activity_name()
        # Make sure the running activity is always selectable, even if it was
        # archived or is otherwise missing from the activity list.
        if current and current not in names:
            names.append(current)
        return [OPTION_NOT_TRACKING, *names]

    @property
    def current_option(self) -> str:
        """Return the currently selected option."""
        return self._current_activity_name() or OPTION_NOT_TRACKING

    async def async_select_option(self, option: str) -> None:
        """Start tracking the chosen activity, or stop when the sentinel is picked."""
        if option == self.current_option:
            return
        client = self.coordinator.config_entry.runtime_data.client
        current = await client.async_get_current_tracking()
        current_id = str(current["activity"]["id"]) if current else None

        if option == OPTION_NOT_TRACKING:
            if current_id is not None:
                await client.async_stop_tracking(current_id)
            await self.coordinator.async_request_refresh()
            return

        target_id = self._resolve_activity_id(option)
        if target_id == current_id:
            # Already tracking this activity — nothing to do.
            return
        if current_id is not None:
            # EARLY only allows one active tracking, so stop the old one first.
            await client.async_stop_tracking(current_id)
        await client.async_start_tracking(target_id)
        await self.coordinator.async_request_refresh()

    def _resolve_activity_id(self, name: str) -> str:
        """Return the activity id for a given activity name."""
        for activity in self._activities():
            if str(activity.get("name", "")) == name:
                return str(activity["id"])
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="activity_not_found",
            translation_placeholders={"activity_name": name},
        )
