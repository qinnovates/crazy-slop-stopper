"""CLI entry point for vibecheck."""

import argparse
import sys
from pathlib import Path

from vibecheck import __version__
from vibecheck.patterns import SEVERITY_ORDER
from vibecheck.scanner import Finding, ScanResult, scan

SEVERITY_COLORS = {
    "critical": "\033[91m",  # red
    "high": "\033[93m",      # yellow
    "medium": "\033[96m",    # cyan
    "low": "\033[37m",       # gray
}
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

CATEGORIES = [
    "security", "error-handling", "typescript", "python", "react",
    "swift", "docker", "ai-llm", "ai-slop", "pseudocode", "visual-slop",
]


def _color(text: str, severity: str) -> str:
    """Colorize text by severity level."""
    code = SEVERITY_COLORS.get(severity, "")
    return f"{code}{text}{RESET}" if code else text


def _print_finding(finding: Finding, *, show_context: bool = False) -> None:
    """Print a single finding."""
    rule = finding.rule
    sev = _color(rule.severity.upper(), rule.severity)
    print(f"  {sev}  {BOLD}{rule.rule_id}{RESET} {rule.name}")
    print(f"       {DIM}{finding.file_path}:{finding.line_number}{RESET}")
    if show_context:
        line = finding.line_content.strip()
        if len(line) > 120:
            line = line[:117] + "..."
        print(f"       {line}")
    if rule.two_pass:
        print(f"       {DIM}(two-pass: requires semantic follow-up){RESET}")
    if rule.co_occurrence:
        print(f"       {DIM}(co-occurrence: {rule.co_occurrence_threshold}+ in same file){RESET}")
    print()


def _print_summary(result: ScanResult) -> None:
    """Print scan summary."""
    print(f"\n{'─' * 60}")
    print(f"  {BOLD}vibecheck{RESET} scan complete")
    print(f"  Rules run: {result.rules_run}")
    print(f"  Findings:  ", end="")

    parts = []
    if result.critical_count:
        parts.append(_color(f"{result.critical_count} critical", "critical"))
    if result.high_count:
        parts.append(_color(f"{result.high_count} high", "high"))
    if result.medium_count:
        parts.append(_color(f"{result.medium_count} medium", "medium"))
    if result.low_count:
        parts.append(_color(f"{result.low_count} low", "low"))

    if parts:
        print(" | ".join(parts))
    else:
        print("\033[92m0 findings\033[0m")

    print(f"{'─' * 60}")

    if result.passed:
        print(f"  \033[92m✓ PASSED{RESET} — no critical or high findings")
    else:
        print(f"  \033[91m✗ FAILED{RESET} — {result.critical_count} critical, {result.high_count} high")
    print()


def _print_json(result: ScanResult) -> None:
    """Print results as JSON."""
    import json

    output = {
        "version": __version__,
        "passed": result.passed,
        "summary": {
            "rules_run": result.rules_run,
            "critical": result.critical_count,
            "high": result.high_count,
            "medium": result.medium_count,
            "low": result.low_count,
        },
        "findings": [
            {
                "rule_id": f.rule.rule_id,
                "name": f.rule.name,
                "severity": f.rule.severity,
                "category": f.rule.category,
                "file": f.file_path,
                "line": f.line_number,
                "content": f.line_content.strip(),
                "notes": f.rule.notes,
                "two_pass": f.rule.two_pass,
                "co_occurrence": f.rule.co_occurrence,
            }
            for f in result.findings
        ],
        "errors": result.errors,
    }
    print(json.dumps(output, indent=2))


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="vibecheck",
        description="Detect AI-generated code before it ships.",
    )
    parser.add_argument(
        "target",
        nargs="?",
        default=".",
        help="Directory to scan (default: current directory)",
    )
    parser.add_argument(
        "--version", action="version", version=f"vibecheck {__version__}",
    )
    parser.add_argument(
        "--severity", "-s",
        choices=["low", "medium", "high", "critical"],
        default="low",
        help="Minimum severity to report (default: low)",
    )
    parser.add_argument(
        "--category", "-c",
        choices=CATEGORIES,
        action="append",
        help="Filter to specific categories (repeatable)",
    )
    parser.add_argument(
        "--context", "-x",
        action="store_true",
        help="Show matching line content",
    )
    parser.add_argument(
        "--json", "-j",
        action="store_true",
        dest="json_output",
        help="Output results as JSON",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 on any finding (not just critical/high)",
    )
    parser.add_argument(
        "--no-two-pass",
        action="store_true",
        help="Skip rules that require semantic follow-up",
    )

    args = parser.parse_args()
    target = Path(args.target).resolve()

    if not target.is_dir():
        print(f"Error: {target} is not a directory", file=sys.stderr)
        sys.exit(2)

    result = scan(
        target,
        categories=args.category,
        severity_min=args.severity,
        exclude_two_pass=args.no_two_pass,
    )

    if result.errors:
        for error in result.errors:
            print(f"Error: {error}", file=sys.stderr)
        sys.exit(2)

    if args.json_output:
        _print_json(result)
    else:
        if result.findings:
            print(f"\n  {BOLD}vibecheck{RESET} — scanning {target}\n")
            for finding in result.findings:
                _print_finding(finding, show_context=args.context)
        _print_summary(result)

    if args.strict and result.findings:
        sys.exit(1)
    elif not result.passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
