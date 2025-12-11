# Investigation: Replace `script` Binary with Python `pty` Module

## Context

The `afk` framework uses the `script` command to wrap Claude Code CLI execution. This provides:
1. PTY emulation so Claude Code CLI streams properly (thinks it's in a real terminal)
2. Output capture to a log file

## Problem

**Priority: HIGH** - This limitation severely impacts debugging on macOS.

On macOS, the BSD `script` command has two critical limitations:

1. **Exit code masking:** Does not propagate the child process's exit code. Returns 0 unless `script` itself fails.
2. **Error output loss:** Error output from crashes is often not captured in the log file.

**Consequence:** If the agent crashes or exits non-zero, `Driver.run()` returns 0 AND the log file contains no error information. The framework cannot distinguish between:
- Agent completed successfully with no commit (prompt issue)
- Agent crashed/failed (process died)

This causes misleading error messages - user sees "No commit detected" with no actionable debugging path when the reality is "Agent crashed".

## Current Implementation

```python
# afk/driver.py
def _build_command(self, prompt: str, log_file: str) -> list[str]:
    claude_cmd = ["claude", "--print"]
    if self.model:
        claude_cmd.extend(["--model", self.model])
    claude_cmd.append(prompt)

    if sys.platform == "darwin":
        return ["script", "-q", log_file] + claude_cmd
    else:
        cmd_str = " ".join(shlex.quote(arg) for arg in claude_cmd)
        return ["script", "-q", "-c", cmd_str, log_file]
```

## Proposed Investigation: Python `pty` Module

Python's `pty` module provides pseudo-terminal functionality that could replace the `script` binary.

### Potential Benefits
1. **Exit code preservation** - Direct access to child process exit code
2. **Cross-platform consistency** - Same behavior on macOS and Linux
3. **More control** - Can handle signals, timeouts, and streaming more precisely
4. **No external dependency** - Pure Python stdlib

### Key Questions to Answer

1. **Does `pty.spawn()` or `pty.fork()` properly propagate exit codes?**
   - Test: spawn a process that exits with code 42, verify we get 42 back

2. **Does Claude Code CLI stream properly under Python PTY?**
   - Claude Code uses terminal detection for streaming behavior
   - Test: run `claude --print "hello"` under pty, verify streaming works

3. **Can we capture output to both terminal AND log file?**
   - `script` does this automatically
   - With `pty`, we'd need to tee the output ourselves

4. **What's the complexity vs benefit tradeoff?**
   - `script` wrapper: ~10 lines
   - `pty` implementation: estimate ~50-100 lines with proper error handling

### Implementation Sketch

```python
import os
import pty
import select
import subprocess

def run_with_pty(cmd: list[str], log_file: str, cwd: str) -> int:
    """Run command in PTY, capture output to log and terminal, return exit code."""

    master_fd, slave_fd = pty.openpty()

    with open(log_file, 'wb') as log:
        proc = subprocess.Popen(
            cmd,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            cwd=cwd,
            start_new_session=True,
        )
        os.close(slave_fd)

        try:
            while True:
                ready, _, _ = select.select([master_fd], [], [], 0.1)
                if ready:
                    try:
                        data = os.read(master_fd, 1024)
                        if not data:
                            break
                        # Write to both terminal and log
                        sys.stdout.buffer.write(data)
                        sys.stdout.buffer.flush()
                        log.write(data)
                    except OSError:
                        break
                if proc.poll() is not None:
                    break
        finally:
            os.close(master_fd)

        proc.wait()
        return proc.returncode  # This should be the REAL exit code
```

### Test Plan

1. Create test script that exits with specific codes (0, 1, 42, 137)
2. Run under current `script` wrapper - verify exit code is lost on macOS
3. Run under proposed `pty` implementation - verify exit code is preserved
4. Test with real `claude` CLI - verify streaming behavior is correct
5. Test signal handling (SIGINT, SIGTERM) - verify proper cleanup

### References

- Python `pty` module: https://docs.python.org/3/library/pty.html
- Current driver implementation: `afk/driver.py`
- Story 1.2 (Driver implementation): `docs/sprint-artifacts/1-2-driver-execute-prompt-via-script-wrapper.md`

### Decision Needed

After investigation, decide whether to:
1. **Replace `script` with `pty`** - If benefits outweigh complexity
2. **Keep `script`, accept limitation** - If `pty` has its own issues
3. **Hybrid approach** - Use `pty` on macOS, `script` on Linux

## Status

**NOT STARTED** - Created as research task for future session.
