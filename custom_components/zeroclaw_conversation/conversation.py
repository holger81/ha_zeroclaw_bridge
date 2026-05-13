"""Conversation platform: forwards Assist to ZeroClaw POST /webhook."""

from __future__ import annotations

import json
import logging
from typing import Final, Literal

from aiohttp import ClientTimeout
from homeassistant.components import conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import intent
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_BASE_URL,
    CONF_BEARER_TOKEN,
    CONF_VERIFY_SSL,
    CONF_WEBHOOK_SECRET,
)

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT_SEC: Final = 120


def _sanitize_session_id(conversation_id: str | None) -> str | None:
    """Map Assist conversation_id to ZeroClaw X-Session-Id (ASCII alnum + - _ ., max 128)."""
    if not conversation_id:
        return None
    safe = "".join(
        c if c.isascii() and (c.isalnum() or c in "-_.") else "_" for c in conversation_id
    ).strip("_")
    if not safe:
        return None
    return safe[:128]


class ZeroClawConversationEntity(
    conversation.ConversationEntity, conversation.AbstractConversationAgent
):
    """Conversation agent backed by ZeroClaw gateway webhook."""

    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize entity."""
        self.hass = hass
        self._entry = entry
        self._attr_unique_id = entry.entry_id
        self._attr_name = entry.title
        self._base_url: str = entry.data[CONF_BASE_URL]
        self._token: str = entry.data.get(CONF_BEARER_TOKEN) or ""
        self._webhook_secret: str = entry.data.get(CONF_WEBHOOK_SECRET) or ""
        self._verify_ssl: bool = entry.data.get(CONF_VERIFY_SSL, True)

    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        """Accept any Assist language; ZeroClaw handles semantics."""
        return MATCH_ALL

    async def async_added_to_hass(self) -> None:
        """Register as conversation agent."""
        await super().async_added_to_hass()
        conversation.async_set_agent(self.hass, self._entry, self)

    async def async_will_remove_from_hass(self) -> None:
        """Unregister agent."""
        conversation.async_unset_agent(self.hass, self._entry)
        await super().async_will_remove_from_hass()

    async def _async_handle_message(
        self,
        user_input: conversation.ConversationInput,
        _chat_log: conversation.ChatLog,
    ) -> conversation.ConversationResult:
        """Send user text to ZeroClaw and return spoken reply."""
        session = async_get_clientsession(self.hass, verify_ssl=self._verify_ssl)
        url = f"{self._base_url}/webhook"

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        if self._webhook_secret:
            headers["X-Webhook-Secret"] = self._webhook_secret

        session_hdr = _sanitize_session_id(user_input.conversation_id)
        if session_hdr:
            headers["X-Session-Id"] = session_hdr

        payload = {"message": user_input.text}

        try:
            async with session.post(
                url,
                json=payload,
                headers=headers,
                timeout=ClientTimeout(total=REQUEST_TIMEOUT_SEC),
            ) as resp:
                status = resp.status
                raw = await resp.read()
                try:
                    body = json.loads(raw.decode())
                except json.JSONDecodeError:
                    snippet = raw.decode(errors="replace")[:400]
                    raise HomeAssistantError(
                        f"ZeroClaw returned non-JSON ({status}): {snippet}"
                    ) from None
        except TimeoutError as err:
            raise HomeAssistantError(
                "ZeroClaw gateway did not respond in time."
            ) from err
        except Exception as err:
            _LOGGER.exception("ZeroClaw webhook request failed")
            raise HomeAssistantError(
                "Could not reach the ZeroClaw gateway. Check URL and network."
            ) from err

        if status == 401:
            raise HomeAssistantError(
                "ZeroClaw rejected authentication. Check bearer token or pairing."
            )
        if status == 429:
            raise HomeAssistantError(
                "ZeroClaw rate limit exceeded. Try again shortly."
            )
        if status == 503 and isinstance(body, dict) and body.get("error") == "needs_onboarding":
            raise HomeAssistantError(
                "ZeroClaw gateway needs onboarding (no model configured)."
            )
        if status >= 400:
            err_txt = body.get("error", "") if isinstance(body, dict) else str(body)
            raise HomeAssistantError(f"ZeroClaw error ({status}): {err_txt}")

        if not isinstance(body, dict):
            raise HomeAssistantError("ZeroClaw returned an unexpected response.")

        reply = body.get("response")
        if not isinstance(reply, str):
            raise HomeAssistantError("ZeroClaw response missing text.")

        response = intent.IntentResponse(language=user_input.language)
        response.async_set_speech(reply)

        return conversation.ConversationResult(
            response=response,
            conversation_id=user_input.conversation_id,
        )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ZeroClaw conversation entity."""
    async_add_entities([ZeroClawConversationEntity(hass, entry)])
