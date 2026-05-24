"""Structure tier: parse `eval/assertions.md` and resolve each `- [ ]` item
under the `## Structural` section.

Resolution strategy:
  1. Try to match the assertion text against a set of known deterministic
     patterns (regex). If matched, evaluate against the filesystem with no API
     call. This is the fast, free path.
  2. Anything that doesn't match a known pattern is bucketed for the LLM judge
     (see `judge_structural`). The runner decides whether to actually call the
     judge (it only happens when an API client is available).

The deterministic patterns cover the assertions that real skills are expected
to use. They are intentionally narrow — fuzziness is delegated to the judge.

Also returns the parsed `assertions.md` so behavior_check.py can extract its
`## Behavioral. <id>` sections without re-parsing.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
ASSERTION_LINE_RE = re.compile(r"^\s*-\s*\[\s*[ xX]?\s*\]\s*(.+?)\s*$")
H2_RE = re.compile(r"^##\s+(.+?)\s*$")


@dataclass
class AssertionResult:
    """Outcome of evaluating a single assertion."""

    item: str
    passed: bool
    justification: str
    resolver: str  # "deterministic" or "judge" or "deterministic-failed-no-judge"

    def to_dict(self) -> dict[str, Any]:
        return {
            "item": self.item,
            "passed": self.passed,
            "justification": self.justification,
            "resolver": self.resolver,
        }


@dataclass
class BehavioralSection:
    """One `## Behavioral. <id>` section parsed from assertions.md."""

    prompt_id: str
    assertions: list[str]


@dataclass
class StructureResult:
    passed: bool
    errors: list[str] = field(default_factory=list)
    structural_assertions: list[str] = field(default_factory=list)
    behavioral_sections: list[BehavioralSection] = field(default_factory=list)
    deterministic_results: list[AssertionResult] = field(default_factory=list)
    judge_pending: list[str] = field(default_factory=list)  # for LLM fallback
    judge_results: list[AssertionResult] = field(default_factory=list)
    skill_body: str = ""
    skill_md_raw: str = ""
    eval_config: dict[str, Any] = field(default_factory=dict)
    prompts: list[dict[str, Any]] = field(default_factory=list)
    assertions_md_path: Path | None = None

    def all_results(self) -> list[AssertionResult]:
        return self.deterministic_results + self.judge_results

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "errors": list(self.errors),
            "assertions": [r.to_dict() for r in self.all_results()],
        }


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def _parse_frontmatter(text: str) -> tuple[dict[str, Any] | None, str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return None, text
    try:
        data = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return None, text
    if not isinstance(data, dict):
        return None, text
    return data, text[match.end() :]


def _parse_assertions_md(
    text: str,
) -> tuple[list[str], list[BehavioralSection]]:
    """Split assertions.md into a Structural list and Behavioral sections.

    Section header rules:
      * `## Structural` — the items below are structural assertions.
      * `## Behavioral. <prompt-id>` — the items below are behavioral assertions
        tied to the prompt with that id.
      * Any other H2 ends the current section without starting a new collector.
    """
    structural: list[str] = []
    behavioral: list[BehavioralSection] = []
    current: list[str] | None = None
    current_kind: str | None = None  # "structural" or "behavioral"

    for raw_line in text.splitlines():
        h2 = H2_RE.match(raw_line)
        if h2:
            heading = h2.group(1).strip()
            if heading.lower() == "structural":
                structural = []
                current = structural
                current_kind = "structural"
                continue
            if heading.lower().startswith("behavioral."):
                prompt_id = heading.split(".", 1)[1].strip().strip("`")
                section = BehavioralSection(prompt_id=prompt_id, assertions=[])
                behavioral.append(section)
                current = section.assertions
                current_kind = "behavioral"
                continue
            current = None
            current_kind = None
            continue
        if current is None:
            continue
        m = ASSERTION_LINE_RE.match(raw_line)
        if m:
            current.append(m.group(1).strip())

    return structural, behavioral


# ---------------------------------------------------------------------------
# Deterministic structural assertion resolvers
# ---------------------------------------------------------------------------


# Each resolver returns (matched, passed, justification). If matched is False,
# the assertion was not recognized and should fall back to the judge.

_BACKTICK = r"`?"


def _r_skill_md_exists(
    assertion: str,
    *,
    skill_path: Path,
    skill_md_text: str,
    frontmatter: dict[str, Any] | None,
    body: str,
    eval_dir: Path,
    prompts: list[dict[str, Any]] | None,
) -> tuple[bool, bool, str] | None:
    pat = re.compile(
        rf"^{_BACKTICK}SKILL\.md{_BACKTICK} exists(?: with frontmatter)?\.?$",
        re.IGNORECASE,
    )
    if not pat.match(assertion.strip()):
        return None
    skill_md = skill_path / "SKILL.md"
    if not skill_md.is_file():
        return True, False, f"SKILL.md not found at {skill_md}"
    needs_frontmatter = "frontmatter" in assertion.lower()
    if needs_frontmatter and frontmatter is None:
        return True, False, "SKILL.md present but frontmatter is missing or invalid"
    return True, True, "SKILL.md present" + (" with frontmatter" if needs_frontmatter else "")


def _r_frontmatter_has_name_and_description(
    assertion: str,
    *,
    frontmatter: dict[str, Any] | None,
    **_: Any,
) -> tuple[bool, bool, str] | None:
    # Examples:
    #   Frontmatter has `name: code-review` and `description: <one-line>`
    #   Frontmatter has name: foo and description: ...
    pat = re.compile(
        r"^frontmatter has\s+`?name:\s*([A-Za-z0-9_-]+)`?\s+and\s+`?description",
        re.IGNORECASE,
    )
    m = pat.match(assertion.strip())
    if not m:
        return None
    expected_name = m.group(1).strip()
    if frontmatter is None:
        return True, False, "no parseable frontmatter"
    actual_name = str(frontmatter.get("name") or "")
    desc = str(frontmatter.get("description") or "")
    if actual_name != expected_name:
        return True, False, f"frontmatter name is {actual_name!r}, expected {expected_name!r}"
    if not desc.strip():
        return True, False, "frontmatter description is empty"
    return True, True, f"name={actual_name!r}, description present"


def _r_body_contains_sections(
    assertion: str,
    *,
    body: str,
    **_: Any,
) -> tuple[bool, bool, str] | None:
    # Examples:
    #   Body contains `## When to use`, `## Process`, `## Common mistakes` H2 sections
    #   Body contains ## When to use and ## Process H2 sections
    if not assertion.lower().lstrip().startswith("body contains"):
        return None
    sections = re.findall(r"`(##\s+[^`]+)`", assertion)
    if not sections:
        # Fallback: look for "## ..." chunks outside backticks.
        sections = re.findall(r"(##\s+[A-Za-z][A-Za-z0-9 \-]+)", assertion)
        sections = [s for s in sections if s.lower() not in ("## sections", "## section")]
    if not sections:
        return None
    missing = [s for s in sections if s not in body]
    if missing:
        return True, False, f"missing sections: {missing}"
    return True, True, f"all {len(sections)} required H2 sections present"


def _r_prompts_json_parses(
    assertion: str,
    *,
    prompts: list[dict[str, Any]] | None,
    eval_dir: Path,
    **_: Any,
) -> tuple[bool, bool, str] | None:
    pat = re.compile(
        r"^`?eval/prompts\.json`? parses(?: and has(?: at least| ≥)?\s*(\d+)\s+entr(?:y|ies))?\.?$",
        re.IGNORECASE,
    )
    m = pat.match(assertion.strip())
    if not m:
        return None
    if prompts is None:
        return True, False, "eval/prompts.json missing or invalid JSON"
    min_entries = int(m.group(1)) if m.group(1) else 0
    if len(prompts) < min_entries:
        return (
            True,
            False,
            f"prompts.json has {len(prompts)} entries, expected at least {min_entries}",
        )
    return True, True, f"prompts.json parses with {len(prompts)} entries"


DETERMINISTIC_RESOLVERS = (
    _r_skill_md_exists,
    _r_frontmatter_has_name_and_description,
    _r_body_contains_sections,
    _r_prompts_json_parses,
)


def _resolve_structural(
    assertion: str,
    *,
    skill_path: Path,
    skill_md_text: str,
    frontmatter: dict[str, Any] | None,
    body: str,
    eval_dir: Path,
    prompts: list[dict[str, Any]] | None,
) -> AssertionResult | None:
    """Try every deterministic resolver. Return None if none match."""
    for resolver in DETERMINISTIC_RESOLVERS:
        outcome = resolver(
            assertion,
            skill_path=skill_path,
            skill_md_text=skill_md_text,
            frontmatter=frontmatter,
            body=body,
            eval_dir=eval_dir,
            prompts=prompts,
        )
        if outcome is None:
            continue
        matched, passed, justification = outcome
        if matched:
            return AssertionResult(
                item=assertion,
                passed=passed,
                justification=justification,
                resolver="deterministic",
            )
    return None


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------


def _load_json(path: Path) -> tuple[Any, str | None]:
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh), None
    except FileNotFoundError:
        return None, f"missing file: {path}"
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON in {path}: {exc}"
    except OSError as exc:
        return None, f"cannot read {path}: {exc}"


def _load_yaml(path: Path) -> tuple[Any, str | None]:
    try:
        with path.open("r", encoding="utf-8") as fh:
            return yaml.safe_load(fh), None
    except FileNotFoundError:
        return None, f"missing file: {path}"
    except yaml.YAMLError as exc:
        return None, f"invalid YAML in {path}: {exc}"
    except OSError as exc:
        return None, f"cannot read {path}: {exc}"


def check_structure(skill_path: Path) -> StructureResult:
    """Parse the skill's eval/ directory and run deterministic structural checks.

    The returned StructureResult includes any `judge_pending` items — the runner
    is responsible for invoking the judge fallback when it has an API client.
    """
    result = StructureResult(passed=False)
    errors = result.errors

    if not skill_path.is_dir():
        errors.append(f"skill path is not a directory: {skill_path}")
        return result

    skill_md = skill_path / "SKILL.md"
    if not skill_md.is_file():
        errors.append(f"missing SKILL.md at {skill_md}")
        return result

    try:
        text = skill_md.read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"cannot read SKILL.md: {exc}")
        return result
    result.skill_md_raw = text

    frontmatter, body = _parse_frontmatter(text)
    result.skill_body = text  # full text passed to behavior tier as system prompt

    eval_dir = skill_path / "eval"
    if not eval_dir.is_dir():
        errors.append(f"missing eval/ directory at {eval_dir}")
        return result

    assertions_md = eval_dir / "assertions.md"
    if not assertions_md.is_file():
        errors.append(f"missing eval/assertions.md at {assertions_md}")
        return result
    result.assertions_md_path = assertions_md

    try:
        assertions_text = assertions_md.read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"cannot read assertions.md: {exc}")
        return result

    structural, behavioral = _parse_assertions_md(assertions_text)
    result.structural_assertions = structural
    result.behavioral_sections = behavioral

    if not structural:
        errors.append("assertions.md has no `## Structural` section or it is empty")

    # Parse prompts.json
    prompts_path = eval_dir / "prompts.json"
    prompts_data, err = _load_json(prompts_path)
    prompts_list: list[dict[str, Any]] | None = None
    if err:
        errors.append(err)
    elif not isinstance(prompts_data, dict) or not isinstance(
        prompts_data.get("evals"), list
    ):
        errors.append(
            f"{prompts_path}: expected object with `evals` array (got {type(prompts_data).__name__})"
        )
    else:
        prompts_list = []
        for i, entry in enumerate(prompts_data["evals"]):
            if not isinstance(entry, dict):
                errors.append(f"{prompts_path}: evals[{i}] is not an object")
                continue
            if not entry.get("id") or not entry.get("prompt"):
                errors.append(
                    f"{prompts_path}: evals[{i}] missing `id` or `prompt`"
                )
                continue
            prompts_list.append(entry)
        result.prompts = prompts_list

    # Parse eval.config.yaml (optional but warn if malformed)
    config_path = eval_dir / "eval.config.yaml"
    config_data, err = _load_yaml(config_path)
    if err:
        errors.append(err)
    elif config_data is not None and not isinstance(config_data, dict):
        errors.append(f"{config_path} must be a YAML mapping")
    elif isinstance(config_data, dict):
        result.eval_config = config_data

    # Resolve each structural assertion deterministically; bucket misses.
    for assertion in structural:
        resolved = _resolve_structural(
            assertion,
            skill_path=skill_path,
            skill_md_text=text,
            frontmatter=frontmatter,
            body=body,
            eval_dir=eval_dir,
            prompts=prompts_list,
        )
        if resolved is None:
            result.judge_pending.append(assertion)
        else:
            result.deterministic_results.append(resolved)
            if not resolved.passed:
                errors.append(
                    f"structural assertion failed: {assertion} — {resolved.justification}"
                )

    # Cross-check that every behavioral section has a matching prompt id.
    if prompts_list is not None:
        prompt_ids = {p["id"] for p in prompts_list}
        for section in behavioral:
            if section.prompt_id not in prompt_ids:
                errors.append(
                    f"assertions.md has `## Behavioral. {section.prompt_id}` "
                    f"but no prompt with id={section.prompt_id!r} in prompts.json"
                )

    # `passed` is preliminary — the judge fallback (if any) is finalized in the
    # caller after running judge_pending. If we are not going to run the judge,
    # any judge_pending items count as unresolved => fail.
    deterministic_failed = any(not r.passed for r in result.deterministic_results)
    result.passed = (not errors) and (not deterministic_failed)
    return result


def finalize_structure(
    result: StructureResult, judge_results: list[AssertionResult]
) -> None:
    """Merge judge fallback results into the structure result and recompute passed."""
    result.judge_results = judge_results
    for r in judge_results:
        if not r.passed:
            result.errors.append(
                f"structural assertion failed (judge): {r.item} — {r.justification}"
            )
    deterministic_failed = any(not r.passed for r in result.deterministic_results)
    judge_failed = any(not r.passed for r in result.judge_results)
    result.passed = (not result.errors) and (not deterministic_failed) and (not judge_failed)


def mark_unresolved_as_failed(result: StructureResult) -> None:
    """When no judge is available, treat every `judge_pending` item as failed."""
    for assertion in result.judge_pending:
        unresolved = AssertionResult(
            item=assertion,
            passed=False,
            justification="unresolved structural assertion (no judge available)",
            resolver="deterministic-failed-no-judge",
        )
        result.judge_results.append(unresolved)
        result.errors.append(
            f"structural assertion unresolved (no API key): {assertion}"
        )
    if result.judge_pending:
        result.passed = False
    result.judge_pending = []
