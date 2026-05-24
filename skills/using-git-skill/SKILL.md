---
name: using-git-skill
description: How an agent should use the git-skill CLI to author, publish, and consume skills and agents stored as git objects.
---

# using-git-skill

Use the `git-skill` CLI (and its sibling invocations `git-agent` / `git-asset`) to manage AI assets — skills and agents — stored as git refs under `refs/assets/<kind>/<name>` and tagged under `refs/asset-tags/<kind>/<name>/v<semver>`.

## When to use

- The user asks to publish, version, or share a skill or agent.
- The user wants to install a skill from another GitHub repo into their project.
- A repo already contains an `assets.json` and the user mentions installing, updating, or removing assets.
- You see a `SKILL.md` or `AGENT.md` file and the user wants it onboarded into a runtime (Claude / Codex / Cursor / OpenCode).
- Do NOT use for ordinary file copying or for editing skill content — that is plain file work.

## Process

### Producer flow (publishing your own skill)

1. `git skill init` — scaffolds `assets.json` and `.gitignore` entries. Run once per repo.
2. Author the skill under `skills/<name>/SKILL.md` (or `agents/<name>/AGENT.md` for agents). Frontmatter MUST include `name` and `description`.
3. `git skill commit <name> --path skills/<name> -m "<message>"` — snapshots the tree into `refs/assets/skill/<name>`.
4. `git skill tag <name> <semver>` — e.g. `1.0.0`. Tags become `refs/asset-tags/skill/<name>/v1.0.0`.
5. `git skill push origin` — pushes both `refs/assets/*` and `refs/asset-tags/*` to the remote.

For agents, swap the binary name to `git-agent` and use `AGENT.md`. The default kind comes from the invocation name.

### Consumer flow (installing someone else's skill)

1. `git skill init` in the consuming repo.
2. `git skill add <ns>/<name>@<spec> --from <git-url>` — `<spec>` is a semver range (`^1.0.0`), exact tag, or commit SHA. Writes the resolved `version` + `commit` into `assets.json`.
3. `git skill install` — materializes every entry in `assets.json` into the configured runtime path (e.g. `.claude/skills/<name>/`).
4. Commit `assets.json` and the materialized tree.

### Upgrade / rollback

- `git skill update <name>` — re-resolves the existing `spec` to the latest matching version, rewrites `commit`, re-materializes.
- Pin to an older release: edit `spec` in `assets.json` to an exact tag or commit, then `git skill install`.
- `git skill remove <name>` — drops the entry and removes both canonical and runtime paths.

### Inspection

- `git skill list` — local refs with their latest tag.
- `git skill log <name>` — commit history of the asset ref.
- `git skill diff <name> <verA> <verB>` — diff two tagged versions.
- `git skill discover <git-url>` — enumerate assets in a remote without installing.

## Common mistakes

- **Editing the materialized runtime tree directly.** Runtime paths (`.claude/skills/<name>/`) are managed outputs. Edit the canonical tree (`skills/<name>/`) and re-run `commit` + `install`.
- **Forgetting to push tags.** `git push origin` alone does NOT push `refs/asset-tags/*`. Always use `git skill push origin`.
- **Hand-editing `assets.json` `commit` field.** Use `update` or `add` — they compute and write the resolution. Manual edits desync `spec` from `version`/`commit`.
- **Confusing kinds.** `SKILL.md` ⇒ kind `skill`, materialized as a directory. `AGENT.md` ⇒ kind `agent`, materialized as a single marker file. Don't put `AGENT.md` inside a skill or vice versa.
- **Skipping `init`.** Without `assets.json`, `add` / `install` / `update` have nothing to operate on.
- **Inventing flags.** Real flags are listed in `git skill <cmd> --help`. The core commands are: `init`, `commit`, `tag`, `push`, `fetch`, `list`, `log`, `diff`, `show`, `add`, `update`, `remove`, `install`, `discover`. There is no `publish`, no `release`, no `sync`.
- **Pointing `--target` at user-owned files.** Runtime targets are git-skill-managed and may be overwritten or deleted.
