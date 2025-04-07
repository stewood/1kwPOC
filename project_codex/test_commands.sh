#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Determine the project root directory (assuming the script is in project_codex)
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
PROJECT_ROOT=$( cd -- "$SCRIPT_DIR/.." &> /dev/null && pwd )
ENV_FILE="$PROJECT_ROOT/.env"
MAIN_SCRIPT="$PROJECT_ROOT/src/main.py"

echo "📂 Project Root: $PROJECT_ROOT"
echo "📄 Env File: $ENV_FILE"
echo "🐍 Main Script: $MAIN_SCRIPT"

# Load environment variables from .env file in the project root
if [ -f "$ENV_FILE" ]; then
    echo " R Loading environment variables from $ENV_FILE..."
    set -a # automatically export all variables
    source "$ENV_FILE"
    set +a # stop exporting variables
else
    echo "❌ Error: .env file not found at $ENV_FILE"
    exit 1
fi

# Check if DB_PATH is set
if [ -z "$DB_PATH" ]; then
    echo "❌ Error: DB_PATH is not set in $ENV_FILE"
    exit 1
fi

DB_FILE_PATH="$PROJECT_ROOT/$DB_PATH" # Construct full path relative to project root

# 1. Remove the existing database file
echo "🗑️ Removing existing database file: $DB_FILE_PATH..."
rm -f "$DB_FILE_PATH"
echo "✅ Database file removed (if it existed)."

# Change to project root directory to run python script correctly
cd "$PROJECT_ROOT"

# 2. Initialize the database
echo "
🚀 Running: python -m src.main --init-db"
python3 -m src.main --init-db
echo "✅ --init-db completed."

# 3. Fetch scans
echo "
🚀 Running: python -m src.main --fetch-scans"
python3 -m src.main --fetch-scans
echo "✅ --fetch-scans completed."

# 4. Update prices
echo "
🚀 Running: python -m src.main --update-prices"
python3 -m src.main --update-prices
echo "✅ --update-prices completed."

# 5. Generate report
echo "
🚀 Running: python -m src.main --generate-report"
python3 -m src.main --generate-report
echo "✅ --generate-report completed."

echo "
🎉 All commands executed successfully!" 