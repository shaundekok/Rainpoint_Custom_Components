from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import HomgarApiClient, HomgarApiError, HomgarAuthError
from .const import (
    CONF_APP_CODE,
    CONF_AREA_CODE,
    CONF_HOME_ID,
    CONF_POLL_INTERVAL,
    DEFAULT_APP_CODE,
    DEFAULT_AREA_CODE,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
    PLATFORMS,
)

type HomgarConfigEntry = ConfigEntry[DataUpdateCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: HomgarConfigEntry) -> bool:
    session = async_get_clientsession(hass)
    client = HomgarApiClient(
        session=session,
        email=entry.data[CONF_EMAIL],
        password=entry.data[CONF_PASSWORD],
        area_code=entry.data.get(CONF_AREA_CODE, DEFAULT_AREA_CODE),
        app_code=entry.data.get(CONF_APP_CODE, DEFAULT_APP_CODE),
        home_id=entry.data.get(CONF_HOME_ID),
    )

    coordinator = HomgarDataUpdateCoordinator(
        hass=hass,
        client=client,
        poll_interval=entry.options.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL),
    )

    try:
        await coordinator.async_config_entry_first_refresh()
    except HomgarAuthError as err:
        raise ConfigEntryAuthFailed(str(err)) from err
    except HomgarApiError as err:
        raise UpdateFailed(str(err)) from err

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: HomgarConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: HomgarConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


class HomgarDataUpdateCoordinator(DataUpdateCoordinator[dict]):
    def __init__(self, hass: HomeAssistant, client: HomgarApiClient, poll_interval: int) -> None:
        super().__init__(
            hass,
            logger=client.logger,
            name=DOMAIN,
            update_interval=client.make_timedelta(poll_interval),
        )
        self.client = client

    async def _async_update_data(self) -> dict:
        try:
            return await self.client.async_fetch_all()
        except HomgarAuthError:
            raise
        except HomgarApiError as err:
            raise UpdateFailed(str(err)) from err