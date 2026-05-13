"""Config flow for ZeroClaw conversation."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    BooleanSelector,
    BooleanSelectorConfig,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    CONF_BASE_URL,
    CONF_BEARER_TOKEN,
    CONF_VERIFY_SSL,
    CONF_WEBHOOK_SECRET,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
)


def _normalize_base(url: str) -> str:
    u = url.strip().rstrip("/")
    if not u.startswith(("http://", "https://")):
        u = f"http://{u}"
    return u


def _validate_base_url(value: str) -> str:
    normalized = _normalize_base(value)
    parsed = urlparse(normalized)
    if not parsed.scheme or not parsed.netloc:
        raise vol.Invalid("invalid_url")
    return normalized


def _host_key(base_url: str) -> str:
    parsed = urlparse(base_url)
    return f"{parsed.scheme}://{parsed.netloc.lower()}"


class ZeroClawConversationConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Prompt for gateway URL and credentials."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                base_url = _validate_base_url(user_input[CONF_BASE_URL])
            except vol.Invalid:
                errors["base"] = "invalid_url"
            else:
                await self.async_set_unique_id(_host_key(base_url))
                self._abort_if_unique_id_configured()

                title = (user_input.get("title") or "").strip() or "ZeroClaw"
                return self.async_create_entry(
                    title=title,
                    data={
                        CONF_BASE_URL: base_url,
                        CONF_BEARER_TOKEN: user_input.get(CONF_BEARER_TOKEN) or "",
                        CONF_WEBHOOK_SECRET: user_input.get(CONF_WEBHOOK_SECRET) or "",
                        CONF_VERIFY_SSL: user_input.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_BASE_URL): TextSelector(
                    TextSelectorConfig(
                        type=TextSelectorType.URL,
                        autocomplete="off",
                    )
                ),
                vol.Optional("title"): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.TEXT, autocomplete="off")
                ),
                vol.Optional(CONF_BEARER_TOKEN): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.PASSWORD)
                ),
                vol.Optional(CONF_WEBHOOK_SECRET): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.PASSWORD)
                ),
                vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): BooleanSelector(
                    BooleanSelectorConfig()
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )
