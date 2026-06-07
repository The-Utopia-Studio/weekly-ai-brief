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

Your job: produce ONE highly-selective, opinionated Slack-ready brief. Karan reads this in 20 seconds. Less is more.

OUTPUT FORMAT (strict — match exactly):

*🤖 The Utopia Studio — AI Brief, Week of {DATE}*

*🆕 TOOLS (max 2)*

• *<tool name>* — one-line what it does · [link](URL) · _So what:_ specific Utopia-relevant insight (one sentence)

---

*🔧 SKILLS (max 2)*

• *<skill name>* — one-line · [github](URL) · _So what:_ would this slot into our marketplace? Why?

---

*🤖 AGENTS (max 1)*

• *<agent or pattern>* — one-line · [link](URL) · _So what:_ how does it advance Ada/Khalil/Salim?

---

*🔥 DISCUSSION (1, optional)*

• *<headline>* — one-sentence summary + why it matters

SELECTION RULES (be ruthless):
- **Max 6 items total across the whole brief.** Cut anything that doesn't earn a Karan reaction.
- **Quality bar:** would Karan forward this to a fellow / portco / Maxime? If no, cut it.
- **One link per item maximum.** No "(via Reddit, also on HN, see TikTok)" — pick the canonical source.
- **No source footer, no "Raw:" link.** Removed for brevity.
- **No padding categories.** If skills or agents have nothing real this week, OMIT THE SECTION ENTIRELY. Better to have just 3 great items than 6 mediocre ones.
- **Multi-source corroboration > single mention.** Prefer items that appeared in 2+ source briefs.

CONTENT RULES:
- Each "So what" must be specific to The Utopia Studio (mention Ada/Khalil/Salim, the marketplace, Cobuild modules M1-M9, portcos, fellows, or Karan's specific stack). NEVER generic ("could be useful", "interesting development").
- Karan dislikes: buzzwords (revolutionizing, game-changing), generic AI promises, vague claims, padding, TikTok-only links when GitHub/X exists.
- Prefer Tier-1 (released this week) over Tier-2 (existing tools getting attention).
- Markdown is Slack mrkdwn (single * for bold, [text](url) → poster converts to <url|text> automatically).
- Brevity is mandatory.
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
