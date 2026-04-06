from __future__ import annotations

import binascii
import hashlib
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import aiohttp

from .const import API_BASE_URL
from .parsers import SENSOR_PARSERS, parse_generic_raw

_LOGGER = logging.getLogger(__name__)


class HomgarApiError(Exception):
    """Base API error."""


class HomgarAuthError(HomgarApiError):
    """Authentication failure."""


@dataclass
class TokenCache:
    token: str | None = None
    token_expires: datetime | None = None
    refresh_token: str | None = None


class HomgarApiClient:
    logger = _LOGGER

    def __init__(
        self,
        session: aiohttp.ClientSession,
        email: str,
        password: str,
        area_code: str,
        app_code: str,
        home_id: str | None = None,
    ) -> None:
        self._session = session
        self._email = email
        self._password = password
        self._area_code = area_code
        self._app_code = app_code
        self._home_id = str(home_id) if home_id is not None else None
        self._token_cache = TokenCache()

    @staticmethod
    def make_timedelta(seconds: int) -> timedelta:
        return timedelta(seconds=seconds)

    def _clear_token(self) -> None:
        self._token_cache = TokenCache()

    def _base_headers(self) -> dict[str, str]:
        return {
            "lang": "en",
            "appCode": self._app_code,
        }

    def _auth_headers(self) -> dict[str, str]:
        if not self._token_cache.token:
            raise HomgarAuthError("No Homgar auth token available")

        headers = self._base_headers()
        headers.update(
            {
                "auth": self._token_cache.token,
                "version": "1.16.1065",
                "sceneType": "1",
            }
        )
        return headers

    async def async_fetch_all(self) -> dict[str, Any]:
        try:
            return await self._async_fetch_all_once()
        except HomgarAuthError as err:
            self.logger.info("Auth failed during update, retrying with fresh login: %s", err)
            self._clear_token()
            await self._async_login()
            return await self._async_fetch_all_once()

    async def _async_fetch_all_once(self) -> dict[str, Any]:
        await self._async_ensure_logged_in()
        homes = await self._async_get_homes()

        if self._home_id is not None:
            homes = [home for home in homes if str(home.get("hid")) == self._home_id]

        devices_by_home: dict[str, list[dict[str, Any]]] = {}
        for home in homes:
            hid = str(home["hid"])
            hubs = await self._async_get_devices_for_hid(hid)
            devices_by_home[hid] = hubs

            for hub in hubs:
                mid = str(hub.get("mid", ""))
                if not mid:
                    hub["status"] = {}
                    continue

                status = await self._async_get_device_status(mid)
                hub["status"] = status or {}

        return self._flatten(homes, devices_by_home)

    async def _async_request_json(
        self,
        method: str,
        url: str,
        *,
        with_auth: bool = True,
        json_body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        headers = self._auth_headers() if with_auth else self._base_headers()

        try:
            async with self._session.request(
                method,
                url,
                headers=headers,
                json=json_body,
                params=params,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status in (401, 403):
                    raise HomgarAuthError(
                        f"Homgar authentication failed with HTTP {resp.status}"
                    )

                resp.raise_for_status()
                payload = await resp.json(content_type=None)

        except aiohttp.ClientError as err:
            raise HomgarApiError(f"Network error talking to Homgar: {err}") from err
        except TimeoutError as err:
            raise HomgarApiError("Timed out talking to Homgar") from err
        except ValueError as err:
            raise HomgarApiError(f"Invalid JSON response from Homgar: {err}") from err

        if not isinstance(payload, dict):
            raise HomgarApiError("Unexpected response structure from Homgar")

        code = payload.get("code")
        if code != 0:
            msg = str(payload.get("msg", "Unknown Homgar API error"))
            msg_lower = msg.lower()

            if (
                code in {1001, 1002, 1003, 1004, 2001}
                or "auth" in msg_lower
                or "token" in msg_lower
                or "login" in msg_lower
            ):
                raise HomgarAuthError(msg)

            raise HomgarApiError(f"Homgar API error {code}: {msg}")

        return payload.get("data")

    async def _async_login(self) -> None:
        body = {
            "areaCode": self._area_code,
            "phoneOrEmail": self._email,
            "password": hashlib.md5(self._password.encode("utf-8")).hexdigest(),
            "deviceId": binascii.b2a_hex(os.urandom(16)).decode("utf-8"),
        }

        data = await self._async_request_json(
            "POST",
            f"{API_BASE_URL}/auth/basic/app/login",
            with_auth=False,
            json_body=body,
        )

        if not isinstance(data, dict) or not data.get("token"):
            raise HomgarAuthError("Homgar login did not return a token")

        expires_in = int(data.get("tokenExpired", 0) or 0)
        if expires_in <= 0:
            expires_in = 3600

        self._token_cache = TokenCache(
            token=data.get("token"),
            token_expires=datetime.now(timezone.utc) + timedelta(seconds=expires_in),
            refresh_token=data.get("refreshToken"),
        )

    async def _async_ensure_logged_in(self) -> None:
        expiry = self._token_cache.token_expires
        now = datetime.now(timezone.utc)

        if self._token_cache.token and expiry and expiry - now > timedelta(minutes=5):
            return

        await self._async_login()

    async def _async_get_homes(self) -> list[dict[str, Any]]:
        data = await self._async_request_json(
            "GET",
            f"{API_BASE_URL}/app/member/appHome/list",
        )
        return data if isinstance(data, list) else []

    async def _async_get_devices_for_hid(self, hid: str) -> list[dict[str, Any]]:
        data = await self._async_request_json(
            "GET",
            f"{API_BASE_URL}/app/device/getDeviceByHid",
            params={"hid": hid},
        )
        return data if isinstance(data, list) else []

    async def _async_get_device_status(self, mid: str) -> dict[str, Any]:
        data = await self._async_request_json(
            "GET",
            f"{API_BASE_URL}/app/device/getDeviceStatus",
            params={"mid": mid},
        )
        return data if isinstance(data, dict) else {}

    def _flatten(
        self,
        homes: list[dict[str, Any]],
        devices_by_home: dict[str, list[dict[str, Any]]],
    ) -> dict[str, Any]:
        flattened: dict[str, Any] = {
            "homes": {},
            "entities": {},
        }

        for home in homes:
            home_id = str(home.get("hid"))
            if not home_id:
                continue

            flattened["homes"][home_id] = {
                "id": home_id,
                "name": home.get("homeName") or f"Home {home_id}",
            }

            for hub in devices_by_home.get(home_id, []):
                sub_status = hub.get("status", {}).get("subDeviceStatus", [])
                status_items = {
                    str(item.get("id")): item
                    for item in sub_status
                    if isinstance(item, dict) and item.get("id") is not None
                }

                for subdevice in hub.get("subDevices", []):
                    if not isinstance(subdevice, dict):
                        continue

                    model = subdevice.get("model")
                    parser = SENSOR_PARSERS.get(model)
                    if parser is None:
                        self.logger.info(
                            "Using generic RAW fallback parser for unsupported subdevice %s model %s",
                            subdevice.get("did"),
                            model,
                        )
                        parser = parse_generic_raw

                    try:
                        parsed = parser(subdevice=subdevice, status_items=status_items)
                        flattened["entities"].update(
                            parsed.build_entities(home=home, hub=hub)
                        )
                    except Exception as err:
                        self.logger.warning(
                            "Failed parsing subdevice %s model %s: %s",
                            subdevice.get("did"),
                            model,
                            err,
                        )

        return flattened