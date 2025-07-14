# Todoist Voice HA - Integration Refactor Scope Document

## Executive Summary

This document outlines the scope for refactoring the **Todoist Voice HA** project from a Home Assistant Add-On + Custom Integration hybrid approach to a pure Custom Integration approach. The current solution uses a Node.js server in an Add-On to handle Todoist API processing, with a separate Custom Integration for Home Assistant services. This refactor aims to consolidate functionality into a single, streamlined Custom Integration.

## Current Implementation Analysis

### Current Architecture
- **Add-On Component**: Node.js server (src/server.js) running in Docker container
- **Custom Integration**: Python-based HA integration in `custom_components/todoist_voice_ha_integration/`
- **Communication**: HTTP API calls from Integration to Add-On server
- **Deployment**: HACS-compatible with both Add-On and Integration components

### Current Functionality

#### Add-On Server Features (src/server.js)
1. **Todoist API Integration**
   - Token validation and authentication
   - Project management (list, create, search, match)
   - Task creation with subtasks
   - Action extraction from conversational text
   - Smart date parsing (natural language to ISO dates)

2. **Conversational Processing**
   - Voice input parsing and analysis
   - Project suggestion and matching algorithms
   - Task extraction from natural language
   - Context-aware conversation state management

3. **Home Assistant Services API**
   - `/ha-services/projects` - Get all projects
   - `/ha-services/find-projects` - Search projects by query
   - `/ha-services/create-project` - Create new project
   - `/ha-services/parse-voice-input` - Parse voice input for actions
   - `/ha-services/create-task` - Create tasks with conversation context
   - `/ha-services/validate-date` - Validate and parse date input
   - `/ha-services/refresh-projects` - Refresh project cache

4. **Legacy Endpoints**
   - `/projects-list` - List all projects
   - `/quick-export` - Quick task creation
   - `/extract-actions` - Extract actions from text

#### Custom Integration Features
1. **Service Registration**: 6 HA services for task and project management
2. **Entity Management**: Auto-creation of helper entities (input_boolean, input_text, etc.)
3. **Data Coordination**: Sensor and binary sensor for status monitoring
4. **Configuration Flow**: UI-based setup and configuration
5. **State Management**: Conversation state tracking through helper entities

### Current Entity Structure
- **Input Booleans**: 5 entities for conversation state tracking
- **Input Text**: 9 entities for data storage and context
- **Input Select**: 1 entity for project selection
- **Input Number**: 1 entity for conversation timeout

## Refactor Scope

### Objective
Convert the hybrid Add-On + Integration architecture to a pure Custom Integration that:
1. Directly integrates with Todoist API (no intermediate server)
2. Maintains all current functionality
3. Improves performance by eliminating HTTP overhead
4. Simplifies deployment and maintenance
5. Follows Home Assistant 2025 integration standards

### Core Components to Migrate

#### 1. Todoist API Client
**From**: Node.js TodoistExporter class
**To**: Python Todoist API client

**Functions to migrate**:
- Token validation
- Project operations (list, create, search, match)
- Task creation with subtasks
- Action extraction algorithms
- Date parsing utilities

#### 2. Conversational Processing Engine
**From**: JavaScript voice parsing and analysis
**To**: Python conversational analysis

**Functions to migrate**:
- Voice input parsing
- Action extraction patterns
- Project matching algorithms
- Context-aware conversation management

#### 3. Service Layer
**From**: HTTP API endpoints
**To**: Native Home Assistant services

**Services to maintain**:
- `create_task`
- `find_projects`
- `create_project`
- `parse_voice_input`
- `validate_date`
- `refresh_projects`

#### 4. State Management
**From**: Project cache in Node.js server
**To**: Home Assistant data coordinator pattern

**Features to maintain**:
- Project caching with TTL
- Automatic cache refresh
- State persistence across restarts

### Technical Requirements

#### Integration Structure (2025 Standards)
```
custom_components/todoist_voice_ha/
├── __init__.py              # Integration setup and entry point
├── manifest.json            # Integration metadata and dependencies
├── config_flow.py           # UI configuration flow
├── const.py                 # Constants and configuration
├── coordinator.py           # Data update coordinator
├── todoist_client.py        # Todoist API client
├── conversation_engine.py   # Conversational processing
├── services.py              # Home Assistant services
├── entity_creator.py        # Entity management
├── sensor.py                # Sensor entities
├── binary_sensor.py         # Binary sensor entities
├── button.py                # Button entities
└── strings.json             # Localization strings
```

