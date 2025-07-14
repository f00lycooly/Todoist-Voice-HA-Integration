"""Conversation engine for processing voice input and managing conversation state."""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    CONVERSATION_STATES,
    PRIORITY_LEVELS,
    DEFAULT_PRIORITY,
    DEFAULT_LABELS,
    ERROR_MESSAGES,
)
from .coordinator import TodoistDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class ConversationEngine:
    """Engine for managing conversational task creation flow."""

    def __init__(self, hass: HomeAssistant, coordinator: TodoistDataUpdateCoordinator) -> None:
        """Initialize the conversation engine."""
        self.hass = hass
        self.coordinator = coordinator
        self._active_conversations: dict[str, ConversationContext] = {}

    async def start_conversation(
        self,
        text: str,
        context: dict[str, Any] | None = None,
        timeout: int = 300,
    ) -> dict[str, Any]:
        """Start a new conversation."""
        conversation_id = str(uuid.uuid4())
        
        # Create conversation context
        conversation_context = ConversationContext(
            conversation_id=conversation_id,
            hass=self.hass,
            coordinator=self.coordinator,
            timeout=timeout,
            initial_context=context or {},
        )
        
        # Store the conversation
        self._active_conversations[conversation_id] = conversation_context
        
        # Process the initial input
        result = await conversation_context.process_input(text)
        
        # Update Home Assistant entities
        await self._update_ha_entities(conversation_context)
        
        return {
            "conversation_id": conversation_id,
            "state": conversation_context.state,
            **result,
        }

    async def continue_conversation(
        self,
        conversation_id: str,
        text: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Continue an existing conversation."""
        conversation_context = self._active_conversations.get(conversation_id)
        
        if not conversation_context:
            raise HomeAssistantError(f"Conversation {conversation_id} not found")
        
        if conversation_context.is_expired():
            await self._cleanup_conversation(conversation_id)
            raise HomeAssistantError(ERROR_MESSAGES["conversation_timeout"])
        
        # Update context if provided
        if context:
            conversation_context.update_context(context)
        
        # Process the input
        result = await conversation_context.process_input(text)
        
        # Update Home Assistant entities
        await self._update_ha_entities(conversation_context)
        
        # Clean up if conversation is complete
        if conversation_context.state in ["completed", "error"]:
            await self._cleanup_conversation(conversation_id)
        
        return {
            "conversation_id": conversation_id,
            "state": conversation_context.state,
            **result,
        }

    async def get_conversation_status(self, conversation_id: str) -> dict[str, Any]:
        """Get the status of a conversation."""
        conversation_context = self._active_conversations.get(conversation_id)
        
        if not conversation_context:
            return {"exists": False, "error": "Conversation not found"}
        
        return {
            "exists": True,
            "conversation_id": conversation_id,
            "state": conversation_context.state,
            "created_at": conversation_context.created_at.isoformat(),
            "expires_at": conversation_context.expires_at.isoformat(),
            "is_expired": conversation_context.is_expired(),
            "context": conversation_context.get_public_context(),
        }

    async def cleanup_expired_conversations(self) -> None:
        """Clean up expired conversations."""
        expired_ids = [
            conv_id
            for conv_id, conv in self._active_conversations.items()
            if conv.is_expired()
        ]
        
        for conv_id in expired_ids:
            await self._cleanup_conversation(conv_id)

    async def _cleanup_conversation(self, conversation_id: str) -> None:
        """Clean up a conversation."""
        conversation_context = self._active_conversations.pop(conversation_id, None)
        
        if conversation_context:
            # Reset Home Assistant entities
            await self._reset_ha_entities()
            _LOGGER.debug("Cleaned up conversation %s", conversation_id)

    async def _update_ha_entities(self, context: ConversationContext) -> None:
        """Update Home Assistant entities with conversation state."""
        try:
            # Update conversation state entities
            await self.hass.services.async_call(
                "input_text",
                "set_value",
                {
                    "entity_id": "input_text.todoist_voice_ha_conversation_id",
                    "value": context.conversation_id,
                },
                blocking=False,
            )
            
            await self.hass.services.async_call(
                "input_text",
                "set_value",
                {
                    "entity_id": "input_text.todoist_voice_ha_conversation_state",
                    "value": context.state,
                },
                blocking=False,
            )
            
            # Update context data
            context_json = json.dumps(context.get_public_context())
            await self.hass.services.async_call(
                "input_text",
                "set_value",
                {
                    "entity_id": "input_text.todoist_voice_ha_conversation_context",
                    "value": context_json,
                },
                blocking=False,
            )
            
            # Update state-specific entities
            if context.parsed_actions:
                actions_text = "\n".join(context.parsed_actions)
                await self.hass.services.async_call(
                    "input_text",
                    "set_value",
                    {
                        "entity_id": "input_text.todoist_voice_ha_parsed_actions",
                        "value": actions_text,
                    },
                    blocking=False,
                )
            
            if context.project_matches:
                matches_text = "\n".join([f"{p['name']} ({p['match_score']})" for p in context.project_matches])
                await self.hass.services.async_call(
                    "input_text",
                    "set_value",
                    {
                        "entity_id": "input_text.todoist_voice_ha_project_matches",
                        "value": matches_text,
                    },
                    blocking=False,
                )
            
            # Update boolean states
            state_booleans = {
                "input_boolean.todoist_voice_ha_conversation_active": context.state != "idle",
                "input_boolean.todoist_voice_ha_awaiting_project_selection": context.state == "project_selection",
                "input_boolean.todoist_voice_ha_awaiting_project_creation": context.state == "project_creation",
                "input_boolean.todoist_voice_ha_awaiting_date_input": context.state == "date_input",
                "input_boolean.todoist_voice_ha_awaiting_final_confirmation": context.state == "confirmation",
            }
            
            for entity_id, state in state_booleans.items():
                service = "turn_on" if state else "turn_off"
                await self.hass.services.async_call(
                    "input_boolean",
                    service,
                    {"entity_id": entity_id},
                    blocking=False,
                )
                
        except Exception as err:
            _LOGGER.warning("Failed to update HA entities: %s", err)

    async def _reset_ha_entities(self) -> None:
        """Reset Home Assistant entities to default state."""
        try:
            # Reset text entities
            text_resets = {
                "input_text.todoist_voice_ha_conversation_id": "",
                "input_text.todoist_voice_ha_conversation_state": "idle",
                "input_text.todoist_voice_ha_input_buffer": "",
                "input_text.todoist_voice_ha_parsed_actions": "",
                "input_text.todoist_voice_ha_project_matches": "",
                "input_text.todoist_voice_ha_selected_project": "",
                "input_text.todoist_voice_ha_pending_due_date": "",
                "input_text.todoist_voice_ha_task_priority": "3",
                "input_text.todoist_voice_ha_conversation_context": "{}",
            }
            
            for entity_id, value in text_resets.items():
                await self.hass.services.async_call(
                    "input_text",
                    "set_value",
                    {"entity_id": entity_id, "value": value},
                    blocking=False,
                )
            
            # Reset boolean entities
            boolean_entities = [
                "input_boolean.todoist_voice_ha_conversation_active",
                "input_boolean.todoist_voice_ha_awaiting_project_selection",
                "input_boolean.todoist_voice_ha_awaiting_project_creation",
                "input_boolean.todoist_voice_ha_awaiting_date_input",
                "input_boolean.todoist_voice_ha_awaiting_final_confirmation",
            ]
            
            for entity_id in boolean_entities:
                await self.hass.services.async_call(
                    "input_boolean",
                    "turn_off",
                    {"entity_id": entity_id},
                    blocking=False,
                )
                
        except Exception as err:
            _LOGGER.warning("Failed to reset HA entities: %s", err)


class ConversationContext:
    """Context for managing a single conversation."""

    def __init__(
        self,
        conversation_id: str,
        hass: HomeAssistant,
        coordinator: TodoistDataUpdateCoordinator,
        timeout: int = 300,
        initial_context: dict[str, Any] | None = None,
    ) -> None:
        """Initialize conversation context."""
        self.conversation_id = conversation_id
        self.hass = hass
        self.coordinator = coordinator
        self.timeout = timeout
        self.created_at = dt_util.utcnow()
        self.expires_at = self.created_at + timedelta(seconds=timeout)
        
        # Conversation state
        self.state = "idle"
        self.original_text = ""
        self.parsed_actions: list[str] = []
        self.project_matches: list[dict[str, Any]] = []
        self.selected_project: dict[str, Any] | None = None
        self.pending_due_date: str | None = None
        self.task_priority = DEFAULT_PRIORITY
        self.labels = DEFAULT_LABELS.copy()
        
        # Additional context
        self.context = initial_context or {}
        self.error_message: str | None = None
        self.last_input = ""

    def is_expired(self) -> bool:
        """Check if conversation has expired."""
        return dt_util.utcnow() > self.expires_at

    def update_context(self, context: dict[str, Any]) -> None:
        """Update conversation context."""
        self.context.update(context)

    def get_public_context(self) -> dict[str, Any]:
        """Get public context for display."""
        return {
            "conversation_id": self.conversation_id,
            "state": self.state,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "original_text": self.original_text,
            "parsed_actions_count": len(self.parsed_actions),
            "project_matches_count": len(self.project_matches),
            "selected_project": self.selected_project["name"] if self.selected_project else None,
            "pending_due_date": self.pending_due_date,
            "task_priority": self.task_priority,
            "labels": self.labels,
            "error_message": self.error_message,
        }

    async def process_input(self, text: str) -> dict[str, Any]:
        """Process input based on current state."""
        self.last_input = text
        
        try:
            if self.state == "idle":
                return await self._process_initial_input(text)
            elif self.state == "project_selection":
                return await self._process_project_selection(text)
            elif self.state == "project_creation":
                return await self._process_project_creation(text)
            elif self.state == "date_input":
                return await self._process_date_input(text)
            elif self.state == "confirmation":
                return await self._process_confirmation(text)
            else:
                self.state = "error"
                self.error_message = f"Unknown state: {self.state}"
                return {"error": self.error_message}
                
        except Exception as err:
            _LOGGER.error("Error processing input: %s", err)
            self.state = "error"
            self.error_message = str(err)
            return {"error": self.error_message}

    async def _process_initial_input(self, text: str) -> dict[str, Any]:
        """Process the initial voice input."""
        self.original_text = text
        self.state = "processing"
        
        # Extract actions from text
        self.parsed_actions = self.coordinator.extract_actions(text)
        
        if not self.parsed_actions:
            self.state = "error"
            self.error_message = ERROR_MESSAGES["no_actions"]
            return {"error": self.error_message}
        
        # Try to find matching projects
        project_hints = self._extract_project_hints(text)
        if project_hints:
            self.project_matches = await self.coordinator.find_matching_projects(project_hints[0])
        
        if not self.project_matches:
            # No project matches, ask for project selection
            self.state = "project_selection"
            return {
                "message": f"Found {len(self.parsed_actions)} actions. Which project should I use?",
                "actions": self.parsed_actions,
                "available_projects": [p["name"] for p in self.coordinator.projects],
            }
        elif len(self.project_matches) == 1:
            # Single match, use it
            self.selected_project = self.project_matches[0]
            return await self._process_date_extraction(text)
        else:
            # Multiple matches, ask for clarification
            self.state = "project_selection"
            return {
                "message": f"Found {len(self.parsed_actions)} actions. Found multiple project matches:",
                "actions": self.parsed_actions,
                "project_matches": [{"name": p["name"], "score": p["match_score"]} for p in self.project_matches],
            }

    async def _process_project_selection(self, text: str) -> dict[str, Any]:
        """Process project selection."""
        # Try to find the selected project
        selected_project = None
        
        # Check if it's a direct project name
        for project in self.coordinator.projects:
            if project["name"].lower() == text.lower():
                selected_project = project
                break
        
        # Check if it's one of the suggested matches
        if not selected_project:
            for match in self.project_matches:
                if match["name"].lower() == text.lower():
                    selected_project = match
                    break
        
        # Check if user wants to create a new project
        if not selected_project and text.lower().startswith("create"):
            project_name = text[6:].strip()  # Remove "create"
            if project_name:
                self.context["new_project_name"] = project_name
                self.state = "project_creation"
                return {
                    "message": f"Create new project '{project_name}'?",
                    "confirm_action": "create_project",
                    "project_name": project_name,
                }
        
        if not selected_project:
            return {
                "error": "Project not found. Please select from available projects or say 'create [project name]'",
                "available_projects": [p["name"] for p in self.coordinator.projects],
            }
        
        self.selected_project = selected_project
        return await self._process_date_extraction(self.original_text)

    async def _process_project_creation(self, text: str) -> dict[str, Any]:
        """Process project creation confirmation."""
        if text.lower() in ["yes", "y", "create", "confirm"]:
            project_name = self.context.get("new_project_name")
            if not project_name:
                self.state = "error"
                self.error_message = "Project name not found"
                return {"error": self.error_message}
            
            try:
                new_project = await self.coordinator.create_project(project_name)
                self.selected_project = new_project
                
                return await self._process_date_extraction(self.original_text)
                
            except Exception as err:
                self.state = "error"
                self.error_message = f"Failed to create project: {err}"
                return {"error": self.error_message}
        
        elif text.lower() in ["no", "n", "cancel", "abort"]:
            self.state = "project_selection"
            return {
                "message": "Project creation cancelled. Which existing project should I use?",
                "available_projects": [p["name"] for p in self.coordinator.projects],
            }
        
        return {
            "error": "Please respond with 'yes' to create the project or 'no' to cancel",
            "confirm_action": "create_project",
            "project_name": self.context.get("new_project_name"),
        }

    async def _process_date_extraction(self, text: str) -> dict[str, Any]:
        """Process date extraction from original text."""
        # Extract date hints from original text
        date_hints = self._extract_date_hints(text)
        
        if date_hints:
            parsed_date = self.coordinator.parse_due_date(date_hints[0])
            if parsed_date:
                self.pending_due_date = parsed_date
                return await self._prepare_confirmation()
        
        # No date found, ask for it
        self.state = "date_input"
        return {
            "message": "When should these tasks be due? (e.g., 'today', 'tomorrow', 'next week', or leave blank for no due date)",
            "actions": self.parsed_actions,
            "project": self.selected_project["name"],
        }

    async def _process_date_input(self, text: str) -> dict[str, Any]:
        """Process date input."""
        if text.lower() in ["none", "no", "skip", "blank", ""]:
            self.pending_due_date = None
        else:
            parsed_date = self.coordinator.parse_due_date(text)
            if not parsed_date:
                return {
                    "error": "Could not parse date. Please try again or say 'none' for no due date",
                    "examples": ["today", "tomorrow", "next week", "2024-01-15", "none"],
                }
            self.pending_due_date = parsed_date
        
        return await self._prepare_confirmation()

    async def _prepare_confirmation(self) -> dict[str, Any]:
        """Prepare final confirmation."""
        self.state = "confirmation"
        
        due_date_str = "No due date"
        if self.pending_due_date:
            try:
                due_date = datetime.fromisoformat(self.pending_due_date)
                due_date_str = due_date.strftime("%Y-%m-%d")
            except ValueError:
                due_date_str = self.pending_due_date
        
        return {
            "message": "Ready to create tasks. Please confirm:",
            "summary": {
                "project": self.selected_project["name"],
                "due_date": due_date_str,
                "priority": PRIORITY_LEVELS.get(self.task_priority, "Medium"),
                "actions": self.parsed_actions,
                "action_count": len(self.parsed_actions),
            },
            "confirm_action": "create_tasks",
        }

    async def _process_confirmation(self, text: str) -> dict[str, Any]:
        """Process final confirmation."""
        if text.lower() in ["yes", "y", "create", "confirm", "do it"]:
            self.state = "creating_task"
            
            try:
                result = await self.coordinator.export_to_todoist(
                    text=self.original_text,
                    project_id=self.selected_project["id"],
                    due_date=self.pending_due_date,
                    priority=self.task_priority,
                    labels=self.labels,
                )
                
                self.state = "completed"
                return {
                    "message": f"Successfully created {result['summary']['successful']} tasks!",
                    "result": result,
                }
                
            except Exception as err:
                self.state = "error"
                self.error_message = f"Failed to create tasks: {err}"
                return {"error": self.error_message}
        
        elif text.lower() in ["no", "n", "cancel", "abort"]:
            self.state = "idle"
            return {"message": "Task creation cancelled"}
        
        return {
            "error": "Please respond with 'yes' to create tasks or 'no' to cancel",
            "confirm_action": "create_tasks",
        }

    def _extract_project_hints(self, text: str) -> list[str]:
        """Extract project hints from text."""
        hints = []
        keywords = ["project", "list", "tasks", "shopping", "work", "home", "personal"]
        
        for keyword in keywords:
            if keyword in text.lower():
                hints.append(keyword)
        
        return hints

    def _extract_date_hints(self, text: str) -> list[str]:
        """Extract date hints from text."""
        hints = []
        keywords = ["today", "tomorrow", "monday", "tuesday", "wednesday", 
                   "thursday", "friday", "saturday", "sunday", "this week", "next week"]
        
        for keyword in keywords:
            if keyword in text.lower():
                hints.append(keyword)
        
        return hints