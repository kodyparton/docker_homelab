#!/bin/bash
# Appends a timestamp,avail_bytes sample and prints recent history as CSV.
set -euo pipefail

cd /Users/kp-srv-01/Documents/docker
mkdir -p scripts/data
HISTORY_FILE="scripts/data/disk_history.csv"
touch "$HISTORY_FILE"

avail_kb=$(df -k /Users/kp-srv-01/Documents/docker | tail -1 | awk '{print $4}')
avail_bytes=$((avail_kb * 1024))
ts=$(date +%s)

echo "${ts},${avail_bytes}" >> "$HISTORY_FILE"

tail -30 "$HISTORY_FILE"
