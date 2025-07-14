# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.0] - 2025-01-XX

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