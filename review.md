1. `Driver` refuses to construct unless a real `claude` binary exists (`afk/driver.py:17-29`), breaking unit tests that inject a fake CLI and blocking use on machines without the CLI installed.
2. PATH check shells out to `which` (`afk/driver.py:20`); `which` is absent on minimal images, causing `FileNotFoundError` before any work. Use `shutil.which` and allow caller-provided env.
3. `Driver.run` no longer handles `KeyboardInterrupt` (`afk/driver.py:46-65`); ^C now raises to the caller instead of returning an exit code, violating “method blocks until process exits.”
4. `commits_between` now always uses `--first-parent --ancestry-path` (`afk/git.py:81-104`), silently dropping commits from merged branches despite the method’s promise to return the full range.
5. `commits_between(None, …)` now calls `root_commit()` which raises on multi-root repos (`afk/git.py:67-104`); many real histories have multiple roots, so this introduces spurious failures where the previous code worked.
6. Pytest is forced to `-q --tb=short` globally (`pyproject.toml:12-14`), hiding diagnostics and making already brittle tests harder to debug without justification.
