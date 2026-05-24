---
name: authoring-skills
description: How to write a high-quality SKILL.md — frontmatter, structure, naming, and what makes a skill actually trigger and help.
---

# authoring-skills

A skill is a Markdown file (`SKILL.md`) with YAML frontmatter, optionally accompanied by reference docs and scripts. The frontmatter triggers the skill; the body teaches the agent.

## When to use

- The user asks to "write a skill", "create a SKILL.md", or "scaffold a new skill".
- You are about to add a new directory under `skills/<name>/` in a producer repo.
- You are reviewing an existing SKILL.md for quality, triggering accuracy, or structural drift.
- Do NOT use for ordinary prose documentation (`README.md`, design docs). Those are not skills.

## Process

### 1. Pick the name

- Lowercase, kebab-case, descriptive verb-or-noun. Examples: `code-review`, `commit-message`, `writing-skill-evals`.
- The directory name, the frontmatter `name:`, and the git ref name MUST all match exactly.
- Namespace with `<org-or-user>/<name>` only when shipping for a registry that needs scoping.

### 2. Write the frontmatter

Required minimum:

```yaml
---
name: my-skill-name
description: One sentence. Starts with a verb. Says what it does and when to use it.
---
```

Optional fields: `version` (semver), `kind` (`skill` or `agent`), `license`.

The `description` is the single most important field — it is what the agent reads when deciding whether to load the skill. Bad: "Skill for code things." Good: "Review a pull request diff for correctness, scope, security, and test coverage; flag issues by severity."

### 3. Structure the body

Use 2–3 H2 sections. Suggested canonical set:

- `## When to use` — explicit trigger conditions and explicit non-triggers ("do NOT use for X").
- `## Process` — numbered or bulleted steps the agent should follow. Concrete commands, not vague advice.
- `## Common mistakes` — pitfalls to avoid, named specifically.

Keep total length 80–200 lines. Bullet lists beat prose. Code fences for commands.

### 4. Dogfood

- Re-read the SKILL.md as if you were a fresh agent. Could you act on it without external context?
- Replace every vague phrase ("handle errors properly") with a concrete instruction ("wrap the call in try/except and log `err.code` before re-raising").
- If the skill has scripts or reference files, link to them by relative path from the SKILL.md.

## Common mistakes

- **Vague description.** "Helps with code." tells the agent nothing about when to trigger. Be specific about inputs and outcomes.
- **Mismatched name.** Directory `code_review/`, frontmatter `name: codereview`, ref `code-review` — all three must agree, exact case and punctuation.
- **No "When to use" section.** Without explicit trigger conditions, the skill loads at the wrong times or never loads at all.
- **Walls of prose.** Agents skim. Convert paragraphs to bullets and numbered steps.
- **Over-length.** A 500-line SKILL.md is rarely read end-to-end. Push reference material into sibling files (`reference/*.md`) and link to them.
- **Inventing process steps that don't match reality.** If the skill teaches a CLI, verify every command exists. Hallucinated commands erode trust.
- **No `Common mistakes` section.** This is where the highest-value guidance often lives — what NOT to do.
- **Frontmatter missing the closing `---`.** YAML must be delimited on both sides or the parser will treat the body as more frontmatter and the skill will fail to load.
