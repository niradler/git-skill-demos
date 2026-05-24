"""Behavior tier: runs each prompt through the Anthropic Messages API, then judges.

Per prompt in `eval/prompts.json`:
  1. Send SKILL.md (full body) as a cached system block. Prompt caching is reused
     across prompts in the same skill since the system block is identical.
  2. Send the prompt's `prompt` field as a single user message.
  3. Find the `## Behavioral. <id>` section in `assertions.md` whose id matches.
  4. Ask the judge to score each assertion in that section 0/1.
  5. Compute prompt_score = passed_count / total_assertions.

Skill-level aggregation lives in run_evals.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from anthropic import Anthropic

from judge import JUDGE_MODEL, JudgeScore, judge_behavioral
from structure_check import BehavioralSection

DEFAULT_SKILL_MODEL = "claude-sonnet-4-6"
DEFAULT_MAX_TOKENS = 2048
DEFAULT_PASSING_SCORE = 0.8


@dataclass
class PromptResult:
    prompt_id: str
    prompt: str
    prompt_score: float
    passed: bool
    response: str
    assertions: list[JudgeScore] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "prompt_id": self.prompt_id,
            "prompt": self.prompt,
            "prompt_score": self.prompt_score,
            "passed": self.passed,
            "response": self.response,
            "assertions": [s.to_dict() for s in self.assertions],
            "error": self.error,
        }


@dataclass
class BehaviorResult:
    model: str
    judge_model: str
    passing_score: float
    skill_score: float
    passed: bool
    prompts: list[PromptResult] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "judge_model": self.judge_model,
            "passing_score": self.passing_score,
            "skill_score": self.skill_score,
            "passed": self.passed,
            "prompts": [p.to_dict() for p in self.prompts],
            "error": self.error,
        }


def _extract_text(content: list[Any]) -> str:
    parts: list[str] = []
    for block in content:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    return "\n".join(parts).strip()


def _run_skill(
    client: Anthropic,
    model: str,
    skill_body: str,
    user_prompt: str,
    max_tokens: int,
) -> str:
    """Invoke the skill-under-test. SKILL.md is the system block, marked cacheable."""
    message = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=[
            {
                "type": "text",
                "text": skill_body,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_prompt}],
    )
    return _extract_text(message.content)


def _resolve_config(eval_config: dict[str, Any]) -> tuple[str, int, float]:
    """Pull skill model, max_tokens, and passing_score from eval.config.yaml."""
    sut = eval_config.get("skill_under_test") or {}
    if not isinstance(sut, dict):
        sut = {}
    model = str(sut.get("model") or DEFAULT_SKILL_MODEL)
    max_tokens = int(sut.get("max_tokens") or DEFAULT_MAX_TOKENS)
    judge_cfg = eval_config.get("judge") or {}
    if not isinstance(judge_cfg, dict):
        judge_cfg = {}
    passing_score = float(judge_cfg.get("passing_score", DEFAULT_PASSING_SCORE))
    return model, max_tokens, passing_score


def run_behavior(
    skill_body: str,
    eval_config: dict[str, Any],
    prompts: list[dict[str, Any]],
    behavioral_sections: list[BehavioralSection],
    client: Anthropic,
) -> BehaviorResult:
    """Run the behavior tier for a single skill and return aggregated results."""
    model, max_tokens, passing_score = _resolve_config(eval_config)
    section_by_id = {s.prompt_id: s for s in behavioral_sections}

    result = BehaviorResult(
        model=model,
        judge_model=JUDGE_MODEL,
        passing_score=passing_score,
        skill_score=0.0,
        passed=False,
    )

    if not prompts:
        result.error = "no prompts to run"
        return result

    prompt_scores: list[float] = []
    for entry in prompts:
        prompt_id = str(entry.get("id") or "<unknown>")
        prompt_text = str(entry.get("prompt") or "")

        pr = PromptResult(
            prompt_id=prompt_id,
            prompt=prompt_text,
            prompt_score=0.0,
            passed=False,
            response="",
        )

        section = section_by_id.get(prompt_id)
        if section is None or not section.assertions:
            pr.error = (
                f"no `## Behavioral. {prompt_id}` section in assertions.md "
                "(or section has zero assertions)"
            )
            prompt_scores.append(0.0)
            result.prompts.append(pr)
            continue

        try:
            response_text = _run_skill(
                client, model, skill_body, prompt_text, max_tokens
            )
            pr.response = response_text
            scores = judge_behavioral(
                client=client,
                skill_body=skill_body,
                prompt=prompt_text,
                response=response_text,
                assertions=section.assertions,
            )
            pr.assertions = scores
            passed_count = sum(1 for s in scores if s.passed)
            total = len(section.assertions) or 1
            pr.prompt_score = passed_count / total
            pr.passed = pr.prompt_score >= passing_score
        except Exception as exc:  # noqa: BLE001 - surface any API/judge failure per-prompt
            pr.error = f"{type(exc).__name__}: {exc}"

        prompt_scores.append(pr.prompt_score)
        result.prompts.append(pr)

    result.skill_score = (
        sum(prompt_scores) / len(prompt_scores) if prompt_scores else 0.0
    )
    result.passed = result.skill_score >= passing_score and all(
        p.error is None for p in result.prompts
    )
    return result
