"""
Session Summary Export Feature (Version 2)
Lucid Sharing Transparency Assistant - Team Dev Op Project
"""

import argparse
import os
import sys
from datetime import datetime, timezone

API_KEY_ENV_VAR = "LUCID_API_KEY"


ENVIRONMENTS = {
    "dev": {
        "base_url": "https://api.lucid.co/dev",
        "label": "Development",
    },
    "test": {
        "base_url": "https://api.lucid.co/test",
        "label": "Test",
    },
}


def get_environment_config(env_name):
    """Return the base URL and label for the requested environment."""
    if env_name not in ENVIRONMENTS:
        raise ValueError(
            f"Unknown environment '{env_name}'. Choose from: {list(ENVIRONMENTS)}"
        )
    return ENVIRONMENTS[env_name]


def get_api_key(cli_value=None):
    """
    Return the Lucid API key, or None if none is set.

    The environment variable is the preferred source because a key passed on
    the command line can show up in shell history and process listings.
    """
    return os.environ.get(API_KEY_ENV_VAR) or cli_value or None


def fetch_board_data(board_id, env_name="test", api_key=None):
    """
    Retrieve comments and tasks for a given Lucid board.

    If api_key is provided, this would call the real Lucid API.
    Without a key, mock data is returned so the feature can be
    tested without live credentials.
    """
    if not board_id or not str(board_id).strip():
        raise ValueError("A board ID is required.")

    if api_key:
        raise NotImplementedError(
            "Live Lucid API integration pending credential setup."
        )

    return _mock_board_data(board_id)


def _mock_board_data(board_id):
    """Sample board data used for Test-stage verification."""
    return {
        "board_id": board_id,
        "board_title": "Sprint Planning - Team Dev Op",
        "comments": [
            {
                "author": "S. Ramirez",
                "text": "Move the infrastructure diagram box left so it lines up with Stage.",
                "timestamp": "2026-09-22T14:05:00Z",
                "resolved": True,
            },
            {
                "author": "J. Okoye",
                "text": "Need to confirm which API endpoint the export feature will call.",
                "timestamp": "2026-09-22T14:12:00Z",
                "resolved": False,
            },
            {
                "author": "S. Ramirez",
                "text": "Agreed on Times New Roman 10-12 for the final report.",
                "timestamp": "2026-09-23T09:30:00Z",
                "resolved": True,
            },
        ],
        "tasks": [
            {
                "title": "Finalize Data Dictionary",
                "assignee": "J. Okoye",
                "status": "In Progress",
                "due": "2026-09-26",
            },
            {
                "title": "Draft Gantt chart update",
                "assignee": "S. Ramirez",
                "status": "Complete",
                "due": "2026-09-20",
            },
            {
                "title": "Promote export feature to Test",
                "assignee": "Christian",
                "status": "In Progress",
                "due": "2026-09-27",
            },
        ],
    }


def format_summary(board_data, env_name="test"):
    """Build a formatted Markdown summary from board data."""
    config = get_environment_config(env_name)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = []
    lines.append("# Session Summary Export")
    lines.append("")
    lines.append(f"**Board:** {board_data['board_title']} (ID: {board_data['board_id']})")
    lines.append(f"**Environment:** {config['label']}")
    lines.append(f"**Generated:** {generated_at}")
    lines.append("")

    lines.append("## Comments")
    lines.append("")
    if not board_data["comments"]:
        lines.append("_No comments found on this board._")
    else:
        for c in board_data["comments"]:
            status = "Resolved" if c["resolved"] else "Open"
            lines.append(f"- **{c['author']}** ({c['timestamp']}, {status}): {c['text']}")
    lines.append("")

    lines.append("## Tasks")
    lines.append("")
    if not board_data["tasks"]:
        lines.append("_No tasks found on this board._")
    else:
        for t in board_data["tasks"]:
            lines.append(
                f"- **{t['title']}** - assigned to {t['assignee']}, "
                f"status: {t['status']}, due: {t['due']}"
            )
    lines.append("")

    open_comments = sum(1 for c in board_data["comments"] if not c["resolved"])
    open_tasks = sum(1 for t in board_data["tasks"] if t["status"] != "Complete")
    lines.append("## Totals")
    lines.append("")
    lines.append(f"- Comments: {len(board_data['comments'])} total, {open_comments} open")
    lines.append(f"- Tasks: {len(board_data['tasks'])} total, {open_tasks} not complete")

    return "\n".join(lines)


def export_to_file(summary_text, output_path):
    """Write the formatted summary to disk."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(summary_text)
    return output_path


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Export a Lucid board's comments and tasks into one summary."
    )
    parser.add_argument("--board-id", default="BOARD-001", help="Lucid board ID")
    parser.add_argument(
        "--env", default="test", choices=list(ENVIRONMENTS), help="Target environment"
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help=f"Lucid API key (optional). Prefer the {API_KEY_ENV_VAR} environment variable.",
    )
    parser.add_argument(
        "--output", default="output/session_summary.md", help="Output file path"
    )
    args = parser.parse_args(argv)

    try:
        data = fetch_board_data(
            args.board_id, env_name=args.env, api_key=get_api_key(args.api_key)
        )
        summary = format_summary(data, env_name=args.env)
        path = export_to_file(summary, args.output)
    except NotImplementedError as err:
        print(f"Error: {err}", file=sys.stderr)
        return 2
    except (ValueError, OSError) as err:
        print(f"Error: {err}", file=sys.stderr)
        return 1

    print(f"Summary exported to {path}")
    print(f"Environment: {ENVIRONMENTS[args.env]['label']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
