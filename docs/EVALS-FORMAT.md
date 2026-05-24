# EVALS-FORMAT

> Format specification for skill evaluation assets in the git-skill demos repo.
> Version: 2
> Status: stable

This document defines the on-disk layout and schema that the `eval-runner` harness consumes. If you are authoring or maintaining a skill, this is the contract you write against.

## Goals

- **Reproducible**: any contributor can run the same checks locally that CI runs.
- **Cheap by default**: most structural assertions resolve deterministically with no API call.
- **Selective when expensive**: the behavior tier (Anthropic API) is opt-in per PR and required on `main`.
- **Author-friendly**: a skill author writes a JSON file of prompts and a markdown checklist of assertions.

## Directory layout

Every skill lives at `skills/<name>/` in the producer repo. Its eval assets live under `eval/` inside the skill directory so they travel with the skill on `git skill commit`.

```text
skills/<name>/
  SKILL.md
  eval/
    prompts.json        # required; test prompts
    assertions.md       # required; binary checklist
    eval.config.yaml    # optional; judge + skill model config
```

The runner refuses to run if `eval/prompts.json` or `eval/assertions.md` is missing.

> Note: the directory is `eval/` (singular). The old `evals/` (plural) format with `eval.yaml` + `cases/*.yaml` is retired. See the migration note at the bottom of this document.

## `prompts.json` schema

A JSON object with one key `evals`, holding an array of prompt entries.

```json
{
  "evals": [
    {
      "id": "divide-by-zero",
      "prompt": "Review this Python:\n\n```python\ndef divide(a, b):\n    return a / b\n```"
    },
    {
      "id": "sql-injection",
      "prompt": "Review this Node.js handler..."
    }
  ]
}
```

### Field reference

| Field | Type | Required | Meaning |
|-------|------|----------|---------|
| `evals` | array | yes | List of prompt entries. At least one. |
| `evals[].id` | string | yes | Kebab-case identifier. Must match the suffix of a `## Behavioral. <id>` section in `assertions.md`. |
| `evals[].prompt` | string | yes | Sent verbatim as a single user message to the skill-under-test. |

## `assertions.md` schema

A markdown file with two top-level section types:

- `## Structural` — one section, holding assertions that describe the static shape of the skill (file presence, frontmatter, required H2 sections, `prompts.json` parsing). These are resolved before any API call.
- `## Behavioral. <prompt-id>` — one section per prompt in `prompts.json`. The `<prompt-id>` matches the `id` of the prompt the assertions are scored against.

Each assertion is a markdown task-list item: `- [ ] <assertion text>`.

```markdown
# code-review Skill. Binary Assertions

Run these after any change to the skill. All must pass.

## Structural

- [ ] `SKILL.md` exists with frontmatter
- [ ] Frontmatter has `name: code-review` and `description: <one-line>`
- [ ] Body contains `## When to use`, `## Process`, `## Common mistakes` H2 sections
- [ ] `eval/prompts.json` parses and has at least 1 entry

## Behavioral. divide-by-zero

- [ ] Mentions the division-by-zero risk when `b` is 0
- [ ] References the `divide` function or its `b` parameter by name
- [ ] Suggests a guard, raise, or exception path for `b == 0`
- [ ] Does NOT introduce unrelated style nits
```

### Header rules

- The Structural header is exactly `## Structural`.
- The Behavioral header is exactly `## Behavioral. <prompt-id>` — note the dot-space between `Behavioral` and the id. The runner pattern-matches this; `## divide-by-zero` alone will be ignored.
- Any other H2 ends the current collector.

### Assertion authoring guidance

- **Atomic** = one observable fact per item. Bad: "Handles errors well." Good: "Mentions the `divide` function by name."
- **Verifiable** = a judge reading the response alone can answer yes/no. Bad: "Demonstrates deep understanding." Good: "Suggests wrapping the call in try/except."
- **Anchored to the skill** = each item maps to a specific instruction in SKILL.md. If an item could pass without the skill loaded, it is not testing the skill.
- **Negative checks allowed** = "Does NOT introduce unrelated style nits" is fine. "Does NOT invent commands like `git skill publish`" is fine.

## `eval.config.yaml` schema

Optional. Defaults are used for any missing key.

```yaml
version: 1
judge:
  model: claude-haiku-4-5-20251001
  passing_score: 0.8
skill_under_test:
  model: claude-sonnet-4-6
  max_tokens: 2048
```

### Config field reference

| Field | Type | Required | Default | Meaning |
|-------|------|----------|---------|---------|
| `version` | int | no | `1` | Schema version. |
| `judge.model` | string | no | `claude-haiku-4-5-20251001` | Currently advisory; the judge model is hard-coded for stability across runs. |
| `judge.passing_score` | float in `[0, 1]` | no | `0.8` | A prompt passes if `prompt_score >= passing_score`. A skill passes if `skill_score >= passing_score`. |
| `skill_under_test.model` | string | no | `claude-sonnet-4-6` | Anthropic model used to run the skill. |
| `skill_under_test.max_tokens` | int | no | `2048` | Max tokens for the skill response. |

## Tiers

### Structure

Runs every `- [ ]` item under `## Structural`. For each item, the runner first tries to match a known **deterministic pattern**. Anything that doesn't match a known pattern is bucketed for the LLM judge as a fallback. If no API key is available, unrecognized items are reported as unresolved failures.

The runner also cross-checks that every `## Behavioral. <id>` section has a matching `id` in `prompts.json` — orphan sections fail the structure tier.

### Behavior

For each prompt in `prompts.json`:

