"""Binary sensor platform for Todoist Voice HA."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import TodoistDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensor platform."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    
    binary_sensors = [
        TodoistConnectedBinarySensor(coordinator, config_entry),
        TodoistConversationActiveBinarySensor(coordinator, config_entry),
    ]
    
    async_add_entities(binary_sensors)


class TodoistConnectedBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor for Todoist connection status."""

    def __init__(
        self,
        coordinator: TodoistDataUpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._attr_name = "Todoist Connected"
        self._attr_unique_id = f"{config_entry.entry_id}_connected"
        self._attr_icon = "mdi:cloud-check"
        self._attr_device_class = "connectivity"

    @property
    def is_on(self) -> bool:
        """Return true if connected."""
        return self.coordinator.last_update_success is not None and not self.coordinator.last_exception

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        return {
            "last_update_success": self.coordinator.last_update_success,
            "last_exception": str(self.coordinator.last_exception) if self.coordinator.last_exception else None,
            "update_interval": self.coordinator.update_interval.total_seconds(),
        }


class TodoistConversationActiveBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor for conversation active status."""

    def __init__(
        self,
        coordinator: TodoistDataUpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._attr_name = "Todoist Conversation Active"
        self._attr_unique_id = f"{config_entry.entry_id}_conversation_active"
        self._attr_icon = "mdi:chat-processing"

    @property
    def is_on(self) -> bool:
        """Return true if conversation is active."""
        # Check the input_boolean entity
        conversation_active_entity = self.hass.states.get(
            f"input_boolean.{DOMAIN}_conversation_active"
        )
        return conversation_active_entity.state == "on" if conversation_active_entity else False

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        # Get conversation state
        conversation_state_entity = self.hass.states.get(
            f"input_text.{DOMAIN}_conversation_state"
        )
        conversation_id_entity = self.hass.states.get(
            f"input_text.{DOMAIN}_conversation_id"
        )
        
        return {
            "conversation_state": conversation_state_entity.state if conversation_state_entity else "idle",
            "conversation_id": conversation_id_entity.state if conversation_id_entity else "",
        }