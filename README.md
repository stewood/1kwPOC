# 1kw POC (Proof of Concept)

A lightweight prototype for options trading analysis using Option Samurai data. This project aims to validate trading strategies by analyzing historical performance of trade opportunities identified through Option Samurai scans.

## Project Structure

- `project_codex/` - Project documentation and planning
  - `01_overview/` - Project overview and goals
  - `02_planning/` - Development planning and technical documentation
  - `03_research/` - Research and analysis
  - `04_operations/` - Operational procedures
  - `TODO.md` - Current tasks and project status
- `src/` - Source code for the application
- `tests/` - Test suite
- `data/` - Data storage directory
- `db/` - SQLite database integration
- `logs/` - Application logs
- `venv/` - Python virtual environment

## Development Status

Currently implementing price history tracking functionality. See [project_codex/TODO.md](project_codex/TODO.md) for detailed status and planned features.

## Getting Started

### Prerequisites
- Python 3.x
- Virtual environment (venv)

### Setup
1. Create and activate virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Project Goals

1. Fetch and store Option Samurai scan results
2. Track and analyze trade opportunities
3. Validate trading strategies
4. Generate performance insights

## License

Private repository - All rights reserved 