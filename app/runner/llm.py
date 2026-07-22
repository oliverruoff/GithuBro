from __future__ import annotations

import json
import logging
import os
import queue
import shlex
import subprocess
import threading
import time
from dataclasses import dataclass

from app.config import Config
from app.github.client import GitHubClient
from app.modes import Mode
from app.runner.heartbeat import Heartbeat
from app.runner.setup import SetupResult

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class LLMResult:
    exit_code: int
    timed_out: bool
    stdout: str
    stderr: str
    runtime_seconds: float


def reasoning_args(pi_args: list[str], effort: str) -> list[str]:
    if "--reasoning-effort" in pi_args or "--thinking" in pi_args:
        return []
    model = ""
    if "--model" in pi_args:
        index = pi_args.index("--model")
        if index + 1 < len(pi_args):
            model = pi_args[index + 1].lower()
    if model.startswith(("openai/", "o3", "o4", "gpt-5", "kimi-coding/", "minimax-coding/", "minimax/")):
        return ["--reasoning-effort", effort]
    if model.startswith(("anthropic/", "claude")):
        return ["--thinking", {"low": "low", "medium": "medium", "high": "max"}[effort]]
    if model:
        log.warning("unknown provider; reasoning effort not appended")
    return []


def command(config: Config) -> list[str]:
    extra = shlex.split(config.pi_args)
    return [
        "pi", "--mode", "rpc", "--no-extensions", "--skill", "/workspace/skills",
        "--extension", "/root/.pi/agent/extensions/github-comment.ts",
        "--extension", "/root/.pi/agent/extensions/github-list-issues.ts",
        "--extension", "/root/.pi/agent/extensions/github-list-pr-comments.ts",
        "--extension", "/root/.pi/agent/extensions/github-create-branch.ts",
        "--extension", "/root/.pi/agent/extensions/github-create-pr.ts",
        "--extension", "/root/.pi/agent/extensions/github-update-pr.ts",
        *extra, *reasoning_args(extra, config.reasoning_effort),
    ]


def build_prompt(config: Config, setup: SetupResult) -> str:
    candidate, issue = setup.candidate, setup.issue
    pr_url = candidate.pr["url"] if candidate.pr else "none"
    common = f"""You are working inside the githubro work tree at: {setup.work}

Repository: {candidate.repo}
Issue: #{issue['number']} — {issue['title']}
Mode: {candidate.mode.value}
Base branch: {config.base_branch}
Your branch: {setup.branch} ({'created now' if candidate.mode == Mode.FRESH else 'already checked out'})
PR target: {config.pr_target}
PR (if any): {pr_url}
Working user: {config.username}

The full issue context (body, comments, repo structure, PR state) is in
`.githubro/issue_context.md`. Read it first.
"""
    nr = issue["number"]
    if candidate.mode == Mode.FRESH:
        job = f"""Your job:
1. Read `.githubro/issue_context.md` carefully.
2. Make the smallest correct change that resolves the issue. Add or update tests if the repo has a test setup.
3. Commit with `agent(#{nr}): <imperative summary>`, then push with `git push -u origin {setup.branch}`.
4. Open a PR with `github_create_pr` against `{config.pr_target}`, then set its body with `github_update_pr` using the mandatory format below.
5. Post one final issue comment beginning `[githubro:agent][outcome:success]`, include the PR URL, and end with `@{config.username}` on its own line.
"""
    elif candidate.mode == Mode.REVISION:
        job = f"""Your job:
1. Read the context, especially "User feedback since last githubro activity".
2. Stay on `{setup.branch}` and address every feedback item. Do not create a branch or PR.
3. If feedback is unclear, make no changes; post `[githubro:agent][outcome:clarification]` with a specific question ending in `@{config.username}` on its own line, then exit cleanly.
4. Commit with `agent(#{nr}): <imperative summary>`, push with `git push origin {setup.branch}`, and update PR {pr_url} using `github_update_pr`.
5. Post `[githubro:agent][outcome:success]` summarizing the revision and ending in `@{config.username}` on its own line.
"""
    else:
        job = f"""Your job:
1. Audit PR {pr_url} against the issue, using "Last diff" and "Linked PR".
2. Stay on `{setup.branch}`. Do not create a branch or PR.
3. Review correctness, edge cases, races, tests, documentation, and PR-body accuracy.
4. If issues are found, make minimal fixes, commit with `agent(#{nr}): <imperative summary>`, push, update the PR body, and post `[githubro:agent][outcome:success]` describing the fixes.
5. If no issues are found, refresh/confirm the PR body with `github_update_pr` and post `[githubro:agent][outcome:audit-passed]` stating that the audit passed.
6. If user input is needed, make no changes and post `[githubro:agent][outcome:clarification]` with the question.
Every issue comment must end in `@{config.username}` on its own line.
"""
    constraints = f"""Hard constraints:
- Never modify the base branch, force-push, expose credentials, touch another repository, or change the PR target.
- Never guess when requirements are unclear; use the clarification outcome.
- Do not leave uncommitted work when asking for clarification.
- The PR title and every commit must reference issue #{nr}.
- If the run exceeds {config.run_timeout} seconds, you will be terminated.

Mandatory PR body:
## What
- 1–6 factual change bullets

## Why
Fixes #{nr}.
One sentence tying the change to the issue.

## How
- Reviewer-relevant implementation bullets, or exactly: No implementation notes.

## Test plan
- [ ] At least one concrete verification step

<sub>generated by githubro ({candidate.mode.value} run)</sub>
"""
    return common + "\n" + job + "\n" + constraints


