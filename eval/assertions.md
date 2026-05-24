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
- [ ] Tags at least one finding with a severity label (blocking / non-blocking / nit)
- [ ] Does NOT flag unrelated style issues as blocking

## Behavioral. sql-injection

- [ ] Flags SQL injection arising from string interpolation of `req.query.id`
- [ ] Recommends parameterized query, prepared statement, or equivalent
- [ ] Marks the SQL injection finding as blocking (highest severity)
- [ ] Notes missing authentication or authorization on the endpoint

## Behavioral. scope-creep

- [ ] Flags the README and logger.py changes as out of scope for a `fix(parser)` PR
- [ ] Recommends splitting unrelated changes into a separate PR
- [ ] Reviews the actual parser change for correctness (e.g. trailing-comma handling)
- [ ] Does NOT approve the PR without raising the scope issue
