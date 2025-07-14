# Todoist Voice HA - Pure Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub release](https://img.shields.io/github/release/f00lycooly/Todoist-Voice-HA-Integration.svg)](https://github.com/f00lycooly/Todoist-Voice-HA-Integration/releases)
[![License](https://img.shields.io/github/license/f00lycooly/Todoist-Voice-HA-Integration.svg)](https://github.com/f00lycooly/Todoist-Voice-HA-Integration/blob/main/LICENSE)

A pure Home Assistant Custom Integration for conversational task creation with Todoist. This is a complete rewrite of the original Add-On + Integration hybrid, providing better performance, simpler installation, and native Home Assistant integration patterns.

## Features

- ✅ **Pure Integration**: No Add-On required - everything runs natively in Home Assistant
- ✅ **Conversational Task Creation**: Natural language processing for voice-driven task creation
- ✅ **Smart Project Matching**: Intelligent project selection based on context
- ✅ **Action Extraction**: Automatically extracts actionable items from voice input
- ✅ **Natural Date Parsing**: Understands relative dates like "tomorrow", "next week", etc.
- ✅ **Conversation State Management**: Maintains context across conversation turns
- ✅ **UI Configuration**: Easy setup through Home Assistant UI
- ✅ **HACS Compatible**: Install and update through HACS
- ✅ **Entity Auto-Creation**: Automatically creates helper entities for state management
- ✅ **Event-Driven**: Fires Home Assistant events for automation integration

## Installation

### HACS (Recommended)

1. Add this repository to HACS as a custom repository
2. Install "Todoist Voice HA Integration"
3. Restart Home Assistant
4. Go to Settings → Integrations → Add Integration
5. Search for "Todoist Voice HA" and follow the setup wizard

### Manual Installation

1. Download the latest release
2. Extract the `custom_components/todoist_voice_ha` folder to your Home Assistant `config/custom_components/` directory
3. Restart Home Assistant
4. Follow the HACS setup steps 4-5

## Configuration

### Initial Setup

1. **Get your Todoist API Token**:
   - Go to [Todoist Integrations](https://todoist.com/prefs/integrations)
   - Copy your API token

2. **Configure the Integration**:
   - Go to Settings → Integrations → Add Integration
   - Search for "Todoist Voice HA"
   - Enter your API token
   - Configure optional settings:
     - Auto-create helper entities (recommended)
     - Conversation timeout (default: 5 minutes)
     - Update interval (default: 5 minutes)

3. **Select Default Project**:
   - Choose your default project for new tasks
   - This will be used when no project is specified

### Helper Entities

The integration automatically creates helper entities for state management:

#### Input Boolean Entities
- `input_boolean.todoist_voice_ha_conversation_active`
- `input_boolean.todoist_voice_ha_awaiting_project_selection`
- `input_boolean.todoist_voice_ha_awaiting_project_creation`
- `input_boolean.todoist_voice_ha_awaiting_date_input`
- `input_boolean.todoist_voice_ha_awaiting_final_confirmation`

#### Input Text Entities
- `input_text.todoist_voice_ha_conversation_id`
- `input_text.todoist_voice_ha_conversation_state`
- `input_text.todoist_voice_ha_input_buffer`
- `input_text.todoist_voice_ha_parsed_actions`
- `input_text.todoist_voice_ha_project_matches`
- `input_text.todoist_voice_ha_selected_project`
- `input_text.todoist_voice_ha_pending_due_date`
- `input_text.todoist_voice_ha_task_priority`
- `input_text.todoist_voice_ha_conversation_context`

#### Input Select Entities
- `input_select.todoist_voice_ha_available_projects`

#### Input Number Entities
- `input_number.todoist_voice_ha_conversation_timeout`

## Usage

### Services

The integration provides several services for task and project management:

#### `todoist_voice_ha.create_task`

Create a task with automatic action extraction:

```yaml
service: todoist_voice_ha.create_task
data:
  text: "Buy groceries: milk, bread, eggs. Also pick up dry cleaning."
  project_name: "Shopping"
  priority: 2
  due_date: "tomorrow"
  labels: ["voice", "urgent"]
```

#### `todoist_voice_ha.start_conversation`

Start a conversational task creation session:

```yaml
service: todoist_voice_ha.start_conversation
data:
  text: "I need to plan my weekend: clean the house, do laundry, grocery shopping"
  timeout: 300
```

#### `todoist_voice_ha.continue_conversation`

Continue an existing conversation:

```yaml
service: todoist_voice_ha.continue_conversation
data:
  conversation_id: "abc123"
  text: "Use the Home project"
```

#### `todoist_voice_ha.find_projects`

Find projects matching a query:

```yaml
service: todoist_voice_ha.find_projects
data:
  query: "home"
  max_results: 3
```

#### `todoist_voice_ha.create_project`

Create a new project:

```yaml
service: todoist_voice_ha.create_project
data:
  name: "Weekend Tasks"
  color: "blue"
```

#### Other Services

- `todoist_voice_ha.parse_voice_input` - Parse voice input for actions
- `todoist_voice_ha.validate_date` - Validate date input
- `todoist_voice_ha.refresh_projects` - Refresh project cache
- `todoist_voice_ha.get_conversation_status` - Get conversation status

### Voice Assistant Integration

Example automation for voice assistant integration:

```yaml
automation:
  - alias: "Todoist Voice Command"
    trigger:
      - platform: conversation
        command: "add todoist task {text}"
    action:
      - service: todoist_voice_ha.start_conversation
        data:
          text: "{{ trigger.slots.text }}"
          timeout: 300
      - wait_for_trigger:
          - platform: event
            event_type: todoist_voice_ha_task_created
        timeout: 300
      - service: tts.speak
        data:
          message: "Tasks created successfully!"
```

### Events

The integration fires events for automation:

- `todoist_voice_ha_task_created`
- `todoist_voice_ha_project_created`
- `todoist_voice_ha_conversation_started`
- `todoist_voice_ha_conversation_continued`
- `todoist_voice_ha_projects_found`
- `todoist_voice_ha_voice_input_parsed`
- `todoist_voice_ha_date_validated`
- `todoist_voice_ha_projects_refreshed`

## Conversation Flow

The integration supports a natural conversation flow:

1. **Initial Input**: "I need to plan my weekend project"
2. **Action Extraction**: Automatically extracts tasks from your description
3. **Project Selection**: Asks which project to use if not clear
4. **Date Confirmation**: Asks for due dates if not specified
5. **Final Confirmation**: Shows summary before creating tasks
6. **Task Creation**: Creates main task with subtasks in Todoist

## Troubleshooting

### Common Issues

1. **API Token Invalid**:
   - Verify your token at [Todoist Integrations](https://todoist.com/prefs/integrations)
   - Reconfigure the integration with the correct token

2. **No Projects Found**:
   - Check your Todoist account has projects
   - Use the "Refresh Projects" button

3. **Conversation Timeout**:
   - Increase timeout in integration options
   - Use "Reset Conversation State" button

4. **Helper Entities Not Created**:
   - Enable "Auto-create entities" in integration options
   - Manually create required entities if needed

### Debug Logging

Enable debug logging for troubleshooting:

```yaml
logger:
  logs:
    custom_components.todoist_voice_ha: debug
```

## Migration from Add-On Version

If you're migrating from the original Add-On + Integration version:

1. **Backup your automations** that use the old services
2. **Install the new integration** following the installation guide
3. **Update your automations** to use the new service names
4. **Remove the old Add-On** and integration
5. **Test thoroughly** before removing backups

### Service Name Changes

| Old Service | New Service |
|-------------|-------------|
| `todoist_voice_ha_integration.create_task` | `todoist_voice_ha.create_task` |
| `todoist_voice_ha_integration.find_projects` | `todoist_voice_ha.find_projects` |

## Development

### Requirements

- Python 3.11+
- Home Assistant 2024.1+
- Todoist API Token

### Testing

The integration includes comprehensive test coverage. Run tests with:

```bash
python -m pytest tests/
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/f00lycooly/Todoist-Voice-HA-Integration/issues)
- **Discussions**: [GitHub Discussions](https://github.com/f00lycooly/Todoist-Voice-HA-Integration/discussions)
- **Documentation**: [Wiki](https://github.com/f00lycooly/Todoist-Voice-HA-Integration/wiki)

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and changes.

---

**Note**: This is a complete rewrite of the original Add-On approach. If you're using the old version, please see the migration guide above.