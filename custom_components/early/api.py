"""API client for the EARLY (formerly Timeular) Public API v2."""

from __future__ import annotations

import asyncio
import base64
import binascii
import json
import socket
import time
from datetime import UTC, datetime
from typing import Any

import aiohttp

# The public API host did not change with the Timeular -> EARLY rebrand; it is
# still served from api.timeular.com. See https://developers.early.app/.
API_BASE = "https://api.timeular.com/api/v2"

# Number of seconds each individual request is allowed to take.
REQUEST_TIMEOUT = 10

# Refresh the bearer token this many seconds before it actually expires, so a
# request never goes out with a token that is about to lapse.
TOKEN_REFRESH_MARGIN = 300

# Fallback lifetime used only when the token's expiry cannot be read from the
# JWT. Kept short so we re-authenticate well within any real lifetime.
DEFAULT_TOKEN_TTL = 1800


class EarlyApiClientError(Exception):
    """Exception to indicate a general API error."""


class EarlyApiClientCommunicationError(EarlyApiClientError):
    """Exception to indicate a communication error."""


class EarlyApiClientAuthenticationError(EarlyApiClientError):
    """Exception to indicate an authentication error."""


def format_timestamp(value: datetime | None = None) -> str:
    """Format a datetime the way the EARLY API expects it.

    The API wants an ISO-8601 timestamp in UTC with millisecond precision and
    **no** timezone offset, e.g. ``2021-08-11T10:00:00.000``.
    """
    if value is None:
        value = datetime.now(UTC)
    elif value.tzinfo is None:
        # Treat a naive datetime as UTC rather than crashing.
        value = value.replace(tzinfo=UTC)
    value = value.astimezone(UTC)
    return f"{value.strftime('%Y-%m-%dT%H:%M:%S')}.{value.microsecond // 1000:03d}"


def _decode_jwt_expiry(token: str) -> float | None:
    """Return the ``exp`` (epoch seconds) claim of a JWT without verifying it.

    The EARLY access token is a JWT; reading its expiry lets us refresh it
    proactively. Returns ``None`` if the token is not a parseable JWT.
    """
    try:
        payload_segment = token.split(".")[1]
    except IndexError:
        return None
    # Restore the base64url padding that JWTs strip.
    padding = "=" * (-len(payload_segment) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(payload_segment + padding))
    except (ValueError, binascii.Error):
        return None
    exp = payload.get("exp")
    return float(exp) if isinstance(exp, (int, float)) else None


def _verify_response_or_raise(response: aiohttp.ClientResponse) -> None:
    """Raise a typed error for non-successful responses."""
    if response.status in (401, 403):
        msg = "Invalid API key or secret"
        raise EarlyApiClientAuthenticationError(msg)
    response.raise_for_status()