#### Dependencies and Requirements
- `python-todoist-api` or similar Todoist API library
- `aiohttp` for async HTTP requests
- `dateutil` for date parsing
- `voluptuous` for schema validation
- Home Assistant core dependencies

#### Data Flow Architecture
```
Voice Input → Conversation Engine → Todoist Client → HA Services → Entity Updates
     ↓                    ↓              ↓              ↓
State Management ← Data Coordinator ← API Response ← Service Call
```

### Migration Strategy

#### Phase 1: Core API Migration
1. Create Python Todoist API client
2. Implement action extraction algorithms
3. Port date parsing utilities
4. Set up data coordinator pattern

#### Phase 2: Service Layer Migration
1. Convert HTTP API endpoints to HA services
2. Implement conversational processing in Python
3. Set up project matching and caching
4. Create conversation state management

#### Phase 3: Integration Enhancement
1. Implement UI configuration flow
2. Set up proper entity management
3. Add proper error handling and logging
4. Implement proper async patterns

#### Phase 4: Testing and Validation
1. Unit tests for all core functionality
2. Integration tests for HA services
3. End-to-end conversation flow testing
4. Performance and reliability testing

### Features to Maintain

#### Essential Features
- ✅ Todoist API integration (projects, tasks, authentication)
- ✅ Conversational task creation
- ✅ Smart project matching and suggestion
- ✅ Natural language date parsing
- ✅ Action extraction from voice input
- ✅ Conversation state management
- ✅ Entity auto-creation and management
- ✅ HACS compatibility

#### Enhanced Features
- ✅ Improved error handling and user feedback
- ✅ Better async performance
- ✅ Native HA integration patterns
- ✅ Simplified configuration
- ✅ Better logging and diagnostics

### Architecture Benefits

#### Performance Improvements
- Eliminate HTTP request overhead between Integration and Add-On
- Native async/await patterns throughout
- Reduced memory footprint (single Python process vs Node.js + Python)
- Better resource utilization

#### Maintenance Benefits
- Single codebase to maintain
- Consistent Python ecosystem
- Better error handling and debugging
- Simplified deployment (no Docker container)

#### User Experience Benefits
- Faster response times
- More reliable operation
- Simpler installation process
- Better integration with HA ecosystem

### Deployment Strategy

#### New Integration Structure
```
custom_components/todoist_voice_ha/
├── Core integration files
└── No Add-On component required
```

#### Migration Path for Existing Users
1. **Backward Compatibility**: Maintain existing service names and signatures
2. **Entity Migration**: Preserve existing entity IDs and states
3. **Configuration Migration**: Auto-migrate from Add-On URL to direct API token
4. **Deprecation Notice**: Provide clear migration instructions

### Risk Assessment

#### Technical Risks
- **Low**: Python Todoist API libraries are well-established
- **Medium**: Conversation processing complexity in Python
- **Low**: Home Assistant integration patterns are well-documented

#### User Impact Risks
- **Low**: Existing automations should continue working
- **Medium**: Configuration changes required
- **Low**: Entity states and IDs will be preserved

### Success Metrics

#### Functional Metrics
- All current features working in new architecture
- Response time improvements (target: <500ms for most operations)
- Error rate reduction (target: <1% for API operations)
- 100% test coverage for core functionality

#### User Experience Metrics
- Simplified installation process
- Reduced configuration complexity
- Improved reliability and stability
- Better error messages and user feedback

## Conclusion

The refactor from Add-On + Integration to pure Integration represents a significant architectural improvement that will:

1. **Simplify the codebase** by eliminating the Node.js server component
2. **Improve performance** by removing HTTP communication overhead
3. **Enhance maintainability** with a single Python codebase
4. **Better align with Home Assistant standards** for 2025 and beyond
5. **Provide a better user experience** with faster responses and simpler setup

The scope is well-defined and achievable, with clear migration paths and minimal user impact. The new architecture will be more robust, performant, and easier to maintain long-term.

---

**Next Steps**: Proceed with refactoring analysis to determine whether to modify the current codebase or create a new project structure.