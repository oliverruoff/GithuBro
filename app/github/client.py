from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Sequence

from app.util.subprocess import run


class GitHubClient:
    def __init__(self, token: str):
        self.env = {"GH_TOKEN": token, "GITHUB_TOKEN": token}

    def command(self, args: Sequence[str], *, timeout: int = 120) -> str:
        return run(["gh", *args], env=self.env, timeout=timeout).stdout

    def json(self, args: Sequence[str]) -> Any:
        raw = self.command(args).strip()
        return json.loads(raw) if raw else None

    def body_file_command(self, args: Sequence[str], body: str) -> str:
        fd, name = tempfile.mkstemp(prefix="githubro-", suffix=".md")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(body)
            return self.command([*args, "--body-file", name])
        finally:
            Path(name).unlink(missing_ok=True)
