"""Todoist API client for Home Assistant integration."""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timedelta
from typing import Any

import aiohttp
try:
    from asyncio import timeout  # Python 3.11+
except ImportError:
    from async_timeout import timeout  # Python 3.10 fallback
from dateutil import parser as date_parser

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import (
    TODOIST_API_BASE,
    TODOIST_API_TIMEOUT,
    ERROR_MESSAGES,
    ACTION_PATTERNS,
    DATE_PATTERNS,
    DEFAULT_PRIORITY,
)

_LOGGER = logging.getLogger(__name__)


class TodoistClient:
    """Client for interacting with the Todoist API."""

    def __init__(self, api_token: str, session: aiohttp.ClientSession | None = None) -> None:
        """Initialize the Todoist client."""
        self.api_token = api_token
        self.session = session
        self._own_session = session is None
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
            "User-Agent": "HomeAssistant-TodoistVoiceHA/3.0.0",
        }

    async def __aenter__(self) -> TodoistClient:
        """Async context manager entry."""
        if self._own_session:
            self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        if self._own_session and self.session:
            await self.session.close()

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: dict[str, Any] | None = None,
        timeout: int = TODOIST_API_TIMEOUT,
    ) -> dict[str, Any]:
        """Make an API request."""
        if not self.session:
            raise HomeAssistantError("Session not initialized")

        url = f"{TODOIST_API_BASE}/{endpoint}"
        _LOGGER.debug("Making API request: %s %s", method, url)
        
        try:
            async with timeout(timeout):
                async with self.session.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    json=data,
                ) as response:
                    _LOGGER.debug("API response status: %s", response.status)
                    
                    # Handle different response types
                    content_type = response.headers.get('content-type', '')
                    if 'application/json' in content_type:
                        response_data = await response.json()
                    else:
                        response_text = await response.text()
                        _LOGGER.error("Unexpected content type: %s, body: %s", content_type, response_text)
                        raise HomeAssistantError(f"Invalid response format: {content_type}")
                    
                    if response.status == 401:
                        _LOGGER.error("Invalid API token - HTTP 401")
                        raise HomeAssistantError(ERROR_MESSAGES["invalid_token"])
                    elif response.status == 403:
                        _LOGGER.error("Forbidden access - HTTP 403")
                        raise HomeAssistantError(ERROR_MESSAGES["invalid_token"])
                    elif response.status >= 400:
                        error_msg = response_data.get("error", f"HTTP {response.status}")
                        _LOGGER.error("API error %s: %s", response.status, error_msg)
                        raise HomeAssistantError(f"{ERROR_MESSAGES['api_error']}: {error_msg}")
                    
                    return response_data
                    
        except Exception as err:
            # Handle different types of errors
            err_str = str(err).lower()
            if "timeout" in err_str or "asyncio.timeout" in err_str:
                _LOGGER.error("Request timeout for %s", url)
                raise HomeAssistantError(ERROR_MESSAGES["timeout_error"]) from err
            elif isinstance(err, aiohttp.ClientError):
                _LOGGER.error("Network error for %s: %s", url, err)
                raise HomeAssistantError(f"{ERROR_MESSAGES['network_error']}: {err}") from err
            elif isinstance(err, HomeAssistantError):
                # Re-raise HomeAssistantError as-is
                raise
            else:
                _LOGGER.error("Unexpected error for %s: %s", url, err)
                raise HomeAssistantError(f"Unexpected error: {err}") from err

    async def validate_token(self) -> dict[str, Any]:
        """Validate the API token."""
        # Ensure we have a session for validation
        need_to_close = False
        if not self.session:
            self.session = aiohttp.ClientSession()
            need_to_close = True
            
        try:
            projects = await self._request("GET", "projects")
            return {"valid": True, "projects": projects}
        except Exception as err:
            _LOGGER.error("Token validation failed: %s", err)
            return {"valid": False, "error": str(err)}
        finally:
            # Clean up session if we created it
            if need_to_close and self.session:
                await self.session.close()
                self.session = None

    async def get_projects(self) -> list[dict[str, Any]]:
        """Get all projects."""
        try:
            projects = await self._request("GET", "projects")
            _LOGGER.debug("Retrieved %d projects", len(projects))
            return projects
        except HomeAssistantError as err:
            _LOGGER.error("Failed to get projects: %s", err)
            raise

    async def get_tasks(self, **kwargs) -> list[dict[str, Any]]:
        """Get all tasks with optional filters."""
        try:
            # Build query parameters
            params = {}
            if "project_id" in kwargs:
                params["project_id"] = kwargs["project_id"]
            if "section_id" in kwargs:
                params["section_id"] = kwargs["section_id"]
            if "label" in kwargs:
                params["label"] = kwargs["label"]
            if "filter" in kwargs:
                params["filter"] = kwargs["filter"]
            if "lang" in kwargs:
                params["lang"] = kwargs["lang"]
            if "ids" in kwargs:
                params["ids"] = ",".join(map(str, kwargs["ids"]))
            
            # Make request with query parameters
            url_params = "&".join([f"{k}={v}" for k, v in params.items()])
            endpoint = f"tasks?{url_params}" if url_params else "tasks"
            
            tasks = await self._request("GET", endpoint)
            _LOGGER.debug("Retrieved %d tasks", len(tasks))
            return tasks
        except HomeAssistantError as err:
            _LOGGER.error("Failed to get tasks: %s", err)
            raise

    async def get_task(self, task_id: str) -> dict[str, Any]:
        """Get a specific task by ID."""
        try:
            task = await self._request("GET", f"tasks/{task_id}")
            _LOGGER.debug("Retrieved task: %s", task.get("content", "Unknown"))
            return task
        except HomeAssistantError as err:
            _LOGGER.error("Failed to get task %s: %s", task_id, err)
            raise

    async def complete_task(self, task_id: str) -> bool:
        """Mark a task as completed."""
        try:
            await self._request("POST", f"tasks/{task_id}/close")
            _LOGGER.info("Completed task: %s", task_id)
            return True
        except HomeAssistantError as err:
            _LOGGER.error("Failed to complete task %s: %s", task_id, err)
            raise

    async def reopen_task(self, task_id: str) -> bool:
        """Reopen a completed task."""
        try:
            await self._request("POST", f"tasks/{task_id}/reopen")
            _LOGGER.info("Reopened task: %s", task_id)
            return True
        except HomeAssistantError as err:
            _LOGGER.error("Failed to reopen task %s: %s", task_id, err)
            raise

    async def create_project(self, name: str, **kwargs) -> dict[str, Any]:
        """Create a new project."""
        data = {"name": name}
        
        # Add optional parameters
        for key in ["color", "parent_id", "is_favorite"]:
            if key in kwargs:
                data[key] = kwargs[key]
        
        try:
            project = await self._request("POST", "projects", data)
            _LOGGER.info("Created project: %s (ID: %s)", project["name"], project["id"])
            return project
        except HomeAssistantError as err:
            _LOGGER.error("Failed to create project '%s': %s", name, err)
            raise

    async def create_task(
        self,
        content: str,
        project_id: str | None = None,
        **kwargs
    ) -> dict[str, Any]:
        """Create a new task."""
        data = {"content": content}
        
        if project_id:
            data["project_id"] = project_id
        
        # Add optional parameters
        for key in ["due_date", "priority", "labels", "parent_id", "description"]:
            if key in kwargs and kwargs[key] is not None:
                data[key] = kwargs[key]
        
        try:
            task = await self._request("POST", "tasks", data)
            _LOGGER.debug("Created task: %s (ID: %s)", task["content"], task["id"])
            return task
        except HomeAssistantError as err:
            _LOGGER.error("Failed to create task '%s': %s", content, err)
            raise

    def find_matching_projects(
        self, projects: list[dict[str, Any]], query: str
    ) -> list[dict[str, Any]]:
        """Find projects that match the query."""
        if not query or not query.strip():
            return []

        query_lower = query.lower().strip()
        matches = []

        # Exact name match (highest priority)
        for project in projects:
            if project["name"].lower() == query_lower:
                matches.append({
                    **project,
                    "match_score": 100,
                    "match_reason": "exact_match",
                })

        # Starts with match
        for project in projects:
            if (
                project["name"].lower().startswith(query_lower)
                and not any(m["id"] == project["id"] for m in matches)
            ):
                matches.append({
                    **project,
                    "match_score": 90,
                    "match_reason": "starts_with",
                })

        # Contains match
        for project in projects:
            if (
                query_lower in project["name"].lower()
                and not any(m["id"] == project["id"] for m in matches)
            ):
                matches.append({
                    **project,
                    "match_score": 70,
                    "match_reason": "contains",
                })

        # Keyword matching
        keyword_map = {
            "shop": ["shopping", "shop", "store", "buy"],
            "work": ["work", "office", "job", "task"],
            "home": ["home", "house", "personal"],
            "food": ["food", "meal", "cook", "recipe", "dinner", "lunch"],
            "car": ["car", "vehicle", "auto", "drive"],
            "health": ["health", "doctor", "medical", "fitness"],
            "book": ["book", "read", "reading"],
            "movie": ["movie", "film", "watch", "entertainment"],
        }

        for category, keywords in keyword_map.items():
            if any(keyword in query_lower for keyword in keywords):
                for project in projects:
                    if (
                        any(keyword in project["name"].lower() for keyword in keywords)
                        and not any(m["id"] == project["id"] for m in matches)
                    ):
                        matches.append({
                            **project,
                            "match_score": 60,
                            "match_reason": "keyword_match",
                        })

        # Sort by score and return top 5
        matches.sort(key=lambda x: x["match_score"], reverse=True)
        return matches[:5]

    def extract_actions(self, text: str) -> list[str]:
        """Extract actionable items from text."""
        if not text:
            return []

        actions = set()
        
        # Apply action patterns
        for pattern in ACTION_PATTERNS:
            matches = re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE)
            for match in matches:
                action = (match.group(1) or match.group(2) or "").strip()
                if 3 < len(action) < 500:
                    # Clean up the action
                    clean_action = re.sub(r"^(that|to|and|or|but)\s+", "", action, flags=re.IGNORECASE)
                    clean_action = re.sub(r"[.!?]+$", "", clean_action).strip()
                    if len(clean_action) > 3:
                        actions.add(clean_action)

        # Fallback: extract sentences with action verbs
        if not actions:
            action_verbs = [
                "create", "make", "build", "setup", "install", "configure",
                "update", "review", "analyze", "implement", "add", "remove",
                "fix", "test", "deploy", "write", "design", "plan", "research",
                "contact", "schedule", "book", "buy", "order", "call", "email", "send"
            ]
            
            sentences = re.split(r'[.!?]\s+', text)
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) > 5:
                    for verb in action_verbs:
                        if sentence.lower().startswith(verb):
                            if len(sentence) < 500:
                                actions.add(sentence)
                            break

        return list(actions)

    def filter_tasks_by_date(self, tasks: list[dict[str, Any]], date_filter: str) -> list[dict[str, Any]]:
        """Filter tasks by date criteria."""
        if not tasks:
            return []

        today = datetime.now().date()
        filtered_tasks = []

        for task in tasks:
            due_date = task.get("due")
            if not due_date:
                if date_filter == "no_due_date":
                    filtered_tasks.append(task)
                continue

            try:
                # Parse due date
                if isinstance(due_date, dict):
                    due_date_str = due_date.get("date")
                else:
                    due_date_str = due_date

                if not due_date_str:
                    continue

                # Handle different date formats
                if "T" in due_date_str:
                    task_date = datetime.fromisoformat(due_date_str.replace("Z", "+00:00")).date()
                else:
                    task_date = datetime.fromisoformat(due_date_str).date()

                # Apply filter
                if date_filter == "today" and task_date == today:
                    filtered_tasks.append(task)
                elif date_filter == "overdue" and task_date < today:
                    filtered_tasks.append(task)
                elif date_filter == "tomorrow" and task_date == (today + timedelta(days=1)):
                    filtered_tasks.append(task)
                elif date_filter == "this_week":
                    days_ahead = (task_date - today).days
                    if 0 <= days_ahead <= 7:
                        filtered_tasks.append(task)
                elif date_filter == "next_week":
                    days_ahead = (task_date - today).days
                    if 7 < days_ahead <= 14:
                        filtered_tasks.append(task)
                elif date_filter == "upcoming":
                    if task_date >= today:
                        filtered_tasks.append(task)

            except (ValueError, TypeError) as err:
                _LOGGER.warning("Failed to parse task due date %s: %s", due_date, err)
                continue

        return filtered_tasks

    def filter_tasks_by_priority(self, tasks: list[dict[str, Any]], priority: int) -> list[dict[str, Any]]:
        """Filter tasks by priority level."""
        return [task for task in tasks if task.get("priority", 1) == priority]

    def filter_tasks_by_project(self, tasks: list[dict[str, Any]], project_id: str) -> list[dict[str, Any]]:
        """Filter tasks by project ID."""
        return [task for task in tasks if task.get("project_id") == project_id]

    def filter_tasks_by_labels(self, tasks: list[dict[str, Any]], labels: list[str]) -> list[dict[str, Any]]:
        """Filter tasks that contain any of the specified labels."""
        if not labels:
            return tasks
        
        filtered_tasks = []
        for task in tasks:
            task_labels = task.get("labels", [])
            if any(label in task_labels for label in labels):
                filtered_tasks.append(task)
        return filtered_tasks

    def get_task_summary(self, tasks: list[dict[str, Any]]) -> dict[str, Any]:
        """Get summary statistics for a list of tasks."""
        if not tasks:
            return {
                "total": 0,
                "by_priority": {1: 0, 2: 0, 3: 0, 4: 0},
                "with_due_date": 0,
                "without_due_date": 0,
                "overdue": 0,
                "due_today": 0,
                "due_tomorrow": 0,
            }

        today = datetime.now().date()
        summary = {
            "total": len(tasks),
            "by_priority": {1: 0, 2: 0, 3: 0, 4: 0},
            "with_due_date": 0,
            "without_due_date": 0,
            "overdue": 0,
            "due_today": 0,
            "due_tomorrow": 0,
        }

        for task in tasks:
            # Count by priority
            priority = task.get("priority", 1)
            summary["by_priority"][priority] = summary["by_priority"].get(priority, 0) + 1

            # Analyze due dates
            due_date = task.get("due")
            if not due_date:
                summary["without_due_date"] += 1
                continue

            summary["with_due_date"] += 1

            try:
                # Parse due date
                if isinstance(due_date, dict):
                    due_date_str = due_date.get("date")
                else:
                    due_date_str = due_date

                if not due_date_str:
                    continue

                if "T" in due_date_str:
                    task_date = datetime.fromisoformat(due_date_str.replace("Z", "+00:00")).date()
                else:
                    task_date = datetime.fromisoformat(due_date_str).date()

                # Categorize by date
                if task_date < today:
                    summary["overdue"] += 1
                elif task_date == today:
                    summary["due_today"] += 1
                elif task_date == (today + timedelta(days=1)):
                    summary["due_tomorrow"] += 1

            except (ValueError, TypeError) as err:
                _LOGGER.warning("Failed to parse task due date %s: %s", due_date, err)

        return summary

    def parse_due_date(self, date_input: str) -> str | None:
        """Parse a due date from various formats."""
        if not date_input:
            return None

        date_input = date_input.lower().strip()
        today = datetime.now().date()

        # Handle relative dates
        if date_input in DATE_PATTERNS:
            days_to_add = DATE_PATTERNS[date_input]
            if days_to_add == 0:
                return today.isoformat()
            elif days_to_add == 7:  # this week -> Friday
                friday = today + timedelta(days=(4 - today.weekday()))
                return friday.isoformat()
            elif days_to_add == 14:  # next week -> next Monday
                next_monday = today + timedelta(days=(7 - today.weekday()))
                return next_monday.isoformat()
            else:
                target_date = today + timedelta(days=days_to_add)
                return target_date.isoformat()

        # Handle "in X days"
        days_match = re.match(r"in (\d+) days?", date_input)
        if days_match:
            days = int(days_match.group(1))
            target_date = today + timedelta(days=days)
            return target_date.isoformat()

        # Handle day names
        day_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        for i, day_name in enumerate(day_names):
            if day_name in date_input:
                days_ahead = i - today.weekday()
                if days_ahead <= 0:  # Target day already happened this week
                    days_ahead += 7
                target_date = today + timedelta(days=days_ahead)
                return target_date.isoformat()

        # Handle ISO format
        if re.match(r"^\d{4}-\d{2}-\d{2}$", date_input):
            return date_input

        # Try to parse other formats
        try:
            parsed_date = date_parser.parse(date_input).date()
            return parsed_date.isoformat()
        except (ValueError, TypeError):
            return None

    def validate_priority(self, priority: int | str | None) -> int:
        """Validate and normalize priority."""
        if priority is None:
            return DEFAULT_PRIORITY
        
        try:
            p = int(priority)
            return max(1, min(4, p))
        except (ValueError, TypeError):
            return DEFAULT_PRIORITY

    def generate_project_name(self, hint: str) -> str:
        """Generate a project name from a hint."""
        if not hint:
            return "New Project"
        
        # Clean and format the hint
        cleaned = hint.strip()
        cleaned = re.sub(r"^(my|the|a|an)\s+", "", cleaned, flags=re.IGNORECASE)  # Remove articles
        cleaned = re.sub(r"\s+", " ", cleaned)  # Normalize spaces
        
        # Title case
        words = cleaned.split()
        formatted_words = [word.capitalize() for word in words if word]
        
        return " ".join(formatted_words) or "New Project"

    async def export_to_todoist(
        self,
        text: str,
        project_id: str,
        main_task_title: str | None = None,
        priority: int = DEFAULT_PRIORITY,
        due_date: str | None = None,
        labels: list[str] | None = None,
        auto_extract: bool = True,
        manual_actions: list[str] | None = None,
    ) -> dict[str, Any]:
        """Export text to Todoist as structured tasks."""
        actions = []
        
        if auto_extract and text:
            actions = self.extract_actions(text)
        
        if manual_actions:
            actions.extend(manual_actions)
        
        if not actions:
            raise HomeAssistantError(ERROR_MESSAGES["no_actions"])

        _LOGGER.info("Exporting %d actions to Todoist", len(actions))

        # Create main task
        main_task_data = {
            "content": main_task_title or f"Voice Tasks - {datetime.now().strftime('%Y-%m-%d')}",
            "project_id": project_id,
            "priority": self.validate_priority(priority),
        }

        if due_date:
            main_task_data["due_date"] = due_date

        if labels:
            main_task_data["labels"] = labels

        main_task = await self.create_task(**main_task_data)

        # Create subtasks
        subtasks = []
        failures = []

        for i, action in enumerate(actions):
            try:
                subtask_data = {
                    "content": action,
                    "project_id": project_id,
                    "parent_id": main_task["id"],
                    "priority": self.validate_priority(priority),
                }

                subtask = await self.create_task(**subtask_data)
                subtasks.append(subtask)
                
                # Small delay to avoid rate limiting
                if i < len(actions) - 1:
                    await asyncio.sleep(0.1)
                    
            except HomeAssistantError as err:
                _LOGGER.error("Failed to create subtask '%s': %s", action, err)
                failures.append({"action": action, "error": str(err)})

        result = {
            "main_task": main_task,
            "subtasks": subtasks,
            "failures": failures,
            "summary": {
                "total_actions": len(actions),
                "successful": len(subtasks),
                "failed": len(failures),
            },
        }

        _LOGGER.info("Export completed: %d/%d tasks created", len(subtasks), len(actions))
        return result