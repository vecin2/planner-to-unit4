#!/usr/bin/env bash

set -e

# --- CONFIG ---
PROJECT_SRC="./src/planner_to_unit4"

FABRIC_SUBMIT_VARIACE_NOTEBOOK_PATH="/mnt/c/Users/dalvarez/OneDrive - CGIAR/Documents/Dev/Fabric/vscode/db32c83c-2139-4943-8dcf-f01bd0f6cf72/SynapseNotebook/5911c37f-f2f5-49af-8497-5316f2bf1cc8/submit_budget_variance"
FABRIC_ARCHIVE_NOTEBOOK_PATH="/mnt/c/Users/dalvarez/OneDrive - CGIAR/Documents/Dev/Fabric/vscode/db32c83c-2139-4943-8dcf-f01bd0f6cf72/SynapseNotebook/82b59beb-a29f-40e4-88e2-6c8d21c0dc4b/archive_plan_data_file"

FABRIC_NOTEBOOK_PATHS=(
  "$FABRIC_SUBMIT_VARIACE_NOTEBOOK_PATH"
  "$FABRIC_ARCHIVE_NOTEBOOK_PATH"
)

# --- EXECUTION ---

for FABRIC_NOTEBOOK_PATH in "${FABRIC_NOTEBOOK_PATHS[@]}"; do
  TARGET="$FABRIC_NOTEBOOK_PATH/builtin/planner_to_unit4"

  echo "Syncing planner_to_unit4 -> $TARGET"

  # Remove previous version
  rm -rf "$TARGET"

  # Recreate folder
  mkdir -p "$TARGET"

  # Copy fresh code
  cp -r "$PROJECT_SRC"/. "$TARGET"/
done

echo "✅ Sync complete to ${#FABRIC_NOTEBOOK_PATHS[@]} notebooks"
