#!/bin/bash
export PATH="/usr/local/bin:/opt/homebrew/bin:$PATH"

LOG_FILE="$HOME/Documents/docker/update.log"
echo "=== Docker update: $(date) ===" >> "$LOG_FILE"

find "$HOME/Documents/docker" -name "compose.yml" | while read compose_file; do
    dir=$(dirname "$compose_file")
    project=$(basename "$dir")
    echo "--- $project ---" >> "$LOG_FILE"
    if cd "$dir" && docker compose pull >> "$LOG_FILE" 2>&1 && docker compose up -d >> "$LOG_FILE" 2>&1; then
        echo "$project: OK" >> "$LOG_FILE"
    else
        echo "$project: FAILED" >> "$LOG_FILE"
    fi
done

echo "=== Done ===" >> "$LOG_FILE"
