# authoring-skills Skill. Binary Assertions

Run these after any change to the skill. All must pass.

## Structural

- [ ] `SKILL.md` exists with frontmatter
- [ ] Frontmatter has `name: authoring-skills` and `description: <one-line>`
- [ ] Body contains `## When to use`, `## Process`, `## Common mistakes` H2 sections
- [ ] `eval/prompts.json` parses and has at least 1 entry

## Behavioral. scaffold-new-skill

- [ ] Output includes YAML frontmatter delimited by `---` on both sides
- [ ] Frontmatter has both `name` and `description` keys
- [ ] `description` is a single specific sentence (NOT vague like "helps with release notes")
- [ ] Body contains `## When to use` and `## Process` H2 sections
- [ ] Skill name uses lowercase kebab-case (e.g. `release-notes`)

## Behavioral. fix-bad-description

- [ ] New description starts with a verb
- [ ] New description names a concrete input or trigger context (not just "database stuff")
- [ ] New description is a single sentence
- [ ] Explicitly identifies the original description as too vague
- [ ] Does NOT keep the phrase "Helps with database stuff" verbatim

## Behavioral. review-skill-structure

- [ ] Flags the missing `description` field in frontmatter
- [ ] Flags the name `api_client` as using underscore instead of kebab-case
- [ ] Flags the absence of a `## When to use` section
- [ ] Flags vague phrases like "handle errors properly" and recommends concrete instructions
- [ ] Mentions the missing `## Common mistakes` section or similar structural omission
