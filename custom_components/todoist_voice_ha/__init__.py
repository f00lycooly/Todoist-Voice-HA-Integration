"""The Todoist Voice HA Integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN, CONF_AUTO_CREATE_ENTITIES
from .coordinator import TodoistDataUpdateCoordinator
from .entity_creator import EntityCreator
from .services import async_setup_services, async_unload_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
]


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the Todoist Voice HA integration."""
    _LOGGER.info("Setting up Todoist Voice HA Integration")
    
    # Initialize domain data
    hass.data.setdefault(DOMAIN, {})
    
    # Set up services
    await async_setup_services(hass)
    
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Todoist Voice HA from a config entry."""
    _LOGGER.info("Setting up Todoist Voice HA from config entry: %s", entry.entry_id)
    
    # Initialize coordinator
    coordinator = TodoistDataUpdateCoordinator(hass, entry)
    
    # Perform first refresh to validate configuration
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        _LOGGER.error("Failed to initialize coordinator: %s", err)
        raise ConfigEntryNotReady(f"Failed to initialize: {err}") from err
    
    # Store coordinator in hass data
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "config": entry.data,
    }
    
    # Create required entities if enabled
    if entry.data.get(CONF_AUTO_CREATE_ENTITIES, True):
        entity_creator = EntityCreator(hass, entry)
        try:
            await entity_creator.create_all_entities()
            _LOGGER.info("Successfully created required entities")
        except Exception as err:
            _LOGGER.error("Failed to create entities: %s", err)
            # Don't fail setup if entity creation fails
    
    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    _LOGGER.info("Todoist Voice HA setup completed successfully")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading Todoist Voice HA Integration")
    
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        # Clean up stored data
        hass.data[DOMAIN].pop(entry.entry_id, None)
        
        # If this was the last entry, unload services
        if not hass.config_entries.async_entries(DOMAIN):
            await async_unload_services(hass)
    
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove a config entry."""
    _LOGGER.info("Removing Todoist Voice HA Integration")
    
    # Clean up entities if they were auto-created
    if entry.data.get(CONF_AUTO_CREATE_ENTITIES, True):
        entity_creator = EntityCreator(hass, entry)
        try:
            await entity_creator.cleanup_entities()
            _LOGGER.info("Successfully cleaned up entities")
        except Exception as err:
            _LOGGER.error("Failed to cleanup entities: %s", err)


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)