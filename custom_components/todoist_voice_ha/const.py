"""Constants for the Todoist Voice HA Integration."""
from __future__ import annotations

from typing import Final

# Integration domain
DOMAIN: Final = "todoist_voice_ha"

# Configuration constants
CONF_API_TOKEN: Final = "api_token"
CONF_AUTO_CREATE_ENTITIES: Final = "auto_create_entities"
CONF_CONVERSATION_TIMEOUT: Final = "conversation_timeout"
CONF_DEFAULT_PROJECT: Final = "default_project"
CONF_UPDATE_INTERVAL: Final = "update_interval"

# Default values
DEFAULT_UPDATE_INTERVAL: Final = 300  # 5 minutes
DEFAULT_CONVERSATION_TIMEOUT: Final = 300  # 5 minutes
DEFAULT_PROJECT_NAME: Final = "Inbox"
DEFAULT_PRIORITY: Final = 3
DEFAULT_LABELS: Final = ["voice", "ha"]

# Todoist API constants
TODOIST_API_BASE: Final = "https://api.todoist.com/rest/v2"
TODOIST_API_TIMEOUT: Final = 10

# Entity configurations for auto-creation
REQUIRED_ENTITIES: Final = {
    "input_boolean": {
        "conversation_active": {
            "name": "Conversation Active",
            "icon": "mdi:chat-processing",
            "initial": False,
        },
        "awaiting_project_selection": {
            "name": "Awaiting Project Selection",
            "icon": "mdi:folder-question",
            "initial": False,
        },
        "awaiting_project_creation": {
            "name": "Awaiting Project Creation",
            "icon": "mdi:folder-plus",
            "initial": False,
        },
        "awaiting_date_input": {
            "name": "Awaiting Date Input",
            "icon": "mdi:calendar-question",
            "initial": False,
        },
        "awaiting_final_confirmation": {
            "name": "Awaiting Final Confirmation",
            "icon": "mdi:check-circle-outline",
            "initial": False,
        },
    },
    "input_text": {
        "conversation_id": {
            "name": "Current Conversation ID",
            "max": 50,
            "icon": "mdi:chat-processing",
        },
        "conversation_state": {
            "name": "Conversation State",
            "max": 50,
            "initial": "idle",
            "icon": "mdi:state-machine",
        },
        "input_buffer": {
            "name": "Voice Input Buffer",
            "max": 2000,
            "icon": "mdi:microphone-message",
        },
        "parsed_actions": {
            "name": "Parsed Task Actions",
            "max": 1000,
            "icon": "mdi:format-list-bulleted",
        },
        "project_matches": {
            "name": "Found Project Matches",
            "max": 500,
            "icon": "mdi:folder-search",
        },
        "selected_project": {
            "name": "Selected Project",
            "max": 100,
            "icon": "mdi:folder-check",
        },
        "pending_due_date": {
            "name": "Pending Due Date",
            "max": 50,
            "icon": "mdi:calendar-clock",
        },
        "task_priority": {
            "name": "Task Priority",
            "max": 10,
            "initial": "3",
            "icon": "mdi:priority-high",
        },
        "conversation_context": {
            "name": "Conversation Context (JSON)",
            "max": 2000,
            "initial": "{}",
            "icon": "mdi:code-json",
        },
    },
    "input_select": {
        "available_projects": {
            "name": "Available Todoist Projects",
            "options": ["Loading..."],
            "initial": "Loading...",
            "icon": "mdi:folder-multiple",
        }
    },
    "input_number": {
        "conversation_timeout": {
            "name": "Conversation Timeout (seconds)",
            "min": 30,
            "max": 600,
            "step": 30,
            "initial": 300,
            "icon": "mdi:timer-outline",
            "unit_of_measurement": "s",
        }
    },
}

# Conversation states
CONVERSATION_STATES: Final = {
    "idle": "Idle",
    "listening": "Listening",
    "processing": "Processing",
    "project_selection": "Project Selection",
    "project_creation": "Project Creation",
    "date_input": "Date Input",
    "confirmation": "Confirmation",
    "creating_task": "Creating Task",
    "completed": "Completed",
    "error": "Error",
}

# Priority levels
PRIORITY_LEVELS: Final = {
    1: "Very High",
    2: "High", 
    3: "Medium",
    4: "Low",
}

# Date parsing patterns
DATE_PATTERNS: Final = {
    "today": 0,
    "tomorrow": 1,
    "this week": 7,
    "next week": 14,
}

# Action extraction patterns
ACTION_PATTERNS: Final = [
    r"(?:^|\n)\s*[-*•]\s*(.+?)(?=\n|$)",
    r"(?:^|\n)\s*\d+\.\s*(.+?)(?=\n|$)",
    r"(?:^|\n)\s*(?:TODO|Action|Task|Step)\s*:?\s*(.+?)(?=\n|$)",
    r"(?:^|\n)\s*(?:Create|Build|Setup|Configure|Install|Update|Review|Analyze|Implement|Add|Remove|Fix|Test|Deploy|Write|Design|Plan|Research|Contact|Schedule|Book|Buy|Order|Call|Email|Send|Upload|Download|Backup|Delete|Archive|Organize|Clean|Prepare|Check|Verify|Validate|Monitor|Track|Document|Record|Report|Submit|Approve|Reject|Complete|Finish|Start|Begin|Launch|Stop|Pause|Resume|Cancel|Postpone|Reschedule)\s+(.+?)(?=\n|$)",
]

# Error messages
ERROR_MESSAGES: Final = {
    "no_token": "Todoist API token is required",
    "invalid_token": "Invalid Todoist API token",
    "no_projects": "No projects found",
    "project_not_found": "Project not found",
    "no_actions": "No actions found in text",
    "api_error": "Todoist API error",
    "network_error": "Network connection error",
    "timeout_error": "Request timeout",
    "conversation_timeout": "Conversation timeout",
}