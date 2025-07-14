"""Config flow for Todoist Voice HA integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import (
    DOMAIN,
    CONF_API_TOKEN,
    CONF_AUTO_CREATE_ENTITIES,
    CONF_CONVERSATION_TIMEOUT,
    CONF_DEFAULT_PROJECT,
    CONF_UPDATE_INTERVAL,
    DEFAULT_CONVERSATION_TIMEOUT,
    DEFAULT_PROJECT_NAME,
    DEFAULT_UPDATE_INTERVAL,
    ERROR_MESSAGES,
)
from .todoist_client import TodoistClient

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_TOKEN): str,
        vol.Optional(CONF_NAME, default="Todoist Voice HA"): str,
        vol.Optional(CONF_AUTO_CREATE_ENTITIES, default=True): bool,
        vol.Optional(CONF_CONVERSATION_TIMEOUT, default=DEFAULT_CONVERSATION_TIMEOUT): vol.All(
            vol.Coerce(int), vol.Range(min=30, max=600)
        ),
        vol.Optional(CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL): vol.All(
            vol.Coerce(int), vol.Range(min=60, max=3600)
        ),
    }
)

STEP_PROJECT_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_DEFAULT_PROJECT, default=DEFAULT_PROJECT_NAME): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    client = TodoistClient(data[CONF_API_TOKEN])
    
    try:
        # Test the API token by attempting to get projects
        validation_result = await client.validate_token()
        if not validation_result["valid"]:
            raise InvalidAuth(validation_result.get("error", "Invalid token"))
        
        # Get projects for default project validation
        projects = await client.get_projects()
        
        return {
            "title": data.get(CONF_NAME, "Todoist Voice HA"),
            "projects": projects,
        }
    except Exception as err:
        _LOGGER.error("Failed to validate input: %s", err)
        raise CannotConnect(str(err)) from err


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Todoist Voice HA."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._data: dict[str, Any] = {}
        self._projects: list[dict[str, Any]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            info = await validate_input(self.hass, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            self._data = user_input
            self._data["title"] = info["title"]
            self._projects = info["projects"]
            
            # If we have projects, allow user to select default project
            if self._projects:
                return await self.async_step_project()
            else:
                # No projects, proceed with default
                return self.async_create_entry(
                    title=info["title"], data=self._data
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_project(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the project selection step."""
        if user_input is None:
            project_names = [p["name"] for p in self._projects]
            project_names.append("Inbox")  # Always add Inbox as an option
            
            # Create schema with project options
            schema = vol.Schema(
                {
                    vol.Optional(CONF_DEFAULT_PROJECT, default=DEFAULT_PROJECT_NAME): vol.In(
                        project_names
                    ),
                }
            )
            
            return self.async_show_form(
                step_id="project",
                data_schema=schema,
                description_placeholders={
                    "project_count": str(len(self._projects))
                },
            )

        # Validate selected project exists
        selected_project = user_input[CONF_DEFAULT_PROJECT]
        if selected_project != "Inbox":
            project_exists = any(p["name"] == selected_project for p in self._projects)
            if not project_exists:
                return self.async_show_form(
                    step_id="project",
                    data_schema=STEP_PROJECT_DATA_SCHEMA,
                    errors={"base": "project_not_found"},
                )

        # Merge project data with main data
        self._data.update(user_input)

        return self.async_create_entry(title=self._data["title"], data=self._data)

    async def async_step_import(self, user_input: dict[str, Any]) -> FlowResult:
        """Handle import from configuration.yaml."""
        return await self.async_step_user(user_input)

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Todoist Voice HA."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_AUTO_CREATE_ENTITIES,
                        default=self.config_entry.data.get(CONF_AUTO_CREATE_ENTITIES, True),
                    ): bool,
                    vol.Optional(
                        CONF_CONVERSATION_TIMEOUT,
                        default=self.config_entry.data.get(
                            CONF_CONVERSATION_TIMEOUT, DEFAULT_CONVERSATION_TIMEOUT
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=30, max=600)),
                    vol.Optional(
                        CONF_UPDATE_INTERVAL,
                        default=self.config_entry.data.get(
                            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=60, max=3600)),
                }
            ),
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""