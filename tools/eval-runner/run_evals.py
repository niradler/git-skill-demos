"""CLI entry point for the eval harness.

Usage:
    python run_evals.py [--tier structure|behavior|all] <skill-path>...

Each skill directory must contain a `SKILL.md` and an `eval/` subdirectory with:
    - prompts.json     (test prompts, JSON)
    - assertions.md    (binary checklist with `## Structural` and `## Behavioral. <id>` sections)
    - eval.config.yaml (judge + skill-under-test config; optional)

Emits a single JSON document on stdout describing all results, and a
human-readable summary on stderr. Exits 0 only if every requested tier passes
for every skill.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from anthropic import Anthropic

from behavior_check import BehaviorResult, run_behavior
from judge import judge_structural
from structure_check import (
    AssertionResult,
    StructureResult,
    check_structure,
    finalize_structure,
    mark_unresolved_as_failed,
)

TIERS = ("structure", "behavior", "all")


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="run_evals.py",
        description=(
            "Run structure and/or behavior evals against one or more skill "
            "directories using the eval/ format (prompts.json + assertions.md)."
        ),
    )
    parser.add_argument(
        "--tier",
        choices=TIERS,
        default="structure",
        help="Which tier(s) to run. 'all' runs structure then behavior. Default: structure.",
    )
    parser.add_argument(
        "skills",
        nargs="+",
        type=Path,
        help="One or more skill directories (each containing SKILL.md and eval/).",
    )
    return parser.parse_args(argv)


def _read_eval_files(skill_path: Path) -> dict[str, str]:
    """Read every file under eval/ into a {filename: content} map for the judge."""
    eval_dir = skill_path / "eval"
    if not eval_dir.is_dir():
        return {}
    out: dict[str, str] = {}
    for path in sorted(eval_dir.iterdir()):
        if path.is_file():
            try:
                out[path.name] = path.read_text(encoding="utf-8")
            except OSError:
                out[path.name] = "<unreadable>"
    return out


def _resolve_structure_with_judge(
    skill_path: Path,
    structure: StructureResult,
    client: Anthropic | None,
) -> None:
    """If structure_check left assertions unresolved, run the judge fallback."""
    if not structure.judge_pending:
        return
    if client is None:
        mark_unresolved_as_failed(structure)
        return
    eval_files = _read_eval_files(skill_path)
    try:
        scores = judge_structural(
            client=client,
            skill_md=structure.skill_md_raw,
            eval_files=eval_files,
            assertions=structure.judge_pending,
        )
    except Exception as exc:  # noqa: BLE001
        # Surface the failure as one error and mark all pending as failed.
        structure.errors.append(
            f"structural judge invocation failed: {type(exc).__name__}: {exc}"
        )
        mark_unresolved_as_failed(structure)
        return
    finalize_structure(
        structure,
        [
            AssertionResult(
                item=s.item,
                passed=s.passed,
                justification=s.justification,
                resolver="judge",
            )
            for s in scores
        ],
    )
    structure.judge_pending = []


def _summarize(report: dict[str, Any]) -> str:
    lines = [f"Tier: {report['tier']}"]
    for entry in report["skills"]:
        path = entry["path"]
        lines.append(f"\nSkill: {path}")
        struct = entry.get("structure")
        if struct is not None:
            tag = "PASS" if struct["passed"] else "FAIL"
            lines.append(f"  structure: {tag}")
            for a in struct.get("assertions", []):
                mark = "+" if a["passed"] else "-"
                lines.append(f"    [{mark}] ({a['resolver']}) {a['item']}")
            for err in struct.get("errors", []):
                lines.append(f"    ! {err}")
        behavior = entry.get("behavior")
        if behavior is not None:
            tag = "PASS" if behavior["passed"] else "FAIL"
            lines.append(
                f"  behavior:  {tag}  "
                f"score={behavior['skill_score']:.2f} "
                f"threshold={behavior['passing_score']:.2f} "
                f"model={behavior['model']}"
            )
            if behavior.get("error"):
                lines.append(f"    ! {behavior['error']}")
            for p in behavior.get("prompts", []):
                ptag = "PASS" if p["passed"] else "FAIL"
                lines.append(
                    f"    prompt {ptag}  score={p['prompt_score']:.2f}  id={p['prompt_id']}"
                )
                if p.get("error"):
                    lines.append(f"      ! {p['error']}")
                for a in p.get("assertions", []):
                    mark = "+" if a["passed"] else "-"
                    lines.append(f"      [{mark}] {a['item']}")
    overall = "PASS" if report["passed"] else "FAIL"
    lines.append(f"\nOverall: {overall}")
    return "\n".join(lines)


def _build_skill_entry(
    skill_path: Path,
    tier: str,
    client: Anthropic | None,
) -> tuple[dict[str, Any], bool]:
    """Run requested tiers for one skill. Returns (entry, ok)."""
    entry: dict[str, Any] = {"path": str(skill_path)}
    ok = True

    structure: StructureResult | None = None
    if tier in ("structure", "all"):
        structure = check_structure(skill_path)
        _resolve_structure_with_judge(skill_path, structure, client)
        entry["structure"] = structure.to_dict()
        if not structure.passed:
            ok = False

    if tier in ("behavior", "all"):
        if structure is None:
            structure = check_structure(skill_path)
            _resolve_structure_with_judge(skill_path, structure, client)
        if not structure.passed:
            entry["behavior"] = BehaviorResult(
                model="",
                judge_model="",
                passing_score=0.0,
                skill_score=0.0,
                passed=False,
                error="skipped: structure tier failed",
            ).to_dict()
            ok = False
        else:
            assert client is not None  # guarded in main()
            behavior = run_behavior(
                skill_body=structure.skill_body,
                eval_config=structure.eval_config,
                prompts=structure.prompts,
                behavioral_sections=structure.behavioral_sections,
                client=client,
            )
            entry["behavior"] = behavior.to_dict()
            if not behavior.passed:
                ok = False

    return entry, ok


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])

    client: Anthropic | None = None
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if args.tier in ("behavior", "all"):
        if not api_key:
            print(
                "ERROR: ANTHROPIC_API_KEY is required for the behavior tier.",
                file=sys.stderr,
            )
            return 2
        client = Anthropic(api_key=api_key)
    elif api_key:
        # Structure tier can OPTIONALLY use the judge fallback for unrecognized
        # assertions. We instantiate a client only if a key is available.
        client = Anthropic(api_key=api_key)

    report: dict[str, Any] = {"tier": args.tier, "skills": [], "passed": True}
    for skill_path in args.skills:
        entry, ok = _build_skill_entry(skill_path, args.tier, client)
        report["skills"].append(entry)
        if not ok:
            report["passed"] = False

    print(json.dumps(report, indent=2))
    print(_summarize(report), file=sys.stderr)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
