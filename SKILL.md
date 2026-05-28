# Utopia Weekly AI Brief

Self-contained system that runs `last30days` for 5 curated topics every week, synthesizes the output via xAI Grok, and posts a concise brief to Slack.

## Files

| File | Purpose |
|------|---------|
| `.env` | Slack webhook URL + xAI API key (chmod 600) |
| `topics.json` | The 5 research topics + depth/lookback config |
| `run.sh` | Cron-triggered orchestrator |
| `synthesize.py` | Curates 5 raw topic briefs → one Slack-ready brief |
| `post_to_slack.py` | Posts markdown to Slack via Block Kit |
| `runs/<date>/` | Per-week working directory with raw outputs |
| `logs/<date>.log` | Per-run log |

## How it works

```
Sunday 7pm → cron triggers run.sh
                │
                ▼
  Loads .env + last30days config
                │
                ▼
  For each topic in topics.json:
      python3 last30days.py "<query>" \
        --emit md --deep --days 7 \
        --save-dir runs/<date>/<id>-raw \
        > runs/<date>/<id>.md
                │
                ▼
  synthesize.py runs/<date>/
      → reads all 5 topic briefs
      → calls xAI Grok with curation prompt
      → writes runs/<date>/brief.md
                │
                ▼
  post_to_slack.py runs/<date>/brief.md
      → converts markdown → Slack mrkdwn
      → POSTs to webhook URL
```

## Editing topics

Just edit `topics.json` and the next cron run picks it up. Keep to 5 topics — more = expensive + noisy.

Each topic has:
- `id` — short hyphenated name (used for filenames)
- `query` — the sentence sent to `last30days`. Be sharp and specific.
- `category` — short tag (TOOLS / SKILLS / AGENTS / INFRA / STUDIO etc.)

## Manual trigger

To run the brief on demand:

```bash
~/utopia-weekly-brief/run.sh
```

Takes ~25-75 minutes (5 topics × 5-15 min each). Output streams to terminal + saves to `logs/<date>.log`.

## Cron schedule

```
0 19 * * 0  /Users/kp/utopia-weekly-brief/run.sh >> /Users/kp/utopia-weekly-brief/logs/cron.log 2>&1
```

Every Sunday at 7pm local time → brief in Slack by Monday morning.

To edit: `crontab -e`
To disable: `crontab -e` and comment out the line, or delete it.

## Cost

Per weekly run:
- ScrapeCreators usage: ~$0.50-1.00 (TikTok + Instagram + Threads queries)
- xAI Grok: ~$0.10-0.50 (synthesis pass)
- **Monthly total: ~$5-10**

Cap your xAI spend at https://console.x.ai/ to stay safe.

## Logs and cleanup

- `logs/<date>.log` — full run log per week
- `runs/<date>/` — raw last30days outputs (markdown + JSON debug data)
- `runs/<date>/brief.md` — the synthesized brief posted to Slack
- Auto-deleted after 12 weeks

## Troubleshooting

**No Slack message after a run:**
- Check `logs/<date>.log` for errors
- Verify webhook URL: `python3 post_to_slack.py /dev/stdin <<< "test"`

**A topic failed:**
- Check `logs/<date>.log` — usually a rate limit or API key issue
- Failed topics produce a placeholder `[Topic query failed — no data]` and don't block the rest

**Brief looks wrong / generic:**
- The curation prompt is in `synthesize.py` → `SYSTEM_PROMPT`
- Edit it to change voice, format, or rules
- Re-run `synthesize.py runs/<date>/` to regenerate without rerunning last30days

**xAI rate-limited:**
- xAI has tight rate limits on free tier
- Upgrade or wait

## Security

- `.env` is `chmod 600` (owner-only read)
- Webhook URL and API keys never logged
- All output is in `~/utopia-weekly-brief/` (gitignored if you ever commit this directory)
