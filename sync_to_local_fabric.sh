#!/usr/bin/env bash

set -e

# --- CONFIG ---
PROJECT_SRC="./src/planner_to_unit4"

FABRIC_NOTEBOOK_PATH="/mnt/c/Users/dalvarez/OneDrive - CGIAR/Documents/Dev/Fabric/vscode/db32c83c-2139-4943-8dcf-f01bd0f6cf72/SynapseNotebook/5911c37f-f2f5-49af-8497-5316f2bf1cc8/register_snapshot"

TARGET="$FABRIC_NOTEBOOK_PATH/builtin/planner_to_unit4"

# --- EXECUTION ---

echo "Syncing planner_to_unit4 → Fabric builtin..."

# Remove previous version
rm -rf "$TARGET"

# Recreate folder
mkdir -p "$TARGET"

# Copy fresh code
cp -r "$PROJECT_SRC/"* "$TARGET"

echo "✅ Sync complete"
