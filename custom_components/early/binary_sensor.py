"""Binary sensor platform for the EARLY integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)

from .entity import EarlyEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import EarlyDataUpdateCoordinator
    from .data import EarlyConfigEntry

ENTITY_DESCRIPTIONS: tuple[BinarySensorEntityDescription, ...] = (
    BinarySensorEntityDescription(
        key="tracking_active",
        translation_key="tracking_active",
        device_class=BinarySensorDeviceClass.RUNNING,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: EarlyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the EARLY binary sensors."""
    async_add_entities(
        EarlyBinarySensor(
            coordinator=entry.runtime_data.coordinator,
            entity_description=entity_description,
        )
        for entity_description in ENTITY_DESCRIPTIONS
    )


class EarlyBinarySensor(EarlyEntity, BinarySensorEntity):
    """Binary sensor that is on while a tracking is running."""

    def __init__(
        self,
        coordinator: EarlyDataUpdateCoordinator,
        entity_description: BinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{entity_description.key}"
        )

    @property
    def is_on(self) -> bool:
        """Return true while a tracking is active."""
        return bool((self.coordinator.data or {}).get("current_tracking"))

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Expose details about the running tracking."""
        data = self.coordinator.data or {}
        current = data.get("current_tracking")
        if not current:
            return None
        activity_id = current.get("activityId")
        names = data.get("activity_names", {})
        return {
            "activity_id": activity_id,
            "activity_name": names.get(str(activity_id)) if activity_id else None,
            "started_at": current.get("startedAt"),
            "note": (current.get("note") or {}).get("text"),
        }
