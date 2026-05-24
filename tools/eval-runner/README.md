# eval-runner

Python harness that validates SKILL.md assets in the git-skill demos repo. It exists as a sister project to `git-skill`, intentionally decoupled from the CLI release cycle.

## Format

Each skill ships an `eval/` directory:

```text
skills/<name>/
├── SKILL.md
└── eval/
    ├── prompts.json        # test prompts (id + prompt text)
    ├── assertions.md       # binary checklist, split into Structural + Behavioral. <id>
    └── eval.config.yaml    # judge + skill-under-test config
```

See [`docs/EVALS-FORMAT.md`](../../docs/EVALS-FORMAT.md) for the full spec.

## Tiers

### `structure`

Calls Anthropic API only if a key is available, and only for unrecognized
assertions. Each `- [ ]` item under `## Structural` is resolved against the
filesystem when possible (SKILL.md exists, frontmatter has expected name +
description, body contains required H2 sections, `prompts.json` parses with
N+ entries). Anything the deterministic resolver can't parse falls back to
the LLM judge.

### `behavior`

Calls Anthropic API. For each prompt in `prompts.json`: sends `SKILL.md` as
the system prompt (with prompt caching), sends the prompt as a user message,
then asks the judge to score each assertion under `## Behavioral. <id>` 0/1.

## Install

```bash
python -m venv .venv
. .venv/bin/activate    # or .venv\Scripts\activate on Windows
pip install -e .
export ANTHROPIC_API_KEY=sk-ant-...   # required for behavior tier; optional for structure
```

## Usage

```bash
python run_evals.py [--tier structure|behavior|all] <skill-path>...
```

`<skill-path>` is a directory containing `SKILL.md` and an `eval/` subdirectory.

Examples:

```bash
# Structure only, single skill
python run_evals.py --tier structure ../../skills/code-review

# Structure + behavior, multiple skills (one invocation, one process)
python run_evals.py --tier all ../../skills/code-review ../../skills/commit-message
```

## Output

- **stdout**: a single JSON object with per-skill, per-tier, per-prompt results. Machine-readable; CI parses this.
- **stderr**: a human-readable summary (skill pass/fail, assertion outcomes).
- **exit code**: `0` if every skill passed every requested tier; non-zero on the first failure.

JSON shape:

```json
{
  "tier": "all",
  "skills": [
    {
      "path": "skills/code-review",
      "structure": {
        "passed": true,
        "errors": [],
        "assertions": [
          { "item": "`SKILL.md` exists with frontmatter", "passed": true, "justification": "...", "resolver": "deterministic" }
        ]
      },
      "behavior": {
        "model": "claude-sonnet-4-6",
        "judge_model": "claude-haiku-4-5-20251001",
        "passing_score": 0.8,
        "skill_score": 0.92,
        "passed": true,
        "prompts": [
          {
            "prompt_id": "divide-by-zero",
            "prompt": "Review this Python...",
            "prompt_score": 1.0,
            "passed": true,
            "response": "<model response text>",
            "assertions": [
              { "item": "Mentions the division-by-zero risk when `b` is 0", "passed": true, "justification": "..." }
            ]
          }
        ]
      }
    }
  ],
  "passed": true
}
```

## Models

- **Judge**: `claude-haiku-4-5-20251001` (hard-coded; cheap, deterministic).
- **Skill under test**: `claude-sonnet-4-6` by default; overridable per skill via `eval.config.yaml:skill_under_test.model`.

## Layout

```text
eval-runner/
  pyproject.toml
  README.md
  run_evals.py        # argparse CLI, aggregates, emits JSON + summary
  structure_check.py  # parse assertions.md, run deterministic resolvers, bucket unmatched for judge
  behavior_check.py   # Anthropic Messages API, prompt caching on SKILL.md, judge per prompt
  judge.py            # haiku judge with structured tool-use output (behavioral + structural modes)
```
