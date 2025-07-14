"""Services for the Todoist Voice HA integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.service import async_register_admin_service

from .const import (
    DOMAIN,
    CONF_API_TOKEN,
    DEFAULT_PRIORITY,
    DEFAULT_LABELS,
    ERROR_MESSAGES,
)
from .coordinator import TodoistDataUpdateCoordinator
from .conversation_engine import ConversationEngine

_LOGGER = logging.getLogger(__name__)

# Service schemas
CREATE_TASK_SCHEMA = vol.Schema(
    {
        vol.Required("text"): cv.string,
        vol.Optional("project_name"): cv.string,
        vol.Optional("project_id"): cv.string,
        vol.Optional("priority", default=DEFAULT_PRIORITY): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=4)
        ),
        vol.Optional("due_date"): cv.string,
        vol.Optional("labels", default=DEFAULT_LABELS): vol.All(
            cv.ensure_list, [cv.string]
        ),
        vol.Optional("main_task_title"): cv.string,
        vol.Optional("conversation_id"): cv.string,
    }
)

FIND_PROJECTS_SCHEMA = vol.Schema(
    {
        vol.Required("query"): cv.string,
        vol.Optional("max_results", default=5): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=20)
        ),
    }
)

CREATE_PROJECT_SCHEMA = vol.Schema(
    {
        vol.Required("name"): cv.string,
        vol.Optional("color"): cv.string,
        vol.Optional("parent_id"): cv.string,
        vol.Optional("is_favorite", default=False): cv.boolean,
    }
)

PARSE_VOICE_INPUT_SCHEMA = vol.Schema(
    {
        vol.Required("text"): cv.string,
        vol.Optional("context", default={}): dict,
    }
)

VALIDATE_DATE_SCHEMA = vol.Schema(
    {
        vol.Required("date_input"): cv.string,
        vol.Optional("context"): cv.string,
    }
)

START_CONVERSATION_SCHEMA = vol.Schema(
    {
        vol.Required("text"): cv.string,
        vol.Optional("context", default={}): dict,
        vol.Optional("timeout", default=300): vol.All(
            vol.Coerce(int), vol.Range(min=30, max=600)
        ),
    }
)

CONTINUE_CONVERSATION_SCHEMA = vol.Schema(
    {
        vol.Required("conversation_id"): cv.string,
        vol.Required("text"): cv.string,
        vol.Optional("context", default={}): dict,
    }
)

CONVERSATION_STATUS_SCHEMA = vol.Schema(
    {
        vol.Required("conversation_id"): cv.string,
    }
)


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for the integration."""
    
    def get_coordinator() -> TodoistDataUpdateCoordinator:
        """Get the first available coordinator."""
        for entry_id, data in hass.data.get(DOMAIN, {}).items():
            if "coordinator" in data:
                return data["coordinator"]
        raise HomeAssistantError("No Todoist Voice HA integration configured")
    
    def get_conversation_engine() -> ConversationEngine:
        """Get or create conversation engine."""
        coordinator = get_coordinator()
        
        # Store conversation engine in domain data
        if "conversation_engine" not in hass.data.get(DOMAIN, {}):
            hass.data[DOMAIN]["conversation_engine"] = ConversationEngine(hass, coordinator)
        
        return hass.data[DOMAIN]["conversation_engine"]

    async def async_create_task(call: ServiceCall) -> None:
        """Create a task via the coordinator."""
        coordinator = get_coordinator()
        
        try:
            # Extract parameters
            text = call.data["text"]
            project_name = call.data.get("project_name")
            project_id = call.data.get("project_id")
            priority = call.data.get("priority", DEFAULT_PRIORITY)
            due_date = call.data.get("due_date")
            labels = call.data.get("labels", DEFAULT_LABELS)
            main_task_title = call.data.get("main_task_title")
            conversation_id = call.data.get("conversation_id")

            # Resolve project
            if project_id:
                project = await coordinator.get_project_by_id(project_id)
                if not project:
                    raise HomeAssistantError(f"Project with ID {project_id} not found")
            elif project_name:
                project = await coordinator.get_project_by_name(project_name)
                if not project:
                    raise HomeAssistantError(f"Project '{project_name}' not found")
            else:
                # Use default project (Inbox)
                project = await coordinator.get_project_by_name("Inbox")
                if not project:
                    # Get first available project
                    projects = coordinator.projects
                    if not projects:
                        raise HomeAssistantError("No projects available")
                    project = projects[0]

            # Parse due date
            parsed_due_date = None
            if due_date:
                parsed_due_date = coordinator.parse_due_date(due_date)

            # Add conversation ID to labels if provided
            if conversation_id:
                labels = labels + [f"conversation-{conversation_id}"]

            # Create task
            result = await coordinator.export_to_todoist(
                text=text,
                project_id=project["id"],
                main_task_title=main_task_title,
                priority=priority,
                due_date=parsed_due_date,
                labels=labels,
            )

            _LOGGER.info("Task created successfully: %s", result.get("summary"))
            
            # Fire event
            hass.bus.async_fire(
                f"{DOMAIN}_task_created",
                {
                    "project_name": project["name"],
                    "task_count": result["summary"]["successful"],
                    "main_task_id": result["main_task"]["id"],
                    "conversation_id": conversation_id,
                },
            )

        except Exception as err:
            _LOGGER.error("Failed to create task: %s", err)
            raise HomeAssistantError(f"Failed to create task: {err}") from err

    async def async_find_projects(call: ServiceCall) -> None:
        """Find matching projects."""
        coordinator = get_coordinator()
        
        try:
            query = call.data["query"]
            max_results = call.data.get("max_results", 5)
            
            matches = await coordinator.find_matching_projects(query)
            
            # Limit results
            limited_matches = matches[:max_results]
            
            _LOGGER.info("Project search completed: %d matches found", len(limited_matches))
            
            # Fire event with results
            hass.bus.async_fire(
                f"{DOMAIN}_projects_found",
                {
                    "query": query,
                    "matches": [
                        {
                            "id": p["id"],
                            "name": p["name"],
                            "match_score": p.get("match_score", 0),
                            "match_reason": p.get("match_reason", "unknown"),
                        }
                        for p in limited_matches
                    ],
                    "match_count": len(limited_matches),
                },
            )

        except Exception as err:
            _LOGGER.error("Failed to find projects: %s", err)
            raise HomeAssistantError(f"Failed to find projects: {err}") from err

    async def async_create_project(call: ServiceCall) -> None:
        """Create a new project."""
        coordinator = get_coordinator()
        
        try:
            name = call.data["name"]
            color = call.data.get("color")
            parent_id = call.data.get("parent_id")
            is_favorite = call.data.get("is_favorite", False)
            
            kwargs = {}
            if color:
                kwargs["color"] = color
            if parent_id:
                kwargs["parent_id"] = parent_id
            if is_favorite:
                kwargs["is_favorite"] = is_favorite
            
            project = await coordinator.create_project(name, **kwargs)
            
            _LOGGER.info("Project created successfully: %s", project["name"])
            
            # Fire event
            hass.bus.async_fire(
                f"{DOMAIN}_project_created",
                {
                    "project_id": project["id"],
                    "project_name": project["name"],
                    "color": project.get("color"),
                    "parent_id": project.get("parent_id"),
                },
            )

        except Exception as err:
            _LOGGER.error("Failed to create project: %s", err)
            raise HomeAssistantError(f"Failed to create project: {err}") from err

    async def async_parse_voice_input(call: ServiceCall) -> None:
        """Parse voice input for actions."""
        coordinator = get_coordinator()
        
        try:
            text = call.data["text"]
            context = call.data.get("context", {})
            
            # Extract actions
            actions = coordinator.extract_actions(text)
            
            # Extract project hints
            project_hints = []
            keywords = ["project", "list", "tasks", "shopping", "work", "home", "personal"]
            for keyword in keywords:
                if keyword in text.lower():
                    project_hints.append(keyword)
            
            # Extract date hints
            date_hints = []
            date_keywords = ["today", "tomorrow", "monday", "tuesday", "wednesday", 
                           "thursday", "friday", "saturday", "sunday", "this week", "next week"]
            for keyword in date_keywords:
                if keyword in text.lower():
                    date_hints.append(keyword)
            
            # Determine priority hints
            priority_hint = DEFAULT_PRIORITY
            if "urgent" in text.lower() or "asap" in text.lower():
                priority_hint = 1
            elif "high priority" in text.lower() or "important" in text.lower():
                priority_hint = 2
            elif "low priority" in text.lower() or "sometime" in text.lower():
                priority_hint = 4
            
            analysis = {
                "original_text": text,
                "extracted_actions": actions,
                "action_count": len(actions),
                "project_hints": project_hints,
                "date_hints": date_hints,
                "priority_hint": priority_hint,
                "has_actions": len(actions) > 0,
                "needs_project_selection": len(project_hints) == 0,
                "needs_date_selection": len(date_hints) == 0,
                "context": context,
            }
            
            _LOGGER.info("Voice input parsed: %d actions found", len(actions))
            
            # Fire event
            hass.bus.async_fire(
                f"{DOMAIN}_voice_input_parsed",
                analysis,
            )

        except Exception as err:
            _LOGGER.error("Failed to parse voice input: %s", err)
            raise HomeAssistantError(f"Failed to parse voice input: {err}") from err

    async def async_validate_date(call: ServiceCall) -> None:
        """Validate date input."""
        coordinator = get_coordinator()
        
        try:
            date_input = call.data["date_input"]
            context = call.data.get("context")
            
            parsed_date = coordinator.parse_due_date(date_input)
            is_valid = parsed_date is not None
            
            human_readable = None
            if is_valid:
                try:
                    from datetime import datetime
                    date_obj = datetime.fromisoformat(parsed_date)
                    human_readable = date_obj.strftime("%Y-%m-%d")
                except ValueError:
                    human_readable = parsed_date
            
            result = {
                "original_input": date_input,
                "parsed_date": parsed_date,
                "is_valid": is_valid,
                "human_readable": human_readable,
                "context": context,
            }
            
            _LOGGER.info("Date validation completed: %s -> %s", date_input, parsed_date)
            
            # Fire event
            hass.bus.async_fire(
                f"{DOMAIN}_date_validated",
                result,
            )

        except Exception as err:
            _LOGGER.error("Failed to validate date: %s", err)
            raise HomeAssistantError(f"Failed to validate date: {err}") from err

    async def async_refresh_projects(call: ServiceCall) -> None:
        """Refresh project cache."""
        coordinator = get_coordinator()
        
        try:
            await coordinator.async_request_refresh()
            
            project_count = len(coordinator.projects)
            project_names = [p["name"] for p in coordinator.projects]
            
            _LOGGER.info("Projects refreshed: %d projects loaded", project_count)
            
            # Fire event
            hass.bus.async_fire(
                f"{DOMAIN}_projects_refreshed",
                {
                    "project_count": project_count,
                    "project_names": project_names,
                    "last_updated": coordinator.last_update_success.isoformat() if coordinator.last_update_success else None,
                },
            )

        except Exception as err:
            _LOGGER.error("Failed to refresh projects: %s", err)
            raise HomeAssistantError(f"Failed to refresh projects: {err}") from err

    async def async_start_conversation(call: ServiceCall) -> None:
        """Start a conversation."""
        conversation_engine = get_conversation_engine()
        
        try:
            text = call.data["text"]
            context = call.data.get("context", {})
            timeout = call.data.get("timeout", 300)
            
            result = await conversation_engine.start_conversation(text, context, timeout)
            
            _LOGGER.info("Conversation started: %s", result.get("conversation_id"))
            
            # Fire event
            hass.bus.async_fire(
                f"{DOMAIN}_conversation_started",
                result,
            )

        except Exception as err:
            _LOGGER.error("Failed to start conversation: %s", err)
            raise HomeAssistantError(f"Failed to start conversation: {err}") from err

    async def async_continue_conversation(call: ServiceCall) -> None:
        """Continue a conversation."""
        conversation_engine = get_conversation_engine()
        
        try:
            conversation_id = call.data["conversation_id"]
            text = call.data["text"]
            context = call.data.get("context", {})
            
            result = await conversation_engine.continue_conversation(conversation_id, text, context)
            
            _LOGGER.info("Conversation continued: %s", conversation_id)
            
            # Fire event
            hass.bus.async_fire(
                f"{DOMAIN}_conversation_continued",
                result,
            )

        except Exception as err:
            _LOGGER.error("Failed to continue conversation: %s", err)
            raise HomeAssistantError(f"Failed to continue conversation: {err}") from err

    async def async_get_conversation_status(call: ServiceCall) -> None:
        """Get conversation status."""
        conversation_engine = get_conversation_engine()
        
        try:
            conversation_id = call.data["conversation_id"]
            
            result = await conversation_engine.get_conversation_status(conversation_id)
            
            _LOGGER.debug("Conversation status retrieved: %s", conversation_id)
            
            # Fire event
            hass.bus.async_fire(
                f"{DOMAIN}_conversation_status",
                result,
            )

        except Exception as err:
            _LOGGER.error("Failed to get conversation status: %s", err)
            raise HomeAssistantError(f"Failed to get conversation status: {err}") from err

    # Register services
    hass.services.async_register(
        DOMAIN, "create_task", async_create_task, schema=CREATE_TASK_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN, "find_projects", async_find_projects, schema=FIND_PROJECTS_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN, "create_project", async_create_project, schema=CREATE_PROJECT_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN, "parse_voice_input", async_parse_voice_input, schema=PARSE_VOICE_INPUT_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN, "validate_date", async_validate_date, schema=VALIDATE_DATE_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN, "refresh_projects", async_refresh_projects
    )
    
    hass.services.async_register(
        DOMAIN, "start_conversation", async_start_conversation, schema=START_CONVERSATION_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN, "continue_conversation", async_continue_conversation, schema=CONTINUE_CONVERSATION_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN, "get_conversation_status", async_get_conversation_status, schema=CONVERSATION_STATUS_SCHEMA
    )

    _LOGGER.info("Todoist Voice HA services registered successfully")


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload services."""
    services = [
        "create_task",
        "find_projects",
        "create_project",
        "parse_voice_input",
        "validate_date",
        "refresh_projects",
        "start_conversation",
        "continue_conversation",
        "get_conversation_status",
    ]
    
    for service in services:
        hass.services.async_remove(DOMAIN, service)
    
    # Clean up conversation engine
    if DOMAIN in hass.data and "conversation_engine" in hass.data[DOMAIN]:
        conversation_engine = hass.data[DOMAIN]["conversation_engine"]
        await conversation_engine.cleanup_expired_conversations()
        del hass.data[DOMAIN]["conversation_engine"]
    
    _LOGGER.info("Todoist Voice HA services unloaded successfully")