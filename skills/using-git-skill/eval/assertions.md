# using-git-skill Skill. Binary Assertions

Run these after any change to the skill. All must pass.

## Structural

- [ ] `SKILL.md` exists with frontmatter
- [ ] Frontmatter has `name: using-git-skill` and `description: <one-line>`
- [ ] Body contains `## When to use`, `## Process`, `## Common mistakes` H2 sections
- [ ] `eval/prompts.json` parses and has at least 1 entry

## Behavioral. publish-new-version

- [ ] Mentions `git skill commit` with the skill name and `--path skills/code-review`
- [ ] Mentions `git skill tag` with version `1.2.0`
- [ ] Mentions `git skill push origin` (not plain `git push`) to push asset refs and tags
- [ ] Does NOT invent commands like `git skill publish` or `git skill release`
- [ ] Steps are in a sensible order (commit before tag before push)

## Behavioral. install-from-other-repo

- [ ] Mentions running `git skill init` in the consuming repo first
- [ ] Uses `git skill add acme/release-notes@^2.0.0 --from https://github.com/acme/skills.git` or equivalent
- [ ] Mentions `git skill install` to materialize into `.claude/skills/`
- [ ] Mentions committing the updated `assets.json` afterward
- [ ] Does NOT suggest hand-editing `assets.json` `commit` field

## Behavioral. rollback-bad-version

- [ ] Recommends editing `spec` in `assets.json` to pin an exact tag or commit (e.g. `1.0.0`)
- [ ] Mentions running `git skill install` after pinning to re-materialize
- [ ] Does NOT recommend hand-editing the `commit` field directly as the resolution mechanism
- [ ] Does NOT suggest waiting for the producer to fix it
