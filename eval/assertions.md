# running-skill-evals Skill. Binary Assertions

Run these after any change to the skill. All must pass.

## Structural

- [ ] `SKILL.md` exists with frontmatter
- [ ] Frontmatter has `name: running-skill-evals` and `description: <one-line>`
- [ ] Body contains `## When to use`, `## Process`, `## Common mistakes` H2 sections
- [ ] `eval/prompts.json` parses and has at least 3 entries

## Behavioral. missing-eval-dir

- [ ] States that the run cannot proceed without `eval/prompts.json` and `eval/assertions.md`
- [ ] Tells the user to stop / report rather than fabricating prompts or fallback behavior
- [ ] Does NOT invent a default eval set or auto-generate prompts

## Behavioral. two-prompts-one-orphan

- [ ] Identifies that prompt id `bar` is missing a matching `## Behavioral. bar` section in `assertions.md`
- [ ] States that this should fail the run (orphan) rather than silently skipping the prompt
- [ ] References the rule that every prompt id must have a matching Behavioral section

## Behavioral. subagent-context-question

- [ ] Answers yes — you still need to inline `SKILL.md` into the subagent prompt
- [ ] Explains that subagents spawned via the Task tool start with empty context and do NOT inherit the parent session's loaded skills
- [ ] Does NOT claim that subagents inherit context, skills, or memory from the parent
