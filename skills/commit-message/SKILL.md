---
name: commit-message
description: Write a Conventional Commits message — type, scope, subject, body, footer — and use BREAKING CHANGE correctly.
---

# commit-message

Follows the Conventional Commits 1.0 spec. A commit message has a structured header, an optional body, and optional footers. The structure makes commits machine-parseable for changelogs and semver bumps.

## When to use

- The user asks to "write a commit message" or "draft a commit".
- A diff or staged change is shown and the user wants to commit it.
- The user mentions Conventional Commits, semantic-release, or changelog generation.
- Do NOT use for PR titles unless the project specifically uses Conventional Commits for PR titles too. PR titles often have different rules.

## Process

### 1. Pick the type

| Type     | When                                                      |
|----------|-----------------------------------------------------------|
| feat     | New user-facing feature                                   |
| fix      | Bug fix in existing behavior                              |
| docs     | Documentation only                                        |
| style    | Formatting, whitespace — no logic change                  |
| refactor | Internal restructure, no behavior change                  |
| perf     | Performance improvement                                   |
| test     | Adding or fixing tests                                    |
| build    | Build system, dependencies                                |
| ci       | CI configuration                                          |
| chore    | Maintenance that doesn't fit above                        |
| revert   | Reverts a previous commit                                 |

### 2. Optional scope

A noun in parentheses naming the affected area: `feat(api):`, `fix(parser):`, `docs(readme):`. Use the codebase's existing scopes — check `git log --oneline | head -20`.

### 3. Write the subject

Format: `<type>(<scope>): <subject>`

- Imperative mood: "add", not "added" or "adds".
- Lowercase first letter (unless proper noun).
- No trailing period.
- 50 characters or fewer if possible, 72 hard maximum.

### 4. Optional body

- Blank line after the subject.
- Wrap at 72 columns.
- Explain **why** the change is needed, not **what** (the diff shows the what).
- Reference prior decisions, constraints, alternatives considered.

### 5. Optional footer

- Blank line before the footer.
- `Refs: #123` or `Closes: #123` for issue references.
- `BREAKING CHANGE: <description>` for breaking changes. The colon is required. The body of the footer explains migration.
- Alternatively, signal a breaking change by appending `!` after the type/scope: `feat(api)!: drop legacy /v1 endpoints`.

## Examples

```
feat(parser): support trailing commas in tuple literals

The grammar previously rejected `(a, b,)` even though Python accepts it.
Aligning to Python's behavior reduces user surprise.

Closes: #482
```

```
fix(auth): reject tokens missing exp claim

Tokens without an expiration were silently accepted as never-expiring,
which lets revoked sessions linger forever in caches.
```

```
refactor(db)!: rename Connection.close() to Connection.shutdown()

BREAKING CHANGE: Connection.close() has been renamed to shutdown().
Update callers; close() now raises AttributeError.
```

## Common mistakes

- **Past-tense subject.** "added support for X" — should be "add support for X". Imperative mood = the commit completes the sentence "If applied, this commit will ___".
- **Type mismatch with content.** A `fix:` that introduces new behavior is actually `feat:`. A `feat:` that only renames internal symbols is `refactor:`.
- **Multiple unrelated changes in one commit.** Split into multiple commits, each with its own type.
- **BREAKING CHANGE in body without the footer token.** Tools parse the literal string `BREAKING CHANGE:` in a footer. Burying it in prose hides it from changelog generators.
- **`!` and `BREAKING CHANGE:` disagree.** If you use `!`, the footer should still describe the break for the changelog.
- **Subject ends with a period.** Conventional Commits forbids it.
- **Vague subject.** "fix bug" / "update code" — name the actual behavior change.
- **Scope mismatch with the diff.** `fix(auth)` that touches only the parser confuses code archaeology.
