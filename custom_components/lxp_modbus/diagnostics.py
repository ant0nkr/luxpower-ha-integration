"""Diagnostics support for the LuxPower Modbus integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_DONGLE_SERIAL, CONF_HOST, CONF_INVERTER_SERIAL, DOMAIN

# Serial numbers identify the hardware and the host is a local address; both are
# redacted so a diagnostics dump can be attached to a public issue.
TO_REDACT = {CONF_HOST, CONF_DONGLE_SERIAL, CONF_INVERTER_SERIAL, "unique_id"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    entry_data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    coordinator = entry_data.get("coordinator")
    api_client = entry_data.get("api_client")

    diagnostics: dict[str, Any] = {
        "entry": {
            "title": entry.title,
            "version": entry.version,
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": async_redact_data(dict(entry.options), TO_REDACT),
            "platforms": [str(platform) for platform in entry_data.get("platforms", [])],
        },
    }

    if coordinator is not None:
        diagnostics["coordinator"] = {
            "last_update_success": coordinator.last_update_success,
            "update_interval": (
                coordinator.update_interval.total_seconds()
                if coordinator.update_interval
                else None
            ),
            "failed_updates": coordinator.failed_updates,
            "is_recovering": coordinator.is_recovering,
            "last_success_timestamp": coordinator.last_success,
        }

        data = coordinator.data or {}
        diagnostics["registers"] = {
            # Register values are keyed by int; JSON needs string keys.
            "input": {str(reg): value for reg, value in data.get("input", {}).items()},
            "hold": {str(reg): value for reg, value in data.get("hold", {}).items()},
            "battery": {
                serial: {str(reg): value for reg, value in regs.items()}
                for serial, regs in data.get("battery", {}).items()
            },
        }

    if api_client is not None:
        connection = async_redact_data(api_client.get_connection_stats(), TO_REDACT)
        diagnostics["connection"] = connection
        diagnostics["packet_recovery"] = api_client.get_recovery_stats()

    return diagnostics