class EarlyApiClient:
    """Thin async client around the EARLY Public API v2."""

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        session: aiohttp.ClientSession,
    ) -> None:
        """Initialize the client."""
        self._api_key = api_key
        self._api_secret = api_secret
        self._session = session
        self._token: str | None = None
        # Epoch seconds at which the current token expires (0 = no token yet).
        self._token_expires_at: float = 0.0
        # Serialise concurrent sign-ins so a burst of requests triggers one only.
        self._auth_lock = asyncio.Lock()

    async def async_validate(self) -> None:
        """Validate the credentials by performing a sign-in."""
        await self._async_sign_in()

    async def async_get_activities(self) -> list[dict[str, Any]]:
        """Return the list of (non-archived) activities."""
        data = await self._authed_request("get", f"{API_BASE}/activities")
        return data.get("activities", [])

    async def async_get_current_tracking(self) -> dict[str, Any] | None:
        """Return the currently running tracking, or ``None`` if idle."""
        data = await self._authed_request("get", f"{API_BASE}/tracking")
        return data.get("currentTracking")

    async def async_start_tracking(
        self,
        activity_id: str,
        started_at: datetime | None = None,
        note: str | None = None,
    ) -> dict[str, Any]:
        """Start tracking the given activity."""
        payload: dict[str, Any] = {"startedAt": format_timestamp(started_at)}
        if note is not None:
            payload["note"] = {"text": note}
        return await self._authed_request(
            "post",
            f"{API_BASE}/tracking/{activity_id}/start",
            data=payload,
        )

    async def async_stop_tracking(
        self,
        activity_id: str,
        stopped_at: datetime | None = None,
    ) -> dict[str, Any]:
        """Stop tracking the given activity."""
        payload = {"stoppedAt": format_timestamp(stopped_at)}
        return await self._authed_request(
            "post",
            f"{API_BASE}/tracking/{activity_id}/stop",
            data=payload,
        )

    async def _async_sign_in(self) -> str:
        """Exchange API key/secret for a bearer token and cache it."""
        data = await self._api_wrapper(
            method="post",
            url=f"{API_BASE}/developer/sign-in",
            data={"apiKey": self._api_key, "apiSecret": self._api_secret},
        )
        token = data.get("token")
        if not token:
            msg = "Sign-in did not return a token"
            raise EarlyApiClientAuthenticationError(msg)
        self._token = token
        expiry = _decode_jwt_expiry(token)
        self._token_expires_at = (
            expiry if expiry is not None else time.time() + DEFAULT_TOKEN_TTL
        )
        return token

    async def _async_valid_token(self, *, force: bool = False) -> str:
        """Return a valid bearer token, refreshing it in the background if due.

        A single lock guards sign-in so a burst of concurrent requests results
        in at most one re-authentication.
        """
        async with self._auth_lock:
            expired = time.time() >= self._token_expires_at - TOKEN_REFRESH_MARGIN
            if force or self._token is None or expired:
                await self._async_sign_in()
            # Narrowing for the type checker; _async_sign_in always sets it.
            assert self._token is not None  # noqa: S101
            return self._token

    async def _authed_request(
        self,
        method: str,
        url: str,
        data: dict | None = None,
        *,
        _retry: bool = True,
    ) -> dict[str, Any]:
        """Perform an authenticated request with proactive token refresh.

        The token is refreshed before it expires (see ``_async_valid_token``);
        a 401 still triggers exactly one forced re-authentication as a safety
        net in case the server invalidates it early.
        """
        token = await self._async_valid_token()
        try:
            return await self._api_wrapper(
                method=method,
                url=url,
                data=data,
                headers={"Authorization": f"Bearer {token}"},
            )
        except EarlyApiClientAuthenticationError:
            if not _retry:
                raise
            await self._async_valid_token(force=True)
            return await self._authed_request(method, url, data=data, _retry=False)

    async def _api_wrapper(
        self,
        method: str,
        url: str,
        data: dict | None = None,
        headers: dict | None = None,
    ) -> dict[str, Any]:
        """Make an HTTP request and return the parsed JSON body."""
        request_headers: dict[str, str] = {"Accept": "application/json"}
        if data is not None:
            request_headers["Content-Type"] = "application/json"
        if headers:
            request_headers.update(headers)

        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                response = await self._session.request(
                    method=method,
                    url=url,
                    headers=request_headers,
                    json=data,
                )
                _verify_response_or_raise(response)
                text = await response.text()
                return json.loads(text) if text else {}

        except TimeoutError as exception:
            msg = f"Timeout error fetching information - {exception}"
            raise EarlyApiClientCommunicationError(msg) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            msg = f"Error fetching information - {exception}"
            raise EarlyApiClientCommunicationError(msg) from exception
        except json.JSONDecodeError as exception:
            msg = f"Invalid JSON received from the API - {exception}"
            raise EarlyApiClientError(msg) from exception
        except EarlyApiClientError:
            # Already-typed errors (auth, comms) are meaningful; re-raise as-is.
            raise
        except Exception as exception:  # pylint: disable=broad-except
            msg = f"Something really wrong happened! - {exception}"
            raise EarlyApiClientError(msg) from exception
