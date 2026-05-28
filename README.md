# Utopia Weekly AI Brief

Auto-curated weekly intelligence on new AI tools, open-source skills, and notable agents. Pulled from Reddit, X, Hacker News, YouTube, GitHub trending, TikTok, Instagram, and Polymarket. Posted to Slack every Monday morning.

Built for [Utopia Capital](https://github.com/The-Utopia-Studio) but the whole thing is generic — fork it and change `topics.json` for your own team.

---

## What it does

Every Sunday at 7pm local time, this system:

1. Runs `last30days` (a research skill) for 5 curated topics
2. Synthesizes the raw output via xAI Grok into one tight brief
3. Posts a Slack message with: 3 new AI tools, 3 open-source skills, 2 agent patterns, 2-3 noteworthy discussions
4. Every item includes a one-line description + a "So what" framing

You read the whole brief in 30 seconds. Links for depth.

---

## Quick start (for new team members)

You'll need:

1. **`last30days` installed**: `npx skills add mvanhorn/last30days-skill` (configured with ScrapeCreators API key)
2. **An xAI API key** (https://console.x.ai/) — drives synthesis + X search
3. **A Slack incoming webhook** for the channel you want the brief in

### Steps

```bash
# 1. Clone
git clone https://github.com/The-Utopia-Studio/weekly-ai-brief.git
cd weekly-ai-brief

# 2. Configure
cp .env.example .env
$EDITOR .env   # fill in webhook + xAI key + paths
chmod 600 .env # lock it down (it has secrets)

# 3. Test the webhook
echo "*Test*" | python3 post_to_slack.py /dev/stdin

# 4. Run once manually (takes 25-75 min)
./run.sh

# 5. Schedule weekly via cron
crontab -e
# Add this line:
# 0 19 * * 0 /path/to/weekly-ai-brief/run.sh >> /path/to/weekly-ai-brief/logs/cron.log 2>&1
```

That's it.

---

## How to contribute

This is the open team repo — anyone in The Utopia Studio org can push improvements.

### Common changes

| Change | File |
|--------|------|
| Add/remove a research topic | `topics.json` |
| Tweak the brief's voice or format | `synthesize.py` → `SYSTEM_PROMPT` |
| Adjust Slack formatting | `post_to_slack.py` → `build_blocks()` |
| Change the schedule | Your own crontab — not in the repo |

### Workflow

1. Fork or branch
2. Make the change
3. Test locally with `./run.sh` (or `python3 synthesize.py runs/<date>/` to skip the slow research step)
4. PR + describe the impact (sample brief output is helpful)

---

## Architecture

```
                  ┌────────────────────────────────────────┐
                  │  cron: Sunday 7pm → ./run.sh           │
                  └────────────────────┬───────────────────┘
                                       │
                                       ▼
                  ┌────────────────────────────────────────┐
                  │  For each topic in topics.json:        │
                  │                                        │
                  │   python3 last30days.py "<query>"      │
                  │     --emit md --deep --days 7          │
                  │                                        │
                  │   → runs/<date>/<id>.md                │
                  └────────────────────┬───────────────────┘
                                       │
                                       ▼
                  ┌────────────────────────────────────────┐
                  │  synthesize.py runs/<date>/            │
                  │   • Merges 5 topic briefs              │
                  │   • Calls xAI Grok (curation prompt)   │
                  │   • Writes runs/<date>/brief.md        │
                  └────────────────────┬───────────────────┘
                                       │
                                       ▼
                  ┌────────────────────────────────────────┐
                  │  post_to_slack.py runs/<date>/brief.md │
                  │   • Converts md → Slack mrkdwn         │
                  │   • POSTs to webhook URL               │
                  └────────────────────────────────────────┘
```

---

## Files

| File | What it does |
|------|--------------|
| `run.sh` | The cron-triggered orchestrator. Loads env, runs `last30days` × 5, calls synthesize.py, posts to Slack. |
| `synthesize.py` | Reads all 5 topic briefs, calls xAI Grok with the curation prompt, outputs the final brief. |
| `post_to_slack.py` | Converts markdown to Slack mrkdwn (Block Kit), POSTs to the incoming webhook. |
| `topics.json` | The 5 research topics. Edit this freely. |
| `SKILL.md` | Per-machine operational docs (paths, troubleshooting). |
| `.env.example` | Template. Copy to `.env` and fill in. |
| `.gitignore` | Keeps secrets and per-machine state out of git. |

---

## Cost

Per weekly run:

- **ScrapeCreators**: ~$0.50-1.00 (TikTok + Instagram queries)
- **xAI Grok**: ~$0.10-0.50 (synthesis pass)
- **Monthly total: ~$5-10**

Cap your xAI spend at [https://console.x.ai/](https://console.x.ai/) to stay safe.

---

## Why this exists

Karan (GP at Utopia) was getting overwhelmed by the firehose of new AI tools / skills / agents launching every week. Reading every Reddit thread, every X post, every HN front-page submission isn't a viable strategy. But missing the genuinely-useful stuff has real cost — for Utopia's own AI work, for portcos, and for fellows.

This brief is the compromise: spend 30 seconds on Monday morning instead of 30 hours across the week.

The "So what" framing is non-negotiable. A list of new tools without context is just noise. Each item explains why it matters to Utopia specifically.

---

## Future ideas

PRs welcome. Things on the wishlist:

- [ ] **Topic-specific channels** — route different topic categories to different Slack channels (e.g. `#utopia-ai-tools` vs `#utopia-portco-news`)
- [ ] **Reply threading** — first message is the brief, replies in-thread expand each item
- [ ] **Notion archive** — append every brief to a running Notion database for searchability
- [ ] **"Hot take" section** — let a named agent (Khalil / Ada) add an opinionated reaction at the end
- [ ] **Multi-language** — Arabic translation for the GCC team
- [ ] **Per-fellow custom briefs** — each fellow's `topics.json` tailored to their portco's domain

---

## License

MIT. Use it, fork it, share it.
