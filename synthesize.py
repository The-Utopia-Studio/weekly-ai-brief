#!/usr/bin/env python3
"""
Synthesize a weekly The Utopia Studio AI brief from last30days outputs.

Reads:  runs/<date>/<topic-id>.md  (5 markdown briefs from last30days)
Output: A Slack-ready markdown brief that curates the top items across topics.

Calls xAI Grok via the OpenAI-compatible API for the synthesis pass.

Usage:
    python3 synthesize.py runs/2026-05-28
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import date
from pathlib import Path


BRIEF_DIR = Path(__file__).parent
ENV_PATH = BRIEF_DIR / ".env"


# -----------------------------------------------------------------------------
# Env loading
# -----------------------------------------------------------------------------

def load_env() -> dict:
    if not ENV_PATH.exists():
        raise SystemExit(f"Missing {ENV_PATH}")
    out: dict[str, str] = {}
    for line in ENV_PATH.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip()
    return out


# -----------------------------------------------------------------------------
# xAI synthesis
# -----------------------------------------------------------------------------

SYSTEM_PROMPT = """You are Karan Pinto's weekly AI radar editor. Karan is CGTO (Chief Growth & Technology Officer) at The Utopia Studio, a Qatar-based venture studio.

You receive 5 raw research briefs across these categories:
  1. New AI coding tools / IDE agents / developer assistants
  2. New open-source Claude/Cursor/agent skills on GitHub
  3. New AI agents, agent frameworks, notable demos
  4. AI infrastructure, model launches, MCP servers
  5. AI strategy moves by VC firms / venture studios / portfolio AI news

Your job: produce ONE concise, opinionated Slack-ready brief.

OUTPUT FORMAT (strict — match exactly):

*🤖 The Utopia Studio — AI Brief, Week of {DATE}*

*🆕 NEW AI TOOLS (3)*

• *<tool name>* — one-line what it does
  <link> · _So what:_ why this matters for The Utopia Studio or its portcos (one sentence)

• [next tool ...]

---

*🔧 OPEN-SOURCE SKILLS (3)*

• *<skill name>* — one-line
  <github link> · _So what:_ would this slot into our marketplace? Why?

---

*🤖 NEW AGENTS & PATTERNS (2)*

• *<agent or pattern>* — one-line
  <link> · _So what:_ what does it advance for our agent system (Ada, Khalil, Salim)?

---

*🔥 DISCUSSIONS TO KNOW (2-3)*

• *<headline>* — one-sentence summary of the conversation and why it matters

---

📊 Sources: Reddit, X, HN, YouTube, GitHub, TikTok, Polymarket
🔗 Raw: <full_brief_link>

RULES:
- Exactly 3 + 3 + 2 + 2-3 items. Cut ruthlessly if more candidates.
- Each "So what" must say something specific to The Utopia Studio, not generic ("could be useful").
- Karan dislikes: buzzwords (revolutionizing, game-changing), generic AI promises, vague claims, padding.
- Prefer Tier-1 (new this week) over Tier-2 (resurfaced).
- If a category has truly nothing worth including, say "Nothing worth surfacing this week" and explain why in one line. Don't pad.
- Markdown is Slack mrkdwn (single * for bold, <url|text> for links — but YOU output regular markdown and the poster handles the conversion).
- Brevity is mandatory. The whole brief should be readable in 30 seconds.
"""


def synthesize(env: dict, run_dir: Path) -> str:
    """Call xAI Grok with the combined topic briefs and return the curated markdown."""
    xai_key = env.get("XAI_API_KEY") or os.environ.get("XAI_API_KEY")
    if not xai_key:
        raise SystemExit("XAI_API_KEY not configured")

    # Load all topic briefs
    topics_config = json.loads((BRIEF_DIR / "topics.json").read_text())
    topic_briefs = []
    for topic in topics_config["topics"]:
        brief_path = run_dir / f"{topic['id']}.md"
        if brief_path.exists():
            content = brief_path.read_text()
            topic_briefs.append(
                f"### {topic['category']}: {topic['query']}\n\n{content}\n\n"
            )
        else:
            topic_briefs.append(
                f"### {topic['category']}: {topic['query']}\n\n[No output — query failed]\n\n"
            )

    user_prompt = (
        f"DATE: {date.today().strftime('%B %-d, %Y')}\n\n"
        f"Here are the 5 raw research briefs from last30days for this week. "
        f"Curate them into a single Slack-ready brief following the format above.\n\n"
        + "\n---\n".join(topic_briefs)
    )

    payload = {
        "model": "grok-4-fast-reasoning",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.4,
    }

    req = urllib.request.Request(
        "https://api.x.ai/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {xai_key}",
            "Content-Type": "application/json",
        },
    )

    print(f"[synth] Calling xAI Grok with {len(user_prompt)} chars of context...", file=sys.stderr)
    with urllib.request.urlopen(req, timeout=180) as resp:
        result = json.loads(resp.read().decode("utf-8"))

    return result["choices"][0]["message"]["content"].strip()


# -----------------------------------------------------------------------------
# Entry point
# -----------------------------------------------------------------------------

def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 1

    run_dir = Path(sys.argv[1]).resolve()
    if not run_dir.is_dir():
        raise SystemExit(f"Not a directory: {run_dir}")

    env = load_env()
    brief = synthesize(env, run_dir)

    # Save the synthesized brief
    out_path = run_dir / "brief.md"
    out_path.write_text(brief)
    print(f"[synth] Wrote {out_path} ({len(brief)} chars)", file=sys.stderr)

    # Print to stdout so run.sh can pipe it
    print(brief)
    return 0


if __name__ == "__main__":
    sys.exit(main())
