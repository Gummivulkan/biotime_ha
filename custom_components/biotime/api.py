"""Async-Client für die BioTime api_v2 (reverse-engineered, verifiziert)."""
from __future__ import annotations

import hashlib
import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

_TIMEOUT = aiohttp.ClientTimeout(total=30)


class BioTimeError(Exception):
    """Basisfehler."""


class BioTimeAuthError(BioTimeError):
    """Login/Token ungültig."""


class BioTimeConnectionError(BioTimeError):
    """Gerät nicht erreichbar / ungültige Antwort."""


class BioTimeApi:
    """Spricht mit dem eingebetteten WebServerZK des BioTime-Terminals.

    Auth-Flow: POST api_v2/authentication (Passwort SHA-512-Hex) -> token,
    der bei allen Folge-Requests als Cookie ``ZKTECOKEY`` mitgeht.
    """

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        port: int,
        usercode: str,
        password: str,
    ) -> None:
        self._session = session
        self._base = f"http://{host}:{port}"
        self._usercode = usercode
        self._password = password
        self._token: str | None = None

    @property
    def base_url(self) -> str:
        """Basis-URL des Terminals (z. B. für configuration_url)."""
        return self._base

    @property
    def _password_hash(self) -> str:
        return hashlib.sha512(self._password.encode()).hexdigest()

    async def async_login(self) -> dict[str, Any]:
        """Authentifizieren und Token speichern. Gibt das ``value``-Objekt zurück."""
        _LOGGER.debug("BioTime-Login an %s als %s", self._base, self._usercode)
        body = {"username": self._usercode, "password": self._password_hash}
        try:
            async with self._session.post(
                f"{self._base}/api_v2/authentication", data=body, timeout=_TIMEOUT
            ) as resp:
                resp.raise_for_status()
                data = await resp.json(content_type=None)
        except aiohttp.ClientError as err:
            raise BioTimeConnectionError(str(err)) from err

        if not data.get("success"):
            raise BioTimeAuthError(data.get("message") or "Login fehlgeschlagen")
        self._token = data["token"]
        return data.get("value", {})

    async def _authed_request(
        self, method: str, path: str, data: dict[str, str] | None = None
    ) -> dict[str, Any]:
        """Request mit Cookie-Auth; bei 401 genau einmal neu einloggen."""
        if self._token is None:
            await self.async_login()

        for attempt in (1, 2):
            headers = {"Cookie": f"ZKTECOKEY={self._token}"}
            try:
                async with self._session.request(
                    method,
                    f"{self._base}/{path}",
                    data=data,
                    headers=headers,
                    timeout=_TIMEOUT,
                ) as resp:
                    if resp.status == 401 and attempt == 1:
                        _LOGGER.debug("401 auf %s – Token wird erneuert", path)
                        self._token = None
                        await self.async_login()
                        continue
                    resp.raise_for_status()
                    return await resp.json(content_type=None)
            except aiohttp.ClientError as err:
                raise BioTimeConnectionError(str(err)) from err

        raise BioTimeAuthError("Authentifizierung nach Token-Erneuerung fehlgeschlagen")

    async def async_get_terminal_info(self) -> dict[str, Any]:
        return await self._authed_request("GET", "api_v2/terminalInfo")

    async def async_get_employees(self) -> list[dict[str, Any]]:
        data = await self._authed_request("GET", "api_v2/employees")
        return data.get("values", [])

    async def async_get_attendances(
        self, start_ms: int, end_ms: int
    ) -> list[dict[str, Any]]:
        """Stempel im Zeitraum. start/end sind Unix-Timestamps in MILLISEKUNDEN.

        Wichtig: Strings statt ms-Zahlen lassen den embedded Server abstürzen.
        """
        body = {
            "start_date": str(start_ms),
            "last_date": str(end_ms),
            "is_special": "true",
            "is_photo": "false",
            "page": "-1",
        }
        data = await self._authed_request("POST", "api_v2/attendances", body)
        return data.get("values", [])
