# Options Trading Analysis Project Codex

This directory contains all planning, documentation, and research materials for the Options Trading Analysis project. It serves as a central knowledge repository separate from the codebase.

## Directory Structure

- `01_overview/` - High-level project documentation
  - [Project Goals](01_overview/project_goals.md) - Core objectives and success criteria
  - System architecture
  - Development timeline

- `02_planning/` - Detailed planning materials
  - [Database Schema](02_planning/database_schema.md) - Complete database structure and design
  - [Database Integration Plan](02_planning/development_chunks/step1_database_integration.md) - Step-by-step integration plan
  - [TODO](TODO.md) - Current task tracking and history
  - Development chunks and tasks
  - Technical decisions and rationale

- `03_research/` - Research and analysis
  - Trading strategies
    * Bull Put Spreads
    * Bear Call Spreads
    * Iron Condors
  - API documentation notes
  - Market research

- `04_operations/` - Operational documentation
  - Deployment procedures
  - Maintenance notes
  - Monitoring plans

## Key Documents

### Planning & Design
- [Project Goals](01_overview/project_goals.md) - Defines core objectives and success criteria
- [Database Schema](02_planning/database_schema.md) - Details the database structure including:
  * Active trades table
  * Completed trades table
  * Audit trails
  * Constraints and triggers
  * Extension points
- [TODO](TODO.md) - Tracks all work items with:
  * Current active tasks
  * Completed work
  * Future plans
  * Task history and context

### Development
- [Database Integration Plan](02_planning/development_chunks/step1_database_integration.md) - Outlines the implementation approach for:
  * Database setup
  * Connection management
  * Data access layer
  * Integration testing

## Usage

This codex should be updated regularly with:
- Development decisions and their rationale
- Research findings
- Technical documentation
- Future plans and ideas

### Document Guidelines
1. Keep each document focused and cross-reference between documents
2. Include context and rationale for decisions
3. Update related documents when making changes
4. Maintain document history in TODO.md
5. Add new documentation under appropriate sections

### Cross-Referencing
When adding new documentation:
1. Update this README if adding major documents
2. Link related documents to each other
3. Update TODO.md with documentation changes
4. Keep section structure consistent 