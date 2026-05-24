---
name: writing-skill-evals
description: Author eval assets for a skill — write realistic test prompts and binary assertions split into structural and behavioral tiers.
---

# writing-skill-evals

Each skill ships an `eval/` directory containing three files: `prompts.json` (test prompts to run the skill against), `assertions.md` (a binary checklist split into Structural and Behavioral sections), and `eval.config.yaml` (judge model and passing threshold). The runner executes structural assertions deterministically, sends each prompt to the skill-under-test, and asks a judge model to score each behavioral assertion 0/1.

The full on-disk schema lives in [`docs/EVALS-FORMAT.md`](../../docs/EVALS-FORMAT.md). Read it before authoring the first eval for a new skill.

## When to use

- The user asks to "write evals" or "add test cases" for a skill.
- A new SKILL.md was added and lacks an `eval/` directory.
- An existing skill is being upgraded and needs a regression assertion for the new behavior.
- Do NOT use for general LLM benchmark design — this format is scoped to single-skill checks under the git-skill demos framework.
- Do NOT use for the OLD YAML rubric format (`evals/eval.yaml` + `evals/cases/*.yaml`). That format is retired; replace it on sight.

## Process

### 1. Lay out the directory

```
skills/<name>/
├── SKILL.md
└── eval/
    ├── prompts.json
    ├── assertions.md
    └── eval.config.yaml
```

Note the singular `eval/` — not `evals/`. The runner refuses to run if `eval/prompts.json` or `eval/assertions.md` is missing.

### 2. Write `eval.config.yaml`

```yaml
version: 1
judge:
  model: claude-haiku-4-5-20251001
  passing_score: 0.8
skill_under_test:
  model: claude-sonnet-4-6
```

- Judge model is `claude-haiku-4-5-20251001` — cheap, fast, deterministic-ish.
- `skill_under_test.model` is what real users will hit. Default `claude-sonnet-4-6`.
- `passing_score` is the fraction of behavioral assertions per prompt that must score 1.

### 3. Write `prompts.json`

Aim for 2–3 realistic prompts per skill. Each has an `id` (kebab-case, used in `assertions.md`) and a `prompt`.

```json
{
  "evals": [
    { "id": "divide-by-zero", "prompt": "Review this Python:\n\n```python\ndef divide(a, b):\n    return a / b\n```" }
  ]
}
```

Prompts must look like something a real user would actually send. For meta-skills (publishing, scaffolding), make them tasks an agent would receive in practice ("I want to publish version 1.2.0 of my skill — what commands do I run?"). For code-touching skills, paste a real-looking diff or snippet.

### 4. Write `assertions.md`

Two top-level sections.

**Structural** — 3–5 items, same shape across every skill. These run without API calls.

```markdown
## Structural

- [ ] `SKILL.md` exists with frontmatter
- [ ] Frontmatter has `name: <skill-name>` and `description: <one-line>`
- [ ] Body contains `## When to use`, `## Process`, `## Common mistakes` H2 sections
- [ ] `eval/prompts.json` parses and has at least 1 entry
```

The runner recognizes these phrasings deterministically — see `docs/EVALS-FORMAT.md` for the full pattern list. Anything unrecognized falls back to the judge with a structural rubric.

**Behavioral** — one section per prompt id, 3–5 atomic assertions each.

```markdown
## Behavioral. divide-by-zero

- [ ] Mentions the division-by-zero risk when `b` is 0
- [ ] References the `divide` function or its `b` parameter by name
- [ ] Suggests a guard, raise, or exception path
- [ ] Does NOT introduce unrelated style nits
```

The section header MUST be exactly `## Behavioral. <prompt-id>` — the runner uses this to associate assertions with prompt outputs.

### 5. Craft atomic behavioral assertions

- **Atomic** = one observable fact per item. Bad: "Handles errors well." Good: "Mentions the `divide` function by name."
- **Verifiable** = a judge reading the response alone can answer yes/no. Bad: "Demonstrates deep understanding." Good: "Suggests wrapping the call in try/except."
- **Anchored to the skill** = each item maps to a specific instruction in SKILL.md. If an item could pass without the skill loaded, it is not testing the skill.
- **Negative checks allowed** = "Does NOT introduce unrelated style nits" is fine. "Does NOT invent commands like `git skill publish`" is fine.

### 6. Sanity check by reading prompts cold

Mentally read each prompt and the matching behavioral assertions side-by-side. If the prompt telegraphs the answer ("mention division by zero in your review"), you are testing echo, not the skill. Tighten the prompt or the assertions.

## Common mistakes

- **Using the old `evals/` (plural) directory or YAML rubric format.** That format is retired. The new directory is `eval/` (singular) with `prompts.json` + `assertions.md` + `eval.config.yaml`.
- **Behavioral section header without the `Behavioral. ` prefix.** The runner pattern-matches `## Behavioral. <id>` — `## divide-by-zero` will be ignored.
- **Prompt id in `assertions.md` doesn't match any `id` in `prompts.json`.** The runner will report unmatched assertion sections as failures.
- **Vague assertion items.** "Handles errors well" cannot be scored. Split into the specific behaviors you want to see.
- **Assertions that pass without the skill loaded.** Mentally run the prompt through a generic model — if it would still pass the assertion, the assertion is not testing the skill.
- **One giant prompt.** Three focused prompts beat one mega-prompt. Scoring is per-prompt and aggregated.
- **Leaking assertion text into the prompt.** This trains the eval to score echo, not behavior.
- **Mismatched models in `eval.config.yaml`.** Judge is `claude-haiku-4-5-20251001`. Skill-under-test default is `claude-sonnet-4-6`.
- **Skipping the structural section.** Behavioral assertions cost API tokens. Structural assertions are free, instant, and catch most regressions (missing sections, broken frontmatter, unparseable `prompts.json`).