def run_llm(client: GitHubClient, config: Config, setup: SetupResult) -> LLMResult:
    env = os.environ.copy()
    env.update({
        "GH_TOKEN": config.github_pat, "GITHUB_TOKEN": config.github_pat,
        "GITHUB_PAT": config.github_pat, "GITHUB_REPO": setup.candidate.repo,
        "GITHUB_ISSUE_NUMBER": str(setup.issue["number"]),
        "GITHUB_USERNAME": config.username, "GITHUB_PR_TARGET": config.pr_target,
    })
    started = time.monotonic()
    heartbeat = Heartbeat(client, config, setup.candidate.repo, setup.issue["number"])
    process = subprocess.Popen(
        command(config), cwd=setup.work, env=env, text=True,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        bufsize=1, start_new_session=True,
    )
    heartbeat.start()
    stdout_lines: list[str] = []
    stderr_lines: list[str] = []
    finished = threading.Event()

    def read_stdout() -> None:
        assert process.stdout is not None
        try:
            for line in process.stdout:
                stdout_lines.append(line)
                try:
                    event = json.loads(line)
                    if event.get("type") == "agent_settled":
                        finished.set()
                except json.JSONDecodeError:
                    pass
        finally:
            if process.poll() is not None:
                finished.set()

    def read_stderr() -> None:
        assert process.stderr is not None
        stderr_lines.extend(process.stderr.readlines())

    out_thread = threading.Thread(target=read_stdout, daemon=True)
    err_thread = threading.Thread(target=read_stderr, daemon=True)
    out_thread.start(); err_thread.start()
    assert process.stdin is not None
    process.stdin.write(json.dumps({"type": "prompt", "message": build_prompt(config, setup)}) + "\n")
    process.stdin.flush()
    timed_out = not finished.wait(config.run_timeout)
    if process.poll() is None:
        if timed_out:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
        else:
            try:
                process.stdin.write(json.dumps({"type": "abort"}) + "\n")
                process.stdin.flush()
            except (BrokenPipeError, OSError):
                pass
            process.terminate()
    try:
        exit_code = process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill(); exit_code = process.wait()
    heartbeat.stop()
    out_thread.join(timeout=2); err_thread.join(timeout=2)
    return LLMResult(exit_code, timed_out, "".join(stdout_lines), "".join(stderr_lines), time.monotonic() - started)
