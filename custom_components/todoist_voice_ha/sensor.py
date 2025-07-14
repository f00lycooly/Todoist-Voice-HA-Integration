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
        TodoistTaskCountSensor(coordinator, config_entry),
        TodoistTasksDueTodaySensor(coordinator, config_entry),
        TodoistOverdueTasksSensor(coordinator, config_entry),
        TodoistUpcomingTasksSensor(coordinator, config_entry),
        TodoistTasksDueTomorrowSensor(coordinator, config_entry),
        TodoistTasksThisWeekSensor(coordinator, config_entry),
        TodoistHighPriorityTasksSensor(coordinator, config_entry),
        TodoistTaskSummarySensor(coordinator, config_entry),
        TodoistNextTaskSensor(coordinator, config_entry),
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


class TodoistTaskCountSensor(CoordinatorEntity, SensorEntity):
    """Sensor for total task count."""

    def __init__(
        self,
        coordinator: TodoistDataUpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._attr_name = "Todoist Task Count"
        self._attr_unique_id = f"{config_entry.entry_id}_task_count"
        self._attr_icon = "mdi:format-list-checkbox"
        self._attr_native_unit_of_measurement = "tasks"

    @property
    def native_value(self) -> int:
        """Return the total number of tasks."""
        return len(self.coordinator.tasks)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        summary = self.coordinator.task_summary
        return {
            "total_tasks": summary.get("total", 0),
            "with_due_date": summary.get("with_due_date", 0),
            "without_due_date": summary.get("without_due_date", 0),
            "by_priority": summary.get("by_priority", {}),
            "last_updated": self.coordinator.last_update_success,
        }


class TodoistTasksDueTodaySensor(CoordinatorEntity, SensorEntity):
    """Sensor for tasks due today."""

    def __init__(
        self,
        coordinator: TodoistDataUpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._attr_name = "Todoist Tasks Due Today"
        self._attr_unique_id = f"{config_entry.entry_id}_tasks_due_today"
        self._attr_icon = "mdi:calendar-today"
        self._attr_native_unit_of_measurement = "tasks"

    @property
    def native_value(self) -> int:
        """Return the number of tasks due today."""
        return self.coordinator.task_summary.get("due_today", 0)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        # Get actual tasks due today for details
        if hasattr(self.coordinator, '_tasks') and self.coordinator.client:
            try:
                tasks_today = self.coordinator.client.filter_tasks_by_date(
                    self.coordinator.tasks, "today"
                )
                return {
                    "tasks": [
                        {
                            "id": task["id"],
                            "content": task["content"],
                            "priority": task.get("priority", 1),
                            "project_id": task.get("project_id"),
                            "due": task.get("due", {}).get("date") if task.get("due") else None,
                        }
                        for task in tasks_today[:10]  # Limit to first 10 tasks
                    ],
                    "total_count": len(tasks_today),
                }
            except Exception:
                pass
        return {"tasks": [], "total_count": 0}


class TodoistOverdueTasksSensor(CoordinatorEntity, SensorEntity):
    """Sensor for overdue tasks."""

    def __init__(
        self,
        coordinator: TodoistDataUpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._attr_name = "Todoist Overdue Tasks"
        self._attr_unique_id = f"{config_entry.entry_id}_overdue_tasks"
        self._attr_icon = "mdi:calendar-alert"
        self._attr_native_unit_of_measurement = "tasks"

    @property
    def native_value(self) -> int:
        """Return the number of overdue tasks."""
        return self.coordinator.task_summary.get("overdue", 0)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        if hasattr(self.coordinator, '_tasks') and self.coordinator.client:
            try:
                overdue_tasks = self.coordinator.client.filter_tasks_by_date(
                    self.coordinator.tasks, "overdue"
                )
                return {
                    "tasks": [
                        {
                            "id": task["id"],
                            "content": task["content"],
                            "priority": task.get("priority", 1),
                            "project_id": task.get("project_id"),
                            "due": task.get("due", {}).get("date") if task.get("due") else None,
                        }
                        for task in overdue_tasks[:10]  # Limit to first 10 tasks
                    ],
                    "total_count": len(overdue_tasks),
                }
            except Exception:
                pass
        return {"tasks": [], "total_count": 0}


class TodoistUpcomingTasksSensor(CoordinatorEntity, SensorEntity):
    """Sensor for upcoming tasks."""

    def __init__(
        self,
        coordinator: TodoistDataUpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._attr_name = "Todoist Upcoming Tasks"
        self._attr_unique_id = f"{config_entry.entry_id}_upcoming_tasks"
        self._attr_icon = "mdi:calendar-clock"
        self._attr_native_unit_of_measurement = "tasks"

    @property
    def native_value(self) -> int:
        """Return the number of upcoming tasks."""
        if hasattr(self.coordinator, '_tasks') and self.coordinator.client:
            try:
                upcoming_tasks = self.coordinator.client.filter_tasks_by_date(
                    self.coordinator.tasks, "upcoming"
                )
                return len(upcoming_tasks)
            except Exception:
                pass
        return 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        if hasattr(self.coordinator, '_tasks') and self.coordinator.client:
            try:
                upcoming_tasks = self.coordinator.client.filter_tasks_by_date(
                    self.coordinator.tasks, "upcoming"
                )
                return {
                    "tasks": [
                        {
                            "id": task["id"],
                            "content": task["content"],
                            "priority": task.get("priority", 1),
                            "project_id": task.get("project_id"),
                            "due": task.get("due", {}).get("date") if task.get("due") else None,
                        }
                        for task in upcoming_tasks[:10]  # Limit to first 10 tasks
                    ],
                    "total_count": len(upcoming_tasks),
                }
            except Exception:
                pass
        return {"tasks": [], "total_count": 0}


class TodoistTasksDueTomorrowSensor(CoordinatorEntity, SensorEntity):
    """Sensor for tasks due tomorrow."""

    def __init__(
        self,
        coordinator: TodoistDataUpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._attr_name = "Todoist Tasks Due Tomorrow"
        self._attr_unique_id = f"{config_entry.entry_id}_tasks_due_tomorrow"
        self._attr_icon = "mdi:calendar-plus"
        self._attr_native_unit_of_measurement = "tasks"

    @property
    def native_value(self) -> int:
        """Return the number of tasks due tomorrow."""
        return self.coordinator.task_summary.get("due_tomorrow", 0)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        if hasattr(self.coordinator, '_tasks') and self.coordinator.client:
            try:
                tasks_tomorrow = self.coordinator.client.filter_tasks_by_date(
                    self.coordinator.tasks, "tomorrow"
                )
                return {
                    "tasks": [
                        {
                            "id": task["id"],
                            "content": task["content"],
                            "priority": task.get("priority", 1),
                            "project_id": task.get("project_id"),
                            "due": task.get("due", {}).get("date") if task.get("due") else None,
                        }
                        for task in tasks_tomorrow[:10]  # Limit to first 10 tasks
                    ],
                    "total_count": len(tasks_tomorrow),
                }
            except Exception:
                pass
        return {"tasks": [], "total_count": 0}


class TodoistTasksThisWeekSensor(CoordinatorEntity, SensorEntity):
    """Sensor for tasks due this week."""

    def __init__(
        self,
        coordinator: TodoistDataUpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._attr_name = "Todoist Tasks This Week"
        self._attr_unique_id = f"{config_entry.entry_id}_tasks_this_week"
        self._attr_icon = "mdi:calendar-week"
        self._attr_native_unit_of_measurement = "tasks"

    @property
    def native_value(self) -> int:
        """Return the number of tasks due this week."""
        if hasattr(self.coordinator, '_tasks') and self.coordinator.client:
            try:
                tasks_this_week = self.coordinator.client.filter_tasks_by_date(
                    self.coordinator.tasks, "this_week"
                )
                return len(tasks_this_week)
            except Exception:
                pass
        return 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        if hasattr(self.coordinator, '_tasks') and self.coordinator.client:
            try:
                tasks_this_week = self.coordinator.client.filter_tasks_by_date(
                    self.coordinator.tasks, "this_week"
                )
                return {
                    "task_count": len(tasks_this_week),
                    "by_day": {},  # Could be expanded to group by day
                }
            except Exception:
                pass
        return {"task_count": 0, "by_day": {}}


class TodoistHighPriorityTasksSensor(CoordinatorEntity, SensorEntity):
    """Sensor for high priority tasks."""

    def __init__(
        self,
        coordinator: TodoistDataUpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._attr_name = "Todoist High Priority Tasks"
        self._attr_unique_id = f"{config_entry.entry_id}_high_priority_tasks"
        self._attr_icon = "mdi:priority-high"
        self._attr_native_unit_of_measurement = "tasks"

    @property
    def native_value(self) -> int:
        """Return the number of high priority tasks."""
        summary = self.coordinator.task_summary
        by_priority = summary.get("by_priority", {})
        return by_priority.get(1, 0) + by_priority.get(2, 0)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        summary = self.coordinator.task_summary
        by_priority = summary.get("by_priority", {})
        return {
            "priority_1_urgent": by_priority.get(1, 0),
            "priority_2_high": by_priority.get(2, 0),
            "priority_3_medium": by_priority.get(3, 0),
            "priority_4_low": by_priority.get(4, 0),
        }


class TodoistTaskSummarySensor(CoordinatorEntity, SensorEntity):
    """Sensor providing overall task summary."""

    def __init__(
        self,
        coordinator: TodoistDataUpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._attr_name = "Todoist Task Summary"
        self._attr_unique_id = f"{config_entry.entry_id}_task_summary"
        self._attr_icon = "mdi:chart-pie"

    @property
    def native_value(self) -> str:
        """Return summary as text."""
        summary = self.coordinator.task_summary
        overdue = summary.get("overdue", 0)
        due_today = summary.get("due_today", 0)
        total = summary.get("total", 0)
        
        if overdue > 0:
            return f"{overdue} overdue, {due_today} today"
        elif due_today > 0:
            return f"{due_today} due today"
        elif total > 0:
            return f"{total} total tasks"
        else:
            return "No tasks"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the full task summary."""
        summary = self.coordinator.task_summary
        task_counts_by_project = self.coordinator.get_task_counts_by_project()
        
        return {
            **summary,
            "by_project": task_counts_by_project,
            "needs_attention": summary.get("overdue", 0) > 0,
            "productivity_score": max(0, 100 - (summary.get("overdue", 0) * 10)),
        }


class TodoistNextTaskSensor(CoordinatorEntity, SensorEntity):
    """Sensor for the next most important task."""

    def __init__(
        self,
        coordinator: TodoistDataUpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._attr_name = "Todoist Next Task"
        self._attr_unique_id = f"{config_entry.entry_id}_next_task"
        self._attr_icon = "mdi:clock-alert"

    @property
    def native_value(self) -> str:
        """Return the next most important task."""
        if not hasattr(self.coordinator, '_tasks') or not self.coordinator.client:
            return "No tasks"
            
        try:
            # Priority order: overdue P1, overdue P2, today P1, today P2, etc.
            overdue_tasks = self.coordinator.client.filter_tasks_by_date(
                self.coordinator.tasks, "overdue"
            )
            today_tasks = self.coordinator.client.filter_tasks_by_date(
                self.coordinator.tasks, "today"
            )
            
            # Find highest priority overdue task
            for priority in [1, 2, 3, 4]:
                for task in overdue_tasks:
                    if task.get("priority", 1) == priority:
                        return task["content"]
            
            # Find highest priority task due today
            for priority in [1, 2, 3, 4]:
                for task in today_tasks:
                    if task.get("priority", 1) == priority:
                        return task["content"]
            
            # If no overdue or today tasks, get next upcoming task
            upcoming_tasks = self.coordinator.client.filter_tasks_by_date(
                self.coordinator.tasks, "upcoming"
            )
            if upcoming_tasks:
                return upcoming_tasks[0]["content"]
                
        except Exception:
            pass
            
        return "No tasks"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes for the next task."""
        if not hasattr(self.coordinator, '_tasks') or not self.coordinator.client:
            return {}
            
        try:
            # Find the same task we returned in native_value
            overdue_tasks = self.coordinator.client.filter_tasks_by_date(
                self.coordinator.tasks, "overdue"
            )
            today_tasks = self.coordinator.client.filter_tasks_by_date(
                self.coordinator.tasks, "today"
            )
            
            # Check overdue tasks first
            for priority in [1, 2, 3, 4]:
                for task in overdue_tasks:
                    if task.get("priority", 1) == priority:
                        return {
                            "task_id": task["id"],
                            "content": task["content"],
                            "priority": task.get("priority", 1),
                            "due_date": task.get("due", {}).get("date") if task.get("due") else None,
                            "project_id": task.get("project_id"),
                            "is_overdue": True,
                            "urgency_level": "overdue",
                        }
            
            # Check today tasks
            for priority in [1, 2, 3, 4]:
                for task in today_tasks:
                    if task.get("priority", 1) == priority:
                        return {
                            "task_id": task["id"],
                            "content": task["content"],
                            "priority": task.get("priority", 1),
                            "due_date": task.get("due", {}).get("date") if task.get("due") else None,
                            "project_id": task.get("project_id"),
                            "is_overdue": False,
                            "urgency_level": "today",
                        }
            
            # Check upcoming tasks
            upcoming_tasks = self.coordinator.client.filter_tasks_by_date(
                self.coordinator.tasks, "upcoming"
            )
            if upcoming_tasks:
                task = upcoming_tasks[0]
                return {
                    "task_id": task["id"],
                    "content": task["content"],
                    "priority": task.get("priority", 1),
                    "due_date": task.get("due", {}).get("date") if task.get("due") else None,
                    "project_id": task.get("project_id"),
                    "is_overdue": False,
                    "urgency_level": "upcoming",
                }
                
        except Exception:
            pass
            
        return {}