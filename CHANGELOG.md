# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.1.0] - 2025-01-14

### 🎉 Added
- **9 New Task Sensors** for comprehensive task monitoring:
  - `sensor.todoist_task_count` - Total number of active tasks
  - `sensor.todoist_tasks_due_today` - Tasks due today (perfect for morning reminders!)
  - `sensor.todoist_overdue_tasks` - Overdue tasks (critical for productivity!)
  - `sensor.todoist_upcoming_tasks` - Upcoming tasks
  - `sensor.todoist_tasks_due_tomorrow` - Tasks due tomorrow
  - `sensor.todoist_tasks_this_week` - Tasks due this week
  - `sensor.todoist_high_priority_tasks` - High priority tasks (P1 & P2)
  - `sensor.todoist_task_summary` - Overall task summary with productivity score
  - `sensor.todoist_next_task` - Next most important task (ideal for Assist integration!)

- **3 New Task Management Services**:
  - `todoist_voice_ha.complete_task` - Mark tasks as completed
  - `todoist_voice_ha.reopen_task` - Reopen completed tasks
  - `todoist_voice_ha.get_tasks` - Retrieve tasks with advanced filtering

- **Enhanced Home Assistant Assist Integration**:
  - Rich sensor data perfect for voice reminders
  - Smart task prioritization (overdue → today → priority)
  - Productivity scoring and task analytics

- **New Events**:
  - `todoist_voice_ha_task_completed` - Fired when tasks are completed
  - `todoist_voice_ha_task_reopened` - Fired when tasks are reopened
  - `todoist_voice_ha_tasks_retrieved` - Fired when tasks are retrieved

### 🔧 Fixed
- **Connection Issues**: Improved session management during token validation
- **Python 3.11+ Compatibility**: Fixed async timeout import issues
- **Error Handling**: Enhanced error detection and logging for better debugging
- **API Response Parsing**: Better handling of different content types
- **Session Cleanup**: Proper cleanup of HTTP sessions during validation

### ⚡ Improved
- **Comprehensive Logging**: Added debug logging throughout for easier troubleshooting
- **Task Data Caching**: Automatic task caching with coordinator pattern
- **Smart Filtering**: Advanced task filtering by date, priority, project, and labels
- **Documentation**: Updated README with complete task sensor examples and Assist integration

### 🏗️ Technical
- Enhanced `TodoistClient` with comprehensive task management methods
- Improved `TodoistDataUpdateCoordinator` with task caching and filtering
- Better error handling and logging throughout the codebase
- HACS publication ready with proper GitHub workflows

### 📖 Documentation
- Added comprehensive task sensor documentation
- Included voice reminder automation examples
- Updated installation instructions for HACS
- Added troubleshooting guide for connection issues

## [3.0.0] - 2025-01-13

### Added
- Complete rewrite as pure Home Assistant Custom Integration
- Native async/await patterns throughout
- Comprehensive conversation engine with state management
- UI-based configuration flow following HA 2025 standards
- Automatic entity creation for helper entities
- Event-driven architecture for automation integration
- Button entities for manual actions (refresh projects, reset conversation)
- Comprehensive test coverage
- Enhanced error handling and logging
- Support for conversation timeouts and cleanup

### Changed
- **BREAKING**: Migrated from Add-On + Integration to pure Integration
- **BREAKING**: Service names changed from `todoist_voice_ha_integration.*` to `todoist_voice_ha.*`
- **BREAKING**: No longer requires Add-On installation
- **BREAKING**: Configuration moved to UI-based flow
- Improved performance by eliminating HTTP request overhead
- Enhanced project matching algorithm with scoring
- Better natural language date parsing
- Simplified installation process

### Removed
- Node.js server component (Add-On)
- HTTP API endpoints
- Docker containerization
- Manual YAML configuration
- Add-On specific configuration files

### Fixed
- Memory leaks in conversation state management
- Race conditions in project caching
- Inconsistent error handling
- Missing entity state updates

### Technical Details
- Built with Home Assistant 2025 integration standards
- Uses DataUpdateCoordinator for efficient data management
- Implements proper async context managers
- Follows Home Assistant naming conventions
- Includes comprehensive type hints
- Uses proper entity platforms (sensor, binary_sensor, button)

### Migration Guide
See README.md for detailed migration instructions from v2.x Add-On version.

## [2.0.0] - 2024-XX-XX (Add-On Version)

### Added
- Home Assistant Add-On with Node.js server
- Custom Integration for HA services
- Conversational task creation
- Project matching and creation
- Voice input parsing
- Date validation and parsing

### Features
- HTTP API for task creation
- Project caching with TTL
- Action extraction from natural language
- Integration with Home Assistant services
- HACS compatibility

## [1.0.0] - 2024-XX-XX (Initial Version)

### Added
- Basic Todoist API integration
- Simple task creation
- Project management
- Basic voice input processing