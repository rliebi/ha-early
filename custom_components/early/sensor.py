"""Sensor platform for the EARLY integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.util import dt as dt_util

from .entity import EarlyEntity

if TYPE_CHECKING:
    from collections.abc import Callable

    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import EarlyDataUpdateCoordinator
    from .data import EarlyConfigEntry


def _current_activity_name(data: dict[str, Any]) -> str | None:
    """Return the name of the currently tracked activity, if any."""
    current = data.get("current_tracking")
    if not current:
        return None
    return current.get("activity", {}).get("name")


def _started_at(data: dict[str, Any]) -> datetime | None:
    """Return the (UTC-aware) start time of the current tracking, if any."""
    current = data.get("current_tracking")
    if not current or not (raw := current.get("startedAt")):
        return None
    parsed = dt_util.parse_datetime(raw)
    if parsed is None:
        return None
    # The API returns UTC without an offset; make the value timezone-aware.
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed


@dataclass(frozen=True, kw_only=True)
class EarlySensorEntityDescription(SensorEntityDescription):
    """Describe an EARLY sensor."""

    value_fn: Callable[[dict[str, Any]], Any]


ENTITY_DESCRIPTIONS: tuple[EarlySensorEntityDescription, ...] = (
    EarlySensorEntityDescription(
        key="current_activity",
        translation_key="current_activity",
        icon="mdi:timer-outline",
        value_fn=_current_activity_name,
    ),
    EarlySensorEntityDescription(
        key="tracking_started_at",
        translation_key="tracking_started_at",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=_started_at,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: EarlyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the EARLY sensors."""
    async_add_entities(
        EarlySensor(
            coordinator=entry.runtime_data.coordinator,
            entity_description=entity_description,
        )
        for entity_description in ENTITY_DESCRIPTIONS
    )


class EarlySensor(EarlyEntity, SensorEntity):
    """A sensor reflecting the EARLY tracking state."""

    entity_description: EarlySensorEntityDescription

    def __init__(
        self,
        coordinator: EarlyDataUpdateCoordinator,
        entity_description: EarlySensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{entity_description.key}"
        )

    @property
    def native_value(self) -> Any:
        """Return the current value of the sensor."""
        return self.entity_description.value_fn(self.coordinator.data or {})
