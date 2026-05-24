---
name: running-skill-evals
description: Run behavior evals for a skill locally inside Claude Code by spawning subagents via the Task tool — no Anthropic API key, no CI involvement.
---

# running-skill-evals

Drive a full behavior-eval pass for a skill from inside a Claude Code session. The skill author runs this on their own machine using their own Claude Code subscription. No `ANTHROPIC_API_KEY` and no CI involvement is needed.

## When to use

- A skill author is about to open a promotion (dev → prod) and needs the behavior tier green before they do.
- A reviewer wants to spot-check a behavior assertion on a single prompt.
- You are dogfooding a new skill and want to see how a fresh agent uses it.
- Do NOT use for structural assertions — those are deterministic and `python tools/eval-runner/run_evals.py --tier structure <skill-path>` handles them in under a second.
- Do NOT use to "fix" a skill — this skill scores; authoring is a different skill (`authoring-skills`).

## Inputs

You need exactly one thing: a path to a skill directory that already has the eval layout in `docs/EVALS-FORMAT.md`:

```text
skills/<name>/
  SKILL.md
  eval/
    prompts.json
    assertions.md
    eval.config.yaml   # optional
```

If `eval/prompts.json` or `eval/assertions.md` is missing, stop and tell the user — there is nothing to evaluate.

## Process

For each prompt in `eval/prompts.json`, spawn a subagent that has the skill loaded, run the prompt, score the response against the matching `## Behavioral. <id>` section of `eval/assertions.md`, and aggregate.

### 1. Read the inputs

- Read `<skill>/SKILL.md` in full.
- Read `<skill>/eval/prompts.json` and parse the `evals` array.
- Read `<skill>/eval/assertions.md` and split it into one block per `## Behavioral. <id>` section.
- Verify every prompt `id` has a matching `## Behavioral. <id>` block. If not, stop and report the orphan.

### 2. Run each prompt in a subagent

For each `{id, prompt}` entry:

1. Spawn a subagent via the Task tool with `subagent_type: "general-purpose"`. Subagents get a clean context — they do NOT inherit the skill from the parent session.
2. The subagent's prompt MUST contain three blocks, in order:
   - **Skill content block.** Prefixed with `--- SKILL: <name> ---`, followed by the full text of `SKILL.md` (frontmatter included), followed by `--- END SKILL ---`. Tell the subagent: *Treat the content between the SKILL markers as a loaded skill. Follow it as you would a normal skill in your context.*
   - **Task block.** The literal `prompt` field from the JSON entry, copied verbatim. No reformatting, no preface beyond `## Task`.
   - **Response format hint.** A single line: *Respond directly to the task above. Do not narrate your process.*
3. Capture the subagent's final text response. That is the "skill response" for this prompt.

### 3. Score the response

For each assertion line under `## Behavioral. <id>`:

1. Read the assertion text (everything after the `- [ ]`).
2. Decide pass/fail using *only* the captured response from step 2.
3. If the decision is non-obvious (e.g. semantic match rather than literal match), spawn a separate **judge** subagent with this prompt:

   ```text
   You are scoring an AI response against one binary assertion.

   ASSERTION:
   <assertion text>

   RESPONSE:
   <captured response>

   Answer with exactly one line:
   PASS — <one-sentence justification>
   or
   FAIL — <one-sentence justification>
   ```

   Parse the first token. Anything other than `PASS` or `FAIL` is treated as a runner error for that assertion.
4. Negative assertions ("Does NOT …") flip in the obvious way: PASS means the response did not do the forbidden thing.

### 4. Aggregate

Per prompt: `prompt_score = passed / total`. Pass if `prompt_score >= passing_score` (default `0.8` if `eval.config.yaml` is absent or silent).

Per skill: `skill_score = mean(prompt_score)` across all prompts. Pass if `skill_score >= passing_score` AND no prompt raised a runner error.

### 5. Report

Print a Markdown summary to the conversation:

```markdown
## running-skill-evals: <skill-name>

**Result:** PASS (score 0.92, threshold 0.80)

### Prompts

#### divide-by-zero — PASS (4/4)

- [x] Mentions the division-by-zero risk when `b` is 0
- [x] References the `divide` function or its `b` parameter by name
- [x] Suggests a guard, raise, or exception path for `b == 0`
- [x] Does NOT introduce unrelated style nits

#### sql-injection — FAIL (2/4)

- [x] Identifies the unsanitized concatenation
- [ ] Names the affected parameter — "did not call out the `user_id` parameter"
- [x] Recommends parameterized queries or an ORM
- [ ] Does NOT invent unrelated CVE references — "fabricated CVE-2024-9999"
```

Do NOT write the report to a file unless the user asks for one. The conversation is the report.

## Mapping to the eval-runner

The Python `tools/eval-runner/` implements the same algorithm headlessly using the Anthropic API (`ANTHROPIC_API_KEY` from env). It exists for users who want a non-interactive flow (e.g. nightly cron on their workstation). The CI in this repo does NOT use it for the behavior tier — only `--tier structure`. The authoritative local flow is THIS skill.

If a user asks "how do I run behavior evals in CI?" — the answer is: you don't, by design. Behavior evals here are a local interactive step run before promotion. See the producer `README.md` section "Running behavior evals locally".

## Common mistakes

- **Loading the skill into the parent session and assuming the subagent inherits it.** Subagents start with empty context. You MUST inline the full `SKILL.md` in the subagent prompt.
- **Reformatting the prompt.** The `prompt` field is the test input. Reformatting it changes the test. Copy verbatim.
- **Letting the subagent see the assertions.** The agent under test must not know what it is being scored on. Pass the skill + the task, nothing else.
- **Scoring against your memory of the response.** Score against the captured text only. If you scrolled past it, re-fetch from the subagent's final message.
- **Running this without structural evals first.** If structure fails, behavior numbers are meaningless. Always `python tools/eval-runner/run_evals.py --tier structure <skill-path>` first.
- **Editing the skill mid-run to make a prompt pass.** Finish the pass, report results, then iterate on the skill in a separate cycle. Otherwise you can't tell which change moved which number.
