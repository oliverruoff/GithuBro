from __future__ import annotations

import os
import shutil
import tempfile
import time
from pathlib import Path

from app.config import Config
from app.util.subprocess import run


def clone_url(repo: str) -> str:
    # gh/git obtain credentials from GH_TOKEN; never place a PAT in argv or logs.
    return f"https://github.com/{repo}.git"


def prepare_clone(config: Config, repo: str, issue_number: int) -> Path:
    basename = repo.rsplit("/", 1)[-1]
    work = Path(f"/tmp/{basename}-{issue_number}-{int(time.time())}")
    # Authenticate git without embedding the PAT in argv, remote URLs, or logs.
    askpass_dir = Path(tempfile.mkdtemp(prefix="githubro-askpass-"))
    askpass = askpass_dir / "askpass.sh"
    askpass.write_text(
        "#!/bin/sh\ncase \"$1\" in *Username*) echo x-access-token;; *) echo \"$GITHUB_PAT\";; esac\n",
        encoding="utf-8",
    )
    askpass.chmod(0o700)
    env = {
        "GH_TOKEN": config.github_pat, "GITHUB_TOKEN": config.github_pat,
        "GITHUB_PAT": config.github_pat, "GIT_ASKPASS": str(askpass),
        "GIT_TERMINAL_PROMPT": "0",
    }
    try:
        run(["git", "clone", clone_url(repo), str(work)], env=env, timeout=600)
    finally:
        shutil.rmtree(askpass_dir, ignore_errors=True)
    run(["git", "config", "user.name", "githubro[bot]"], cwd=work)
    run(["git", "config", "user.email", f"{config.username}@users.noreply.github.com"], cwd=work)
    return work


def checkout_fresh(work: Path, base: str, branch: str) -> None:
    run(["git", "checkout", base], cwd=work)
    run(["git", "pull", "--ff-only"], cwd=work)
    # A closed run may have left a branch. Remove it remotely before recreating.
    remote = run(["git", "ls-remote", "--heads", "origin", branch], cwd=work).stdout.strip()
    if remote:
        run(["git", "push", "origin", "--delete", branch], cwd=work)
    run(["git", "checkout", "-b", branch], cwd=work)


def checkout_existing(work: Path, branch: str) -> None:
    run(["git", "fetch", "origin"], cwd=work)
    run(["git", "checkout", "--track", f"origin/{branch}"], cwd=work)
    run(["git", "pull", "--ff-only", "origin", branch], cwd=work)


def remote_branch_exists(work: Path, branch: str) -> bool:
    return bool(run(["git", "ls-remote", "--heads", "origin", branch], cwd=work).stdout.strip())


def remove_worktree(work: Path | None) -> None:
    if work and work.exists() and str(work).startswith("/tmp/"):
        shutil.rmtree(work, ignore_errors=True)
