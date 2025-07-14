"""Sensor platform for Todoist Voice HA."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
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
    """Set up sensor platform."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    
    sensors = [
        TodoistProjectCountSensor(coordinator, config_entry),
        TodoistLastUpdateSensor(coordinator, config_entry),
        TodoistConversationStateSensor(coordinator, config_entry),
    ]
    
    async_add_entities(sensors)


class TodoistProjectCountSensor(CoordinatorEntity, SensorEntity):
    """Sensor for project count."""

    def __init__(
        self,
        coordinator: TodoistDataUpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._attr_name = "Todoist Project Count"
        self._attr_unique_id = f"{config_entry.entry_id}_project_count"
        self._attr_icon = "mdi:folder-multiple"
        self._attr_native_unit_of_measurement = "projects"

    @property
    def native_value(self) -> int:
        """Return the state of the sensor."""
        return len(self.coordinator.projects)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        return {
            "project_names": [p["name"] for p in self.coordinator.projects],
            "last_updated": self.coordinator.last_update_success,
        }


class TodoistLastUpdateSensor(CoordinatorEntity, SensorEntity):
    """Sensor for last update time."""

    def __init__(
        self,
        coordinator: TodoistDataUpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._attr_name = "Todoist Last Update"
        self._attr_unique_id = f"{config_entry.entry_id}_last_update"
        self._attr_icon = "mdi:clock-outline"
        self._attr_device_class = "timestamp"

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        if self.coordinator.last_update_success:
            return self.coordinator.last_update_success.isoformat()
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        return {
            "update_interval": self.coordinator.update_interval.total_seconds(),
            "last_update_success": self.coordinator.last_update_success,
            "last_update_error": str(self.coordinator.last_exception) if self.coordinator.last_exception else None,
        }


class TodoistConversationStateSensor(CoordinatorEntity, SensorEntity):
    """Sensor for conversation state."""

    def __init__(
        self,
        coordinator: TodoistDataUpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._attr_name = "Todoist Conversation State"
        self._attr_unique_id = f"{config_entry.entry_id}_conversation_state"
        self._attr_icon = "mdi:chat-processing"

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        # Try to get state from input_text entity
        conversation_state_entity = self.hass.states.get(
            f"input_text.{DOMAIN}_conversation_state"
        )
        if conversation_state_entity:
            return conversation_state_entity.state
        return "idle"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        # Get conversation data from related entities
        conversation_id_entity = self.hass.states.get(
            f"input_text.{DOMAIN}_conversation_id"
        )
        conversation_active_entity = self.hass.states.get(
            f"input_boolean.{DOMAIN}_conversation_active"
        )
        
        attributes = {
            "conversation_id": conversation_id_entity.state if conversation_id_entity else "",
            "is_active": conversation_active_entity.state == "on" if conversation_active_entity else False,
        }
        
        # Add state-specific attributes
        if self.native_value == "project_selection":
            project_matches_entity = self.hass.states.get(
                f"input_text.{DOMAIN}_project_matches"
            )
            if project_matches_entity:
                attributes["project_matches"] = project_matches_entity.state
        
        return attributes