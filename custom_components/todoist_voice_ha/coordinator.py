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
        self._tasks: list[dict[str, Any]] = []
        self._tasks_by_id: dict[str, dict[str, Any]] = {}
        self._task_summary: dict[str, Any] = {}

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

    @property
    def tasks(self) -> list[dict[str, Any]]:
        """Get the cached tasks."""
        return self._tasks

    @property
    def tasks_by_id(self) -> dict[str, dict[str, Any]]:
        """Get tasks indexed by ID."""
        return self._tasks_by_id

    @property
    def task_summary(self) -> dict[str, Any]:
        """Get task summary statistics."""
        return self._task_summary

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
                
                # Fetch tasks
                tasks = await client.get_tasks()
                
                # Update internal caches
                self._projects = projects
                self._projects_by_id = {p["id"]: p for p in projects}
                self._projects_by_name = {p["name"].lower(): p for p in projects}
                
                self._tasks = tasks
                self._tasks_by_id = {t["id"]: t for t in tasks}
                self._task_summary = client.get_task_summary(tasks)
                
                # Update entity registry if needed
                await self._update_project_entities()
                
                return {
                    "projects": projects,
                    "project_count": len(projects),
                    "tasks": tasks,
                    "task_count": len(tasks),
                    "task_summary": self._task_summary,
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

    async def get_task_by_id(self, task_id: str) -> dict[str, Any] | None:
        """Get a task by ID."""
        if not self._tasks_by_id:
            await self.async_request_refresh()
        return self._tasks_by_id.get(task_id)

    async def get_tasks_by_filter(self, filter_type: str, **kwargs) -> list[dict[str, Any]]:
        """Get tasks by various filters."""
        if not self.client:
            return []
            
        if not self._tasks:
            await self.async_request_refresh()
            
        async with self.client as client:
            if filter_type == "date":
                return client.filter_tasks_by_date(self._tasks, kwargs.get("date_filter", "today"))
            elif filter_type == "priority":
                return client.filter_tasks_by_priority(self._tasks, kwargs.get("priority", 1))
            elif filter_type == "project":
                return client.filter_tasks_by_project(self._tasks, kwargs.get("project_id", ""))
            elif filter_type == "labels":
                return client.filter_tasks_by_labels(self._tasks, kwargs.get("labels", []))
            else:
                return self._tasks

    async def get_tasks_due_today(self) -> list[dict[str, Any]]:
        """Get tasks due today."""
        return await self.get_tasks_by_filter("date", date_filter="today")

    async def get_overdue_tasks(self) -> list[dict[str, Any]]:
        """Get overdue tasks."""
        return await self.get_tasks_by_filter("date", date_filter="overdue")

    async def get_upcoming_tasks(self) -> list[dict[str, Any]]:
        """Get upcoming tasks."""
        return await self.get_tasks_by_filter("date", date_filter="upcoming")

    async def get_tasks_due_tomorrow(self) -> list[dict[str, Any]]:
        """Get tasks due tomorrow."""
        return await self.get_tasks_by_filter("date", date_filter="tomorrow")

    async def get_tasks_this_week(self) -> list[dict[str, Any]]:
        """Get tasks due this week."""
        return await self.get_tasks_by_filter("date", date_filter="this_week")

    async def get_high_priority_tasks(self) -> list[dict[str, Any]]:
        """Get high priority tasks (priority 1 and 2)."""
        high_priority_1 = await self.get_tasks_by_filter("priority", priority=1)
        high_priority_2 = await self.get_tasks_by_filter("priority", priority=2)
        return high_priority_1 + high_priority_2

    async def get_tasks_by_project_name(self, project_name: str) -> list[dict[str, Any]]:
        """Get tasks for a specific project by name."""
        project = await self.get_project_by_name(project_name)
        if not project:
            return []
        return await self.get_tasks_by_filter("project", project_id=project["id"])

    async def complete_task(self, task_id: str) -> bool:
        """Complete a task."""
        if not self.client:
            raise UpdateFailed("Client not initialized")
            
        async with self.client as client:
            success = await client.complete_task(task_id)
            if success:
                # Refresh data after completing task
                await self.async_request_refresh()
            return success

    async def reopen_task(self, task_id: str) -> bool:
        """Reopen a task."""
        if not self.client:
            raise UpdateFailed("Client not initialized")
            
        async with self.client as client:
            success = await client.reopen_task(task_id)
            if success:
                # Refresh data after reopening task
                await self.async_request_refresh()
            return success

    def get_task_counts_by_project(self) -> dict[str, int]:
        """Get task counts grouped by project."""
        counts = {}
        for task in self._tasks:
            project_id = task.get("project_id")
            if project_id:
                project = self._projects_by_id.get(project_id)
                project_name = project["name"] if project else f"Project {project_id}"
                counts[project_name] = counts.get(project_name, 0) + 1
        return counts

    def get_task_counts_by_priority(self) -> dict[int, int]:
        """Get task counts grouped by priority."""
        counts = {1: 0, 2: 0, 3: 0, 4: 0}
        for task in self._tasks:
            priority = task.get("priority", 1)
            counts[priority] = counts.get(priority, 0) + 1
        return counts