#!/usr/bin/env python3
"""
Posts a markdown-formatted brief to a Slack incoming webhook.

Usage:
    python3 post_to_slack.py path/to/brief.md
    echo "..." | python3 post_to_slack.py -
"""

import json
import os
import re
import sys
import urllib.request
from pathlib import Path


# -----------------------------------------------------------------------------
# Slack Block Kit conversion
# -----------------------------------------------------------------------------

def md_to_slack_mrkdwn(text: str) -> str:
    """Convert markdown to Slack mrkdwn.

    Differences:
      • **bold** → *bold*
      • [link](url) → <url|link>
      • Headers (# ##) → *bold* (Slack doesn't have headers in mrkdwn)
    """
    # Bold (do before headers since headers also use #)
    text = re.sub(r"\*\*([^*]+)\*\*", r"*\1*", text)
    # Markdown links → Slack format
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"<\2|\1>", text)
    # Headers → bold lines
    text = re.sub(r"^#{1,6}\s*(.+)$", r"*\1*", text, flags=re.MULTILINE)
    return text


def build_blocks(markdown: str) -> list:
    """Split a long markdown brief into Slack section blocks (3000-char limit each)."""
    converted = md_to_slack_mrkdwn(markdown)

    # Split by horizontal rules so each "section" of the brief is its own block
    sections = re.split(r"\n---+\n", converted)

    blocks = []
    for i, section in enumerate(sections):
        section = section.strip()
        if not section:
            continue

        # Split sections that exceed Slack's 3000-char block limit
        while len(section) > 2900:
            split_at = section.rfind("\n", 0, 2900)
            if split_at == -1:
                split_at = 2900
            blocks.append(_section(section[:split_at]))
            section = section[split_at:].lstrip()

        if section:
            blocks.append(_section(section))

        # Divider between sections
        if i < len(sections) - 1:
            blocks.append({"type": "divider"})

    return blocks


def _section(text: str) -> dict:
    return {"type": "section", "text": {"type": "mrkdwn", "text": text}}


# -----------------------------------------------------------------------------
# Posting
# -----------------------------------------------------------------------------

def post(webhook_url: str, markdown: str, fallback_text: str = "Utopia AI Brief") -> None:
    payload = {
        "text": fallback_text,  # Plain-text fallback for notifications
        "blocks": build_blocks(markdown),
    }

    req = urllib.request.Request(
        webhook_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8")
        if resp.status != 200 or body.strip() != "ok":
            raise RuntimeError(f"Slack returned {resp.status}: {body}")

    print(f"✓ Posted to Slack ({len(payload['blocks'])} blocks, {len(markdown)} chars)")


def load_env() -> str:
    """Load SLACK_WEBHOOK_URL from .env file next to this script."""
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        raise SystemExit(f"Missing {env_path}")
    for line in env_path.read_text().splitlines():
        if line.startswith("SLACK_WEBHOOK_URL="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("SLACK_WEBHOOK_URL not found in .env")


# -----------------------------------------------------------------------------
# Entry point
# -----------------------------------------------------------------------------

def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 1

    arg = sys.argv[1]
    if arg == "-":
        markdown = sys.stdin.read()
    else:
        markdown = Path(arg).read_text()

    webhook = load_env()
    fallback = markdown.splitlines()[0].strip() if markdown else "Utopia AI Brief"
    post(webhook, markdown, fallback_text=fallback[:150])
    return 0


if __name__ == "__main__":
    sys.exit(main())
