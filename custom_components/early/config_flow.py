"""Config flow for the EARLY integration."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    EarlyApiClient,
    EarlyApiClientAuthenticationError,
    EarlyApiClientCommunicationError,
    EarlyApiClientError,
)
from .const import API_KEYS_URL, CONF_API_KEY, CONF_API_SECRET, DOMAIN, LOGGER


class EarlyFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the config flow for EARLY."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step where the user enters API credentials."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                await self._test_credentials(
                    api_key=user_input[CONF_API_KEY],
                    api_secret=user_input[CONF_API_SECRET],
                )
            except EarlyApiClientAuthenticationError as exception:
                LOGGER.warning("Authentication failed: %s", exception)
                errors["base"] = "auth"
            except EarlyApiClientCommunicationError as exception:
                LOGGER.error("Communication error: %s", exception)
                errors["base"] = "connection"
            except EarlyApiClientError as exception:
                LOGGER.exception("Unexpected error: %s", exception)
                errors["base"] = "unknown"
            else:
                # The API key is stable per account, so it makes a good unique id
                # and prevents the same account from being added twice.
                await self.async_set_unique_id(user_input[CONF_API_KEY])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="EARLY",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            description_placeholders={"api_keys_url": API_KEYS_URL},
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_KEY): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.TEXT,
                        ),
                    ),
                    vol.Required(CONF_API_SECRET): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD,
                        ),
                    ),
                },
            ),
            errors=errors,
        )

    async def _test_credentials(self, api_key: str, api_secret: str) -> None:
        """Validate the credentials against the API."""
        client = EarlyApiClient(
            api_key=api_key,
            api_secret=api_secret,
            session=async_get_clientsession(self.hass),
        )
        await client.async_validate()
