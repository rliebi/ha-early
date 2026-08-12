"""The EARLY (Timeular) integration.

A HACS custom integration that bridges Home Assistant with the EARLY
(formerly Timeular) time-tracking API, exposing the current tracking state as
entities and offering start/stop tracking services.
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.const import Platform
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.loader import async_get_loaded_integration

from .api import EarlyApiClient
from .const import CONF_API_KEY, CONF_API_SECRET, DOMAIN, LOGGER
from .coordinator import EarlyDataUpdateCoordinator
from .data import EarlyData
from .services import async_setup_services, async_unload_services

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import EarlyConfigEntry

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.SELECT,
    Platform.SENSOR,
]

UPDATE_INTERVAL = timedelta(seconds=60)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EarlyConfigEntry,
) -> bool:
    """Set up EARLY from a config entry."""
    coordinator = EarlyDataUpdateCoordinator(
        hass=hass,
        logger=LOGGER,
        name=DOMAIN,
        update_interval=UPDATE_INTERVAL,
        config_entry=entry,
    )
    entry.runtime_data = EarlyData(
        client=EarlyApiClient(
            api_key=entry.data[CONF_API_KEY],
            api_secret=entry.data[CONF_API_SECRET],
            session=async_get_clientsession(hass),
        ),
        integration=async_get_loaded_integration(hass, entry.domain),
        coordinator=coordinator,
    )

    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Services are domain-global; register them the first time an entry is set up.
    async_setup_services(hass)

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: EarlyConfigEntry,
) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        # Drop the services once the last EARLY entry has been removed.
        loaded_entries = [
            loaded
            for loaded in hass.config_entries.async_loaded_entries(DOMAIN)
            if loaded.entry_id != entry.entry_id
        ]
        if not loaded_entries:
            async_unload_services(hass)
    return unloaded
