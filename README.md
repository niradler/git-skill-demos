# git-skill-demos (producer)

A live, end-to-end demonstration of the [git-skill](https://github.com/niradler/git-skill) workflow for AI-agent **skills**: authoring, evaluating, publishing versioned releases over git refs, and gating the whole thing with GitHub Actions. One sample agent is included as a footnote to show the second asset kind works end-to-end too — everything else is about skills.

This repo is the **producer** half of the demo. The consumer half lives at
[niradler/git-skill-consumer-demo](https://github.com/niradler/git-skill-consumer-demo).

## Skills published here

Each directory under `skills/` becomes its own versioned asset, snapshotted into `refs/assets/skill/<name>` and tagged under `refs/asset-tags/skill/<name>/v<semver>`. Consumers fetch by name + spec, never by branch.

| Path                              | Role                                              |
|-----------------------------------|---------------------------------------------------|
| `skills/using-git-skill/`         | Meta — teaches an agent the `git-skill` CLI       |
| `skills/authoring-skills/`        | Meta — how to write a good `SKILL.md`             |
| `skills/writing-skill-evals/`     | Meta — how to write eval cases                    |
| `skills/code-review/`             | Real example — PR review checklist                |
| `skills/commit-message/`          | Real example — Conventional Commits guidance      |

Each skill carries its evals alongside its `SKILL.md` under `eval/` (a `prompts.json` of test prompts + an `assertions.md` of binary checks, split into Structural and Behavioral sections). The format and runner live in `docs/EVALS-FORMAT.md` and `tools/eval-runner/`.

### Also: one sample agent

`agents/security-auditor/` exists only to demonstrate that `Asset-Kind: agent` (single-file marker) goes through the same git-skill commit/tag/push pipeline. No evals around it, no PR flow. Skills are where the action is.

## How to consume these skills

From any repo that has `git-skill` installed:

```bash
git skill init
git skill add niradler/code-review@^1.0.0 \
    --from https://github.com/niradler/git-skill-demos
git skill install
```

See the consumer demo for fully-worked PRs covering install, upgrade, dev-pin,
and rollback: <https://github.com/niradler/git-skill-consumer-demo>.

## CI gates

Three workflows under `.github/workflows/` enforce the lifecycle. **CI never calls the Anthropic API.** Behavior evals are a local, interactive workflow — see "Running behavior evals locally" below.

### 1. `structure-evals.yml` — every PR, every push

Triggers on `pull_request` and `push` to any branch. Detects changed skills via
`git diff --name-only` filtered to `skills/*/`, then for each one runs:

```bash
python tools/eval-runner/run_evals.py --tier structure <skill-path>
```

Cheap, deterministic, no API calls. Failures annotate the PR and fail the job.
**This is the merge gate for structural quality** (required sections, file layout,
manifest sanity, `prompts.json` parses, `assertions.md` parses).

### 2. `publish.yml` — `push` to `main`

For each skill or agent whose canonical tree changed in the merged commit:

1. Install `git-skill` via `go install github.com/niradler/git-skill/cmd/git-skill@latest`.
2. Read `version.txt` from the asset dir (default `0.1.0`).
3. `git skill commit <name> --path skills/<name> -m "publish from CI: <sha>"`
4. `git skill tag <name> <base-version>-dev.<run_number>`
5. `git skill push origin`

The job is **idempotent**: if the working tree for that asset matches the tip of
the existing `refs/assets/<kind>/<name>`, it is skipped. Re-running the workflow
on an unchanged commit is a no-op.

Dev tags follow the `X.Y.Z-dev.N` semver pattern so consumers can opt in to
in-progress versions via the spec `^X.Y.Z-dev`.

### 3. `promote.yml` — manual dev → prod

`workflow_dispatch` with two inputs: `skill` (name) and `version` (bare semver,
e.g. `1.0.0`). It re-verifies structure evals at the current commit, and only on
green:

1. `git skill tag <skill> <version>`
2. `git skill push origin`
3. Best-effort: posts a comment on the most recent closed PR that touched
   `skills/<skill>/`.

This is the only path to a non-`-dev` tag. Consumers pinning `^1.0.0` will not
pick up anything until a human runs this workflow. **Behavior-eval verification
is the skill author's responsibility before opening the promotion** — see below.

## Running behavior evals locally

Behavior evals (does the model actually do what the skill says?) need an LLM in
the loop. We keep that loop **local and interactive**, not in CI:

- No API key sits in this repo's secrets.
- The author runs evals on their own machine, using their own Claude Code
  subscription (or Anthropic API key — their choice).
- The skill `skills/running-skill-evals/` walks Claude Code through the loop:
  for each prompt in `eval/prompts.json`, spawn a Claude Code subagent with the
  target skill loaded into its context (`Task` tool), capture the response, and
  score each behavioral assertion under `## Behavioral. <prompt-id>` in
  `eval/assertions.md`.

The Python `tools/eval-runner/` still includes `--tier behavior` for users who
prefer a headless flow (it reads `ANTHROPIC_API_KEY` from env), but it's not
called from CI.

## Permissions model

Each workflow declares the narrowest `permissions:` block it needs:

| Workflow            | `contents` | `pull-requests` |
|---------------------|------------|-----------------|
| `structure-evals`   | `read`     | (none)          |
| `publish`           | `write`    | (none)          |
| `promote`           | `write`    | `write`         |

`publish.yml` and `promote.yml` push refs back to the repo using
`GITHUB_TOKEN` under a `github-actions[bot]` identity.

## Layout

```text
.
├── README.md
├── assets.json
├── skills/
│   └── <name>/
│       ├── SKILL.md
│       ├── version.txt
│       └── eval/
│           ├── prompts.json
│           ├── assertions.md
│           └── eval.config.yaml
├── agents/
│   └── security-auditor/
│       └── AGENT.md
├── tools/eval-runner/     (Python runner)
├── docs/                  (EVALS-FORMAT.md)
└── .github/workflows/     (the four files above)
```

## Related

- [niradler/git-skill](https://github.com/niradler/git-skill) — the CLI and format
- [niradler/git-skill-consumer-demo](https://github.com/niradler/git-skill-consumer-demo) — the consumer side of this demo
