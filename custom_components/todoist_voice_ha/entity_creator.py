"""Entity creator for Todoist Voice HA integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, REQUIRED_ENTITIES

_LOGGER = logging.getLogger(__name__)


class EntityCreator:
    """Handles creation and cleanup of required entities."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the entity creator."""
        self.hass = hass
        self.config_entry = config_entry
        self.entity_registry = er.async_get(hass)

    async def create_all_entities(self) -> None:
        """Create all required entities."""
        _LOGGER.info("Creating required entities for Todoist Voice HA")
        
        created_count = 0
        
        for domain, entities in REQUIRED_ENTITIES.items():
            for entity_key, entity_config in entities.items():
                try:
                    await self._create_entity(domain, entity_key, entity_config)
                    created_count += 1
                except Exception as err:
                    _LOGGER.error(
                        "Failed to create entity %s.%s_%s: %s",
                        domain,
                        DOMAIN,
                        entity_key,
                        err,
                    )
        
        _LOGGER.info("Created %d entities for Todoist Voice HA", created_count)

    async def _create_entity(
        self, domain: str, entity_key: str, entity_config: dict[str, Any]
    ) -> None:
        """Create a single entity."""
        entity_id = f"{domain}.{DOMAIN}_{entity_key}"
        
        # Check if entity already exists
        if self.hass.states.get(entity_id):
            _LOGGER.debug("Entity %s already exists, skipping creation", entity_id)
            return
        
        try:
            if domain == "input_boolean":
                await self._create_input_boolean(entity_id, entity_config)
            elif domain == "input_text":
                await self._create_input_text(entity_id, entity_config)
            elif domain == "input_select":
                await self._create_input_select(entity_id, entity_config)
            elif domain == "input_number":
                await self._create_input_number(entity_id, entity_config)
            else:
                _LOGGER.warning("Unknown domain: %s", domain)
                return
                
            _LOGGER.debug("Created entity: %s", entity_id)
            
        except Exception as err:
            _LOGGER.error("Failed to create entity %s: %s", entity_id, err)
            raise

    async def _create_input_boolean(
        self, entity_id: str, config: dict[str, Any]
    ) -> None:
        """Create an input_boolean entity."""
        await self.hass.services.async_call(
            "input_boolean",
            "create",
            {
                "id": entity_id.split(".")[1],
                "name": config.get("name", entity_id),
                "icon": config.get("icon"),
                "initial": config.get("initial", False),
            },
            blocking=True,
        )

    async def _create_input_text(
        self, entity_id: str, config: dict[str, Any]
    ) -> None:
        """Create an input_text entity."""
        data = {
            "id": entity_id.split(".")[1],
            "name": config.get("name", entity_id),
            "icon": config.get("icon"),
            "initial": config.get("initial", ""),
        }
        
        # Add optional parameters
        if "max" in config:
            data["max"] = config["max"]
        if "min" in config:
            data["min"] = config["min"]
        if "mode" in config:
            data["mode"] = config["mode"]
        if "pattern" in config:
            data["pattern"] = config["pattern"]
        
        await self.hass.services.async_call(
            "input_text",
            "create",
            data,
            blocking=True,
        )

    async def _create_input_select(
        self, entity_id: str, config: dict[str, Any]
    ) -> None:
        """Create an input_select entity."""
        await self.hass.services.async_call(
            "input_select",
            "create",
            {
                "id": entity_id.split(".")[1],
                "name": config.get("name", entity_id),
                "icon": config.get("icon"),
                "initial": config.get("initial", ""),
                "options": config.get("options", []),
            },
            blocking=True,
        )

    async def _create_input_number(
        self, entity_id: str, config: dict[str, Any]
    ) -> None:
        """Create an input_number entity."""
        data = {
            "id": entity_id.split(".")[1],
            "name": config.get("name", entity_id),
            "icon": config.get("icon"),
            "initial": config.get("initial", 0),
        }
        
        # Add optional parameters
        if "min" in config:
            data["min"] = config["min"]
        if "max" in config:
            data["max"] = config["max"]
        if "step" in config:
            data["step"] = config["step"]
        if "mode" in config:
            data["mode"] = config["mode"]
        if "unit_of_measurement" in config:
            data["unit_of_measurement"] = config["unit_of_measurement"]
        
        await self.hass.services.async_call(
            "input_number",
            "create",
            data,
            blocking=True,
        )

    async def cleanup_entities(self) -> None:
        """Clean up created entities."""
        _LOGGER.info("Cleaning up entities for Todoist Voice HA")
        
        cleanup_count = 0
        
        for domain, entities in REQUIRED_ENTITIES.items():
            for entity_key, _ in entities.items():
                try:
                    await self._cleanup_entity(domain, entity_key)
                    cleanup_count += 1
                except Exception as err:
                    _LOGGER.error(
                        "Failed to cleanup entity %s.%s_%s: %s",
                        domain,
                        DOMAIN,
                        entity_key,
                        err,
                    )
        
        _LOGGER.info("Cleaned up %d entities for Todoist Voice HA", cleanup_count)

    async def _cleanup_entity(self, domain: str, entity_key: str) -> None:
        """Clean up a single entity."""
        entity_id = f"{domain}.{DOMAIN}_{entity_key}"
        
        # Check if entity exists
        if not self.hass.states.get(entity_id):
            _LOGGER.debug("Entity %s does not exist, skipping cleanup", entity_id)
            return
        
        try:
            # Remove from entity registry if it exists
            entity_entry = self.entity_registry.async_get(entity_id)
            if entity_entry:
                self.entity_registry.async_remove(entity_id)
                _LOGGER.debug("Removed entity from registry: %s", entity_id)
            
            # Remove the entity using the appropriate service
            await self.hass.services.async_call(
                domain,
                "remove",
                {"id": entity_id.split(".")[1]},
                blocking=True,
            )
            
            _LOGGER.debug("Cleaned up entity: %s", entity_id)
            
        except Exception as err:
            _LOGGER.error("Failed to cleanup entity %s: %s", entity_id, err)
            raise

    async def update_project_list(self, projects: list[str]) -> None:
        """Update the project selection entity with current projects."""
        entity_id = f"input_select.{DOMAIN}_available_projects"
        
        if not self.hass.states.get(entity_id):
            _LOGGER.debug("Project list entity %s does not exist", entity_id)
            return
        
        try:
            await self.hass.services.async_call(
                "input_select",
                "set_options",
                {
                    "entity_id": entity_id,
                    "options": projects,
                },
                blocking=True,
            )
            
            _LOGGER.debug("Updated project list with %d projects", len(projects))
            
        except Exception as err:
            _LOGGER.error("Failed to update project list: %s", err)

    async def reset_conversation_state(self) -> None:
        """Reset all conversation state entities to default values."""
        _LOGGER.debug("Resetting conversation state entities")
        
        try:
            # Reset boolean entities
            boolean_entities = [
                f"input_boolean.{DOMAIN}_conversation_active",
                f"input_boolean.{DOMAIN}_awaiting_project_selection",
                f"input_boolean.{DOMAIN}_awaiting_project_creation",
                f"input_boolean.{DOMAIN}_awaiting_date_input",
                f"input_boolean.{DOMAIN}_awaiting_final_confirmation",
            ]
            
            for entity_id in boolean_entities:
                if self.hass.states.get(entity_id):
                    await self.hass.services.async_call(
                        "input_boolean",
                        "turn_off",
                        {"entity_id": entity_id},
                        blocking=False,
                    )
            
            # Reset text entities
            text_resets = {
                f"input_text.{DOMAIN}_conversation_id": "",
                f"input_text.{DOMAIN}_conversation_state": "idle",
                f"input_text.{DOMAIN}_input_buffer": "",
                f"input_text.{DOMAIN}_parsed_actions": "",
                f"input_text.{DOMAIN}_project_matches": "",
                f"input_text.{DOMAIN}_selected_project": "",
                f"input_text.{DOMAIN}_pending_due_date": "",
                f"input_text.{DOMAIN}_task_priority": "3",
                f"input_text.{DOMAIN}_conversation_context": "{}",
            }
            
            for entity_id, value in text_resets.items():
                if self.hass.states.get(entity_id):
                    await self.hass.services.async_call(
                        "input_text",
                        "set_value",
                        {"entity_id": entity_id, "value": value},
                        blocking=False,
                    )
            
            _LOGGER.debug("Conversation state entities reset successfully")
            
        except Exception as err:
            _LOGGER.error("Failed to reset conversation state: %s", err)

    def get_entity_ids(self) -> dict[str, list[str]]:
        """Get all entity IDs that would be created."""
        entity_ids = {}
        
        for domain, entities in REQUIRED_ENTITIES.items():
            entity_ids[domain] = []
            for entity_key, _ in entities.items():
                entity_id = f"{domain}.{DOMAIN}_{entity_key}"
                entity_ids[domain].append(entity_id)
        
        return entity_ids

    def check_entities_exist(self) -> dict[str, bool]:
        """Check which entities exist."""
        entity_status = {}
        
        for domain, entities in REQUIRED_ENTITIES.items():
            for entity_key, _ in entities.items():
                entity_id = f"{domain}.{DOMAIN}_{entity_key}"
                entity_status[entity_id] = self.hass.states.get(entity_id) is not None
        
        return entity_status