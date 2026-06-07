#!/usr/bin/env bash
# Weekly Utopia AI brief orchestrator.
#
# Runs last30days for each topic in topics.json, synthesizes them via xAI,
# and posts the curated brief to Slack.
#
# Triggered weekly via cron. Run manually with:
#   ~/utopia-weekly-brief/run.sh

set -euo pipefail

# Cron uses a minimal PATH. Make sure we pick up Homebrew-installed binaries
# (python3.14, node, gh, jq) instead of macOS system defaults (python3.9).
export PATH="/opt/homebrew/bin:/usr/local/bin:/opt/homebrew/sbin:$PATH"

BRIEF_DIR="$HOME/utopia-weekly-brief"
DATE="$(date +%Y-%m-%d)"
RUN_DIR="$BRIEF_DIR/runs/$DATE"
LOG_FILE="$BRIEF_DIR/logs/$DATE.log"

mkdir -p "$RUN_DIR" "$BRIEF_DIR/logs"

# Redirect all output to the log file AND keep stdout/stderr for cron
exec > >(tee -a "$LOG_FILE") 2>&1

echo "============================================================"
echo "Utopia Weekly AI Brief — $(date)"
echo "============================================================"

# ----- Load env -----
set -a
# shellcheck source=/dev/null
source "$BRIEF_DIR/.env"
# Also pull SCRAPECREATORS_API_KEY from last30days config
if [ -f "$LAST30DAYS_ENV" ]; then
    # shellcheck source=/dev/null
    source "$LAST30DAYS_ENV"
fi
set +a

if [ -z "${SLACK_WEBHOOK_URL:-}" ]; then
    echo "FATAL: SLACK_WEBHOOK_URL not set"
    exit 1
fi
if [ -z "${SCRAPECREATORS_API_KEY:-}" ]; then
    echo "FATAL: SCRAPECREATORS_API_KEY not set (check ~/.config/last30days/.env)"
    exit 1
fi
if [ -z "${XAI_API_KEY:-}" ]; then
    echo "FATAL: XAI_API_KEY not set"
    exit 1
fi

# ----- Parse topics.json -----
TOPICS_JSON="$BRIEF_DIR/topics.json"
LOOKBACK_DAYS="$(python3 -c "import json; print(json.load(open('$TOPICS_JSON'))['lookback_days'])")"
DEPTH="$(python3 -c "import json; print(json.load(open('$TOPICS_JSON'))['depth'])")"
TOPIC_COUNT="$(python3 -c "import json; print(len(json.load(open('$TOPICS_JSON'))['topics']))")"

echo "Lookback: $LOOKBACK_DAYS days · Depth: $DEPTH · Topics: $TOPIC_COUNT"
echo ""

# ----- Run last30days for each topic -----
for i in $(seq 0 $((TOPIC_COUNT - 1))); do
    TOPIC_ID="$(python3 -c "import json; print(json.load(open('$TOPICS_JSON'))['topics'][$i]['id'])")"
    TOPIC_QUERY="$(python3 -c "import json; print(json.load(open('$TOPICS_JSON'))['topics'][$i]['query'])")"

    echo "------------------------------------------------------------"
    echo "[$((i+1))/$TOPIC_COUNT] $TOPIC_ID"
    echo "Query: $TOPIC_QUERY"
    echo "------------------------------------------------------------"

    OUT_PATH="$RUN_DIR/${TOPIC_ID}.md"

    # Run last30days. --emit=md gives us a markdown brief.
    # --save-dir keeps the raw debug data for inspection.
    if python3 "$LAST30DAYS_PATH/scripts/last30days.py" \
        "$TOPIC_QUERY" \
        --emit md \
        --"$DEPTH" \
        --days "$LOOKBACK_DAYS" \
        --save-dir "$RUN_DIR/${TOPIC_ID}-raw" \
        > "$OUT_PATH" 2>> "$LOG_FILE"
    then
        echo "✓ Saved $(wc -c < "$OUT_PATH" | tr -d ' ') bytes to $(basename "$OUT_PATH")"
    else
        echo "✗ Topic $TOPIC_ID failed — see log. Continuing."
        echo "[Topic query failed — no data]" > "$OUT_PATH"
    fi
    echo ""
done

# ----- Synthesize -----
echo "============================================================"
echo "Synthesizing brief..."
echo "============================================================"
python3 "$BRIEF_DIR/synthesize.py" "$RUN_DIR" > "$RUN_DIR/brief.md"
echo "✓ Brief synthesized to $RUN_DIR/brief.md"
echo ""

# ----- Post to Slack -----
echo "============================================================"
echo "Posting to Slack..."
echo "============================================================"
python3 "$BRIEF_DIR/post_to_slack.py" "$RUN_DIR/brief.md"

echo ""
echo "============================================================"
echo "Done — $(date)"
echo "============================================================"

# ----- Log rotation: keep last 12 weeks -----
find "$BRIEF_DIR/logs" -name "*.log" -mtime +84 -delete 2>/dev/null || true
find "$BRIEF_DIR/runs" -mindepth 1 -maxdepth 1 -type d -mtime +84 -exec rm -rf {} + 2>/dev/null || true
