# commit-message Skill. Binary Assertions

Run these after any change to the skill. All must pass.

## Structural

- [ ] `SKILL.md` exists with frontmatter
- [ ] Frontmatter has `name: commit-message` and `description: <one-line>`
- [ ] Body contains `## When to use`, `## Process`, `## Common mistakes` H2 sections
- [ ] `eval/prompts.json` parses and has at least 1 entry

## Behavioral. feat-with-scope

- [ ] Subject begins with `feat` type
- [ ] Subject includes a parenthesized scope (e.g. `auth`)
- [ ] Subject is in imperative mood ("add", not "added" or "adds")
- [ ] Subject has no trailing period
- [ ] Footer references issue 217 (e.g. `Closes: #217` or `Refs: #217`)

## Behavioral. breaking-change

- [ ] Uses `!` after type/scope OR a `BREAKING CHANGE:` footer (or both)
- [ ] If a footer is used, the literal token `BREAKING CHANGE:` appears with the colon
- [ ] Subject describes the rename from `close()` to `shutdown()` clearly
- [ ] Body or footer explains that callers must update
- [ ] Type is `refactor` or `feat` (NOT `fix`, since this is a deliberate API change)

## Behavioral. fix-with-body

- [ ] Subject begins with `fix` type
- [ ] Subject is in imperative mood and has no trailing period
- [ ] Body explains the why (revoked sessions lingering, security impact) rather than restating the diff
- [ ] Mentions the `exp` claim by name
- [ ] Subject stays under 72 characters
