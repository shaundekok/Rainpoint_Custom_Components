from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig, SelectOptionDict

from .api import HomgarApiClient, HomgarApiError, HomgarAuthError
from .const import (
    APP_CODE_HOMGAR,
    APP_CODE_RAINPOINT,
    CONF_APP_CODE,
    CONF_AREA_CODE,
    CONF_HOME_ID,
    CONF_HOME_NAME,
    CONF_POLL_INTERVAL,
    DEFAULT_APP_CODE,
    DEFAULT_AREA_CODE,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
    MIN_POLL_INTERVAL,
)


class HomgarRainpointConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._user_input: dict[str, Any] = {}
        self._homes: list[dict[str, Any]] = []

    async def async_step_user(self, user_input=None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            email = user_input[CONF_EMAIL].strip().lower()
            password = user_input[CONF_PASSWORD]
            area_code = str(user_input[CONF_AREA_CODE]).strip()
            app_code = str(user_input[CONF_APP_CODE]).strip()

            client = HomgarApiClient(
                session=async_get_clientsession(self.hass),
                email=email,
                password=password,
                area_code=area_code,
                app_code=app_code,
            )

            try:
                await client._async_ensure_logged_in()
                homes = await client._async_get_homes()
            except HomgarAuthError:
                errors["base"] = "invalid_auth"
            except HomgarApiError:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"
            else:
                if not homes:
                    errors["base"] = "no_homes"
                else:
                    self._user_input = {
                        CONF_EMAIL: email,
                        CONF_PASSWORD: password,
                        CONF_AREA_CODE: area_code,
                        CONF_APP_CODE: app_code,
                    }
                    self._homes = homes
                    return await self.async_step_select_home()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL): str,
                    vol.Required(CONF_PASSWORD): str,
                    vol.Required(CONF_AREA_CODE, default=DEFAULT_AREA_CODE): str,
                    vol.Required(CONF_APP_CODE, default=DEFAULT_APP_CODE): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                SelectOptionDict(value=APP_CODE_HOMGAR, label="Homgar"),
                                SelectOptionDict(value=APP_CODE_RAINPOINT, label="RainPoint"),
                            ],
                            mode="dropdown",
                        )
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_select_home(self, user_input=None) -> FlowResult:
        errors: dict[str, str] = {}

        if not self._homes or not self._user_input:
            return await self.async_step_user()

        if user_input is not None:
            selected_home_id = str(user_input[CONF_HOME_ID])

            selected_home = next(
                (home for home in self._homes if str(home.get("hid")) == selected_home_id),
                None,
            )
            if selected_home is None:
                errors["base"] = "invalid_home"
            else:
                app_code = self._user_input[CONF_APP_CODE]
                email = self._user_input[CONF_EMAIL]
                home_name = selected_home.get("homeName") or f"Home {selected_home_id}"

                unique_id = f"{email}_{app_code}_{selected_home_id}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"{home_name} ({'Homgar' if app_code == APP_CODE_HOMGAR else 'RainPoint'})",
                    data={
                        **self._user_input,
                        CONF_HOME_ID: selected_home_id,
                        CONF_HOME_NAME: home_name,
                    },
                    options={
                        CONF_POLL_INTERVAL: DEFAULT_POLL_INTERVAL,
                    },
                )

        home_options = [
            SelectOptionDict(
                value=str(home.get("hid")),
                label=home.get("homeName") or f"Home {home.get('hid')}",
            )
            for home in self._homes
            if home.get("hid") is not None
        ]

        return self.async_show_form(
            step_id="select_home",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOME_ID): SelectSelector(
                        SelectSelectorConfig(
                            options=home_options,
                            mode="dropdown",
                        )
                    ),
                }
            ),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return HomgarRainpointOptionsFlow(config_entry)


class HomgarRainpointOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_POLL_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL
                        ),
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_POLL_INTERVAL),
                    ),
                }
            ),
        )