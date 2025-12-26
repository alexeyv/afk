#!/usr/bin/env python3
"""
Tracer Bullet: Minimal 1-turn validation of the afk framework.

This script validates the driver works end-to-end with real Claude Code CLI.
It creates a hello.py file in a fresh workspace directory.

Usage:
    python examples/tracer_bullet.py [workspace_path]

If workspace_path is not provided, uses ~/runs/tracer-{timestamp}/
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def _configure_claude_permissions(workspace: Path) -> None:
    """Configure Claude CLI to allow file operations without interactive prompts.

    For autonomous operation, Claude needs pre-approved permissions. This creates
    a .claude/settings.local.json that allows the tools needed for basic file
    creation and git operations.
    """
    claude_dir = workspace / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)

    settings = {
        "permissions": {
            "allow": [
                "Bash(git commit:*)",
                "Bash(git add:*)",
                "Bash(git status:*)",
                "Write",
            ]
        }
    }

    settings_file = claude_dir / "settings.local.json"
    settings_file.write_text(json.dumps(settings, indent=2) + "\n")


def main() -> int:
    # Determine workspace path
    if len(sys.argv) > 1:
        workspace = Path(sys.argv[1]).expanduser().resolve()
    else:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        workspace = Path.home() / "runs" / f"tracer-{timestamp}"

    print("=== Tracer Bullet: Hello World Session ===")
    print(f"Workspace: {workspace}")
    print()

    # 1. Create workspace directory (MUST exist before Git/Session)
    workspace.mkdir(parents=True, exist_ok=True)
    print("✓ Workspace directory created")

    # 2. Import afk components (late import to catch import errors clearly)
    try:
        from afk import Driver, Git, Session, TransitionType
    except ImportError as e:
        print(f"✗ Failed to import afk: {e}")
        print("  Ensure afk is installed: pip install -e .")
        return 1

    # 3. Check environment (Driver checks git, script, claude on PATH)
    try:
        driver = Driver(workspace)
        print("✓ Driver initialized (environment checks passed)")
    except RuntimeError as e:
        print(f"✗ Driver initialization failed: {e}")
        return 1

    # 4. Initialize Git (takes str, not Path!)
    git = Git(str(workspace))
    print("✓ Git initialized")

    # 5. Create session with unique name (this initializes git repo if empty)
    session_name = f"tracer_{datetime.now().strftime('%H%M%S')}"
    try:
        session = Session(workspace, session_name, driver, git)
        print(f"✓ Session created: {session_name}")
        print(f"  Session start tag: afk-{session_name}-0")
    except RuntimeError as e:
        print(f"✗ Session creation failed: {e}")
        return 1

    # 6. Configure Claude permissions for autonomous operation (after git init)
    _configure_claude_permissions(workspace)
    print("✓ Claude permissions configured")

    # 7. Read prompt from examples/prompts/hello_world.md
    prompt_path = Path(__file__).parent / "prompts" / "hello_world.md"
    if not prompt_path.exists():
        print(f"✗ Prompt file not found: {prompt_path}")
        return 1

    prompt = prompt_path.read_text()
    print(f"✓ Prompt loaded from {prompt_path.name}")
    print()

    # 8. Execute one turn
    print("Executing turn with Claude Code CLI...")
    print("-" * 40)
    try:
        result = session.execute_turn(prompt, TransitionType("init"))
    except RuntimeError as e:
        print(f"✗ Turn execution failed: {e}")
        return 1

    print("-" * 40)
    print()

    # 9. Display TurnResult
    print("=== Turn Result ===")
    print(f"Outcome:     {result.outcome}")
    print(f"Turn Number: {result.turn_number}")
    print(f"Commit Hash: {result.commit_hash}")
    print("Message:")
    for line in result.message.split("\n"):
        print(f"  {line}")
    print()

    # 10. Verify git tags exist
    print("=== Git Tag Verification ===")
    tag_start = f"afk-{session_name}-0"
    tag_turn1 = f"afk-{session_name}-1"

    tags_output = subprocess.run(
        ["git", "tag", "-l", f"afk-{session_name}-*"],
        cwd=workspace,
        capture_output=True,
        text=True,
    )
    existing_tags = (
        tags_output.stdout.strip().split("\n") if tags_output.stdout.strip() else []
    )

    tag_start_exists = tag_start in existing_tags
    tag_turn1_exists = tag_turn1 in existing_tags

    print(f"Tag {tag_start}: {'✓ exists' if tag_start_exists else '✗ missing'}")
    print(f"Tag {tag_turn1}: {'✓ exists' if tag_turn1_exists else '✗ missing'}")
    print()

    # 11. Verify hello.py exists and works
    print("=== File Verification ===")
    hello_path = workspace / "hello.py"
    if hello_path.exists():
        print(f"✓ hello.py exists at {hello_path}")

        # Run hello.py
        run_result = subprocess.run(
            [sys.executable, "hello.py"],
            cwd=workspace,
            capture_output=True,
            text=True,
        )
        output = run_result.stdout.strip()
        print(f"  Output: {output!r}")

        if "hello world" in output.lower():
            print("✓ Output contains 'hello world'")
        else:
            print("✗ Expected output to contain 'hello world'")
    else:
        print(f"✗ hello.py not found at {hello_path}")
    print()

    # 12. Show git log
    print("=== Git Log ===")
    log_result = subprocess.run(
        ["git", "log", "--oneline", "-3"],
        cwd=workspace,
        capture_output=True,
        text=True,
    )
    print(log_result.stdout)

    # 13. Final summary
    print("=== Summary ===")
    success = (
        result.outcome == "success"
        and tag_start_exists
        and tag_turn1_exists
        and hello_path.exists()
    )

    if success:
        print("✓ Tracer bullet PASSED - Framework working end-to-end!")
        return 0
    else:
        print("✗ Tracer bullet FAILED - Check output above for details")
        return 1


if __name__ == "__main__":
    sys.exit(main())
