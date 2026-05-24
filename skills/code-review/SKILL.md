---
name: code-review
description: Review a pull request diff for scope, correctness, style, security, and test coverage; flag issues by severity.
---

# code-review

A focused checklist for reviewing a pull request. Read the diff first, form a model of intent, then walk the checklist top-to-bottom. Surface issues with severity tags: `blocking`, `non-blocking`, `nit`.

## When to use

- The user asks for a PR review, code review, or "look at this diff".
- A diff or patch is pasted into the conversation.
- The user mentions reviewing changes before merge.
- Do NOT use for greenfield code authorship — this is review, not generation. Do NOT use for architectural design reviews; those need a different lens.

## Process

### 1. Establish scope

- What problem does the PR claim to solve? (Title, description, linked issue.)
- Does the diff match that scope? Flag any unrelated changes as **non-blocking**: "out of scope, split into a separate PR".
- Is the diff size reasonable? Anything over ~400 lines deserves a flag suggesting a split.

### 2. Correctness

- Walk every changed function. Ask: what input would break this?
- Off-by-one: loops, slice indices, range boundaries.
- Null / undefined / empty: every dereference and array index.
- Concurrency: shared mutable state, missing locks, races on init.
- Resource leaks: file handles, connections, goroutines, timers — is there a paired close/cancel?
- Error handling: every error path either handles or propagates with context. No silent `catch {}`.

### 3. Security

- Untrusted input flowing into: SQL (parameterize), shell (no string concat), HTML (escape), path joins (no traversal), eval/exec (forbidden).
- Secrets: no hardcoded tokens, keys, passwords. Check tests and fixtures too.
- AuthN/AuthZ: every new endpoint or mutation has explicit checks. New admin paths need extra scrutiny.
- Logging: no PII, no full request bodies, no tokens written to logs.

### 4. Style and clarity

- Naming: variables and functions read aloud as English.
- Function size: anything over ~50 lines or 4 levels of nesting is a refactor candidate (**nit**).
- Comments explain *why*, not *what*. Strip "// increment i" type comments.
- Consistency with surrounding code style — match the codebase, not your preference.

### 5. Tests

- Every new branch has a test, or an explicit reason not.
- Every bug fix has a regression test that fails without the fix.
- Tests assert behavior, not implementation. No mocking of the thing under test.
- Coverage of edge cases identified in step 2.

### 6. Write the review

Group findings by severity. For each:

- **File:line** anchor.
- One sentence on the problem.
- One sentence on the fix (or "consider X").

End with a one-line summary verdict: `approve` / `request changes` / `comment only`.

## Common mistakes

- **Drive-by style nits drowning out blocking issues.** Lead with correctness and security. Save nits for the bottom.
- **Reviewing line-by-line instead of function-by-function.** You miss interactions.
- **"LGTM" with no questions asked.** If you can't explain what the PR does, you can't approve it.
- **Suggesting rewrites in review.** Review is feedback, not authorship. Suggest direction; let the author write.
- **Ignoring the PR description.** If the description says "fixes bug X", verify a regression test for X exists.
- **Flagging style issues that disagree with the linter.** If the linter is silent, your taste is not the standard.
