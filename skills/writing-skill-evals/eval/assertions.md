# writing-skill-evals Skill. Binary Assertions

Run these after any change to the skill. All must pass.

## Structural

- [ ] `SKILL.md` exists with frontmatter
- [ ] Frontmatter has `name: writing-skill-evals` and `description: <one-line>`
- [ ] Body contains `## When to use`, `## Process`, `## Common mistakes` H2 sections
- [ ] `eval/prompts.json` parses and has at least 1 entry

## Behavioral. draft-eval-for-new-skill

- [ ] Output proposes content for all three files: `prompts.json`, `assertions.md`, `eval.config.yaml`
- [ ] `prompts.json` is valid JSON with an `evals` array
- [ ] `assertions.md` includes a `## Structural` section AND at least one `## Behavioral. <id>` section
- [ ] Each behavioral section header matches an `id` from the proposed `prompts.json`
- [ ] `eval.config.yaml` references `claude-haiku-4-5-20251001` as judge and `claude-sonnet-4-6` as skill model

## Behavioral. fix-vague-assertions

- [ ] Replaces "Output is good" with a specific, observable assertion (NOT just rewording)
- [ ] Replaces "Handles errors properly" with at least one concrete error-handling check (e.g. mentions a specific exception or guard)
- [ ] Replaces "Demonstrates understanding of SQL injection" with an output-observable check (e.g. "Recommends parameterized query")
- [ ] Keeps the `- [ ]` checkbox markdown format
- [ ] Does NOT keep any of the original three vague items verbatim

## Behavioral. migrate-old-yaml-format

- [ ] Mentions renaming or replacing the `evals/` directory with `eval/` (singular)
- [ ] Maps the old `eval.yaml` to the new `eval.config.yaml`
- [ ] Maps old case `input` fields to entries in `prompts.json`
- [ ] Maps old case `rubric` items to behavioral checkboxes in `assertions.md`
- [ ] Mentions that structural assertions live in their own `## Structural` section, separate from behavioral
