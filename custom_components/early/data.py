"""Custom types for the EARLY integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.loader import Integration

    from .api import EarlyApiClient
    from .coordinator import EarlyDataUpdateCoordinator

type EarlyConfigEntry = ConfigEntry[EarlyData]


@dataclass
class EarlyData:
    """Runtime data for the EARLY integration."""

    client: EarlyApiClient
    coordinator: EarlyDataUpdateCoordinator
    integration: Integration
