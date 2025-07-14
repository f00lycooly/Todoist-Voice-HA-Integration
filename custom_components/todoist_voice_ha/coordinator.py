"""Data update coordinator for Todoist Voice HA."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    CONF_API_TOKEN,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    ERROR_MESSAGES,
)
from .todoist_client import TodoistClient

_LOGGER = logging.getLogger(__name__)


class TodoistDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Todoist data."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.config_entry = config_entry
        self.api_token = config_entry.data[CONF_API_TOKEN]
        
        update_interval = timedelta(
            seconds=config_entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        )
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )
        
        self.client: TodoistClient | None = None
        self._projects: list[dict[str, Any]] = []
        self._projects_by_id: dict[str, dict[str, Any]] = {}
        self._projects_by_name: dict[str, dict[str, Any]] = {}

    @property
    def projects(self) -> list[dict[str, Any]]:
        """Get the cached projects."""
        return self._projects

    @property
    def projects_by_id(self) -> dict[str, dict[str, Any]]:
        """Get projects indexed by ID."""
        return self._projects_by_id

    @property
    def projects_by_name(self) -> dict[str, dict[str, Any]]:
        """Get projects indexed by name."""
        return self._projects_by_name

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Todoist API."""
        if not self.client:
            # Initialize client on first update
            self.client = TodoistClient(self.api_token)
        
        try:
            # Use the client as an async context manager
            async with self.client as client:
                # Validate token first
                validation = await client.validate_token()
                if not validation["valid"]:
                    raise ConfigEntryAuthFailed(
                        f"Invalid Todoist API token: {validation.get('error', 'Unknown error')}"
                    )
                
                # Fetch projects
                projects = await client.get_projects()
                
                # Update internal caches
                self._projects = projects
                self._projects_by_id = {p["id"]: p for p in projects}
                self._projects_by_name = {p["name"].lower(): p for p in projects}
                
                # Update entity registry if needed
                await self._update_project_entities()
                
                return {
                    "projects": projects,
                    "project_count": len(projects),
                    "last_updated": self.last_update_success,
                }
                
        except ConfigEntryAuthFailed:
            raise
        except Exception as err:
            _LOGGER.error("Error fetching Todoist data: %s", err)
            raise UpdateFailed(f"Error fetching Todoist data: {err}") from err

    async def _update_project_entities(self) -> None:
        """Update project-related entities."""
        if not self.hass or not self._projects:
            return
            
        # Update input_select with current projects
        project_names = [p["name"] for p in self._projects]
        project_names.append("Inbox")  # Always include Inbox
        
        # Try to update the input_select entity
        entity_id = "input_select.todoist_voice_ha_available_projects"
        if self.hass.states.get(entity_id):
            try:
                await self.hass.services.async_call(
                    "input_select",
                    "set_options",
                    {
                        "entity_id": entity_id,
                        "options": project_names,
                    },
                    blocking=True,
                )
                _LOGGER.debug("Updated project list with %d projects", len(project_names))
            except Exception as err:
                _LOGGER.warning("Failed to update project list: %s", err)

    async def get_project_by_id(self, project_id: str) -> dict[str, Any] | None:
        """Get a project by ID."""
        if not self._projects_by_id:
            await self.async_request_refresh()
        return self._projects_by_id.get(project_id)

    async def get_project_by_name(self, project_name: str) -> dict[str, Any] | None:
        """Get a project by name."""
        if not self._projects_by_name:
            await self.async_request_refresh()
        return self._projects_by_name.get(project_name.lower())

    async def find_matching_projects(self, query: str) -> list[dict[str, Any]]:
        """Find projects matching the query."""
        if not self.client:
            return []
            
        if not self._projects:
            await self.async_request_refresh()
            
        async with self.client as client:
            return client.find_matching_projects(self._projects, query)

    async def create_project(self, name: str, **kwargs) -> dict[str, Any]:
        """Create a new project."""
        if not self.client:
            raise UpdateFailed("Client not initialized")
            
        async with self.client as client:
            project = await client.create_project(name, **kwargs)
            
            # Refresh data after creating project
            await self.async_request_refresh()
            
            return project

    async def create_task(
        self,
        content: str,
        project_id: str | None = None,
        **kwargs
    ) -> dict[str, Any]:
        """Create a new task."""
        if not self.client:
            raise UpdateFailed("Client not initialized")
            
        async with self.client as client:
            return await client.create_task(content, project_id, **kwargs)

    async def export_to_todoist(
        self,
        text: str,
        project_id: str,
        **kwargs
    ) -> dict[str, Any]:
        """Export text to Todoist as structured tasks."""
        if not self.client:
            raise UpdateFailed("Client not initialized")
            
        async with self.client as client:
            return await client.export_to_todoist(text, project_id, **kwargs)

    def extract_actions(self, text: str) -> list[str]:
        """Extract actions from text."""
        if not self.client:
            return []
            
        # This is a synchronous operation, so we can call it directly
        return self.client.extract_actions(text)

    def parse_due_date(self, date_input: str) -> str | None:
        """Parse due date from input."""
        if not self.client:
            return None
            
        return self.client.parse_due_date(date_input)

    def generate_project_name(self, hint: str) -> str:
        """Generate project name from hint."""
        if not self.client:
            return "New Project"
            
        return self.client.generate_project_name(hint)

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator."""
        if self.client:
            # Close the client session if it exists
            if hasattr(self.client, 'session') and self.client.session:
                await self.client.session.close()
        
        await super().async_shutdown()