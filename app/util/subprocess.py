from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence


class CommandError(RuntimeError):
    pass


@dataclass(frozen=True)
class CommandResult:
    stdout: str
    stderr: str
    returncode: int


def run(
    args: Sequence[str], *, cwd: Path | str | None = None,
    env: Mapping[str, str] | None = None, timeout: int = 120,
) -> CommandResult:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    try:
        completed = subprocess.run(
            list(args), cwd=cwd, env=merged_env, text=True,
            capture_output=True, timeout=timeout, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CommandError(f"command failed: {args[0]}: {exc}") from exc
    result = CommandResult(completed.stdout, completed.stderr, completed.returncode)
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        raise CommandError(f"command failed ({result.returncode}): {args[0]}: {detail}")
    return result
