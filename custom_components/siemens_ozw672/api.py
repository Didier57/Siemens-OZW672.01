"""Async client for the Siemens OZW672 (OZW web server) HTTP API.

The OZW672 exposes a small JSON API on top of its web interface:

* ``GET /api/auth/login.json?user=<user>&pwd=<password>``
  returns ``{"SessionId": <id>}``
* ``GET /api/menutree/read_datapoint.json?SessionId=<sid>&Id=<datapoint>``
  returns ``{"Data": {"Value": <value>}}``
* ``GET /api/menutree/write_datapoint.json?SessionId=<sid>&Id=<datapoint>``
  with the extra ``Type=<type>&Value=<value>`` parameters writes a datapoint.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import aiohttp

from .const import TYPE_NUMERIC

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = 15

_READ_DATAPOINT = "/api/menutree/read_datapoint.json"
_WRITE_DATAPOINT = "/api/menutree/write_datapoint.json"
_LOGIN = "/api/auth/login.json"
_LOGOUT = "/api/auth/logout.json"


class OZW672Error(Exception):
    """Base class for OZW672 errors."""


class OZW672ConnectionError(OZW672Error):
    """Raised when the OZW672 cannot be reached."""


class OZW672AuthError(OZW672Error):
    """Raised when authentication with the OZW672 fails."""


class OZW672ApiError(OZW672Error):
    """Raised when the OZW672 API returns an unexpected response."""


def _extract_error(payload: Any) -> str | None:
    """Return the device side error message of a response, if there is one.

    Failures are reported by the OZW as, for example::

        {"Data": {},
         "Result": {"Success": "false",
                    "Error": {"Txt": "read failed", "Nr": "6"}}}
    """
    if not isinstance(payload, dict):
        return None

    for value in (payload, payload.get("Data"), payload.get("Result")):
        if not isinstance(value, dict):
            continue

        error = value.get("Error", value.get("error"))
        if isinstance(error, dict):
            text = error.get("Txt", error.get("Text", error.get("txt")))
            number = error.get("Nr", error.get("nr"))
            if text:
                return f"{text} (Nr {number})" if number is not None else str(text)
            return json.dumps(error, sort_keys=True)
        if isinstance(error, str) and error:
            return error

        success = value.get("Success", value.get("success"))
        if success is not None and str(success).lower() in {"false", "0", "no"}:
            return "unknown device error"

    return None


class OZW672Client:
    """Thin async wrapper around the OZW672 web API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        username: str,
        password: str,
        *,
        port: int | None = None,
        use_https: bool = False,
        verify_ssl: bool = False,
    ) -> None:
        """Initialise the client."""
        self._session = session
        self._username = username
        self._password = password
        self._verify_ssl = verify_ssl
        self._session_id: str | None = None
        self._lock = asyncio.Lock()
        self._warned_payloads: set[int] = set()

        scheme = "https" if use_https else "http"
        authority = host
        if port:
            # ``port`` may be a float coming from a Home Assistant number
            # selector (``80.0``) and would otherwise produce an invalid URL.
            authority = f"{host}:{int(float(port))}"
        self.base_url = f"{scheme}://{authority}"

    @property
    def session_id(self) -> str | None:
        """Return the current session id, if any."""
        return self._session_id

    async def async_login(self) -> None:
        """Force a new login."""
        async with self._lock:
            await self._async_login()

    async def async_ensure_session(self) -> str:
        """Login if no session id is available yet."""
        async with self._lock:
            if self._session_id is None:
                await self._async_login()
            assert self._session_id is not None
            return self._session_id

    async def async_logout(self) -> None:
        """Log out and forget the current session id."""
        async with self._lock:
            if self._session_id is None:
                return
            try:
                await self._async_request(_LOGOUT, {"SessionId": self._session_id})
            except OZW672Error as err:
                _LOGGER.debug("Logout failed (ignored): %s", err)
            finally:
                self._session_id = None

    async def async_read_datapoint(self, datapoint_id: int) -> Any:
        """Read a single datapoint value."""
        session_id = await self.async_ensure_session()
        try:
            payload = await self._async_request(
                _READ_DATAPOINT, {"SessionId": session_id, "Id": int(datapoint_id)}
            )
        except OZW672AuthError:
            _LOGGER.debug("Session expired, re-authenticating")
            await self.async_login()
            session_id = self._session_id
            payload = await self._async_request(
                _READ_DATAPOINT, {"SessionId": session_id, "Id": int(datapoint_id)}
            )

        return self._extract_value(datapoint_id, payload)

    def _extract_value(self, datapoint_id: int, payload: Any) -> Any:
        """Pull the value out of a ``read_datapoint`` response.

        The documented shape is ``{"Data": {"Value": <value>}}`` but the
        firmware is not consistent about the capitalisation and about where the
        value lives, so several shapes are accepted. An unrecognised payload is
        reported once per datapoint instead of silently yielding ``None``.
        """
        _LOGGER.debug("Datapoint %s raw response: %r", datapoint_id, payload)

        error = _extract_error(payload)
        if error is not None:
            raise OZW672ApiError(f"Read of datapoint {datapoint_id} failed: {error}")

        if isinstance(payload, dict):
            for key in ("Value", "value"):
                if key in payload:
                    return payload[key]

            data = payload.get("Data", payload.get("data"))
            if isinstance(data, dict):
                for key in ("Value", "value"):
                    if key in data:
                        return data[key]
            elif isinstance(data, (int, float, str, bool)):
                return data
        elif isinstance(payload, (int, float, str, bool)):
            return payload

        if datapoint_id not in self._warned_payloads:
            self._warned_payloads.add(datapoint_id)
            _LOGGER.warning(
                "Unexpected response for datapoint %s: %r. Please report this "
                "payload at https://github.com/Didier57/Siemens-OZW672.01/issues",
                datapoint_id,
                payload,
            )
        return None

    async def async_write_datapoint(
        self,
        datapoint_id: int,
        value: Any,
        value_type: str = TYPE_NUMERIC,
    ) -> Any:
        """Write a single datapoint value."""
        session_id = await self.async_ensure_session()
        params: dict[str, Any] = {
            "SessionId": session_id,
            "Id": int(datapoint_id),
            "Type": value_type,
            "Value": value,
        }
        try:
            payload = await self._async_request(_WRITE_DATAPOINT, params)
        except OZW672AuthError:
            _LOGGER.debug("Session expired, re-authenticating")
            await self.async_login()
            params["SessionId"] = self._session_id
            payload = await self._async_request(_WRITE_DATAPOINT, params)

        error = _extract_error(payload)
        if error is not None:
            raise OZW672ApiError(f"Write of datapoint {datapoint_id} failed: {error}")
        return payload

    async def _async_login(self) -> None:
        """Perform the login handshake (lock must be held)."""
        payload = await self._async_request(
            _LOGIN, {"user": self._username, "pwd": self._password}
        )
        session_id = None
        if isinstance(payload, dict):
            for key in ("SessionId", "SessionID", "sessionId", "Sessionid"):
                if payload.get(key) is not None:
                    session_id = str(payload[key])
                    break

        if not session_id or session_id in {"0", "None", "null"}:
            raise OZW672AuthError("Login rejected by the OZW672 (check credentials)")

        self._session_id = session_id
        _LOGGER.debug("Logged in to OZW672 at %s", self.base_url)

    async def _async_request(self, path: str, params: dict[str, Any]) -> Any:
        """Perform a GET request against the OZW672 and return the JSON payload."""
        url = f"{self.base_url}{path}"
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                response = await self._session.get(
                    url, params=params, ssl=False if not self._verify_ssl else None
                )
                status = response.status
                text = await response.text()
        except TimeoutError as err:
            raise OZW672ConnectionError(f"Timeout while calling {path}") from err
        except aiohttp.ClientError as err:
            raise OZW672ConnectionError(f"Cannot reach {self.base_url}: {err}") from err

        if status == 401:
            raise OZW672AuthError(f"HTTP 401 on {path}")
        if status >= 400:
            raise OZW672ApiError(f"HTTP {status} on {path}")

        try:
            return json.loads(text)
        except ValueError as err:
            lowered = text.lower()
            if "session" in lowered:
                raise OZW672AuthError(f"Invalid session on {path}") from err
            raise OZW672ApiError(
                f"Non-JSON response on {path}: {text[:200]!r}"
            ) from err
