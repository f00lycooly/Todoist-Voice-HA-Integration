"""Button platform for Todoist Voice HA."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
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
    """Set up button platform."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    
    buttons = [
        TodoistRefreshProjectsButton(coordinator, config_entry),
        TodoistResetConversationButton(coordinator, config_entry),
    ]
    
    async_add_entities(buttons)


class TodoistRefreshProjectsButton(CoordinatorEntity, ButtonEntity):
    """Button to refresh projects."""

    def __init__(
        self,
        coordinator: TodoistDataUpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._attr_name = "Refresh Todoist Projects"
        self._attr_unique_id = f"{config_entry.entry_id}_refresh_projects"
        self._attr_icon = "mdi:refresh"

    async def async_press(self) -> None:
        """Handle the button press."""
        _LOGGER.info("Refreshing Todoist projects via button")
        await self.coordinator.async_request_refresh()


class TodoistResetConversationButton(CoordinatorEntity, ButtonEntity):
    """Button to reset conversation state."""

    def __init__(
        self,
        coordinator: TodoistDataUpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._attr_name = "Reset Conversation State"
        self._attr_unique_id = f"{config_entry.entry_id}_reset_conversation"
        self._attr_icon = "mdi:restart"

    async def async_press(self) -> None:
        """Handle the button press."""
        _LOGGER.info("Resetting conversation state via button")
        
        # Get the entity creator to reset conversation state
        from .entity_creator import EntityCreator
        entity_creator = EntityCreator(self.hass, self.config_entry)
        await entity_creator.reset_conversation_state()
        
        # Clean up any active conversations
        if DOMAIN in self.hass.data and "conversation_engine" in self.hass.data[DOMAIN]:
            conversation_engine = self.hass.data[DOMAIN]["conversation_engine"]
            await conversation_engine.cleanup_expired_conversations()