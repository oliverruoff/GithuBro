<p align="center">
  <img src="githubro_icon.png" alt="GithuBro icon" width="220">
</p>

<h1 align="center">GithuBro</h1>

<p align="center">
  A minimal, self-hosted worker that turns labelled GitHub issues into pull requests.
</p>

GithuBro watches selected repositories for open issues labelled `agent`. At each
polling tick, it selects at most one issue, creates a clean temporary checkout,
and asks the [pi coding agent](https://github.com/earendil-works/pi) to implement
the requested change or review an existing pull request.

GitHub itself is the state store: labels act as the state machine, while
structured issue comments form a durable event log. No database or persistent
worktree is required.

## How it works

Each run consists of four phases:

1. **Poll:** Find the oldest eligible issue across all configured repositories.
2. **Setup:** Lock the issue, post a start message, clone the repository, and
   prepare the correct branch and issue context.
3. **Agent run:** Invoke pi in headless RPC mode. A background worker posts
   heartbeat comments during long-running tasks.
4. **Cleanup:** Reconstruct the outcome from GitHub, transition labels, and
   remove the temporary checkout.

GithuBro supports three deterministic modes:

| Mode | Condition | Behaviour |
|---|---|---|
| `fresh` | No open matching PR exists | Create a new `agent/<issue>-<slug>` branch and PR |
| `revision` | An open PR exists and newer user feedback is present | Continue on the existing PR branch |
| `self-audit` | An open PR exists without newer feedback | Review and, if necessary, repair the existing implementation |

Only Phase 3 invokes the language model. An idle polling tick consumes no model
tokens.

## Requirements

- Linux host with Docker
- GitHub Personal Access Token with `repo` permissions
- Model-provider credentials supported by pi
- Permission for the PAT to create labels. On startup, GithuBro idempotently
  creates `agent`, `agent-in-progress`, and `agent-done` when they are missing.

## Quickstart

Clone the repository and create the environment file:

```bash
git clone https://github.com/oliverruoff/githubro.git
cd githubro
cp .env.example .env
```

At minimum, configure:

```dotenv
GITHUB_PAT=ghp_replace_me
GITHUB_REPOS=owner/repository,owner/another-repository
PI_ARGS=--model openai/gpt-5
OPENAI_API_KEY=replace_me
```

Then deploy:

```bash
chmod +x deploy.sh
./deploy.sh
```

Add the `agent` label to an open issue. With the default configuration, the
worker picks it up at the next local quarter-hour boundary (`00`, `15`, `30`, or
`45`).

## Installation runbook for AI agents

This section is an operational contract for an AI or coding agent asked to
install GithuBro. A user should be able to point an agent at this README and say
“install this for me.” The agent should then follow the workflow below from
discovery through verification.

### Safety rules

- Never invent credentials, repository names, usernames, branches, or provider
  settings.
- Never print secrets in chat, terminal output, logs, command arguments, Git
  history, or process listings.
- Never commit `.env`; create it with file mode `600`.
- Only inspect existing credential files the user explicitly identifies or
  authorizes. Do not search the entire home directory for secrets.
- Reuse existing provider settings only after confirming that the user wants the
  same provider and model.
- Before replacing an existing `githubro` container or `.env`, inspect it and
  preserve its configuration. Ask before overwriting unrelated or ambiguous
  resources.
- Do not create a test issue, trigger a paid model call, or modify repository
  content unless the user explicitly asks for an end-to-end test.

### 1. Discover the target environment

The agent should determine as much as possible with read-only checks before
asking questions:

1. Identify the target host, SSH user, and installation directory. Default to
   `~/githubro` only when the user has not requested another location.
2. Confirm that the host is Linux and that `git` and a running Docker daemon are
   available.
3. Check whether the installation directory, `github-bro:latest` image, or
   `githubro` container already exists.
4. Check whether an explicitly authorized existing `.env` contains reusable
   GitHub or provider configuration. Read variable names first; do not display
   their values.
5. Confirm that the target host can reach GitHub, npm, the selected model
   provider, and Docker package registries.

If Docker or Git is missing, explain what must be installed and request approval
before changing system packages. Do not silently use `sudo`.

### 2. Collect required decisions and secrets

After discovery, ask one concise, consolidated set of questions for all values
that could not be determined safely:

| Input | What the agent should ask | How the user obtains it |
|---|---|---|
| Target host | Hostname/IP and SSH username; ask for an authentication method if no working session exists | From the user's server or home-network configuration |
| `GITHUB_PAT` | A GitHub PAT with access to every watched repository and permission to read/write issues, labels, branches, and pull requests | GitHub → Settings → Developer settings → Personal access tokens. The user must create/copy it; the agent must not expose it |
| `GITHUB_REPOS` | Optional. Exact comma-separated `owner/repo` entries to watch. Leave empty to watch every active, non-fork repository owned by `GITHUB_USERNAME`. | From the URLs of the desired GitHub repositories |
| `GITHUB_USERNAME` | GitHub handle that should receive issue mentions | The user's GitHub profile/login |
| Provider/model | Which pi provider and model to use, or whether an existing pi configuration should be reused | From the user's existing pi setup or the chosen provider's model documentation |
| Provider credential | The environment variable and API key required by that provider, for example `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or `MINIMAX_API_KEY` | The provider's API-key/account console |
| Base/target branch | Whether the defaults (`main`) are correct for every watched repository | From each repository's default-branch settings |

The agent may reuse values from an authorized existing environment file, such as
another pi installation, by copying only the required keys. It must tell the
user which **variable names** it plans to reuse, never their values. At minimum,
GithuBro requires `GITHUB_PAT`; `GITHUB_REPOS` is optional and defaults to every
repository owned by `GITHUB_USERNAME`. A usable deployment also needs `PI_ARGS`
plus the selected provider's credential.

If the user has no PAT or provider key yet, pause and guide them to the relevant
account settings. Do not accept secrets committed to a repository. Prefer a
secure secret-input mechanism or direct creation on the target host over sending
secrets in chat.

### 3. Validate the proposed configuration

Before deployment, validate without revealing values:

- Every `GITHUB_REPOS` entry matches `owner/repo` and is reachable with the PAT.
- The authenticated GitHub login matches the intended account.
- The PAT can read issues and labels for every configured repository.
- `PI_ARGS` includes a provider/model selection supported by pi.
- The matching provider credential is present.
- `BRO_REASONING_EFFORT` is one of `low`, `medium`, or `high`.
- `BRO_HEARTBEAT_STALE_AFTER_SECONDS` is greater than
  `BRO_HEARTBEAT_INTERVAL_SECONDS`.
- The configured base and PR target branches exist.

Report validation as booleans or account/repository names. Never echo token or
API-key values.

### 4. Install and configure

For a new installation, run the equivalent of:

```bash
git clone https://github.com/oliverruoff/GithuBro.git ~/githubro
cd ~/githubro
cp .env.example .env
chmod 600 .env
```

Populate `.env` with the confirmed values. Include only required variables,
selected overrides, and the chosen provider credentials. A typical file is:

```dotenv
GITHUB_PAT=<secret>
GITHUB_REPOS=owner/repository,owner/another-repository
GITHUB_USERNAME=owner
GITHUB_BASE_BRANCH=main
GITHUB_PR_TARGET=main

PI_ARGS=--provider <provider> --model <model>
<PROVIDER_API_KEY_VARIABLE>=<secret>
BRO_REASONING_EFFORT=medium

BRO_POLL_INTERVAL_SECONDS=900
BRO_HEARTBEAT_INTERVAL_SECONDS=1200
BRO_HEARTBEAT_STALE_AFTER_SECONDS=2700
BRO_RUN_TIMEOUT_SECONDS=5400
BRO_LOG_LEVEL=INFO
```

For an existing installation, use `git status` before pulling. Preserve local
changes and the existing `.env`; never reset or discard them automatically.
Update with `git pull --ff-only` only when the worktree is safe.

GithuBro automatically creates missing workflow labels in every configured
repository during startup. The equivalent manual commands are shown below for
troubleshooting or installations whose PAT cannot create labels:

```bash
gh label create agent --repo owner/repository --color FBCA04 \
  --description "Queue for githubro"
gh label create agent-in-progress --repo owner/repository --color D4C5F9 \
  --description "githubro is processing this issue"
gh label create agent-done --repo owner/repository --color 0E8A16 \
  --description "githubro completed this issue"
```

Existing labels are preserved. During verification, the installing agent should
confirm that automatic provisioning succeeded and report which labels GithuBro
created.

### 5. Deploy

Run:

```bash
cd ~/githubro
chmod +x deploy.sh
./deploy.sh
```

The script pulls with fast-forward-only semantics, rebuilds pi with a cache
buster, replaces only the `githubro` container, loads `.env`, and starts the
container with `--restart unless-stopped`.

If the build fails, stop and diagnose the concrete error. Do not repeatedly
rebuild without changing anything, run broad Docker cleanup commands, or delete
unrelated images and containers.

### 6. Verify the deployment

Installation is complete only after all checks below pass:

```bash
docker ps --filter name=^/githubro$
docker inspect githubro --format \
  'running={{.State.Running}} restarting={{.State.Restarting}} restarts={{.RestartCount}}'
docker logs --tail 50 githubro
docker exec githubro pi --version
```

The agent must additionally verify, without exposing secrets:

1. The container is running and not restart-looping.
2. Logs contain `next tick in ... seconds` and no configuration exception.
3. `pi --version` succeeds inside the container.
4. A GitHub API request through the worker's configured PAT succeeds.
5. Every watched repository is reachable and has all three workflow labels.
6. A manual call to the deterministic polling function returns `no candidates`
   when no issue is queued. This confirms polling without invoking the model.

An end-to-end model test is optional and potentially billable. Perform it only
with explicit user approval by creating or selecting a real test issue and
adding `agent`.

### 7. Hand-off to the user

Conclude with a concise deployment report containing:

- Host and installation path
- Container and image names
- Running/restart status
- Watched repositories
- Provider and model names, but no credentials
- GitHub account used for authentication
- Label readiness per repository
- Next scheduled tick
- Any warnings, skipped checks, or remaining user action

Never include `.env` contents, tokens, API keys, or passwords in the hand-off.

## Configuration

All runtime configuration is provided through `.env`.

### Required

| Variable | Description |
|---|---|
| `GITHUB_PAT` | GitHub PAT used for issues, comments, branches, and pull requests |
| `GITHUB_REPOS` | Optional. Comma-separated repositories in `owner/repo` format. When unset or empty, the worker watches every active, non-fork repository owned by `GITHUB_USERNAME` (default `oliverruoff`). |

### GitHub workflow

| Variable | Default | Description |
|---|---|---|
| `GITHUB_USERNAME` | `oliverruoff` | User mentioned in issue notifications |
| `GITHUB_LABEL_TRIGGER` | `agent` | Queued-work label |
| `GITHUB_LABEL_IN_PROGRESS` | `agent-in-progress` | Active-run lock label |
| `GITHUB_LABEL_DONE` | `agent-done` | Successful-run label |
| `GITHUB_BASE_BRANCH` | `main` | Base branch for fresh work |
| `GITHUB_PR_TARGET` | Value of `GITHUB_BASE_BRANCH` | Pull-request target branch |

### Agent and scheduling

| Variable | Default | Description |
|---|---|---|
| `PI_ARGS` | Unset | Additional pi arguments, especially `--model provider/model` |
| `BRO_REASONING_EFFORT` | `medium` | Reasoning level: `low`, `medium`, or `high` |
| `BRO_POLL_INTERVAL_SECONDS` | `900` | Polling interval; production runs remain quarter-hour aligned |
| `BRO_HEARTBEAT_INTERVAL_SECONDS` | `1200` | Interval between heartbeat comments |
| `BRO_HEARTBEAT_STALE_AFTER_SECONDS` | `2700` | Age after which an interrupted run is recovered |
| `BRO_RUN_TIMEOUT_SECONDS` | `5400` | Hard timeout for one pi run |
| `BRO_LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, or `ERROR` |

Provider credentials such as `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` are passed
through to pi and are never validated or persisted by GithuBro.

## Label lifecycle

```text
agent
  └─ picked up ──> agent-in-progress
                       ├─ success/audit passed ──> agent-done
                       └─ clarification/error ───> agent
```

`agent-in-progress` is the distributed lock. If a container stops during an
agent run, the next worker detects stale runner activity, posts a recovery
comment, removes leftover temporary worktrees, and re-queues the issue.

To request another pass after a successful run, remove `agent-done` and add
`agent` again. New feedback selects revision mode; otherwise GithuBro performs a
self-audit.

## Comment protocol

Comments are both notifications and restart-safe state evidence:

- `[githubro:runner]` identifies deterministic start, heartbeat, recovery, and
  infrastructure messages.
- `[githubro:agent][outcome:success]` records a completed implementation.
- `[githubro:agent][outcome:clarification]` records a question that requires
  user input.
- `[githubro:agent][outcome:audit-passed]` records a successful self-audit with
  no code changes required.

Every issue comment ends with the configured `@GITHUB_USERNAME` mention so that
GitHub sends a notification.

## Agent instructions and skills

The system-level agent contract lives in [`AGENTS.md`](AGENTS.md). It is copied
to `/root/.pi/agent/AGENTS.md` during the image build. Changes therefore take
effect after the next deployment.

Additional pi skills can be placed below `skills/` before rebuilding the image.

## Development

Run the Python tests:

```bash
python -m pytest -q
```

Type-check the pi extensions:

```bash
cd extensions
npm install
npx tsc --noEmit
```

Build the container locally:

```bash
docker build --build-arg "CACHEBUST=$(date +%s)" -t github-bro:latest .
```

## Operations and troubleshooting

Inspect the worker logs:

```bash
docker logs -f githubro
```

Common problems:

- **The container exits immediately:** Check required environment variables and
  `docker logs githubro` for a configuration error.
- **An issue is not selected:** Confirm it is open, carries `agent`, belongs to a
  configured repository, and is not protected by a fresh `agent-in-progress`
  heartbeat.
- **A run appears stuck:** It is recovered after
  `BRO_HEARTBEAT_STALE_AFTER_SECONDS`; restarting the container does not lose the
  GitHub-backed run state.
- **pi cannot authenticate:** Verify `PI_ARGS` and the selected provider's API
  key in `.env`.
- **GitHub operations fail:** Ensure the PAT can read issues and comments, edit
  labels, push branches, and create or update pull requests.

GithuBro deliberately does not auto-merge pull requests, run issues in parallel,
send external notifications, or expose a web server.
