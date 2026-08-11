"""Base entity for the EARLY integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN
from .coordinator import EarlyDataUpdateCoordinator


class EarlyEntity(CoordinatorEntity[EarlyDataUpdateCoordinator]):
    """Base class for EARLY entities."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(self, coordinator: EarlyDataUpdateCoordinator) -> None:
        """Initialize the entity and attach it to the account device."""
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="EARLY (Timeular)",
        )
