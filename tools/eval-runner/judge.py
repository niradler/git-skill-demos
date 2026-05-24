"""LLM-as-judge: scores model responses against binary assertions.

The judge model is hard-coded to `claude-haiku-4-5-20251001`. We use tool use to
force strict JSON output: the model must call `report_scores` with one entry per
assertion. This is more reliable than parsing free-form JSON from text.

Two judge modes:
  * `judge_behavioral` — score a skill response against a list of behavioral assertions.
  * `judge_structural` — fallback for structural assertions the deterministic
    resolver could not parse. Operates on the raw SKILL.md and eval files, not
    on a model response.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from anthropic import Anthropic

JUDGE_MODEL = "claude-haiku-4-5-20251001"
JUDGE_MAX_TOKENS = 2048

BEHAVIORAL_JUDGE_SYSTEM = (
    "You are a strict evaluator. You will be given a skill's instructions, "
    "a user prompt, the model's response to that prompt, and a list of binary "
    "assertions. For each assertion, decide whether the model's response satisfies "
    "it (true) or not (false). Be literal and conservative: only mark passed=true "
    "if the response clearly meets the assertion. Provide a single short sentence "
    "of justification per assertion. You MUST call the `report_scores` tool exactly "
    "once with one entry per assertion, in order."
)

STRUCTURAL_JUDGE_SYSTEM = (
    "You are a strict evaluator of skill repository structure. You will be given "
    "the raw contents of a skill's SKILL.md, the contents of its eval/ files, "
    "and a list of binary structural assertions. For each assertion, decide "
    "whether it is satisfied (true) or not (false) by inspecting the provided "
    "files only. Be literal and conservative. Provide a single short sentence "
    "of justification per assertion. You MUST call the `report_scores` tool "
    "exactly once with one entry per assertion, in order."
)

REPORT_SCORES_TOOL: dict[str, Any] = {
    "name": "report_scores",
    "description": "Report a 0/1 score plus one-sentence justification for each assertion, in input order.",
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "scores": {
                "type": "array",
                "description": "One entry per assertion, in the order provided.",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "item": {
                            "type": "string",
                            "description": "The assertion text being scored.",
                        },
                        "passed": {
                            "type": "boolean",
                            "description": "True if the assertion is satisfied.",
                        },
                        "justification": {
                            "type": "string",
                            "description": "One sentence explaining the decision.",
                        },
                    },
                    "required": ["item", "passed", "justification"],
                },
            }
        },
        "required": ["scores"],
    },
}


@dataclass
class JudgeScore:
    item: str
    passed: bool
    justification: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "item": self.item,
            "passed": self.passed,
            "justification": self.justification,
        }


def _invoke_judge(
    client: Anthropic,
    system: str,
    user_text: str,
    assertions: list[str],
) -> list[JudgeScore]:
    message = client.messages.create(
        model=JUDGE_MODEL,
        max_tokens=JUDGE_MAX_TOKENS,
        system=system,
        tools=[REPORT_SCORES_TOOL],
        tool_choice={"type": "tool", "name": "report_scores"},
        messages=[{"role": "user", "content": user_text}],
    )

    tool_use = next(
        (block for block in message.content if getattr(block, "type", None) == "tool_use"),
        None,
    )
    if tool_use is None:
        raise RuntimeError("judge did not return a tool_use block")

    raw_scores = (tool_use.input or {}).get("scores")
    if not isinstance(raw_scores, list):
        raise RuntimeError("judge tool_use missing `scores` array")

    # Align to assertions length: pad with failures if the judge under-reports,
    # truncate if it over-reports. Keeps aggregation honest.
    scores: list[JudgeScore] = []
    for i, item in enumerate(assertions):
        if i < len(raw_scores) and isinstance(raw_scores[i], dict):
            entry = raw_scores[i]
            scores.append(
                JudgeScore(
                    item=str(entry.get("item") or item),
                    passed=bool(entry.get("passed", False)),
                    justification=str(entry.get("justification") or ""),
                )
            )
        else:
            scores.append(
                JudgeScore(
                    item=item,
                    passed=False,
                    justification="judge omitted this assertion",
                )
            )
    return scores


def judge_behavioral(
    client: Anthropic,
    skill_body: str,
    prompt: str,
    response: str,
    assertions: list[str],
) -> list[JudgeScore]:
    """Score a skill response against a list of behavioral assertions."""
    assertions_block = "\n".join(f"{i+1}. {a}" for i, a in enumerate(assertions))
    user_text = (
        "Score the model's response against the assertions.\n\n"
        "=== SKILL INSTRUCTIONS (the system prompt the model received) ===\n"
        f"{skill_body}\n\n"
        "=== USER PROMPT ===\n"
        f"{prompt}\n\n"
        "=== MODEL RESPONSE ===\n"
        f"{response}\n\n"
        "=== ASSERTIONS ===\n"
        f"{assertions_block}\n\n"
        "Call `report_scores` now with one entry per assertion, in the order listed."
    )
    return _invoke_judge(client, BEHAVIORAL_JUDGE_SYSTEM, user_text, assertions)


def judge_structural(
    client: Anthropic,
    skill_md: str,
    eval_files: dict[str, str],
    assertions: list[str],
) -> list[JudgeScore]:
    """Score structural assertions the deterministic resolver could not parse."""
    eval_block = "\n".join(
        f"--- {name} ---\n{content}" for name, content in eval_files.items()
    )
    assertions_block = "\n".join(f"{i+1}. {a}" for i, a in enumerate(assertions))
    user_text = (
        "Score the structural assertions against the provided files.\n\n"
        "=== SKILL.md ===\n"
        f"{skill_md}\n\n"
        "=== eval/ FILES ===\n"
        f"{eval_block}\n\n"
        "=== ASSERTIONS ===\n"
        f"{assertions_block}\n\n"
        "Call `report_scores` now with one entry per assertion, in the order listed."
    )
    return _invoke_judge(client, STRUCTURAL_JUDGE_SYSTEM, user_text, assertions)