1. Send `SKILL.md` (full file, including frontmatter) as a cached system block.
2. Send the prompt's `prompt` field as a single user message.
3. Find the `## Behavioral. <id>` section in `assertions.md` whose `<id>` matches.
4. Ask the judge (`claude-haiku-4-5-20251001`) to score each assertion 0/1 via a tool call.
5. Compute `prompt_score = passed / total`.

If structure fails for a skill, behavior is skipped for that skill.

## Deterministic structural patterns

The runner recognizes these phrasings without an API call. Use them in `## Structural` when you want zero-cost checks. Anything else falls back to the judge.

| Pattern (case-insensitive) | What it checks |
|----------------------------|----------------|
| `` `SKILL.md` exists`` | `<skill>/SKILL.md` is a file. |
| `` `SKILL.md` exists with frontmatter`` | Also requires parseable YAML frontmatter. |
| `` Frontmatter has `name: <NAME>` and `description: ...` `` | Frontmatter `name` exactly equals `<NAME>` and `description` is non-empty. The exact name is captured from the assertion text. |
| `` Body contains `## A`, `## B`, ... H2 sections `` | Every backticked H2 string appears as a substring of the SKILL.md body. |
| `` `eval/prompts.json` parses `` | `prompts.json` exists, parses, and has an `evals` array. |
| `` `eval/prompts.json` parses and has at least N entries `` | Same as above, also requires `len(evals) >= N`. |

If you write a structural assertion that does not match any of the above, the runner will route it to the judge with the raw `SKILL.md` + `eval/` contents as context. That works, but costs an API call per run.

## Scoring

Per prompt:

```text
prompt_score = passed_assertions / total_assertions
prompt.passed = (prompt_score >= judge.passing_score)
```

Per skill:

```text
skill_score = mean(prompt_score for each prompt)
skill.passed = (skill_score >= judge.passing_score) AND (no prompt raised an error)
```

`skill_score` is the **arithmetic mean of per-prompt scores**, not the global pass rate across all assertions. A skill with one excellent prompt and one terrible prompt scores ~0.5 even if total assertion pass count is high. That is intentional: every prompt is supposed to test a real capability.

## Output format

The runner emits one JSON document on stdout:

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
          {
            "item": "`SKILL.md` exists with frontmatter",
            "passed": true,
            "justification": "SKILL.md present with frontmatter",
            "resolver": "deterministic"
          }
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
              {
                "item": "Mentions the division-by-zero risk when `b` is 0",
                "passed": true,
                "justification": "Response calls out ZeroDivisionError when b is 0."
              }
            ],
            "error": null
          }
        ],
        "error": null
      }
    }
  ],
  "passed": true
}
```

A human-readable summary goes to stderr. The process exits non-zero on any failure.

## Complete example

`skills/code-review/SKILL.md`:

```markdown
---
name: code-review
description: Review a pull request diff for scope, correctness, style, security, and test coverage; flag issues by severity.
---

# code-review

## When to use
...

## Process
...

## Common mistakes
...
```

`skills/code-review/eval/prompts.json`:

```json
{
  "evals": [
    {
      "id": "divide-by-zero",
      "prompt": "Review this Python:\n\n```python\ndef divide(a, b):\n    return a / b\n```"
    }
  ]
}
```

`skills/code-review/eval/assertions.md`:

```markdown
# code-review Skill. Binary Assertions

## Structural

- [ ] `SKILL.md` exists with frontmatter
- [ ] Frontmatter has `name: code-review` and `description: <one-line>`
- [ ] Body contains `## When to use`, `## Process`, `## Common mistakes` H2 sections
- [ ] `eval/prompts.json` parses and has at least 1 entry

## Behavioral. divide-by-zero

- [ ] Mentions the division-by-zero risk when `b` is 0
- [ ] References the `divide` function or its `b` parameter by name
- [ ] Suggests a guard, raise, or exception path for `b == 0`
- [ ] Does NOT introduce unrelated style nits
```

`skills/code-review/eval/eval.config.yaml`:

```yaml
version: 1
judge:
  model: claude-haiku-4-5-20251001
  passing_score: 0.8
skill_under_test:
  model: claude-sonnet-4-6
```

Run it:

```bash
python run_evals.py --tier all skills/code-review
```

## Versioning

This document describes `version: 2` of the eval format. Future breaking changes will bump the integer and the runner will refuse incompatible files with a clear error.

## Prior art

This format draws on two upstream conventions:

- [Anthropic skill-creator](https://raw.githubusercontent.com/anthropics/skills/main/skills/skill-creator/SKILL.md) — `evals/evals.json` for test prompts. We reuse the `{ "evals": [ { "id", "prompt" } ] }` shape.
- [TromboneTimo coaching-db](https://raw.githubusercontent.com/TromboneTimo/claude-system/a7b848f2548cffbfbd36bdd6babc366bd2b08265/skills/coaching-db/eval/assertions.md) — `eval/assertions.md` with binary markdown checkboxes split by Structural / Behavioral sections. We reuse the directory name `eval/` and the checkbox-based section layout.

The combination — JSON prompts + markdown checklist + a deterministic resolver for the structural tier — is specific to this repo.

## Migration from the old format

The retired format was:

```text
skills/<name>/evals/
  eval.yaml
  cases/
    01-foo.yaml
    02-bar.yaml
```

Mapping to the new format:

| Old | New |
|-----|-----|
| `evals/` directory | `eval/` directory |
| `evals/eval.yaml` | `eval/eval.config.yaml` (drop `required_sections`; encode as structural assertions instead) |
| Each `evals/cases/<n>.yaml` `input` | An entry in `eval/prompts.json` |
| Each `evals/cases/<n>.yaml` `rubric` item | A `- [ ]` line in the matching `## Behavioral. <id>` section of `eval/assertions.md` |
| `required_sections` list | Structural assertions of the form `Body contains \`## X\`, \`## Y\`, ... H2 sections` |
